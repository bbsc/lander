#!/usr/bin/env python3

import pygame
import random
import click
import copy
import math
import time
import sys
import os
 

ICON = 'lander_icon.gif'
ICON_FILE = os.path.join(os.path.dirname(__file__), ICON)
FONT = 'fonts/ShareTechMono-Regular.ttf'
FONT_FILE = os.path.join(os.path.dirname(__file__), FONT)
WINDOW_CAPTION = 'Lunar Lander, (c) 1973'
XDIM = 1024
YDIM = 768
WINDOW_SIZE = (XDIM, YDIM)
WHITE = (255, 255, 255)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GRAVITY = 0.05
FUEL = 100

# TODO:
#   - detect collisions with terrain
#   - support successful landing as collision type
#   - move terrain under ship/zoom out instead of bouncing off top of screen
#   - add sounds:
#       - thrust, louder per level
#       - random beeps, announcements from houston, etc
#       - astronaut/mission control interrupts
#       - "one small step for a woman" sound bite upon successful landing
#       - handle signals to kill full screen


class Terrain(object):

    def __init__(self, where, xdim, ydim, landing_zones=2):
        # TODO:
        #   - handle different places with different gravity
        #     and terrain dynamics
        #   - dynamically calculate new terrain as ship moves
        #     across surface
        self.type = where
        self.terrain = None
        self.landing_zones = landing_zones
        self.xdim = xdim
        self.ydim = ydim

    def get_terrain(self):
        ''' return current terrain, generating
        '''
        if self.terrain is None:
            self._gen_terrain()
        return self.terrain

    def _gen_terrain(self):
        ''' randomly generate terrain
            - always provide at least 2 landable (horizontally level) surfaces
        '''
        terrain_points = []
        tx = 0
        ty = self.ydim * 0.85
        lastx = 100
        lasty = ty
        flat_segments = [random.randint(10, self.xdim), random.randint(10, self.xdim)]
        flat_segments.sort()
        next_flat_segment = flat_segments.pop(0)
        while True:
            if ty < self.ydim:
                ty += 100
            if ty > self.ydim:
                ty -= 100
            terrain_points.append((tx, ty))
            tx += random.randint(40,100)
            ty += random.randint(-100,100)
            if next_flat_segment < tx:
                ty = lasty
                try:
                    next_flat_segment = flat_segments.pop(0)
                except IndexError:
                    next_flat_segment = sys.maxsize
            if tx > self.xdim:
                tx = self.xdim
                terrain_points.append((tx, ty))
                break
            lasty = ty

        self.terrain = terrain_points

    def check_collision(self, shape):
        ''' determine if something is colliding with terrain
        '''
        pass

    def check_land(self, shape):
        ''' determine if collision is a crash or successful landing
        '''
        pass


