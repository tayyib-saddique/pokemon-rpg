import pygame
import pytest

from pokemon_rpg.data.pokemon import SPRITE_SHEETS
from pokemon_rpg.data.world import MAPS
from pokemon_rpg.gameplay.combat.moves import MOVE_CLASSES, POKEMON_MOVES
from pokemon_rpg.gameplay.combat.projectiles.base import FACING_VELOCITY
from pokemon_rpg.settings import ASSET_ROOT

ACTIONS = ["walk", "idle", "shoot", "strike"]


@pytest.mark.parametrize("pokemon", POKEMON_MOVES)
def test_every_shoot_move_is_registered(pokemon):
    for move in POKEMON_MOVES[pokemon]["shoot"]:
        assert move in MOVE_CLASSES, f"{pokemon} uses unregistered move {move}"


@pytest.mark.parametrize("pokemon", POKEMON_MOVES)
def test_pokemon_with_moves_has_sprite_sheets(pokemon):
    assert pokemon in SPRITE_SHEETS
    for action in ACTIONS:
        assert (ASSET_ROOT / "pokemon" / pokemon / f"{action}.png").is_file()


@pytest.mark.parametrize("pokemon", SPRITE_SHEETS)
def test_mouth_fracs_cover_every_facing(pokemon):
    fracs = SPRITE_SHEETS[pokemon]["mouth_fracs"]

    assert set(fracs) == set(FACING_VELOCITY)
    for fx, fy in fracs.values():
        assert 0 <= fx <= 1 and 0 <= fy <= 1


@pytest.mark.parametrize(
    ("pokemon", "action"),
    [(pokemon, action) for pokemon in SPRITE_SHEETS for action in ACTIONS],
)
def test_sheet_columns_fall_between_frames(pokemon, action):
    sheet = pygame.image.load(ASSET_ROOT / "pokemon" / pokemon / f"{action}.png")
    data = SPRITE_SHEETS[pokemon][action]
    width, height = sheet.get_size()

    assert width % data["cols"] == 0
    assert height % 8 == 0

    # A sprite may touch its own frame's edge (e.g. lunging in a strike), but a
    # wrong column count slices a sprite in two: opaque pixels on both sides
    # of the cut in the same row.
    frame_w = width // data["cols"]
    for col in range(1, data["cols"]):
        x = col * frame_w
        bridged = sum(
            sheet.get_at((x - 1, y)).a > 0 and sheet.get_at((x, y)).a > 0
            for y in range(height)
        )
        assert bridged == 0, f"cut at x={x} slices through a sprite"


@pytest.mark.parametrize("map_name", MAPS)
def test_enemy_spawns_use_known_pokemon(map_name):
    for spawn in MAPS[map_name].get("enemy_spawns", []):
        assert spawn["pokemon"] in SPRITE_SHEETS
        assert spawn["pokemon"] in POKEMON_MOVES
