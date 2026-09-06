from pathlib import Path

import pytmx

from pokemon_rpg.data.world import MAPS
from pokemon_rpg.settings import ASSET_ROOT, PROJECT_ROOT


def resolve_map_path(map_name: str) -> Path:
    """Resolve a registered map while preventing paths outside the asset tree."""
    try:
        configured_path = MAPS[map_name]["path"]
    except KeyError as error:
        raise ValueError(f"Unknown map: {map_name!r}") from error

    path = (PROJECT_ROOT / configured_path).resolve()
    asset_root = ASSET_ROOT.resolve()
    if not path.is_relative_to(asset_root):
        raise ValueError(f"Map path escapes the asset directory: {configured_path!r}")
    if not path.is_file():
        raise FileNotFoundError(f"Map file does not exist: {path}")
    return path


def load_map(map_name: str):
    """Load a registered TMX map for Pygame."""
    return pytmx.load_pygame(str(resolve_map_path(map_name)), pixelalpha=True)
