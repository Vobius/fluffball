#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FLUFFYs – ein kleines, asset-freies Vektor-Arcade-Spiel. V0.3"""

import math
import os
import random

import pygame
from pygame.math import Vector2
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

# ----------------------------------------------------------------------------
# Konstanten
# ----------------------------------------------------------------------------

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60
PLAYFIELD_TOP = 72

BALL_RADIUS = 10
BALL_MIN_SPEED = 5.0
BALL_MAX_CHARGE_BONUS = 8.0
CHARGE_RATE = 0.015
PLAYER_TURN_SPEED = 1.0
PLAYER_MOVE_SPEED = 4.0
MAX_BALLS = 3

GOAL_SCORE = 100
BANK_SHOT_BONUS = 50
GLASS_BREAK_SCORE = -40          # Gläser zerschießen kostet jetzt Punkte
GLASS_BONUS_SCORE = 30           # ... es sei denn, ein Bonusball war drin
GLASS_REMAINDER_BONUS = 25       # Belohnung für heil gebliebene Gläser
BONUS_BALL_CHANCE = 0.25
SAMPLE_RATE = 22050
BPM = 103
BEAT = 60.0 / BPM

DEATH_PENALTY = -50
SPILL_LIFETIME = 210

GLASS_MIN_BREAK_CHANCE = 0.08
GLASS_MAX_BREAK_CHANCE = 0.95
GLASS_BREAK_SCALE = 12.0
GLASS_BREAK_OFFSET = 0.20

HIGHSCORE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "fluffys_highscore.txt"
)

LIQUID_COLORS = {
    "green": (38, 190, 92),
    "blue": (40, 120, 220),
    "red": (225, 52, 52),
    "yellow": (240, 205, 30),
    "purple": (155, 75, 205),
}

# Bewegungstempo der Gläser je Farbe
GLASS_SPEEDS = {
    "yellow": 2.6,
    "green": 1.8,
    "blue": 1.1,
    "red": 0.6,
    "purple": 2.0,
}

BACKGROUND = (9, 12, 29)
INK = (230, 240, 255)
CYAN = (46, 235, 255)
PINK = (255, 74, 170)
GOLD = (255, 220, 90)
GREEN_SCORE = (120, 245, 150)
RED_SCORE = (255, 95, 105)

# Spielbare Fluffy-Farbvarianten
FLUFFY_SKINS = [
    {
        "name": "SKY",
        "body": (150, 200, 240),
        "shade": (115, 168, 215),
        "belly": (238, 246, 252),
        "tail": (130, 185, 235),
        "tail_tip": (185, 222, 248),
    },
    {
        "name": "LILAC",
        "body": (185, 165, 230),
        "shade": (150, 128, 200),
        "belly": (240, 238, 250),
        "tail": (168, 120, 225),
        "tail_tip": (210, 180, 245),
    },
    {
        "name": "SNOW",
        "body": (245, 243, 246),
        "shade": (208, 208, 218),
        "belly": (255, 255, 255),
        "tail": (130, 190, 235),
        "tail_tip": (190, 225, 250),
    },
    {
        "name": "SUNNY",
        "body": (250, 165, 80),
        "shade": (215, 128, 55),
        "belly": (252, 244, 234),
        "tail": (230, 60, 60),
        "tail_tip": (255, 130, 110),
    },
]

# Leveldaten: Tore fest, Gläser werden pro Level zufällig generiert.
LEVELS = [
    {
        "goals": [(675, 105, 92, 115, "big")],
        "goal_speed": 0,
        "glass_count": 4,
        "colors": ["green", "blue"],
        "hardness": (7.0, 9.0),
    },
    {
        "goals": [(650, 90, 72, 86, "big"), (690, 275, 64, 78, "small")],
        "goal_speed": 1.25,
        "glass_count": 6,
        "colors": ["blue", "green", "yellow"],
        "hardness": (8.0, 12.0),
    },
    {
        "goals": [
            (625, 80, 60, 70, "small"),
            (700, 210, 52, 65, "small"),
            (620, 360, 56, 66, "big"),
        ],
        "goal_speed": 2.0,
        "glass_count": 8,
        "colors": ["green", "yellow", "blue", "purple", "red"],
        "hardness": (9.0, 15.0),
    },
]


# ----------------------------------------------------------------------------
# Hilfsfunktionen
# ----------------------------------------------------------------------------

def draw_text(screen, font, value, position, color=INK, centered=False):
    surface = font.render(str(value), True, color)
    if centered:
        target = surface.get_rect(center=position)
    else:
        target = surface.get_rect(topleft=position)
    screen.blit(surface, target)


def draw_dashed_line(screen, color, start, end, dash=8, gap=7, width=1):
    first = Vector2(start)
    second = Vector2(end)
    direction = second - first
    length = direction.length()
    if length == 0:
        return
    unit = direction / length
    offset = 0.0
    while offset < length:
        dash_end = min(offset + dash, length)
        pygame.draw.line(screen, color, first + unit * offset, first + unit * dash_end, width)
        offset += dash + gap


# ----------------------------------------------------------------------------
# Sound: alles prozedural, keine Dateien
# ----------------------------------------------------------------------------

NOTE_FREQ = {
    "C#3": 138.59, "E3": 164.81, "F#3": 185.00, "G#3": 207.65, "B3": 246.94,
    "C#4": 277.18, "D#4": 311.13, "E4": 329.63, "F#4": 369.99, "G#4": 415.30,
    "A#4": 466.16, "B4": 493.88, "C#5": 554.37, "D#5": 622.25, "E5": 659.26,
    "F#5": 739.99, "G#5": 830.61,
}


