#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FLUFFBALL ARCADE – ein kleines, asset-freies Vektor-Spiel."""

# ---------------------------------------------------------------------------
# Balancing und Darstellung: Diese Werte sind die zentrale Schraubstelle.
# ---------------------------------------------------------------------------
import math
import random
import sys

import pygame
from pygame.math import Vector2

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
BONUS_BALL_CHANCE = 0.20
GLASS_BREAK_SCORE = 75
GOAL_SCORE = 100
BANK_SHOT_BONUS = 50
GLASS_REMAINDER_BONUS = 25
GLASS_MIN_BREAK_CHANCE = 0.08
GLASS_MAX_BREAK_CHANCE = 0.95
GLASS_BREAK_SCALE = 12.0
GLASS_BREAK_OFFSET = 0.20

# Farbcode: Die Flüssigkeitsfarbe verändert den Ball nach dem Bruch.
LIQUID_COLORS = {
    "green": (38, 190, 92),
    "blue": (40, 120, 220),
    "red": (225, 52, 52),
    "yellow": (240, 205, 30),
    "purple": (155, 75, 205),
}
BACKGROUND = (9, 12, 29)
INK = (230, 240, 255)
CYAN = (46, 235, 255)
PINK = (255, 74, 170)
GOLD = (255, 220, 90)

# Leveldaten: Tore sind x, y, Breite, Höhe; Gläser zusätzlich Farbe und Härte.
# Die Härte erhöht die nötige Geschwindigkeit für einen sicheren Bruch.
LEVELS = [
    {
        "goals": [(675, 105, 92, 115)],
        "glasses": [
            (360, 430, 42, 72, "green", 8),
            (530, 315, 35, 62, "yellow", 12),
        ],
        "goal_speed": 0,
    },
    {
        "goals": [(650, 90, 72, 86), (690, 275, 64, 78)],
        "glasses": [
            (300, 400, 36, 65, "blue", 11),
            (440, 275, 32, 55, "red", 15),
            (565, 440, 46, 72, "purple", 9),
        ],
        "goal_speed": 1.25,
    },
    {
        "goals": [(625, 80, 60, 70), (700, 210, 52, 65), (620, 360, 56, 66)],
        "glasses": [
            (270, 350, 32, 58, "green", 10),
            (390, 185, 30, 52, "yellow", 9),
            (500, 420, 36, 62, "blue", 14),
            (560, 250, 28, 48, "purple", 12),
        ],
        "goal_speed": 2.0,
    },
]


def draw_text(screen, font, value, position, color=INK, centered=False):
    """Rendert eine kurze Beschriftung an einer Pixelposition."""
    surface = font.render(str(value), True, color)
    if centered:
        target = surface.get_rect(center=position)
    else:
        target = surface.get_rect(topleft=position)
    screen.blit(surface, target)


def draw_dashed_line(screen, color, start, end, dash=8, gap=7, width=1):
    """Zeichnet die Flugbahn als gut erkennbare gestrichelte Linie."""
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


class Particle:
    """Kleiner Splitter oder Flüssigkeitstropfen für Treffer-Feedback."""

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


class Goal:
    """Ein bewegliches, leuchtendes Tor mit Pfosten und Netzlinien."""

    def __init__(self, data):
        self.base_rect = pygame.Rect(data[:4])
        self.rect = self.base_rect.copy()
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

    def draw_net(self, screen, rect):
        """Das innere Netz besteht aus mehreren sichtbaren Linien."""
        inner = rect.inflate(-18, -20)
        pygame.draw.rect(screen, (5, 10, 20), inner, border_radius=3)
        for x in range(inner.left + 7, inner.right, 10):
            pygame.draw.line(screen, (30, 75, 105), (x, inner.top), (x, inner.bottom), 1)
        for y in range(inner.top + 7, inner.bottom, 10):
            pygame.draw.line(screen, (30, 75, 105), (inner.left, y), (inner.right, y), 1)

    def draw(self, screen, font):
        if not self.alive:
            return
        rect = self.rect
        frame = (24, 35, 65)
        pygame.draw.rect(screen, frame, rect, border_radius=5)
        pygame.draw.rect(screen, CYAN, rect, 3, border_radius=5)
        self.draw_net(screen, rect)
        pygame.draw.line(screen, PINK, (rect.centerx, rect.top + 8), (rect.centerx, rect.bottom - 8), 2)
        pygame.draw.line(screen, GOLD, rect.topleft, (rect.left, rect.bottom), 2)
        pygame.draw.line(screen, GOLD, rect.topright, (rect.right, rect.bottom), 2)
        pygame.draw.arc(screen, GOLD, rect.inflate(7, 7), math.pi, math.tau, 2)
        draw_text(screen, font, "GOAL", (rect.centerx, rect.bottom + 5), GOLD, True)


