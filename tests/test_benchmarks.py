"""Keep the benchmark harnesses runnable as the moves change."""

import importlib.util
import json

import pygame
import pytest

from pokemon_rpg.gameplay.combat.moves import MOVE_CLASSES
from pokemon_rpg.gameplay.combat.projectiles.base import FACING_VELOCITY
from pokemon_rpg.settings import PROJECT_ROOT


@pytest.fixture(scope="module")
def moves_bench():
    path = PROJECT_ROOT / "benchmarks" / "moves.py"
    spec = importlib.util.spec_from_file_location("moves_bench", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_headless_benchmark_covers_every_move(moves_bench, tmp_path):
    out = tmp_path / "results.json"

    moves_bench.main(
        [
            "--headless",
            "--seconds",
            "0.1",
            "--warmup",
            "0",
            "--casters",
            "1",
            "--json",
            str(out),
        ]
    )

    results = json.loads(out.read_text())["results"]
    assert {r["move"] for r in results} == set(MOVE_CLASSES)
    assert all(r["frame_ms"] > 0 for r in results)


def test_baseline_comparison_matches_runs(moves_bench, tmp_path, capsys):
    baseline = tmp_path / "before.json"
    args = ["--headless", "--moves", "ember", "--seconds", "0.05", "--warmup", "0"]
    args += ["--casters", "1"]
    moves_bench.main(args + ["--json", str(baseline)])
    capsys.readouterr()

    moves_bench.main(args + ["--baseline", str(baseline)])

    row = capsys.readouterr().out.strip().splitlines()[-1]
    assert row.startswith("ember") and row.endswith("%")


@pytest.mark.parametrize("facing", FACING_VELOCITY)
def test_aim_label_matches_travel_direction(moves_bench, facing):
    vx, vy = FACING_VELOCITY[facing]
    label = moves_bench.aim_label(facing)

    assert ("left" in label) == (vx < 0)
    assert ("right" in label) == (vx > 0)
    assert ("up" in label) == (vy < 0)
    assert ("down" in label) == (vy > 0)


def test_windowed_benchmark_runs_and_can_be_skipped(moves_bench, monkeypatch, capsys):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    real_get = pygame.event.get
    polls = {"n": 0}

    def scripted_events():
        real_get()
        polls["n"] += 1
        # Skip the second run partway through its warm-up
        if polls["n"] == 25:
            return [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)]
        return []

    monkeypatch.setattr(pygame.event, "get", scripted_events)
    moves_bench.main(
        ["--moves", "razor_leaf", "--casters", "1", "3", "--seconds", "0.2"]
        + ["--warmup", "0.2"]
    )

    out = capsys.readouterr().out.splitlines()
    assert any(line.startswith("razor_leaf") and line.endswith("%") for line in out)
    assert any(line.startswith("razor_leaf") and "skipped" in line for line in out)


def test_escape_stops_benchmark_early(moves_bench, monkeypatch, capsys):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    real_get = pygame.event.get

    def press_escape():
        real_get()
        return [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)]

    monkeypatch.setattr(pygame.event, "get", press_escape)
    moves_bench.main(["--casters", "1", "--seconds", "0.1", "--warmup", "0"])

    out = capsys.readouterr().out
    assert "Stopped early." in out
    assert out.count("skipped") == 1