def square_wave(freq, duration, volume=0.25, duty=0.5):
    """Rechteckwelle mit weichem Ein-/Ausblenden gegen Klickgeräusche."""
    n = int(SAMPLE_RATE * duration)
    if n <= 0:
        return np.zeros(0, dtype=np.float32)
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    phase = (t * freq) % 1.0
    wave = np.where(phase < duty, 1.0, -1.0).astype(np.float32) * volume
    edge = max(1, int(SAMPLE_RATE * 0.004))
    if n > edge * 2:
        wave[:edge] *= np.linspace(0, 1, edge)
        wave[-edge:] *= np.linspace(1, 0, edge)
    return wave


def saw_wave(freq, duration, volume=0.2):
    n = int(SAMPLE_RATE * duration)
    if n <= 0:
        return np.zeros(0, dtype=np.float32)
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    wave = (2.0 * ((t * freq) % 1.0) - 1.0).astype(np.float32) * volume
    edge = max(1, int(SAMPLE_RATE * 0.006))
    if n > edge * 2:
        wave[:edge] *= np.linspace(0, 1, edge)
        wave[-edge:] *= np.linspace(1, 0, edge)
    return wave


def noise_burst(duration, volume=0.3, decay=True):
    n = int(SAMPLE_RATE * duration)
    if n <= 0:
        return np.zeros(0, dtype=np.float32)
    wave = (np.random.uniform(-1, 1, n).astype(np.float32)) * volume
    if decay:
        wave *= np.linspace(1.0, 0.0, n) ** 2
    return wave


def kick_drum(duration=0.12, volume=0.5):
    n = int(SAMPLE_RATE * duration)
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    freq = 110.0 * np.exp(-t * 28.0) + 42.0
    phase = np.cumsum(2 * np.pi * freq / SAMPLE_RATE)
    wave = np.sin(phase).astype(np.float32) * volume
    wave *= np.exp(-t * 13.0)
    return wave


def sweep(start_freq, end_freq, duration, volume=0.3):
    n = int(SAMPLE_RATE * duration)
    if n <= 0:
        return np.zeros(0, dtype=np.float32)
    t = np.arange(n, dtype=np.float32) / SAMPLE_RATE
    freq = np.linspace(start_freq, end_freq, n)
    phase = np.cumsum(2 * np.pi * freq / SAMPLE_RATE)
    wave = np.sign(np.sin(phase)).astype(np.float32) * volume
    wave *= np.linspace(1.0, 0.0, n) ** 0.6
    return wave


def to_sound(mono):
    """Float-Array in ein pygame.Sound-Objekt umwandeln (stereo, int16)."""
    mono = np.clip(mono, -1.0, 1.0)
    data = (mono * 32767).astype(np.int16)
    stereo = np.ascontiguousarray(np.column_stack((data, data)))
    return pygame.sndarray.make_sound(stereo)


def mix_into(target, source, offset_samples):
    """Quelle additiv an Position in Ziel mischen."""
    start = int(offset_samples)
    end = min(len(target), start + len(source))
    if start >= len(target) or end <= start:
        return
    target[start:end] += source[: end - start]


def build_music_loop():
    """Vier Takte G#m - F# - Emaj7 - C#m als Chiptune-Loop."""
    bars = [
        {"bass": "G#3", "arp": ["B4", "D#5", "G#5"], "pad": ["G#3", "B3", "D#4"]},
        {"bass": "F#3", "arp": ["A#4", "D#5", "F#5"], "pad": ["F#3", "A#4", "C#4"]},
        {"bass": "E3",  "arp": ["B4", "D#5", "G#5"], "pad": ["E3", "G#3", "B3"]},
        {"bass": "C#3", "arp": ["G#4", "C#5", "E5"], "pad": ["C#3", "E3", "G#3"]},
    ]
    bar_time = BEAT * 4
    total = np.zeros(int(SAMPLE_RATE * bar_time * len(bars)) + SAMPLE_RATE, dtype=np.float32)
    sixteenth = BEAT / 4.0

    for bar_index, bar in enumerate(bars):
        bar_start = bar_index * bar_time

        # Pad: liegender Akkord, leise im Hintergrund
        for note in bar["pad"]:
            pad = saw_wave(NOTE_FREQ[note], bar_time * 0.95, 0.045)
            # grobes Sidechain-Ducking im Viertelraster
            for beat in range(4):
                pos = int(SAMPLE_RATE * beat * BEAT)
                dip = int(SAMPLE_RATE * 0.16)
                if pos + dip < len(pad):
                    pad[pos:pos + dip] *= np.linspace(0.25, 1.0, dip)
            mix_into(total, pad, SAMPLE_RATE * bar_start)

        # Bass: Achtel, warm und tief
        for step in range(8):
            pos = bar_start + step * (BEAT / 2)
            mix_into(total, square_wave(NOTE_FREQ[bar["bass"]], BEAT * 0.4, 0.16, 0.25),
                     SAMPLE_RATE * pos)

        # Arpeggio: durchgehende 16tel
        for step in range(16):
            note = bar["arp"][step % len(bar["arp"])]
            pos = bar_start + step * sixteenth
            mix_into(total, square_wave(NOTE_FREQ[note], sixteenth * 0.85, 0.085, 0.5),
                     SAMPLE_RATE * pos)

        # Kick auf allen Vierteln
        for beat in range(4):
            mix_into(total, kick_drum(), SAMPLE_RATE * (bar_start + beat * BEAT))

        # Clap auf 2 und 4
        for beat in (1, 3):
            mix_into(total, noise_burst(0.09, 0.16), SAMPLE_RATE * (bar_start + beat * BEAT))

        # HiHats auf Achteln
        for step in range(8):
            pos = bar_start + step * (BEAT / 2) + BEAT / 4
            mix_into(total, noise_burst(0.025, 0.05), SAMPLE_RATE * pos)

    return to_sound(total[:int(SAMPLE_RATE * bar_time * len(bars))])


