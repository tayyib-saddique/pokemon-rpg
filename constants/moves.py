from projectiles.bubble_beam import BubbleBeam
from projectiles.flamethrower import Flamethrower
from projectiles.ember import Ember

MOVE_CLASSES = {
    'bubble_beam': BubbleBeam,
    'flamethrower': Flamethrower,
    'ember': Ember,
}

POKEMON_MOVES = {
    'totodile': {
        'shoot': ['bubble_beam'],
        'strike': 'slash'
        },
    'charmander': {
        'shoot': ['ember', 'flamethrower'],
        'strike': 'slash'
        },
}

SPAWN_OFFSETS = {
    'charmander': {'right': (-3, -15), 'left': (3, -15), 'up': (0, -10), 'down': (0, 5)},
    'totodile':   {'right': (8,  -3), 'left': (-8,  -3), 'up': (0, -8),  'down': (0, 3)},
}