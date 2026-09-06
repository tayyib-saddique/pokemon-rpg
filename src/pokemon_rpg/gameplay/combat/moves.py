from pokemon_rpg.gameplay.combat.projectiles.bubble_beam import BubbleBeam
from pokemon_rpg.gameplay.combat.projectiles.ember import Ember
from pokemon_rpg.gameplay.combat.projectiles.flamethrower import Flamethrower

MOVE_CLASSES = {
    "bubble_beam": BubbleBeam,
    "flamethrower": Flamethrower,
    "ember": Ember,
}

POKEMON_MOVES = {
    "totodile": {"shoot": ["bubble_beam"], "strike": "slash"},
    "charmander": {"shoot": ["ember", "flamethrower"], "strike": "slash"},
}
