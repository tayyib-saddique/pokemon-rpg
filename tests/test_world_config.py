import pytest

from pokemon_rpg.data.world import MAPS, get_connection
from pokemon_rpg.resources.map_repository import resolve_map_path


@pytest.mark.parametrize("map_name", MAPS)
def test_registered_map_files_exist(map_name):
    assert resolve_map_path(map_name).is_file()


def test_unknown_map_is_rejected():
    with pytest.raises(ValueError, match="Unknown map"):
        resolve_map_path("../../outside")


def test_registered_path_cannot_escape_asset_directory(monkeypatch):
    unsafe_map = {"path": "../outside.tmx", "connections": {}}
    monkeypatch.setitem(MAPS, "unsafe", unsafe_map)

    with pytest.raises(ValueError, match="escapes the asset directory"):
        resolve_map_path("unsafe")


@pytest.mark.parametrize(
    ("map_name", "edge", "connection"),
    [
        (map_name, edge, connection)
        for map_name, config in MAPS.items()
        for edge, connection in config["connections"].items()
        if connection is not None
    ],
)
def test_connections_reference_registered_maps(map_name, edge, connection):
    assert connection["map"] in MAPS, f"Invalid connection from {map_name}:{edge}"
    assert len(connection["entry_pos"]) == 2


def test_get_connection_returns_configured_edge():
    assert get_connection("vertia_city", "east") == {
        "map": "vertia_road",
        "entry_pos": (126, 568),
    }


def test_get_connection_returns_none_for_unknown_edge():
    assert get_connection("vertia_city", "unknown") is None
