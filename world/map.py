import pygame
import pytmx
from entities.sprite import Generic
from world.depth import get_depth_value, tile_depth


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
    Pass 1: build dicts of (tile_x, tile_y) to depth_value:
      - tree_base_positions: tiles from any layer named 'Tree Base'
      - town_positions: every tile in any 'Town' layer, used for self-anchored
        depth lookups on town overlay objects

    Returns empty dicts for any type when those layers are not present,
    so maps without them work without any special casing.
    """
    tree_base_positions: dict = {}
    town_positions: dict = {}

    for layer in layers:
        if not isinstance(layer, pytmx.TiledTileLayer):
            continue

        if layer.name == "Tree Base":
            for x, y, image in layer.tiles():
                if image:
                    tree_base_positions[(x, y)] = get_depth_value(y, tile_h)

        elif "Town" in layer.name:
            for x, y, image in layer.tiles():
                if image:
                    town_positions[(x, y)] = get_depth_value(y, tile_h)

    return tree_base_positions, town_positions


BUILDING_LAYER_NAMES = (
    "Buildings",
    "Buildings Base",
    "Buildings Roof",
)


def collect_building_foot_depths(layers: list, tile_h: int) -> dict:
    """
    Map each building wall/roof tile to the depth of its local footprint.

    Decorative lower trim can extend south of the wall face, so collision tiles
    define the row where the building should stop occluding actors. Building
    visuals can touch between nearby houses, so collision islands are used as
    seeds and their wall/roof tiles flood-fill outward from there.
    """
    cells: set = set()
    collision_cells: set = set()
    for layer in layers:
        if not isinstance(layer, pytmx.TiledTileLayer):
            continue
        if layer.name == "Collisions":
            for x, y, image in layer.tiles():
                if image:
                    collision_cells.add((x, y))
            continue
        if layer.name not in BUILDING_LAYER_NAMES:
            continue
        for x, y, image in layer.tiles():
            if image:
                cells.add((x, y))

    seeds = cells & collision_cells
    foot_depths: dict = {}
    queue: list = []

    unvisited = set(seeds)
    while unvisited:
        start = unvisited.pop()
        component = {start}
        stack = [start]
        while stack:
            cx, cy = stack.pop()
            for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                if (nx, ny) in unvisited:
                    unvisited.discard((nx, ny))
                    component.add((nx, ny))
                    stack.append((nx, ny))

        foot_row = max(cy for _, cy in component)
        depth = foot_row * tile_h
        for cell in component:
            foot_depths[cell] = depth
            queue.append(cell)

    visited = set(queue)
    index = 0
    while index < len(queue):
        cx, cy = queue[index]
        index += 1
        depth = foot_depths[(cx, cy)]
        for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
            cell = (nx, ny)
            if cell in cells and cell not in visited:
                visited.add(cell)
                foot_depths[cell] = depth
                queue.append(cell)

    unvisited = cells - visited
    while unvisited:
        start = unvisited.pop()
        component = [start]
        stack = [start]
        while stack:
            cx, cy = stack.pop()
            for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                if (nx, ny) in unvisited:
                    unvisited.discard((nx, ny))
                    component.append((nx, ny))
                    stack.append((nx, ny))

        depth = max(cy for _, cy in component) * tile_h
        for cell in component:
            foot_depths[cell] = depth

    return foot_depths


def build_sprites(
    layers: list,
    tile_w: int,
    tile_h: int,
    tree_base_positions: dict,
    town_positions: dict,
    building_foot_depths: dict,
    map_height: int,
    all_sprites,
    collision_sprites,
) -> list:
    """
    Pass 2: iterate every tile layer and create Generic sprites, assigning
    ground_y for depth sorting. Returns the list of door trigger rects
    collected from any 'Doors' layer.
    """
    door_rects: list = []

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
                town_positions=town_positions,
                building_foot_depths=building_foot_depths,
                fallback=map_height + 100,
            )

            if "Door" in layer.name:
                trigger = pygame.Rect(pos, (tile_w, tile_h))
                trigger.inflate_ip(-tile_w // 2, -tile_h // 2)
                door_rects.append(trigger)

    return door_rects


def build_collision_matrix_from_tmx(layer, cols, rows):
    grid = [[0 for _ in range(cols)] for _ in range(rows)]

    for x, y, gid in layer.tiles():
        if gid != 0:
            grid[y][x] = 1

    return grid
