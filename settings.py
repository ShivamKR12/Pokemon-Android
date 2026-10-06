import pygame
from pygame.math import Vector2 as vector 
from sys import exit


pygame.init()
info = pygame.display.Info()
WINDOW_WIDTH, WINDOW_HEIGHT = info.current_w, info.current_h
pygame.quit()

TILE_SIZE = 64 
ANIMATION_SPEED = 6
BATTLE_OUTLINE_WIDTH = 4

# Magic Numbers
DEFENSE_DIVISOR = 2000
DEFENDING_DAMAGE_REDUCTION = 0.2
MONSTER_PATCH_Y_OFFSET = 40
EVOLUTION_STAR_SPEED = 20
EVOLUTION_TINT_SPEED = 80

TYPE_MULTIPLIERS = {
    'fire': {'plant': 2.0, 'water': 0.5},
    'water': {'fire': 2.0, 'plant': 0.5},
    'plant': {'water': 2.0, 'fire': 0.5}
}

COLORS = {
	'white': '#f4fefa', 
	'pure white': '#ffffff',
	'dark': '#2b292c',
	'light': '#c8c8c8',
	'gray': '#3a373b',
	'gold': '#ffd700',
	'light-gray': '#4b484d',
	'fire':'#f8a060',
	'water':'#50b0d8',
	'plant': '#64a990', 
	'black': '#000000', 
	'red': '#f03131',
	'blue': '#66d7ee',
	'normal': '#ffffff',
	'dark white': '#f0f0f0'
}

WORLD_LAYERS = {
	'water': 0,
	'bg': 1,
	'shadow': 2,
	'main': 3,
	'top': 4
}

BATTLE_POSITIONS = {
    'left': {
        'top': (WINDOW_WIDTH * 0.28, WINDOW_HEIGHT * 0.36),
        'center': (WINDOW_WIDTH * 0.15, WINDOW_HEIGHT * 0.55),
        'bottom': (WINDOW_WIDTH * 0.32, WINDOW_HEIGHT * 0.72)},
    'right': {
        'top': (WINDOW_WIDTH * 0.7, WINDOW_HEIGHT * 0.36),
        'center': (WINDOW_WIDTH * 0.87, WINDOW_HEIGHT * 0.54),
        'bottom': (WINDOW_WIDTH * 0.7, WINDOW_HEIGHT * 0.76)}
}

BATTLE_LAYERS =  {
	'outline': 0,
	'name': 1,
	'monster': 2,
	'effects': 3,
	'overlay': 4
}

BATTLE_CHOICES = {
	'full': {
		'fight':  {'pos' : vector(WINDOW_WIDTH * 0.023, -WINDOW_HEIGHT * 0.083), 'icon': 'sword'},
		'defend': {'pos' : vector(WINDOW_WIDTH * 0.031, -WINDOW_HEIGHT * 0.027), 'icon': 'shield'},
		'switch': {'pos' : vector(WINDOW_WIDTH * 0.031,  WINDOW_HEIGHT * 0.027), 'icon': 'arrows'},
		'catch':  {'pos' : vector(WINDOW_WIDTH * 0.023,  WINDOW_HEIGHT * 0.083), 'icon': 'hand'},
		'exit':   {'pos' : vector(WINDOW_WIDTH * 0.023,  WINDOW_HEIGHT * 0.138), 'icon': 'exit'}},
	
	'limited': {
		'fight':  {'pos' : vector(WINDOW_WIDTH * 0.023, -WINDOW_HEIGHT * 0.055), 'icon': 'sword'},
		'defend': {'pos' : vector(WINDOW_WIDTH * 0.031,  0), 'icon': 'shield'},
		'switch': {'pos' : vector(WINDOW_WIDTH * 0.023,  WINDOW_HEIGHT * 0.055), 'icon': 'arrows'},
		'exit':   {'pos' : vector(WINDOW_WIDTH * 0.023,  WINDOW_HEIGHT * 0.111), 'icon': 'exit'}}
}
