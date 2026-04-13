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


def collect_base_positions(layers: list, tile_h: int) -> tuple[dict, dict]:
    """
    Pass 1 — build two dicts of (tile_x, tile_y) → depth_value:
      - tree_base_positions  — tiles from any layer named 'Tree Base'
      - building_base_positions — tiles from any layer named 'Building Base'

    Returns empty dicts for either type when those layers aren't present,
    so maps without trees or buildings work without any special casing.
    """
    tree_base_positions: dict = {}
    building_base_positions: dict = {}

    for layer in layers:
        if not isinstance(layer, pytmx.TiledTileLayer):
            continue

        if layer.name == "Tree Base":
            for x, y, image in layer.tiles():
                if image:
                    tree_base_positions[(x, y)] = get_depth_value(y, tile_h)

        elif layer.name == "Building Base":
            for x, y, image in layer.tiles():
                if image:
                    building_base_positions[(x, y)] = get_depth_value(y, tile_h)

    return tree_base_positions, building_base_positions


def build_sprites(
    layers: list,
    tile_w: int,
    tile_h: int,
    tree_base_positions: dict,
    building_base_positions: dict,
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
                x=x,
                y=y,
                tile_h=tile_h,
                layer_name=layer.name,
                tree_base_positions=tree_base_positions,
                building_base_positions=building_base_positions,
                fallback=map_height + 100,
            )
