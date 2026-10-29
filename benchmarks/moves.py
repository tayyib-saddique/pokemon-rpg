"""
moves.py
========
Benchmark every registered move using the real projectile classes.

Benchmark (default)
-------------------
Each move is cast on repeat by a crowd of Pokemon that know it, scattered
through a screen-sized arena with walls and target dummies, at a fixed 60 fps
simulation step. The runs play out in a window so you can watch every attack,
and a results table is printed to the terminal as each run finishes. Only the
moves' own update and draw are timed; the arena, HUD and window are not.

    uv run python benchmarks/moves.py
    uv run python benchmarks/moves.py --moves razor_leaf bullet_seed --casters 1 50
    uv run python benchmarks/moves.py --targets 20   # crowded screen
    uv run python benchmarks/moves.py --headless     # no window, runs flat out
    uv run python benchmarks/moves.py --json after.json --baseline before.json

  SPACE   skip to the next run
  ESC     stop (results so far are still printed and saved)

Timings are wall-clock: run on an otherwise idle machine, and only compare
--baseline results recorded on the same machine.

Columns:
  live       mean casts alive at once (a cast lingers while its effects play)
  effects    peak particles / shots alive at once
  update     mean ms per frame in update()
  draw       mean ms per frame in draw()
  frame      mean / p95 / max ms per frame (update + draw)
  budget     mean frame cost as a share of a 60 fps frame (16.7 ms)
  vs base    change in mean frame cost against --baseline

Interactive (--interactive)
---------------------------
  1-9 / TAB   select move
  Arrow keys  aim (combine for diagonals)
  Z           fire once
  HOLD Z      rapid fire (every 120 ms)
  X           storm: fire in all 8 directions at once
  C           clear all projectiles
  ESC         quit
"""

import argparse
import json
import os
import platform
import random
import sys
import time
from collections import deque

import pygame

from pokemon_rpg.data.pokemon import SPRITE_SHEETS
from pokemon_rpg.gameplay.combat.moves import MOVE_CLASSES, POKEMON_MOVES
from pokemon_rpg.gameplay.combat.projectiles.base import FACING_VELOCITY, BaseProjectile
from pokemon_rpg.gameplay.direction import direction_name
from pokemon_rpg.resources.asset_store import load_pokemon_animations
from pokemon_rpg.settings import FPS, HEIGHT, WIDTH

DT = 1 / FPS
FRAME_BUDGET_MS = 1000 / FPS
MAP_SIZE = (1440, 1440)
TILE = 48  # collision tiles are 16px scaled x3
RAPID_FIRE_MS = 120

BG = (18, 22, 30)
GRID_COLOUR = (30, 36, 48)
WALL_COLOUR = (70, 64, 72)
DUMMY_COLOUR = (120, 110, 140)
DUMMY_HIT_COLOUR = (230, 90, 90)
HUD_HEADLINE = (255, 220, 80)
HUD_TEXT = (200, 200, 200)
HUD_PANEL = (10, 12, 18, 200)
BAR_OK = (90, 200, 110)
BAR_WARN = (240, 200, 70)
BAR_OVER = (230, 80, 70)


class Wall(pygame.sprite.Sprite):
    def __init__(self, rect):
        super().__init__()
        self.rect = pygame.Rect(rect)


class Dummy(pygame.sprite.Sprite):
    """Indestructible target that counts the hits it takes."""

    def __init__(self, centre):
        super().__init__()
        self.rect = pygame.Rect(0, 0, TILE, TILE)
        self.rect.center = centre
        self.hits = 0
        self.flash = 0.0

    def take_damage(self, amount, source=None):
        self.hits += 1
        self.flash = 0.12


def effect_count(projectile):
    """Live particles/sub-shots, counted through a volley's shots."""
    count = 0
    for name, value in vars(projectile).items():
        if name.startswith("_") or name.endswith("_sprites"):
            continue
        if isinstance(value, list):
            count += sum(
                effect_count(v) if isinstance(v, BaseProjectile) else 1 for v in value
            )
    return count


