"""Throughput benchmark: how many games/s does fastsim give us?

Uses a synthetic *heavy* agent (max hands, full 10-order market queue, every unit
acting every turn) so the number is a worst-case floor, not a PASS-agent fantasy.

    python engine/bench.py [n_games] [n_procs]
"""

from __future__ import annotations

import sys
import time
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import fastsim  # noqa: E402

CROPS = ["WHEAT", "CARROT", "TOMATO", "MELON"]


def heavy_agent(obs):
    """Upper bound on per-turn engine work: hire every turn, keep the market queue
    full, give every unit a real (non-PASS) op."""
    me = obs["farms"][obs["player"]]
    priv = obs["private"]
    step, day = obs["step"], obs["day"]

    market = [["HIRE"]] * 3
    if me["money"] > 1500 and len(me["unlocked_quadrants"]) < 4:
        market.append(["BUY_LAND"])
    market.append(["BUY_SEED", CROPS[day % len(CROPS)], 4])
    for item in ("WHEAT", "CARROT", "TOMATO", "MELON", "EGG"):
        n = priv["shed"].get(item, 0)
        if n:
            market.append(["SELL", item, n])
    market = market[:10]

    tiles = me["tiles"]
    board = len(tiles)

    def op(i, pos):
        x, y = pos
        t = tiles[y][x]
        if t is None:
            return ["PLANT", CROPS[(day + i) % len(CROPS)]]
        if t == "LOCKED":
            return ["WEST" if x >= board // 2 else "EAST"]
        if t.get("kind") == "PLANT":
            if not t["watered_today"]:
                return ["WATER"]
            return ["HARVEST"] if t["yield_units"] > 0 else [["NORTH", "SOUTH", "EAST", "WEST"][(step + i) % 4]]
        if t.get("kind") == "WEED":
            return ["DIG"]
        return ["FEED"] if "animal" in t else ["BUILD_COOP"]

    hands = me["hands"]
    return {
        "farmer": op(0, me["farmer"]),
        "hands": [op(i + 1, p) for i, p in enumerate(hands)],
        "market": market,
    }


def one(seed: int) -> float:
    return fastsim.run(heavy_agent, heavy_agent, seed=seed)[0]


def main(n_games: int = 40, n_procs: int = 0) -> int:
    import os
    n_procs = n_procs or os.cpu_count()

    t = time.time()
    one(1)
    serial = time.time() - t
    print(f"1 game, serial: {serial*1000:.0f} ms  ({1/serial:.1f} games/s/core)")

    t = time.time()
    with Pool(n_procs) as p:
        p.map(one, range(n_games))
    dt = time.time() - t
    print(f"{n_games} games on {n_procs} procs: {dt:.1f}s  -> {n_games/dt:.1f} games/s aggregate "
          f"({n_games/dt*3600:,.0f} games/hour)")
    print(f"effective parallelism: {serial*n_games/dt:.1f}x")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(*(int(a) for a in sys.argv[1:])))
