"""Round-robin between agents on fixed held-out seeds, both seats.

The ladder scores wins against other strong agents, so money-vs-starter is the
wrong ranking for choosing what to submit or what to build on. This is the right one.

    python opt/tournament.py [--seeds 10] agentA agentB ...
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
import time
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "engine"))

import fastsim  # noqa: E402
import opponents  # noqa: E402

HELD_OUT_BASE = 31337


def _game(job):
    a, b, seed = job
    m = fastsim.run(opponents.get(a), opponents.get(b), seed)
    return a, b, seed, m[0], m[1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("agents", nargs="+")
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--out", default="runs/tournament.json")
    args = ap.parse_args()

    seeds = [HELD_OUT_BASE + i for i in range(args.seeds)]
    # Both seat orders: the market lockstep processes player 0 first.
    jobs = [(a, b, s) for a, b in itertools.permutations(args.agents, 2) for s in seeds]
    t = time.time()
    with Pool() as pool:
        res = pool.map(_game, jobs, chunksize=1)
    print(f"{len(res)} games in {time.time()-t:.0f}s\n")

    wins = defaultdict(float)
    games = defaultdict(int)
    pair = defaultdict(lambda: [0.0, 0])
    cash = defaultdict(list)
    for a, b, _s, ma, mb in res:
        sa = 1.0 if ma > mb else (0.5 if ma == mb else 0.0)
        for x, y, sx in ((a, b, sa), (b, a, 1 - sa)):
            wins[x] += sx
            games[x] += 1
            pair[(x, y)][0] += sx
            pair[(x, y)][1] += 1
        cash[a].append(ma)
        cash[b].append(mb)

    order = sorted(args.agents, key=lambda n: -wins[n] / max(1, games[n]))
    short = {n: n[:10] for n in order}
    print(f"{'':30s}" + "".join(f"{short[n]:>11s}" for n in order) + "   overall   mean $")
    for x in order:
        row = ""
        for y in order:
            if x == y:
                row += f"{'-':>11s}"
            else:
                w, n = pair[(x, y)]
                row += f"{w / n * 100:10.0f}%"
        ov = wins[x] / games[x] * 100
        mc = sum(cash[x]) / len(cash[x])
        print(f"{x:30s}{row}   {ov:6.1f}%   {mc:>9,.0f}")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps({
        "seeds": seeds, "overall": {n: wins[n] / games[n] for n in order},
        "pair": {f"{x}|{y}": v[0] / v[1] for (x, y), v in pair.items()},
        "mean_cash": {n: sum(v) / len(v) for n, v in cash.items()},
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