def percentile(values, pct):
    ordered = sorted(values)
    return ordered[round(pct / 100 * (len(ordered) - 1))]


def aim_label(facing):
    """On-screen direction of travel (facing names are mirrored left/right)."""
    vx, vy = FACING_VELOCITY[facing]
    vertical = "up" if vy < 0 else "down" if vy > 0 else ""
    horizontal = "left" if vx < 0 else "right" if vx > 0 else ""
    return "-".join(part for part in (vertical, horizontal) if part)


def caster_for(move):
    """A Pokemon that knows the move, to stand in as the caster."""
    for pokemon, moves in POKEMON_MOVES.items():
        if move in moves["shoot"]:
            return pokemon
    return next(iter(SPRITE_SHEETS))


def caster_pose(pokemon, facing, centre):
    """The caster's sprite, its rect, and the mouth point it fires from."""
    sprite = load_pokemon_animations(pokemon)[f"{facing}_idle"][0]
    rect = sprite.get_rect(center=centre)
    fx, fy = SPRITE_SHEETS[pokemon]["mouth_fracs"].get(facing, (0.5, 0.4))
    return sprite, rect, (rect.left + rect.width * fx, rect.top + rect.height * fy)


# Drawing shared by both windowed modes


def draw_grid(surface):
    for gx in range(0, WIDTH, 64):
        pygame.draw.line(surface, GRID_COLOUR, (gx, 0), (gx, HEIGHT))
    for gy in range(0, HEIGHT, 64):
        pygame.draw.line(surface, GRID_COLOUR, (0, gy), (WIDTH, gy))


def draw_arena(surface, offset, walls, dummies):
    surface.fill(BG)
    draw_grid(surface)
    for wall in walls:
        pygame.draw.rect(surface, WALL_COLOUR, wall.rect.move(-offset[0], -offset[1]))
    for dummy in dummies:
        colour = DUMMY_HIT_COLOUR if dummy.flash > 0 else DUMMY_COLOUR
        pygame.draw.rect(surface, colour, dummy.rect.move(-offset[0], -offset[1]))


def draw_hud(surface, font, lines, budget_pct=None):
    """Text panel in the top-left; the first line is the headline.

    Each line is a (label, value) pair drawn in two columns, or a plain string.
    """
    pad, line_h, value_x = 10, 20, 110
    widths = [
        value_x + font.size(line[1])[0]
        if isinstance(line, tuple)
        else font.size(line)[0]
        for line in lines
    ]
    height = len(lines) * line_h + pad * 2 + (14 if budget_pct is not None else 0)
    panel = pygame.Surface((max(max(widths) + pad * 2, 240), height), pygame.SRCALPHA)
    panel.fill(HUD_PANEL)
    surface.blit(panel, (0, 0))
    for i, line in enumerate(lines):
        colour = HUD_HEADLINE if i == 0 else HUD_TEXT
        y = pad + i * line_h
        if isinstance(line, tuple):
            label, value = line
            surface.blit(font.render(label, True, colour), (pad, y))
            surface.blit(font.render(value, True, colour), (pad + value_x, y))
        else:
            surface.blit(font.render(line, True, colour), (pad, y))
    if budget_pct is not None:
        # Bar spans two frame budgets; the tick marks one full 60 fps frame
        bar = pygame.Rect(pad, pad + len(lines) * line_h + 2, 220, 8)
        colour = (
            BAR_OK if budget_pct < 50 else BAR_WARN if budget_pct < 100 else BAR_OVER
        )
        fill = bar.copy()
        fill.width = round(bar.width * min(budget_pct, 200) / 200)
        pygame.draw.rect(surface, GRID_COLOUR, bar)
        pygame.draw.rect(surface, colour, fill)
        pygame.draw.line(
            surface, HUD_TEXT, (bar.centerx, bar.top - 2), (bar.centerx, bar.bottom + 1)
        )