class Glass:
    """Zerbrechliches Glas mit Füllstand, Rand, Lichtreflex und CLINK-Zustand."""

    def __init__(self, data):
        x, y, width, height, color_name, hardness = data
        self.rect = pygame.Rect(x, y, width, height)
        self.color_name = color_name
        self.hardness = hardness
        self.alive = True
        self.shake_frames = 0

    def update(self):
        self.shake_frames = max(0, self.shake_frames - 1)

    def hit(self):
        """Markiert einen harten Treffer, der noch nicht gebrochen hat."""
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
        fill_rect = pygame.Rect(rect.x + 3, rect.bottom - fill_height - 3, rect.width - 6, fill_height)
        pygame.draw.rect(screen, liquid, fill_rect, border_radius=2)
        pygame.draw.rect(screen, glass_edge, rect, 2, border_radius=4)
        pygame.draw.line(screen, (245, 255, 255), (rect.left + 6, rect.top + 6), (rect.left + 6, rect.bottom - 12), 2)
        pygame.draw.arc(screen, (210, 235, 255), rect.inflate(4, 3), 0, math.pi, 2)
        draw_text(screen, font, self.color_name.upper(), (rect.centerx, rect.bottom + 4), (190, 220, 240), True)
        if self.shake_frames:
            draw_text(screen, font, "CLINK!", (rect.centerx, rect.top - 18), GOLD, True)


class Player:
    """Hamster-Kanone: Bewegung, Winkel und vollständig gezeichnetes Sprite."""

    def __init__(self):
        self.position = Vector2(105, 510)
        self.angle = -38.0
        self.variant = 0
        self.colors = [(245, 145, 48), (70, 170, 245), (245, 95, 170)]

    def update(self, keys):
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

    def draw_whiskers(self, screen, center):
        for side in (-1, 1):
            start = (center[0] + side * 8, center[1] + 5)
            pygame.draw.line(screen, (255, 245, 220), start, (center[0] + side * 32, center[1] - 2), 1)
            pygame.draw.line(screen, (255, 245, 220), start, (center[0] + side * 33, center[1] + 8), 1)

    def draw(self, screen):
        center = (int(self.position.x), int(self.position.y))
        color = self.colors[self.variant]
        # Schweif und Ohren machen die Figur auch aus der Entfernung lesbar.
        pygame.draw.arc(screen, (245, 200, 100), pygame.Rect(center[0] - 35, center[1] - 13, 30, 30), math.pi / 2, math.pi * 1.7, 5)
        left_ear = [(center[0] - 22, center[1] - 26), (center[0] - 30, center[1] - 52), (center[0] - 7, center[1] - 38)]
        right_ear = [(center[0] + 22, center[1] - 26), (center[0] + 30, center[1] - 52), (center[0] + 7, center[1] - 38)]
        pygame.draw.polygon(screen, color, left_ear)
        pygame.draw.polygon(screen, color, right_ear)
        pygame.draw.circle(screen, color, center, 27)
        pygame.draw.circle(screen, (255, 220, 175), (center[0], center[1] + 7), 16)
        pygame.draw.circle(screen, (20, 20, 30), (center[0] - 10, center[1] - 5), 4)
        pygame.draw.circle(screen, (20, 20, 30), (center[0] + 10, center[1] - 5), 4)
        pygame.draw.circle(screen, (30, 18, 25), (center[0], center[1] + 5), 4)
        self.draw_whiskers(screen, center)
        muzzle = self.muzzle_position()
        pygame.draw.line(screen, (150, 175, 205), center, muzzle, 9)
        pygame.draw.line(screen, (255, 230, 120), center, muzzle, 3)


class Ball:
    """Der Ball fliegt geradlinig; nur Spielfeldränder erzeugen Bank-Shots."""

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


