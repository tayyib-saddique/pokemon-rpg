from pokemon_rpg.gameplay.combat.projectiles.bubble_beam import BubbleBeam
from pokemon_rpg.gameplay.combat.projectiles.bullet_seed import BulletSeed
from pokemon_rpg.gameplay.combat.projectiles.ember import Ember
from pokemon_rpg.gameplay.combat.projectiles.flamethrower import Flamethrower
from pokemon_rpg.gameplay.combat.projectiles.razor_leaf import RazorLeaf
from pokemon_rpg.gameplay.combat.projectiles.water_gun import WaterGun

MOVE_CLASSES = {
    "bubble_beam": BubbleBeam,
    "flamethrower": Flamethrower,
    "ember": Ember,
    "water_gun": WaterGun,
    "bullet_seed": BulletSeed,
    "razor_leaf": RazorLeaf,
}

POKEMON_MOVES = {
    "totodile": {"shoot": ["bubble_beam", "water_gun"], "strike": "slash"},
    "charmander": {"shoot": ["ember", "flamethrower"], "strike": "slash"},
    "bulbasaur": {"shoot": ["razor_leaf", "bullet_seed"], "strike": "tackle"},
}