# Benchmark


class Viewer:
    """Shows benchmark runs in the window at real-time speed."""

    def __init__(self, surface, total_runs):
        self.surface = surface
        self.total_runs = total_runs
        self.run_number = 0
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 22)
        self.fps = deque(maxlen=60)
        self.stopped = False

    def poll(self):
        """'quit' to stop everything, 'skip' to end this run, else None."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
            ):
                self.stopped = True
                return "quit"
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                return "skip"
        return None

    def present(self, lines, budget_pct):
        self.fps.append(self.clock.get_fps())
        fps = self.clock.get_fps()
        avg = sum(self.fps) / len(self.fps)
        draw_hud(
            self.surface,
            self.font,
            [("FPS", f"{fps:5.1f}  (avg {avg:5.1f})")] + lines,
            budget_pct,
        )
        pygame.display.flip()
        self.clock.tick(FPS)


def hud_area(view):
    """World rect under the benchmark's HUD panel, kept free of the arena."""
    return pygame.Rect(view.left, view.top, 360, 250)


def build_crowd(rng, move, count, view):
    pokemon = caster_for(move)
    spawn_area = view.inflate(-200, -200)
    hud = hud_area(view).inflate(80, 80)
    crowd = []
    for _ in range(count):
        for _ in range(50):
            centre = (
                rng.randrange(spawn_area.left, spawn_area.right),
                rng.randrange(spawn_area.top, spawn_area.bottom),
            )
            if not hud.collidepoint(centre):
                break
        facing = rng.choice(list(FACING_VELOCITY))
        sprite, rect, mouth = caster_pose(pokemon, facing, centre)
        crowd.append({"facing": facing, "sprite": sprite, "rect": rect, "mouth": mouth})
    return crowd


def build_arena(rng, view, wall_count, target_count, keep_clear):
    """Scattered walls and dummies inside the view, off the casters' spots."""
    inner = view.inflate(-TILE * 2, -TILE * 2)

    def free_rect(w, h):
        for _ in range(50):
            rect = pygame.Rect(
                rng.randrange(inner.left, inner.right - w),
                rng.randrange(inner.top, inner.bottom - h),
                w,
                h,
            )
            if rect.collidelist(keep_clear) == -1:
                return rect
        return rect

    walls = pygame.sprite.Group(Wall(free_rect(TILE, TILE)) for _ in range(wall_count))
    dummies = pygame.sprite.Group(
        Dummy(free_rect(TILE, TILE).center) for _ in range(target_count)
    )
    return walls, dummies