class Lander(object):
    SHIP_SIZE = (41,120)

    THRUST_MAP = {
        0: 0,
        1: GRAVITY * 0.9,
        2: GRAVITY * 2.0,
        3: GRAVITY * 5.0,
        4: GRAVITY * 10.0,
    }

    SHIP_POINTS = [
        # top
        (10,45),
        (30,45),
        # right side
        (40,65),
        # bottom to right leg
        (30,65),
        # right leg
        (35,75),
        (30,65),
        # bottom to left leg
        (10,65),
        # left leg
        (5,75),
        (10,65),
        # bottom to left side
        (0,65)
    ]
    
    SM_JET_POINTS = [
        (15, 65),
        (20, 75),
        (25, 65),
    ]

    MED_JET_POINTS = [
        (15, 65),
        (20, 90),
        (25, 65),
    ]

    BIG_JET_POINTS = [
        (15, 65),
        (20, 110),
        (25, 65),
    ]

    MAX_JET_POINTS = [
        (12, 65),
        (20, 120),
        (28, 65),
    ]

    LEFT_JET_POINTS = [
        (10,65),
        (0,75),
        (5,65),
    ]

    RIGHT_JET_POINTS = [
        (30,65),
        (40,75),
        (35,65),
    ]
    def __init__(self, xdim, ydim):
        ''' initialize variables controlling ship movement
        '''
        self.current_surface = pygame.Surface(self.SHIP_SIZE)
        self.shipx = 250
        self.shipy = 150
        self.xspeed = 0
        self.yspeed = 0
        self.thrust = 0
        self.thrust_level = 0
        self.degree = 0
        self.degree_change = 0
        self.fuel = FUEL
        self.thrust_fuel_burn = 0
        self.spin_fuel_burn = 0
        self.xdim = xdim
        self.ydim = ydim
        self.pause = False

    def get_position(self):
        ''' returns coordinates of ship
        '''
        # shouldn't need to do it this way, will fix later
        # using the returned object to place the ship takes the upper-left
        # coordinates, not the coordinates of .center
        rot_rec =  self.current_surface.get_rect()
        rot_rec.center = (self.shipx, self.shipy)
        return rot_rec

    def update_telemetry(self):
        ''' housekeeping ship calculations
            - ship speed in x and y dimentions considering
            - absolute speed
            - update ship surface with current location, rotation, and jets
            - fuel consumption
        '''
        self.current_surface = self._get_ship_surface()
        self.thrust = self.THRUST_MAP[self.thrust_level]

        if self.fuel <= 0:
            self.thrust = 0

        # pygame degree positions:
        #    0 = up
        #   90 = left
        #  180 = down
        #  270 = right
        self.degree += self.degree_change
        if self.degree > 360:
            self.degree -= 360
        if self.degree < 0:
            self.degree += 360
    
        # maths to calculate thurst level in x and y directions based on engine
        # thrust and degrees ship is pointed
        degree_adjust = self.degree
        degree_adjust += 90
        if degree_adjust >= 360:
            degree_adjust -= 360
        radians = float("{0:.3f}".format(math.radians(degree_adjust)))
        x_thrust_multiplier = float("{0:.3f}".format(math.cos(radians)))
        y_thrust_multiplier = float("{0:.3f}".format(math.sin(-radians)))

        # increase speed based on thrust level
        self.xspeed += self.thrust * x_thrust_multiplier
        self.yspeed += self.thrust * y_thrust_multiplier

        # gravity always increases speed in y dimention
        self.yspeed += GRAVITY

        # bounce back with diminished speed if ship passes a screen edge
        if self.shipy > self.ydim and self.yspeed > 0:
            self.yspeed = (self.yspeed * 0.7) * -1
            self.xspeed *= 0.7
            self.degree_change *= 0.5
        if self.shipy < 0 and self.yspeed < 0:
            self.yspeed = (self.yspeed * 0.7) * -1
            self.xspeed *= 0.7
            self.degree_change *= 0.5
        if self.shipx > self.xdim and self.xspeed > 0:
            self.xspeed = (self.xspeed * 0.7) * -1
            self.yspeed *= 0.7
            self.degree_change *= 0.5
        if self.shipx < 0 and self.xspeed < 0:
            self.xspeed = (self.xspeed * 0.7) * -1
            self.yspeed *= 0.7
            self.degree_change *= 0.5

        # calculate absoluted speed vector (for speed indicator)
        self.speed = math.sqrt(self.xspeed**2 + self.yspeed**2)

        # ship x,y coordinates
        self.shipx += self.xspeed
        self.shipy += self.yspeed
    
        # update fuel reserves
        self.fuel = self.fuel - self.thrust_fuel_burn - self.spin_fuel_burn
        if self.fuel < 0:
            self.fuel = 0

        self.current_surface =  pygame.transform.rotate(self.current_surface, self.degree)

    def thrust_up(self):
        self.thrust_fuel_burn += 0.05
        self.thrust_level += 1
        if self.thrust_level > 4:
            self.thrust_level = 0
            self.thrust_fuel_burn = 0

    def thrust_down(self):
        self.thrust_level -= 1
        self.thrust_fuel_burn -= 0.05
        if self.thrust_level < 0:
            self.thrust_level = 0
            self.thrust_fuel_burn = 0

    def spin_left(self):
        if self.fuel > 0:
            self.degree_change = 5
            self.spin_fuel_burn = 0.001

    def spin_right(self):
        if self.fuel > 0:
            self.degree_change = -5
            self.spin_fuel_burn = 0.001

    def spin_stop(self):
        if self.fuel > 0:
            self.degree_change = 0
            self.spin_fuel_burn = 0

    def _get_ship_surface(self):
        ''' starts with blank jet surface, layeres on other jet surface according
            to thrust level, overlay ship last so jets are underneath
            
            returns finished ship surface
        '''
        # build base ship surgace
        base_surface = pygame.Surface(self.SHIP_SIZE)
        base_surface.fill(BLACK)
        base_surface.set_colorkey(BLACK)
    
        # ship shape
        ship_surface = pygame.Surface(self.SHIP_SIZE)
        ship_surface.fill(BLACK)
        ship_surface.set_colorkey(BLACK)
        pygame.draw.polygon(ship_surface, WHITE, self.SHIP_POINTS, 1)
 
        # variable jet size
        jet_surface = pygame.Surface(self.SHIP_SIZE)
        jet_surface.fill(BLACK)
        jet_surface.set_colorkey(BLACK)

        if self.fuel > 0:
            if self.thrust_level > 0:
                pygame.draw.polygon(jet_surface, WHITE, self.SM_JET_POINTS, 1)
            if self.thrust_level > 1:
                pygame.draw.polygon(jet_surface, WHITE, self.MED_JET_POINTS, 1)
            if self.thrust_level > 2:
                pygame.draw.polygon(jet_surface, WHITE, self.BIG_JET_POINTS, 1)
            if self.thrust_level > 3:
                pygame.draw.polygon(jet_surface, WHITE, self.MAX_JET_POINTS, 1)
            if self.degree_change < 0:
                pygame.draw.polygon(jet_surface, WHITE, self.LEFT_JET_POINTS, 1)
            if self.degree_change > 0:
                pygame.draw.polygon(jet_surface, WHITE, self.RIGHT_JET_POINTS, 1)

        jet_surface.blit(ship_surface, (0,0))
        base_surface.blit(jet_surface, (0,0))
        return base_surface


