"""Head-to-head on a FIXED held-out seed set. The search rotates seeds every
generation, so its reported 'best' is a high-water mark on a lucky block -- this
is the number that decides what gets submitted.

    python opt/evaluate.py runs/v1_elites.json runs/v2.json
"""

from __future__ import annotations

import json
import sys
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "engine"))

import fastsim  # noqa: E402
import opponents  # noqa: E402
import policy  # noqa: E402

# Never used during search (search uses 1000+, 50000+, 90000+).
HELD_OUT = list(range(31337, 31337 + 12))


def _one(job):
    genome, opp_name, seed, swap = job
    me = policy.make_agent(genome)
    opp = opponents.get(opp_name)
    m = fastsim.run(opp, me, seed) if swap else fastsim.run(me, opp, seed)
    return (m[1], m[0]) if swap else (m[0], m[1])


def score(pool, genome, opp_name, seeds=HELD_OUT):
    jobs = [(genome, opp_name, s, sw) for s in seeds for sw in (False, True)]
    res = pool.map(_one, jobs)
    w = sum(1 for a, b in res if a > b)
    t = sum(1 for a, b in res if a == b)
    n = len(res)
    return {"win_rate": (w + 0.5 * t) / n, "w": w, "l": n - w - t, "t": t,
            "cash": sum(a for a, _ in res) / n,
            "opp_cash": sum(b for _, b in res) / n}


def load(path):
    d = json.loads(Path(path).read_text())
    return policy.clamp_genome(d["best"]), d.get("island", Path(path).stem)


def main() -> int:
    paths = sys.argv[1:] or ["runs/v1_elites.json", "runs/v2.json"]
    cands = [load(p) for p in paths]
    panel = ["starter", "pipe-7-wheat-microstructure"]
    with Pool() as pool:
        for opp in panel:
            print(f"\n=== vs {opp}   ({len(HELD_OUT)} held-out seeds, both seats)")
            for genome, name in cands:
                r = score(pool, genome, opp)
                print(f"  {name:12s} win {r['win_rate']*100:5.1f}%  "
                      f"({r['w']}W/{r['l']}L/{r['t']}T)   "
                      f"our ${r['cash']:>10,.0f}   theirs ${r['opp_cash']:>10,.0f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