def bench_move(move, casters, args, surface, viewer=None):
    """Run one move with a crowd of casters. Returns stats, or None if skipped."""
    rng = random.Random(args.seed)
    # Camera centred on the middle of the map, like the player's view
    view = pygame.Rect(0, 0, WIDTH, HEIGHT)
    view.center = (MAP_SIZE[0] // 2, MAP_SIZE[1] // 2)
    offset = pygame.math.Vector2(view.topleft)
    crowd = build_crowd(rng, move, casters, view)
    walls, dummies = build_arena(
        rng,
        view,
        args.walls,
        args.targets,
        [hud_area(view)] + [c["rect"] for c in crowd],
    )
    # Stagger casters so casts don't all land on the same frame
    next_cast = [rng.uniform(0, args.refire) for _ in crowd]

    cls = MOVE_CLASSES[move]
    # Projectile effects draw from the global RNG; seed it for repeatable load
    random.seed(args.seed)
    group = pygame.sprite.Group()
    warmup_frames = round(args.warmup * FPS)
    total_frames = warmup_frames + round(args.seconds * FPS)
    update_ms, draw_ms, live, peak_effects = [], [], [], 0
    recent = deque(maxlen=30)  # (update, draw) for the on-screen readout

    for frame in range(total_frames):
        if viewer and viewer.poll():
            break

        for i, caster in enumerate(crowd):
            next_cast[i] -= DT
            if next_cast[i] <= 0:
                next_cast[i] += args.refire
                group.add(
                    cls(
                        *caster["mouth"],
                        caster["facing"],
                        map_size=MAP_SIZE,
                        collision_sprites=walls,
                        combat_sprites=dummies,
                    )
                )

        start = time.perf_counter()
        group.update(DT)
        updated = time.perf_counter()

        if viewer:
            for dummy in dummies:
                dummy.flash = max(0.0, dummy.flash - DT)
            draw_arena(surface, offset, walls, dummies)
            for caster in crowd:
                surface.blit(
                    caster["sprite"], caster["rect"].move(-offset.x, -offset.y)
                )
        else:
            surface.fill(BG)

        drawing = time.perf_counter()
        for projectile in group:
            projectile.draw(surface, offset)
        drawn = time.perf_counter()

        effects = sum(effect_count(p) for p in group)
        recent.append(((updated - start) * 1000, (drawn - drawing) * 1000))
        if frame >= warmup_frames:
            update_ms.append(recent[-1][0])
            draw_ms.append(recent[-1][1])
            live.append(len(group))
            peak_effects = max(peak_effects, effects)

        if viewer:
            upd = sum(u for u, _ in recent) / len(recent)
            drw = sum(d for _, d in recent) / len(recent)
            if frame < warmup_frames:
                phase = "warming up"
            else:
                phase = f"measuring {(frame - warmup_frames) / FPS:.1f} / {args.seconds:g} s"
            viewer.present(
                [
                    ("Run", f"{viewer.run_number} / {viewer.total_runs}   ({phase})"),
                    ("Move", move),
                    ("Casters", f"{casters} x {caster_for(move)}"),
                    ("Live casts", str(len(group))),
                    ("Effects", str(effects)),
                    ("Update", f"{upd:.2f} ms"),
                    ("Draw", f"{drw:.2f} ms"),
                    (
                        "Frame",
                        f"{upd + drw:.2f} ms  "
                        f"({(upd + drw) / FRAME_BUDGET_MS * 100:.0f}% of {FPS} fps)",
                    ),
                    "SPACE = skip run   ESC = stop",
                ],
                (upd + drw) / FRAME_BUDGET_MS * 100,
            )

    if not update_ms:
        return None
    frame_ms = [u + d for u, d in zip(update_ms, draw_ms)]
    mean_frame = sum(frame_ms) / len(frame_ms)
    return {
        "move": move,
        "casters": casters,
        "frames": len(frame_ms),
        "live_mean": sum(live) / len(live),
        "peak_effects": peak_effects,
        "update_ms": sum(update_ms) / len(update_ms),
        "draw_ms": sum(draw_ms) / len(draw_ms),
        "frame_ms": mean_frame,
        "frame_p95_ms": percentile(frame_ms, 95),
        "frame_max_ms": max(frame_ms),
        "budget_pct": mean_frame / FRAME_BUDGET_MS * 100,
        "hits": sum(d.hits for d in dummies),
    }


def load_baseline(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {(r["move"], r["casters"]): r["frame_ms"] for r in data["results"]}


def print_header(baseline):
    header = (
        f"{'move':<14}{'casters':>8}{'live':>7}{'effects':>9}"
        f"{'update':>9}{'draw':>8}   {'frame mean / p95 / max':<24}{'budget':>8}"
    )
    if baseline:
        header += f"{'vs base':>10}"
    print(header)
    print("-" * len(header))


def print_row(r, baseline):
    frame = f"{r['frame_ms']:.2f} / {r['frame_p95_ms']:.2f} / {r['frame_max_ms']:.2f}"
    row = (
        f"{r['move']:<14}{r['casters']:>8}{r['live_mean']:>7.1f}"
        f"{r['peak_effects']:>9}{r['update_ms']:>9.2f}{r['draw_ms']:>8.2f}"
        f"   {frame:<24}{r['budget_pct']:>7.1f}%"
    )
    if baseline:
        before = baseline.get((r["move"], r["casters"]))
        change = f"{(r['frame_ms'] - before) / before * 100:+.1f}%" if before else "n/a"
        row += f"{change:>10}"
    print(row, flush=True)


def open_window(headless):
    if headless:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()
    try:
        surface = pygame.display.set_mode((WIDTH, HEIGHT))
    except pygame.error:
        print("No display available, running headless.\n")
        pygame.display.quit()
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.display.init()
        surface = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Move benchmark")
    return surface


def run_benchmark(args):
    surface = open_window(args.headless)
    runs = [(move, casters) for move in args.moves for casters in args.casters]
    viewer = None if args.headless else Viewer(surface, len(runs))

    print(
        f"Benchmarking {len(args.moves)} moves: {args.seconds:g}s per run after "
        f"{args.warmup:g}s warm-up, each caster recasts every {args.refire:g}s, "
        f"{args.walls} walls, {args.targets} targets, {FPS} fps step.\n"
    )
    baseline = load_baseline(args.baseline) if args.baseline else None
    print_header(baseline)
    results = []
    for number, (move, casters) in enumerate(runs, start=1):
        if viewer:
            viewer.run_number = number
        result = bench_move(move, casters, args, surface, viewer)
        if result is None:
            print(f"{move:<14}{casters:>8}   skipped", flush=True)
        else:
            results.append(result)
            print_row(result, baseline)
        if viewer and viewer.stopped:
            print("\nStopped early.")
            break

    if args.json:
        meta = {
            "python": platform.python_version(),
            "pygame": pygame.version.ver,
            "platform": platform.platform(),
            "seconds": args.seconds,
            "warmup": args.warmup,
            "refire": args.refire,
            "seed": args.seed,
            "walls": args.walls,
            "targets": args.targets,
            "fps": FPS,
        }
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"meta": meta, "results": results}, f, indent=2)
        print(f"\nWrote {args.json}")
    pygame.quit()