class SoundEngine:
    def __init__(self):
        self.enabled = False
        self.music = None
        self.effects = {}
        self.music_on = True
        if not HAS_NUMPY:
            return
        try:
            pygame.mixer.pre_init(SAMPLE_RATE, -16, 2, 512)
            pygame.mixer.init(SAMPLE_RATE, -16, 2, 512)
            pygame.mixer.set_num_channels(16)
        except pygame.error:
            return
        try:
            self.build_effects()
            self.music = build_music_loop()
            self.music.set_volume(0.45)
            self.enabled = True
        except Exception:
            self.enabled = False

    def build_effects(self):
        self.effects["shoot"] = to_sound(sweep(760, 210, 0.13, 0.28))
        self.effects["clink"] = to_sound(
            np.concatenate([
                square_wave(1560, 0.035, 0.22),
                square_wave(2100, 0.045, 0.15),
            ])
        )
        self.effects["break"] = to_sound(
            np.concatenate([
                noise_burst(0.06, 0.38),
                noise_burst(0.11, 0.24),
                square_wave(2400, 0.04, 0.12),
            ])
        )
        goal = np.zeros(int(SAMPLE_RATE * 0.45), dtype=np.float32)
        for i, note in enumerate(["C#5", "E5", "G#5", "C#5"]):
            mix_into(goal, square_wave(NOTE_FREQ[note] * (2 if i == 3 else 1), 0.11, 0.26),
                     SAMPLE_RATE * i * 0.09)
        self.effects["goal"] = to_sound(goal)
        self.effects["death"] = to_sound(
            np.concatenate([
                sweep(600, 90, 0.4, 0.3),
                noise_burst(0.18, 0.16),
            ])
        )
        self.effects["drip"] = to_sound(sweep(1300, 480, 0.09, 0.16))
        bonus = np.zeros(int(SAMPLE_RATE * 0.4), dtype=np.float32)
        for i, note in enumerate(["G#4", "C#5", "E5", "G#5"]):
            mix_into(bonus, square_wave(NOTE_FREQ[note], 0.09, 0.24), SAMPLE_RATE * i * 0.075)
        self.effects["bonus"] = to_sound(bonus)
        self.effects["charge"] = to_sound(sweep(180, 620, 0.7, 0.14))
        self.effects["select"] = to_sound(square_wave(880, 0.05, 0.2))

    def play(self, name):
        if self.enabled and name in self.effects:
            self.effects[name].play()

    def start_music(self):
        if self.enabled and self.music and self.music_on:
            self.music.play(loops=-1)

    def stop_music(self):
        if self.enabled and self.music:
            self.music.stop()

    def toggle_music(self):
        self.music_on = not self.music_on
        if self.music_on:
            self.start_music()
        else:
            self.stop_music()


# ----------------------------------------------------------------------------
# Effekte
# ----------------------------------------------------------------------------

class Particle:
    def __init__(self, position, color, kind="shard"):
        self.position = Vector2(position)
        self.velocity = Vector2(random.uniform(-3, 3), random.uniform(-4, 1))
        self.color = color
        self.life = random.randint(25, 55)
        self.kind = kind
        self.size = random.randint(2, 5)

    def update(self):
        self.position += self.velocity
        self.velocity.y += 0.12
        self.life -= 1

    def draw(self, screen):
        if self.life <= 0:
            return
        point = (int(self.position.x), int(self.position.y))
        if self.kind == "drop":
            pygame.draw.circle(screen, self.color, point, self.size)
        else:
            tail = self.position - self.velocity * 2
            pygame.draw.line(screen, self.color, self.position, tail, 2)


