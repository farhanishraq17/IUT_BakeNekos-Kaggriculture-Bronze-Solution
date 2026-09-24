"""Where do two agents' action streams first diverge?

A router that hands control from agent A to agent B at step k is only sound if A
and B played identically up to k -- otherwise B inherits a farm its tape did not
build and its actions misfire. So: play each agent against the same fixed
opponent on the same seeds, record every action, and report the first step at
which each pair differs.

    python opt/prefix.py agentA agentB ...
"""

from __future__ import annotations

import itertools
import json
import os
import sys
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "engine"))

import fastsim  # noqa: E402
import opponents  # noqa: E402

SEEDS = [31337, 31338, 31339]
OPP = "c-one-more-wheat"   # a realistic, interacting opponent


def tape(job):
    name, seed = job
    me, opp = opponents.get(name), opponents.get(OPP)
    g = fastsim.Game(seed)
    two = [fastsim._takes_config(me), fastsim._takes_config(opp)]
    cfg = g.env.configuration
    out = []
    for _ in range(719):
        a = me(g.obs(0), cfg) if two[0] else me(g.obs(0))
        b = opp(g.obs(1), cfg) if two[1] else opp(g.obs(1))
        out.append(json.dumps(a, sort_keys=True))
        g.step([a, b])
        if g.done:
            break
    return name, seed, out


def main(names):
    with Pool() as pool:
        res = pool.map(tape, [(n, s) for n in names for s in SEEDS])
    tapes = {(n, s): t for n, s, t in res}
    print(f"first differing step (min over {len(SEEDS)} seeds; 719 = identical all game)\n")
    for a, b in itertools.combinations(names, 2):
        firsts = []
        for s in SEEDS:
            ta, tb = tapes[(a, s)], tapes[(b, s)]
            k = next((i for i, (x, y) in enumerate(zip(ta, tb)) if x != y), min(len(ta), len(tb)))
            firsts.append(k)
        print(f"{a:22s} vs {b:22s} {min(firsts):4d}   per seed {firsts}")


if __name__ == "__main__":
    main(sys.argv[1:])
