from typing import List, Tuple, Any
from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder
from world.matrix import build_collision_matrix

WorldPos = Tuple[float, float]
GridPos = Tuple[int, int]


class NavGrid:
    def __init__(
        self,
        collision_sprites: List[Any],
        map_width: int,
        map_height: int,
        tile_size: int,
    ):
        self.collision_sprites = collision_sprites
        self.map_width = map_width
        self.map_height = map_height

        self.tile_w = tile_size
        self.tile_h = tile_size

        self.cols = map_width // tile_size
        self.rows = map_height // tile_size

    # conversions
    def to_grid(self, x: float, y: float) -> GridPos:
        return int(x // self.tile_w), int(y // self.tile_h)

    def to_world(self, gx: int, gy: int) -> WorldPos:
        return (
            gx * self.tile_w + self.tile_w // 2,
            gy * self.tile_h + self.tile_h // 2,
        )

    # matrix
    def clamp_to_walkable(self, grid, gx, gy):
        if grid[gy][gx] == 1:
            return gx, gy

        # search nearest walkable tile
        for radius in range(1, 10):
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    nx, ny = gx + dx, gy + dy
                    if 0 <= nx < self.cols and 0 <= ny < self.rows:
                        if grid[ny][nx] == 1:
                            return nx, ny

        return gx, gy  # fallback

    def _matrix(self):
        return build_collision_matrix(
            self.collision_sprites, self.map_width, self.map_height, self.tile_w
        )

    def find_path(self, start_world, goal_world):
        start = self.to_grid(*start_world)
        goal = self.to_grid(*goal_world)
        matrix = self._matrix()

        start = self.clamp_to_walkable(matrix, *start)
        goal = self.clamp_to_walkable(matrix, *goal)

        walkable = sum(cell == 1 for row in matrix for cell in row)
        blocked = sum(cell == 0 for row in matrix for cell in row)

        grid = Grid(matrix=matrix)

        start_node = grid.node(*start)
        end_node = grid.node(*goal)

        finder = AStarFinder(diagonal_movement=2)
        path, _ = finder.find_path(start_node, end_node, grid)

        world_path = [self.to_world(x, y) for x, y in path]
        return world_path
