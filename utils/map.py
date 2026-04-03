"""
TMX map utility helpers — layer flattening and base position collection.
"""
import pygame
import pytmx
from sprite import Generic
from utils.depth import get_depth_value, tile_depth


def flatten_layers(layers: list) -> list:
    """Recursively unwrap pytmx layer groups into a flat list."""
    result = []
    for layer in layers:
        if hasattr(layer, "layers"):
            result.extend(flatten_layers(layer.layers))
        else:
            result.append(layer)
    return result


def collect_base_positions(layers: list, tile_h: int) -> dict:
    """
    Pass 1 — build a dict of (tile_x, tile_y) → depth_value
    for every Base tile in the map.
    """
    base_positions = {}
    for layer in layers:
        if isinstance(layer, pytmx.TiledTileLayer) and "Base" in layer.name:
            for x, y, image in layer.tiles():
                if image:
                    base_positions[(x, y)] = get_depth_value(y, tile_h)
    return base_positions


def build_sprites(
    layers: list,
    tile_w: int,
    tile_h: int,
    base_positions: dict,
    map_height: int,
    all_sprites,
    collision_sprites,
) -> None:
    """
    Pass 2 — iterate every tile layer and create Generic sprites,
    assigning ground_y for depth sorting.
    """
    for layer in layers:
        if not isinstance(layer, pytmx.TiledTileLayer):
            continue

        for x, y, image in layer.tiles():
            if not image:
                continue

            pos = (x * tile_w, y * tile_h)
            scaled = pygame.transform.scale(image, (tile_w, tile_h))

            if layer.name == "Collisions":
                Generic(
                    pos=pos,
                    surface=pygame.Surface((tile_w, tile_h)),
                    groups=collision_sprites,
                )
                continue

            sprite = Generic(pos=pos, surface=scaled, groups=all_sprites)
            sprite.layer_name = layer.name
            sprite.ground_y = tile_depth(
                x, y, tile_h, layer.name, base_positions, fallback=map_height + 100
            )
