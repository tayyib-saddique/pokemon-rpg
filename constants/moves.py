from projectiles.bubble_beam import BubbleBeam
from projectiles.flamethrower import Flamethrower
from projectiles.ember import Ember

MOVE_CLASSES = {
    "bubble_beam": BubbleBeam,
    "flamethrower": Flamethrower,
    "ember": Ember,
}

POKEMON_MOVES = {
    "totodile": {"shoot": ["bubble_beam"], "strike": "slash"},
    "charmander": {"shoot": ["ember", "flamethrower"], "strike": "slash"},
}