# Interactive


def run_interactive(args):
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Move benchmark (interactive)")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 22)

    centre = (WIDTH // 2, HEIGHT // 2)
    walls = pygame.sprite.Group(
        Wall((0, 0, WIDTH, TILE)),
        Wall((0, HEIGHT - TILE, WIDTH, TILE)),
        Wall((0, 0, TILE, HEIGHT)),
        Wall((WIDTH - TILE, 0, TILE, HEIGHT)),
        Wall((centre[0] - 260, centre[1] - 200, TILE * 2, TILE)),
        Wall((centre[0] + 200, centre[1] + 120, TILE, TILE * 2)),
    )
    dummies = pygame.sprite.Group(
        Dummy((centre[0] + dx, centre[1] + dy))
        for dx, dy in [(260, 0), (-260, 40), (0, 220), (40, -230), (200, -160)]
    )
    projectiles = pygame.sprite.Group()

    move_index, facing = 0, "down"
    fired, rapid_timer = 0, 0.0
    update_ms, draw_ms = deque(maxlen=60), deque(maxlen=60)
    fps_samples = deque(maxlen=60)

    def fire(direction):
        nonlocal fired
        move = args.moves[move_index]
        _, _, mouth = caster_pose(caster_for(move), direction, centre)
        projectiles.add(
            MOVE_CLASSES[move](
                *mouth,
                direction,
                map_size=(WIDTH, HEIGHT),
                collision_sprites=walls,
                combat_sprites=dummies,
            )
        )
        fired += 1

    frame = 0
    running = True
    while running:
        dt = clock.tick(FPS) / 1000
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_TAB:
                    move_index = (move_index + 1) % len(args.moves)
                elif pygame.K_1 <= event.key <= pygame.K_9:
                    move_index = min(event.key - pygame.K_1, len(args.moves) - 1)
                elif event.key == pygame.K_z:
                    fire(facing)
                    rapid_timer = 0.0
                elif event.key == pygame.K_x:
                    for direction in FACING_VELOCITY:
                        fire(direction)
                elif event.key == pygame.K_c:
                    projectiles.empty()

        keys = pygame.key.get_pressed()
        dx = keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]
        dy = keys[pygame.K_DOWN] - keys[pygame.K_UP]
        if dx or dy:
            facing = direction_name(dx, dy, facing)
        if keys[pygame.K_z]:
            rapid_timer += dt * 1000
            if rapid_timer >= RAPID_FIRE_MS:
                rapid_timer -= RAPID_FIRE_MS
                fire(facing)

        start = time.perf_counter()
        projectiles.update(dt)
        updated = time.perf_counter()
        for dummy in dummies:
            dummy.flash = max(0.0, dummy.flash - dt)

        draw_arena(screen, (0, 0), walls, dummies)
        move = args.moves[move_index]
        sprite, rect, _ = caster_pose(caster_for(move), facing, centre)
        screen.blit(sprite, rect)

        drawing = time.perf_counter()
        for projectile in projectiles:
            projectile.draw(screen, (0, 0))
        drawn = time.perf_counter()

        update_ms.append((updated - start) * 1000)
        draw_ms.append((drawn - drawing) * 1000)
        fps_samples.append(clock.get_fps())
        upd = sum(update_ms) / len(update_ms)
        drw = sum(draw_ms) / len(draw_ms)
        draw_hud(
            screen,
            font,
            [
                (
                    "FPS",
                    f"{clock.get_fps():5.1f}  "
                    f"(avg {sum(fps_samples) / len(fps_samples):5.1f})",
                ),
                (
                    "Move",
                    f"[{move_index + 1}] {move}  (TAB / 1-{len(args.moves)} to switch)",
                ),
                ("Aim", aim_label(facing)),
                ("Active casts", str(len(projectiles))),
                ("Effects", str(sum(effect_count(p) for p in projectiles))),
                ("Total fired", str(fired)),
                ("Update", f"{upd:.2f} ms"),
                ("Draw", f"{drw:.2f} ms"),
                "",
                "Z = fire  (hold = rapid-fire stress)   X = storm",
                "Arrows = aim   C = clear   ESC = quit",
            ],
        )
        pygame.display.flip()

        frame += 1
        if args.max_frames and frame >= args.max_frames:
            running = False
    pygame.quit()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Benchmark every registered move.")
    parser.add_argument(
        "--moves",
        nargs="+",
        default=sorted(MOVE_CLASSES),
        choices=sorted(MOVE_CLASSES),
        help="moves to benchmark (default: all)",
    )
    parser.add_argument(
        "--casters",
        nargs="+",
        type=int,
        default=[1, 10, 25],
        help="crowd sizes to run each move with (default: 1 10 25)",
    )
    parser.add_argument(
        "--targets", type=int, default=5, help="target dummies on screen (default: 5)"
    )
    parser.add_argument(
        "--walls", type=int, default=40, help="wall tiles on screen (default: 40)"
    )
    parser.add_argument("--seconds", type=float, default=2.0, help="measured seconds")
    parser.add_argument("--warmup", type=float, default=0.5, help="unmeasured seconds")
    parser.add_argument(
        "--refire", type=float, default=0.4, help="seconds between a caster's casts"
    )
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--json", help="write results to this JSON file")
    parser.add_argument("--baseline", help="compare against an earlier --json file")
    parser.add_argument(
        "--headless", action="store_true", help="no window; run as fast as possible"
    )
    parser.add_argument(
        "--interactive", action="store_true", help="fire moves by hand instead"
    )
    # Lets the interactive harness be smoke-tested headlessly
    parser.add_argument("--max-frames", type=int, default=0, help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.interactive:
        run_interactive(args)
    else:
        run_benchmark(args)


if __name__ == "__main__":
    sys.exit(main())
