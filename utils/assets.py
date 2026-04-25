"""
Pokemon sprite sheet loader.
Returns a ready-to-use animations dict for a given pokemon.
"""

import os
import pygame
from utils.sprite_sheet import load_pmd_sheet
from constants.sprite_sheets import SPRITE_SHEETS

SCALE = 3


def load_pokemon_animations(pokemon: str) -> dict:
    """
    Load and scale all animation frames for a pokemon.
    Returns a dict of { 'direction_action': [Surface, ...] }
    """
    animations = {}
    pokemon_data = SPRITE_SHEETS.get(pokemon, {})
    actions = ["walk", "idle", "shoot", "strike"]

    for action in actions:
        data = pokemon_data.get(action)
        path = f"graphics/pokemon/{pokemon}/{action}.png"

        if not data or not os.path.exists(path):
            continue

        sheet = pygame.image.load(path).convert_alpha()
        frame_w = sheet.get_width() // data["cols"]
        frame_h = sheet.get_height() // 8

        frames = load_pmd_sheet(path, frame_w, frame_h)

        for direction, imgs in frames.items():
            scaled = [
                pygame.transform.scale(img, (frame_w * SCALE, frame_h * SCALE))
                for img in imgs
            ]

            if "trim" in data:
                scaled = [f for i, f in enumerate(scaled) if i in data["trim"]]

            animations[f"{direction}_{action}"] = scaled

    return animations