@click.command()
@click.option('--window', is_flag=True, help='Run In Window Mode')
@click.option('--nobg', is_flag=True, help='No background image')
def main(window, nobg):
    ''' Clone of 70's game Lunar Lander 
    '''
    pygame.init()
    pygame.mouse.set_visible(False)

    if window is True:
        screen = pygame.display.set_mode(WINDOW_SIZE)
        xdim = XDIM
        ydim = YDIM
    else:
        screen = pygame.display.set_mode((0,0), pygame.FULLSCREEN)
        video_info = pygame.display.Info()
        xdim = video_info.current_w
        ydim = video_info.current_h

    icon = pygame.image.load(ICON_FILE)
    pygame.display.set_icon(icon)

    BACKGROUND = 'lunar_surface.gif'
    BACKGROUND_FILE = os.path.join(os.path.dirname(__file__), BACKGROUND)
    bg = pygame.image.load(BACKGROUND_FILE)
    bg = pygame.transform.scale(bg, (xdim, ydim))

    pygame.display.set_caption(WINDOW_CAPTION)
    font = pygame.font.Font(FONT_FILE, 20)
 
    lander = Lander(xdim, ydim)
    terrain = Terrain("moon", xdim, ydim)

    clock = pygame.time.Clock()

    while True:
        if lander.pause is True:
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_p:
                        lander.pause = False
                        break
            time.sleep(0.1)
            continue

        if nobg is True:
            screen.fill(BLACK)
        else:
            screen.blit(bg, (0,0))
     

        # draw moon terrain
        pygame.draw.lines(screen, WHITE, False, terrain.get_terrain(), 2)

        # handle inputs
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    lander.thrust_up()
                if event.key == pygame.K_DOWN:
                    lander.thrust_down()
                if event.key == pygame.K_LEFT:
                    lander.spin_left()
                if event.key == pygame.K_RIGHT:
                    lander.spin_right()
                if event.key == pygame.K_ESCAPE:
                    pygame.display.quit()
                    sys.exit(0)
                if event.key == pygame.K_r:
                    lander.fuel += 10
                if event.key == pygame.K_l:
                    lander.degree = 0
                if event.key == pygame.K_p:
                    if lander.pause is True:
                        lander.pause = False
                    else:
                        lander.pause = True
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_LEFT:
                    lander.spin_stop()
                if event.key == pygame.K_RIGHT:
                    lander.spin_stop()
            if event.type == pygame.QUIT:
                pygame.display.quit()

        lander.update_telemetry()
        screen.blit(lander.current_surface, lander.get_position())

        msg = 'Fuel: {:.1f}%  Speed: {:.1f} m/s'.format(lander.fuel, lander.speed)
        text = font.render(msg, True, WHITE)
        textpos = text.get_rect()
        textpos.centerx = screen.get_rect().centerx
        screen.blit(text, textpos)

        clock.tick(30)  # Max fps
        pygame.display.flip()


if __name__ == '__main__':
    main()