class Game:
    """Verwaltet Zustände, Regeln, Levelwechsel und die Hauptschleife."""

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("FLUFFBALL ARCADE")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        self.big_font = pygame.font.Font(None, 42)
        self.title_font = pygame.font.Font(None, 30)
        self.running = True
        self.state = "play"
        self.score = 0
        self.level_index = 0
        self.balls = MAX_BALLS
        self.ball = None
        self.power = 0.0
        self.charging = False
        self.particles = []
        self.message = ""
        self.message_time = 0
        self.player = Player()
        self.load_level()

    def load_level(self):
        data = LEVELS[self.level_index]
        self.goals = [Goal(item) for item in data["goals"]]
        self.glasses = [Glass(item) for item in data["glasses"]]
        self.ball = None
        self.power = 0.0
        self.charging = False

    def reset(self):
        self.score = 0
        self.level_index = 0
        self.balls = MAX_BALLS
        self.state = "play"
        self.message = ""
        self.message_time = 0
        self.load_level()

    def fire(self):
        if self.ball is None and self.balls > 0:
            self.balls -= 1
            self.ball = Ball(self.player.muzzle_position(), self.player.angle, self.power)
            self.power = 0.0

    def burst(self, position, color, amount=12, kind="shard"):
        for _ in range(amount):
            self.particles.append(Particle(position, color, kind))

    def add_message(self, message, duration):
        self.message = message
        self.message_time = duration

    def apply_liquid_effect(self, ball, color_name):
        # Jede Farbe ist bewusst ein eigener, leicht testbarer Regelpfad.
        if color_name == "blue":
            ball.velocity *= 0.75
        elif color_name == "red":
            ball.velocity *= 0.45
        elif color_name == "yellow":
            ball.velocity *= 1.25
        elif color_name == "purple":
            if random.random() < 0.5:
                ball.velocity *= 0.55
            else:
                self.balls += 1

    def hit_goal(self, ball):
        for goal in self.goals:
            if goal.contains(ball.position):
                goal.alive = False
                self.score += GOAL_SCORE
                if ball.banks:
                    self.score += BANK_SHOT_BONUS
                    self.add_message("BANK-SHOT +50", 70)
                else:
                    self.add_message("GOAL!", 70)
                self.burst(ball.position, CYAN, 16)
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
                    self.score += GLASS_BREAK_SCORE
                    self.burst(ball.position, (190, 230, 250), 16, "shard")
                    self.burst(ball.position, LIQUID_COLORS[glass.color_name], 10, "drop")
                    if random.random() < BONUS_BALL_CHANCE:
                        self.balls += 1
                        self.add_message("BONUSBALL +1", 80)
                    self.apply_liquid_effect(ball, glass.color_name)
                else:
                    glass.hit()
                    self.add_message("CLINK!", 50)
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
                self.score += remaining * GLASS_REMAINDER_BONUS
                self.add_message("LEVEL CLEAR!", 110)
                self.state = "clear"
            elif self.balls <= 0:
                self.state = "gameover"

    def update_particles(self):
        for particle in self.particles:
            particle.update()
        self.particles = [particle for particle in self.particles if particle.life > 0]

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
        if self.ball is not None:
            self.ball.update()
            self.collision()
            self.finish_shot()
        self.update_particles()
        self.message_time = max(0, self.message_time - 1)

    def update_clear(self):
        self.update_particles()
        self.message_time = max(0, self.message_time - 1)
        if self.message_time == 0:
            if self.level_index < len(LEVELS) - 1:
                self.level_index += 1
                self.load_level()
                self.state = "play"
            else:
                self.state = "win"

    def update(self):
        if self.state == "play":
            self.update_play()
        elif self.state == "clear":
            self.update_clear()

    def draw_hud(self):
        draw_text(self.screen, self.title_font, "FLUFFBALL ARCADE", (24, 18), CYAN)
        draw_text(self.screen, self.font, f"SCORE {self.score:05d}", (260, 21))
        draw_text(self.screen, self.font, f"LEVEL {self.level_index + 1}/3", (430, 21), PINK)
        draw_text(self.screen, self.font, f"BALLS {self.balls}", (590, 21), GOLD)

    def draw_overlay(self):
        if self.message_time:
            draw_text(self.screen, self.big_font, self.message, (SCREEN_WIDTH // 2, 75), GOLD, True)
        if self.state in ("gameover", "win"):
            pygame.draw.rect(self.screen, (8, 10, 25), (180, 210, 440, 145))
            title = "YOU WIN!" if self.state == "win" else "GAME OVER"
            color = CYAN if self.state == "win" else PINK
            draw_text(self.screen, self.big_font, title, (400, 250), color, True)
            draw_text(self.screen, self.font, "R = Neustart    ESC = Ende", (400, 305), INK, True)

    def draw(self):
        self.screen.fill(BACKGROUND)
        pygame.draw.rect(self.screen, (18, 25, 52), (10, 64, SCREEN_WIDTH - 20, SCREEN_HEIGHT - 74), 2)
        self.draw_hud()
        for goal in self.goals:
            goal.draw(self.screen, self.font)
        for glass in self.glasses:
            glass.draw(self.screen, self.font)
        if self.ball is None and self.state == "play":
            direction = self.player.direction()
            draw_dashed_line(self.screen, (65, 90, 125), self.player.muzzle_position(), self.player.muzzle_position() + direction * 600, 6, 8)
        self.player.draw(self.screen)
        if self.ball is not None:
            self.ball.draw(self.screen)
        for particle in self.particles:
            particle.draw(self.screen)
        pygame.draw.rect(self.screen, (30, 35, 60), (24, 555, 210, 20), 2)
        pygame.draw.rect(self.screen, PINK, (27, 558, int(204 * self.power), 14))
        draw_text(self.screen, self.font, "POWER", (242, 555))
        draw_text(self.screen, self.font, "←/→ MOVE   ↑/↓ ANGLE   SPACE CHARGE/FIRE   R RESET   ESC QUIT", (275, 558), (150, 165, 195))
        self.draw_overlay()
        pygame.display.flip()

    def events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_r:
                    self.reset()
                elif event.key == pygame.K_SPACE and self.state == "play" and self.ball is None:
                    self.charging = True
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
    """Startpunkt für den normalen Desktop-Aufruf."""
    Game().run()


if __name__ == "__main__":
    main()
