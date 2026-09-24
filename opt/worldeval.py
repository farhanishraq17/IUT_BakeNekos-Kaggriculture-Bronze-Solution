"""Play candidates against a panel over many seeds and record the shop draw of
every game -- the raw material for a shop-conditional router.

Runs identically locally and on a Kaggle worker (where the panel is a mounted
dataset, located via KAGRI_PANEL_DIR or found under /kaggle/input).

    python opt/worldeval.py --cands a,b --opps x,y --seed-lo 100000 --seed-hi 100200 --out runs/we.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")


def _find_panel():
    if os.environ.get("KAGRI_PANEL_DIR"):
        return
    base = Path("/kaggle/input")
    if base.exists():
        # Mount layout varies by image: /kaggle/input/<slug> or .../datasets/<owner>/<slug>.
        for p in base.rglob("PANEL_MANIFEST.json"):
            os.environ["KAGRI_PANEL_DIR"] = str(p.parent)
            return


_find_panel()
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "engine"))

import fastsim  # noqa: E402
import opponents  # noqa: E402


def _game(job):
    cand, opp, seed, seat = job
    me, them = opponents.get(cand), opponents.get(opp)
    try:
        m = fastsim.run(me, them, seed) if seat == 0 else fastsim.run(them, me, seed)
    except Exception as e:  # noqa: BLE001 -- one broken game must not kill a 12 h shard
        return {"cand": cand, "opp": opp, "seed": seed, "seat": seat, "error": repr(e)[:200]}
    mine, theirs = (m[0], m[1]) if seat == 0 else (m[1], m[0])
    err = fastsim.run.errors[seat]
    return {"cand": cand, "opp": opp, "seed": seed, "seat": seat, "shops": fastsim.run.shops,
            "me": mine, "them": theirs, "my_errors": err}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cands", required=True)
    ap.add_argument("--opps", required=True)
    ap.add_argument("--seed-lo", type=int, required=True)
    ap.add_argument("--seed-hi", type=int, required=True)
    ap.add_argument("--procs", type=int, default=0)
    ap.add_argument("--out", required=True)
    ap.add_argument("--minutes", type=float, default=0.0,
                    help="stop cleanly after this long; Kaggle may drop the output of a "
                         "kernel that is killed by its time limit")
    args = ap.parse_args()

    cands = [c for c in args.cands.split(",") if c]
    opps = [o for o in args.opps.split(",") if o]
    for n in cands + opps:
        opponents.get(n)  # fail fast in the parent if the panel is incomplete
    jobs = [(c, o, s, seat) for s in range(args.seed_lo, args.seed_hi)
            for c in cands for o in opps if o != c for seat in (0, 1)]
    print(f"panel dir: {opponents.DIR}\n{len(jobs)} games", flush=True)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    t = time.time()
    done = 0
    # Stream results to disk so a kernel that hits its time limit still leaves data.
    pool = Pool(args.procs or os.cpu_count())
    with out.open("w") as f:
        for row in pool.imap_unordered(_game, jobs, chunksize=2):
            f.write(json.dumps(row) + "\n")
            done += 1
            if done % 200 == 0:
                f.flush()
                print(f"{done}/{len(jobs)}  {time.time()-t:.0f}s", flush=True)
            if args.minutes and time.time() - t > args.minutes * 60:
                print("time budget reached, stopping cleanly", flush=True)
                break
    pool.terminate()
    print(f"done {done} games in {time.time()-t:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