class ScorePopup:
    """Punktzahl, die an Ort und Stelle von klein nach groß wächst."""

    def __init__(self, position, value, extra=""):
        self.position = Vector2(position)
        self.value = value
        self.extra = extra
        self.life = 55
        self.max_life = 55

    def update(self):
        self.life -= 1
        self.position.y -= 0.55

    def draw(self, screen):
        if self.life <= 0:
            return
        progress = 1.0 - (self.life / self.max_life)
        if progress < 0.35:
            scale = progress / 0.35
        else:
            scale = 1.0 - (progress - 0.35) * 0.25
        size = int(14 + 26 * max(0.0, min(1.0, scale)))
        if size < 8:
            return
        alpha = 255 if self.life > 18 else int(255 * self.life / 18)
        color = GREEN_SCORE if self.value >= 0 else RED_SCORE
        sign = "+" if self.value >= 0 else ""
        label = f"{sign}{self.value}"
        if self.extra:
            label += f" {self.extra}"
        font = pygame.font.Font(None, size)
        text = font.render(label, True, color)
        text.set_alpha(alpha)
        shadow = font.render(label, True, (0, 0, 0))
        shadow.set_alpha(alpha // 2)
        rect = text.get_rect(center=(int(self.position.x), int(self.position.y)))
        screen.blit(shadow, (rect.x + 2, rect.y + 2))
        screen.blit(text, rect)

class Spill:
    """Flüssigkeit, die aus einem zerbrochenen Glas nach unten läuft."""

    def __init__(self, x, y, color, sounds=None):
        self.x = float(x)
        self.top = float(y)
        self.color = color
        self.length = 0.0
        self.speed = random.uniform(2.4, 3.6)
        self.life = SPILL_LIFETIME
        self.width = random.randint(5, 9)
        self.landed = False
        self.puddle_width = 0.0
        self.drops = []
        self.sounds = sounds
        self.drip_timer = 0

    @property
    def bottom(self):
        return self.top + self.length

    def update(self, floor_y):
        self.life -= 1
        if not self.landed:
            self.length += self.speed
            if self.bottom >= floor_y:
                self.length = floor_y - self.top
                self.landed = True
                if self.sounds:
                    self.sounds.play("drip")
        else:
            self.puddle_width = min(46.0, self.puddle_width + 1.1)
        self.drip_timer += 1
        if self.drip_timer % 14 == 0 and self.life > 40:
            self.drops.append([self.x + random.uniform(-3, 3), self.top + self.length * 0.5,
                               random.uniform(2.0, 3.5)])
        for drop in self.drops:
            drop[1] += drop[2]
        self.drops = [d for d in self.drops if d[1] < floor_y]

    def hits(self, point, radius=26):
        """Trifft der Strahl oder die Pfütze diesen Punkt?"""
        if abs(point[0] - self.x) > radius:
            return False
        return self.top <= point[1] <= self.bottom + 12

    def draw(self, screen):
        if self.life <= 0:
            return
        alpha = 1.0 if self.life > 60 else self.life / 60.0
        color = tuple(int(c * alpha) for c in self.color)
        pygame.draw.line(screen, color, (self.x, self.top),
                         (self.x, self.bottom), self.width)
        pygame.draw.circle(screen, color, (int(self.x), int(self.bottom)),
                           self.width // 2 + 2)
        for drop in self.drops:
            pygame.draw.circle(screen, color, (int(drop[0]), int(drop[1])), 3)
        if self.landed and self.puddle_width > 2:
            puddle = pygame.Rect(0, 0, int(self.puddle_width), 9)
            puddle.center = (int(self.x), int(self.bottom + 3))
            pygame.draw.ellipse(screen, color, puddle)

# ----------------------------------------------------------------------------
# Spielobjekte
# ----------------------------------------------------------------------------

class Goal:
    """Bewegliches Tor: 'big' = Fußballtor mit Netz, 'small' = Basketballkorb."""

    def __init__(self, data):
        x, y, width, height, goal_type = data
        self.base_rect = pygame.Rect(x, y, width, height)
        self.rect = self.base_rect.copy()
        self.goal_type = goal_type
        self.alive = True
        self.animation_time = 0.0

    def update(self, movement_speed):
        self.animation_time += movement_speed
        if movement_speed != 0:
            wave = math.sin(self.animation_time / 22) * 18
            self.rect.y = self.base_rect.y + int(wave)
        else:
            self.rect.y = self.base_rect.y

    def contains(self, position):
        return self.alive and self.rect.collidepoint(position.x, position.y)

    def draw_big_goal(self, surface, rect):
        post_color = (245, 245, 250)
        net_color = (90, 100, 130)
        step = 10
        for gx in range(rect.left, rect.right, step):
            pygame.draw.line(surface, net_color, (gx, rect.top), (gx, rect.bottom), 1)
        for gy in range(rect.top, rect.bottom, step):
            pygame.draw.line(surface, net_color, (rect.left, gy), (rect.right, gy), 1)
        pygame.draw.rect(surface, post_color, rect, 4)

    def draw_small_goal(self, surface, rect):
        ring_color = (255, 140, 40)
        net_color = (230, 230, 235)
        center_top = (rect.centerx, rect.top + 6)
        ring_radius = rect.width // 2
        pygame.draw.ellipse(
            surface,
            ring_color,
            (center_top[0] - ring_radius, center_top[1] - 4, ring_radius * 2, 8),
            3,
        )
        net_points = []
        segments = 6
        for i in range(segments + 1):
            t = i / segments
            x = center_top[0] - ring_radius + t * ring_radius * 2
            y = center_top[1] + 4 + math.sin(t * math.pi) * (rect.height - 14)
            net_points.append((x, y))
        if len(net_points) > 1:
            pygame.draw.lines(surface, net_color, False, net_points, 2)

    def draw(self, screen, font):
        if not self.alive:
            return
        rect = self.rect
        pygame.draw.rect(screen, CYAN, rect, 1, border_radius=5)
        if self.goal_type == "big":
            self.draw_big_goal(screen, rect)
        else:
            self.draw_small_goal(screen, rect)


class Glass:
    """Zerbrechliches, wanderndes Glas mit Füllstand und CLINK-Zustand."""

    def __init__(self, color_name, x, y, width, height, hardness):
        self.rect = pygame.Rect(int(x), int(y), width, height)
        self.color_name = color_name
        self.hardness = hardness
        self.alive = True
        self.shake_frames = 0
        self.has_bonus = random.random() < BONUS_BALL_CHANCE
        self.start_y = float(y)
        self.pos_y = float(y)
        self.speed = GLASS_SPEEDS[color_name] * random.choice((1, -1))
        self.range = random.randint(45, 120)

    def update(self):
        self.shake_frames = max(0, self.shake_frames - 1)
        if not self.alive:
            return
        # Lila ist unberechenbar und wechselt spontan die Richtung
        if self.color_name == "purple" and random.random() < 0.012:
            self.speed = -self.speed
        self.pos_y += self.speed
        low = self.start_y - self.range
        high = self.start_y + self.range
        if self.pos_y < low or self.pos_y > high:
            self.speed = -self.speed
            self.pos_y = max(low, min(high, self.pos_y))
        self.pos_y = max(PLAYFIELD_TOP + 20, min(SCREEN_HEIGHT - 120, self.pos_y))
        self.rect.y = int(self.pos_y)

    def hit(self):
        self.shake_frames = 35

    def break_glass(self):
        self.alive = False

    def draw(self, screen, font):
        if not self.alive:
            return
        horizontal_shift = random.randint(-2, 2) if self.shake_frames else 0
        rect = self.rect.move(horizontal_shift, 0)
        liquid = LIQUID_COLORS[self.color_name]
        glass_edge = (155, 205, 225)
        pygame.draw.rect(screen, (40, 65, 85), rect, border_radius=4)
        fill_height = max(10, rect.height // 4)
        fill_rect = pygame.Rect(
            rect.x + 3, rect.bottom - fill_height - 3, rect.width - 6, fill_height
        )
        pygame.draw.rect(screen, liquid, fill_rect, border_radius=2)
        pygame.draw.rect(screen, glass_edge, rect, 2, border_radius=4)
        pygame.draw.line(
            screen,
            (245, 255, 255),
            (rect.left + 6, rect.top + 6),
            (rect.left + 6, rect.bottom - 12),
            2,
        )
        if self.shake_frames:
            draw_text(screen, font, "CLINK!", (rect.centerx, rect.top - 18), GOLD, True)


def generate_glasses(level_data):
    """Erzeugt Gläser an zufälligen Positionen mit Mindestabstand."""
    glasses = []
    attempts = 0
    while len(glasses) < level_data["glass_count"] and attempts < 500:
        attempts += 1
        width = random.randint(30, 42)
        height = random.randint(52, 72)
        x = random.randint(250, 560)
        y = random.randint(PLAYFIELD_TOP + 40, SCREEN_HEIGHT - 190)
        candidate = pygame.Rect(x, y, width, height).inflate(40, 130)
        if any(candidate.colliderect(g.rect.inflate(40, 130)) for g in glasses):
            continue
        color = random.choice(level_data["colors"])
        hardness = random.uniform(*level_data["hardness"])
        glasses.append(Glass(color, x, y, width, height, hardness))
    return glasses


class Player:
    """Fluffy-Kanone: Bewegung, Winkel und vollständig gezeichnetes Sprite."""

    def __init__(self, skin_index=0):
        self.position = Vector2(105, 510)
        self.angle = -38.0
        self.skin = FLUFFY_SKINS[skin_index % len(FLUFFY_SKINS)]
        self.shock = 0
        self.dead = 0
        self.bob = 0.0

    def set_skin(self, index):
        self.skin = FLUFFY_SKINS[index % len(FLUFFY_SKINS)]

    def update(self, keys):
        self.bob += 0.08
        if self.dead > 0:
            self.dead -= 1
            return
        if self.shock > 0:
            self.shock -= 1
            return
        if keys[pygame.K_LEFT]:
            self.position.x = max(45, self.position.x - PLAYER_MOVE_SPEED)
        if keys[pygame.K_RIGHT]:
            self.position.x = min(300, self.position.x + PLAYER_MOVE_SPEED)
        if keys[pygame.K_UP]:
            self.angle = min(-8, self.angle + PLAYER_TURN_SPEED)
        if keys[pygame.K_DOWN]:
            self.angle = max(-78, self.angle - PLAYER_TURN_SPEED)

    def direction(self):
        radians = math.radians(self.angle)
        return Vector2(math.cos(radians), math.sin(radians))

    def muzzle_position(self):
        return self.position + self.direction() * 36

    def scare(self, frames=90):
        self.shock = frames

    def draw(self, screen, show_cannon=True):
        skin = self.skin
        cx = int(self.position.x)
        cy = int(self.position.y + math.sin(self.bob) * 1.5)

        # Puschelschwanz aus vielen kleinen Kreisen (Fell-Look)
        tail_cx = cx - 32
        tail_cy = cy - 14
        state = random.getstate()
        random.seed(7)
        for _ in range(28):
            angle = random.uniform(0, math.tau)
            dist = random.uniform(0, 16)
            px = tail_cx + math.cos(angle) * dist
            py = tail_cy + math.sin(angle) * dist * 1.15
            radius = random.randint(4, 8)
            color = skin["tail_tip"] if dist > 8 else skin["tail"]
            pygame.draw.circle(screen, color, (int(px), int(py)), radius)
        random.setstate(state)

        # Ohren
        for side in (-1, 1):
            ox = cx + side * 11
            oy = cy - 20
            pygame.draw.polygon(
                screen, skin["body"],
                [(ox - 7, oy + 10), (ox + 7, oy + 10), (ox + side * 2, oy - 6)],
            )
            pygame.draw.polygon(
                screen, (250, 180, 200),
                [(ox - 4, oy + 9), (ox + 4, oy + 9), (ox + side * 1, oy)],
            )

        # Körper: liegende Ellipse
        body_rect = pygame.Rect(0, 0, 64, 46)
        body_rect.center = (cx, cy)
        pygame.draw.ellipse(screen, skin["shade"], body_rect.inflate(3, 3))
        pygame.draw.ellipse(screen, skin["body"], body_rect)

        # Weißer Bauch
        belly = pygame.Rect(0, 0, 52, 21)
        belly.center = (cx + 3, cy + 14)
        pygame.draw.ellipse(screen, skin["belly"], belly)

        # Wange
        pygame.draw.circle(screen, (255, 190, 205), (cx + 21, cy + 4), 6)

        self.draw_face(screen, cx, cy)

        if show_cannon:
            muzzle = self.muzzle_position()
            pygame.draw.line(screen, (150, 175, 205), (cx, cy), muzzle, 9)
            pygame.draw.line(screen, (255, 230, 120), (cx, cy), muzzle, 3)

    def draw_face(self, screen, cx, cy):
        if self.dead > 0:
            for ex in (cx + 6, cx + 22):
                pygame.draw.line(screen, (30, 25, 35), (ex - 6, cy - 9), (ex + 6, cy + 3), 3)
                pygame.draw.line(screen, (30, 25, 35), (ex + 6, cy - 9), (ex - 6, cy + 3), 3)
            pygame.draw.ellipse(screen, (230, 110, 140), (cx + 11, cy + 5, 7, 12))
            return
        if self.shock > 0:
            for ex in (cx + 6, cx + 22):
                pygame.draw.line(screen, (25, 25, 35), (ex - 5, cy - 8), (ex + 5, cy + 2), 3)
                pygame.draw.line(screen, (25, 25, 35), (ex + 5, cy - 8), (ex - 5, cy + 2), 3)
            pygame.draw.ellipse(screen, (200, 90, 110), (cx + 10, cy + 6, 10, 8))
            return

        # Große glänzende Augen
        for ex in (cx + 6, cx + 22):
            pygame.draw.circle(screen, (20, 18, 26), (ex, cy - 3), 7)
            pygame.draw.circle(screen, (255, 255, 255), (ex + 2, cy - 6), 3)
            pygame.draw.circle(screen, (255, 255, 255), (ex - 2, cy - 1), 1)

        # Rosa Dreiecksnase
        nx, ny = cx + 14, cy + 5
        pygame.draw.polygon(
            screen, (245, 130, 165),
            [(nx - 4, ny - 2), (nx + 4, ny - 2), (nx, ny + 3)],
        )

        # Mund aus zwei kleinen Bögen
        pygame.draw.arc(screen, (60, 50, 60), (nx - 8, ny + 1, 8, 7), math.pi, math.tau, 2)
        pygame.draw.arc(screen, (60, 50, 60), (nx, ny + 1, 8, 7), math.pi, math.tau, 2)

    def kill(self, frames=100):
        self.dead = frames
        self.shock = 0


class Ball:
    def __init__(self, position, angle, charge):
        radians = math.radians(angle)
        speed = BALL_MIN_SPEED + charge * BALL_MAX_CHARGE_BONUS
        self.position = Vector2(position)
        self.velocity = Vector2(math.cos(radians), math.sin(radians)) * speed
        self.radius = BALL_RADIUS
        self.banks = 0
        self.alive = True

    def update(self):
        self.position += self.velocity
        if self.position.x < 15 or self.position.x > SCREEN_WIDTH - 15:
            self.velocity.x *= -1
            self.position.x = max(15, min(SCREEN_WIDTH - 15, self.position.x))
            self.banks += 1
        if self.position.y < PLAYFIELD_TOP:
            self.velocity.y *= -1
            self.position.y = PLAYFIELD_TOP
            self.banks += 1
        if self.position.y > SCREEN_HEIGHT + 30:
            self.alive = False

    def draw(self, screen):
        point = (int(self.position.x), int(self.position.y))
        pygame.draw.circle(screen, (255, 248, 190), point, self.radius)
        pygame.draw.circle(screen, (255, 255, 255), (point[0] - 3, point[1] - 3), 3)


# ----------------------------------------------------------------------------
# Spiel
# ----------------------------------------------------------------------------

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("FLUFFYs")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        self.big_font = pygame.font.Font(None, 42)
        self.title_font = pygame.font.Font(None, 30)
        self.logo_font = pygame.font.Font(None, 96)
        self.running = True
        self.state = "menu"
        self.skin_index = 0
        self.highscore = self.load_highscore()
        self.score = 0
        self.level_index = 0
        self.balls = MAX_BALLS
        self.ball = None
        self.power = 0.0
        self.charging = False
        self.particles = []
        self.popups = []
        self.message = ""
        self.message_time = 0
        self.menu_timer = 0.0
        self.player = Player(self.skin_index)
        self.sounds = SoundEngine()
        self.spills = []
        self.respawn_timer = 0
        self.load_level()
        self.sounds.start_music()

    # ---------- Highscore ----------

    def load_highscore(self):
        try:
            with open(HIGHSCORE_FILE, "r") as handle:
                return int(handle.read().strip())
        except Exception:
            return 0

    def save_highscore(self):
        if self.score > self.highscore:
            self.highscore = self.score
            try:
                with open(HIGHSCORE_FILE, "w") as handle:
                    handle.write(str(self.highscore))
            except Exception:
                pass

    # ---------- Level ----------

    def load_level(self):
        data = LEVELS[self.level_index]
        self.goals = [Goal(item) for item in data["goals"]]
        self.glasses = generate_glasses(data)
        self.ball = None
        self.power = 0.0
        self.charging = False
        self.balls = MAX_BALLS
        self.spills = []
        self.respawn_timer = 0
        self.player.dead = 0
        self.player.shock = 0

    def start_game(self):
        self.score = 0
        self.level_index = 0
        self.particles = []
        self.popups = []
        self.message = ""
        self.message_time = 0
        self.player = Player(self.skin_index)
        self.load_level()
        self.state = "play"

    # ---------- Effekte ----------

    def burst(self, position, color, amount=12, kind="shard"):
        for _ in range(amount):
            self.particles.append(Particle(position, color, kind))

    def add_popup(self, position, value, extra=""):
        self.popups.append(ScorePopup(position, value, extra))
        self.score += value

    def add_message(self, message, duration):
        self.message = message
        self.message_time = duration

    def fire(self):
        if self.balls <= 0:
            self.add_message("KEINE BAELLE MEHR", 60)
            self.power = 0.0
            return
        if self.ball is None:
            self.balls -= 1
            self.ball = Ball(self.player.muzzle_position(), self.player.angle, self.power)
            self.sounds.play("shoot")
            self.power = 0.0

    def apply_liquid_effect(self, ball, color_name):
        if color_name == "blue":
            ball.velocity *= 0.75
        elif color_name == "red":
            ball.velocity *= 0.45
        elif color_name == "yellow":
            ball.velocity *= 1.25
        elif color_name == "purple":
            ball.velocity *= random.choice((0.55, 1.35))

    # ---------- Kollisionen ----------

    def hit_goal(self, ball):
        for goal in self.goals:
            if goal.contains(ball.position):
                goal.alive = False
                value = GOAL_SCORE
                extra = ""
                if ball.banks:
                    value += BANK_SHOT_BONUS
                    extra = "BANK!"
                self.add_popup(ball.position, value, extra)
                self.add_message("GOAL!", 70)
                self.burst(ball.position, CYAN, 16)
                self.sounds.play("goal")
                ball.alive = False
                return True
        return False

    def hit_glass(self, ball):
        for glass in self.glasses:
            if glass.alive and glass.rect.collidepoint(ball.position.x, ball.position.y):
                speed = ball.velocity.length()
                chance = (speed - glass.hardness) / GLASS_BREAK_SCALE + GLASS_BREAK_OFFSET
                chance = min(GLASS_MAX_BREAK_CHANCE, max(GLASS_MIN_BREAK_CHANCE, chance))
                if random.random() < chance:
                    glass.break_glass()
                    self.burst(ball.position, (190, 230, 250), 16, "shard")
                    self.burst(ball.position, LIQUID_COLORS[glass.color_name], 10, "drop")
                    self.sounds.play("break")
                    self.spills.append(
                        Spill(glass.rect.centerx, glass.rect.bottom,
                              LIQUID_COLORS[glass.color_name], self.sounds)
                    )
                    if glass.has_bonus:
                        self.balls += 1
                        self.add_popup(glass.rect.center, GLASS_BONUS_SCORE, "+BALL")
                        self.add_message("BONUSBALL!", 80)
                        self.sounds.play("bonus")
                    else:
                        self.add_popup(glass.rect.center, GLASS_BREAK_SCORE)
                        self.add_message("SCHERBEN!", 60)
                    self.apply_liquid_effect(ball, glass.color_name)
                else:
                    glass.hit()
                    self.add_message("CLINK!", 50)
                    self.sounds.play("clink")
                return True
        return False

    def collision(self):
        if self.ball is None:
            return
        if self.hit_goal(self.ball):
            return
        self.hit_glass(self.ball)

    def finish_shot(self):
        if self.ball is not None and not self.ball.alive:
            self.ball = None
            if not any(goal.alive for goal in self.goals):
                remaining = sum(1 for glass in self.glasses if glass.alive)
                if remaining:
                    self.add_popup(
                        (SCREEN_WIDTH // 2, 220),
                        remaining * GLASS_REMAINDER_BONUS,
                        "HEIL!",
                    )
                self.add_message("LEVEL CLEAR!", 110)
                self.state = "clear"
            elif self.balls <= 0:
                self.save_highscore()
                self.state = "gameover"

    # ---------- Updates ----------

    def update_effects(self):
        for particle in self.particles:
            particle.update()
        self.particles = [p for p in self.particles if p.life > 0]
        for popup in self.popups:
            popup.update()
        self.popups = [p for p in self.popups if p.life > 0]
        self.message_time = max(0, self.message_time - 1)

    def update_play(self):
        keys = pygame.key.get_pressed()
        self.player.update(keys)
        if self.charging:
            self.power = min(1.0, self.power + CHARGE_RATE)
        movement = LEVELS[self.level_index]["goal_speed"]
        for goal in self.goals:
            goal.update(movement)
        for glass in self.glasses:
            glass.update()
        self.update_spills()
        self.check_spill_hits()

        if self.respawn_timer > 0:
            self.respawn_timer -= 1
            if self.respawn_timer == 0:
                if self.balls <= 0:
                    self.save_highscore()
                    self.state = "gameover"
                else:
                    self.player.position = Vector2(105, 510)
                    self.player.dead = 0

        if self.ball is not None:
            self.ball.update()
            self.collision()
            self.finish_shot()
        self.update_effects()


    def check_spill_hits(self):
        if self.player.dead > 0 or self.player.shock > 0:
            return
        point = (self.player.position.x, self.player.position.y)
        for spill in self.spills:
            if spill.hits(point):
                self.player.kill()
                self.burst(self.player.position, spill.color, 14, "drop")
                self.sounds.play("death")
                break

    def update_clear(self):
        self.update_effects()
        if self.message_time == 0:
            if self.level_index < len(LEVELS) - 1:
                self.level_index += 1
                self.load_level()
                self.state = "play"
            else:
                self.save_highscore()
                self.state = "win"

    def update(self):
        if self.state == "play":
            self.update_play()
        elif self.state == "clear":
            self.update_clear()
        elif self.state == "menu":
            self.menu_timer += 0.05

    def update_spills(self):
        floor_y = SCREEN_HEIGHT - 74  # oder deine tatsächliche Bodenlinie
        for spill in self.spills:
            spill.update(floor_y)
        self.spills = [s for s in self.spills if s.life > 0]

    # ---------- Startscreen ----------

    def draw_logo(self, cx, cy):
        text = "FLUFFYs"
        for offset, color in ((6, (40, 20, 70)), (4, (120, 40, 130)), (2, (200, 70, 160))):
            surface = self.logo_font.render(text, True, color)
            self.screen.blit(surface, surface.get_rect(center=(cx + offset, cy + offset)))
        surface = self.logo_font.render(text, True, (255, 235, 250))
        rect = surface.get_rect(center=(cx, cy))
        self.screen.blit(surface, rect)
        pygame.draw.line(
            self.screen, CYAN, (rect.left, rect.bottom + 4), (rect.right, rect.bottom + 4), 3
        )

    def draw_menu(self):
        self.screen.fill(BACKGROUND)

        state = random.getstate()
        random.seed(3)
        for _ in range(70):
            x = random.randint(0, SCREEN_WIDTH)
            y = random.randint(0, SCREEN_HEIGHT)
            brightness = random.randint(60, 160)
            pygame.draw.circle(self.screen, (brightness, brightness, brightness + 30), (x, y), 1)
        random.setstate(state)

        bob = math.sin(self.menu_timer) * 6
        self.draw_logo(SCREEN_WIDTH // 2, int(110 + bob))
        draw_text(self.screen, self.font, "WAEHLE DEIN FLUFFY", (SCREEN_WIDTH // 2, 200), CYAN, True)

        spacing = 160
        start_x = SCREEN_WIDTH // 2 - spacing * (len(FLUFFY_SKINS) - 1) // 2
        for i, skin in enumerate(FLUFFY_SKINS):
            x = start_x + i * spacing
            y = 310
            selected = i == self.skin_index
            if selected:
                pygame.draw.rect(self.screen, PINK, (x - 62, y - 56, 124, 112), 3, border_radius=10)
                pygame.draw.rect(self.screen, (25, 30, 60), (x - 58, y - 52, 116, 104), border_radius=8)
            preview = Player(i)
            preview.position = Vector2(x + 10, y + (bob * 0.4 if selected else 0))
            preview.bob = 0.0
            preview.draw(self.screen, show_cannon=False)
            color = GOLD if selected else (130, 145, 180)
            draw_text(self.screen, self.font, skin["name"], (x, y + 66), color, True)

        draw_text(
            self.screen, self.font,
            "PFEIL LINKS/RECHTS = AUSWAHL    ENTER = START    ESC = ENDE",
            (SCREEN_WIDTH // 2, 430), INK, True,
        )
        draw_text(
            self.screen, self.big_font, f"HIGHSCORE  {self.highscore:05d}",
            (SCREEN_WIDTH // 2, 495), GOLD, True,
        )
        draw_text(
            self.screen, self.font, "Triff die Tore - schone die Glaeser!",
            (SCREEN_WIDTH // 2, 550), (150, 165, 195), True,
        )

    # ---------- Spiel zeichnen ----------

    def draw_hud(self):
        draw_text(self.screen, self.title_font, "FLUFFYs", (24, 18), CYAN)
        draw_text(self.screen, self.font, f"SCORE {self.score:05d}", (170, 21))
        draw_text(self.screen, self.font, f"HI {self.highscore:05d}", (320, 21), GOLD)
        draw_text(self.screen, self.font, f"LEVEL {self.level_index + 1}/{len(LEVELS)}", (450, 21), PINK)
        draw_text(self.screen, self.font, f"BALLS {self.balls}", (610, 21), GOLD)

    def draw_overlay(self):
        if self.message_time:
            draw_text(self.screen, self.big_font, self.message, (SCREEN_WIDTH // 2, 75), GOLD, True)
        if self.state in ("gameover", "win"):
            pygame.draw.rect(self.screen, (8, 10, 25), (180, 200, 440, 175))
            pygame.draw.rect(self.screen, CYAN, (180, 200, 440, 175), 2)
            title = "YOU WIN!" if self.state == "win" else "GAME OVER"
            color = CYAN if self.state == "win" else PINK
            draw_text(self.screen, self.big_font, title, (400, 240), color, True)
            draw_text(self.screen, self.font, f"SCORE {self.score:05d}", (400, 285), INK, True)
            if self.score >= self.highscore and self.score > 0:
                draw_text(self.screen, self.font, "NEUER HIGHSCORE!", (400, 312), GOLD, True)
            draw_text(self.screen, self.font, "ENTER = Menue    ESC = Ende", (400, 348), INK, True)

    def draw_play(self):
        self.screen.fill(BACKGROUND)
        pygame.draw.rect(self.screen, (18, 25, 52), (10, 64, SCREEN_WIDTH - 20, SCREEN_HEIGHT - 74), 2)
        self.draw_hud()
        for goal in self.goals:
            goal.draw(self.screen, self.font)
        for glass in self.glasses:
            glass.draw(self.screen, self.font)
        for spill in self.spills:
            spill.draw(self.screen)
        if self.ball is None and self.state == "play":
            direction = self.player.direction()
            muzzle = self.player.muzzle_position()
            draw_dashed_line(self.screen, (65, 90, 125), muzzle, muzzle + direction * 600, 6, 8)
        self.player.draw(self.screen)
        if self.ball is not None:
            self.ball.draw(self.screen)
        for particle in self.particles:
            particle.draw(self.screen)
        for popup in self.popups:
            popup.draw(self.screen)
        pygame.draw.rect(self.screen, (30, 35, 60), (24, 555, 210, 20), 2)
        pygame.draw.rect(self.screen, PINK, (27, 558, int(204 * self.power), 14))
        draw_text(self.screen, self.font, "POWER", (242, 555))
        draw_text(
            self.screen, self.font,
            "PFEILE = ZIELEN   SPACE = SCHUSS   M = MUSIK   R = MENUE   ESC = ENDE",
            (310, 558), (150, 165, 195),
        )
        self.draw_overlay()

    def draw(self):
        if self.state == "menu":
            self.draw_menu()
        else:
            self.draw_play()
        pygame.display.flip()

    # ---------- Events ----------

    def events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif self.state == "menu":
                    if event.key == pygame.K_LEFT:
                        self.skin_index = (self.skin_index - 1) % len(FLUFFY_SKINS)
                    elif event.key == pygame.K_RIGHT:
                        self.skin_index = (self.skin_index + 1) % len(FLUFFY_SKINS)
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                        self.start_game()
                elif self.state in ("gameover", "win"):
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        self.state = "menu"
                elif self.state == "play":
                    if event.key == pygame.K_r:
                        self.save_highscore()
                        self.state = "menu"
                    elif event.key == pygame.K_SPACE and self.ball is None and self.player.dead == 0:
                        self.charging = True
                        self.sounds.play("charge")
                    elif event.key == pygame.K_m:
                        self.sounds.toggle_music()
            elif event.type == pygame.KEYUP and event.key == pygame.K_SPACE:
                if self.charging:
                    self.charging = False
                    self.fire()

    def run(self):
        while self.running:
            self.events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()


def main():
    Game().run()


if __name__ == "__main__":
    main()
