"""Score candidates against the live top-10 teams' recorded action tapes.

For every archived top-10 game, the top team's seat replays its recorded actions
open-loop and the candidate takes the other seat, same seed. An open-loop
opponent does not react to us, so this is an approximation -- but it is the only
way to measure against the private agents we actually meet above 2800, and it is
the method the public 2820 notebook used for its live-opponent testbed.

    python opt/tapeeval.py data/top10/sample_0919.parquet candA,candB,...
"""

from __future__ import annotations

import os
import sys
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "engine"))

import fastsim  # noqa: E402
import opponents  # noqa: E402
import replays  # noqa: E402

TOP = {"Majkel1337", "DSM", "ymg_aq", "THIRD FARM CLUB", "Otter Vibe", "QQ", "Sida Zuo",
       "SpaTaro", "Orbital Terraformer", "Arda Ceylan", "Unknown Mother-Goose",
       "Planned Economy", "THUNDER THUNDER", "binghua", "Yannik Schiffner"}


def one(job):
    eid, tape_seat, cand = job
    c = replays._COMPACT[eid]
    me = opponents.get(cand)
    two = fastsim._takes_config(me)
    g = fastsim.Game(c["seed"], {"episodeSteps": c["steps"]})
    cfg = g.env.configuration
    my_seat = 1 - tape_seat
    for t in range(c["n"]):
        acts = [None, None]
        acts[tape_seat] = c["acts"][t][tape_seat]
        try:
            acts[my_seat] = me(g.obs(my_seat), cfg) if two else me(g.obs(my_seat))
        except Exception:
            acts[my_seat] = replays.PASS
        g.step(acts)
        if g.done:
            break
    m = g.money
    return cand, c["teams"][tape_seat], m[my_seat], m[tape_seat]


def main(path, cands):
    reps = replays.compact(path)
    jobs = [(eid, s, cand) for eid, c in reps.items() for s in (0, 1) if c["teams"][s] in TOP
            for cand in cands]
    print(f"{len(jobs)} games vs top-team tapes")
    with Pool(initializer=replays._init, initargs=(path,)) as pool:
        res = pool.map(one, jobs, chunksize=4)
    by = defaultdict(list)
    by_team = defaultdict(lambda: defaultdict(list))
    for cand, team, me, them in res:
        s = 1.0 if me > them else 0.5 if me == them else 0.0
        by[cand].append(s)
        by_team[cand][team].append(s)
    teams = sorted({t for d in by_team.values() for t in d}, key=lambda t: -sum(len(by_team[c][t]) for c in cands))[:6]
    print(f"\n{'candidate':22s} {'vs top-10 tapes':>16s}   " + "  ".join(f"{t[:10]:>10s}" for t in teams))
    for cand, v in sorted(by.items(), key=lambda kv: -sum(kv[1]) / len(kv[1])):
        cells = "  ".join(f"{sum(by_team[cand][t])/max(1,len(by_team[cand][t]))*100:9.0f}%" for t in teams)
        print(f"{cand:22s} {sum(v)/len(v)*100:14.1f}%   {cells}   (n={len(v)})")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2].split(","))
