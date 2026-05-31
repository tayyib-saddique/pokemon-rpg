def world_to_grid(pos, tile_size):
    return int(pos[0] // tile_size), int(pos[1] // tile_size)


def grid_to_world(cell, tile_size):
    x, y = cell
    return (
        x * tile_size + tile_size // 2,
        y * tile_size + tile_size // 2,
    )


def build_collision_matrix(collision_sprites, map_width, map_height, tile_size):
    cols = map_width // tile_size
    rows = map_height // tile_size

    grid = [[1 for _ in range(cols)] for _ in range(rows)]

    for sprite in collision_sprites:
        rect = sprite.rect

        x0, y0 = world_to_grid((rect.left, rect.top), tile_size)
        x1, y1 = world_to_grid((rect.right - 1, rect.bottom - 1), tile_size)

        for y in range(max(0, y0), min(rows, y1 + 1)):
            for x in range(max(0, x0), min(cols, x1 + 1)):
                grid[y][x] = 0  # blocked

    return grid
