"""Live-ladder replays: reproduce them in fastsim, and identify which public agent
a top team is running.

Replays (ashok205/kaggriculture-top10-replay-archive) carry info.seed and every
action of both players. steps[t][p]["action"] is the action that produced state
t, so the agent that saw steps[t-1] emitted steps[t][p]["action"].

    python opt/replays.py verify data/top10/replays_2026-09-19.parquet [n]
    python opt/replays.py match  data/top10/replays_2026-09-19.parquet agentA,agentB,...
"""

from __future__ import annotations

import json
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

PASS = {"farmer": ["PASS"], "hands": [], "market": []}


def load(path, limit=0):
    import pyarrow.parquet as pq
    t = pq.read_table(path)
    rows = t.slice(0, limit).to_pylist() if limit else t.to_pylist()
    for r in rows:
        yield r["episode_id"], json.loads(r["replay_json"])


def recorded(rep, player, t):
    """Action player emitted after seeing state t."""
    st = rep["steps"]
    a = st[t + 1][player].get("action") if t + 1 < len(st) else None
    return a if isinstance(a, dict) else PASS


def _canon(a):
    return json.dumps(a if isinstance(a, dict) else PASS, sort_keys=True, default=str)


def verify_one(item):
    """Replay both recorded action streams; final banks must match the replay."""
    eid, rep = item
    g = fastsim.Game(rep["info"]["seed"], {"episodeSteps": rep["configuration"]["episodeSteps"]})
    for t in range(len(rep["steps"]) - 1):
        g.step([recorded(rep, 0, t), recorded(rep, 1, t)])
        if g.done:
            break
    want = [float(s.get("reward") or 0) for s in rep["steps"][-1]]
    return eid, g.money == want, g.money, want


_COMPACT = {}


def compact(path):
    """eid -> {seed, n, acts[t] = [a0, a1], teams}. Actions only, cached to disk.

    Shipping whole replays (every observation, MBs each) to pool workers made the
    matcher IPC-bound: an hour for 6k jobs. Workers need only the action streams."""
    import pickle
    cache = Path(str(path) + ".compact.pkl")
    if cache.exists():
        return pickle.loads(cache.read_bytes())
    out = {}
    for eid, rep in load(path):
        n = len(rep["steps"]) - 1
        out[eid] = {"seed": rep["info"]["seed"], "n": n, "teams": rep["info"]["TeamNames"],
                    "steps": rep["configuration"]["episodeSteps"],
                    "acts": [[recorded(rep, 0, t), recorded(rep, 1, t)] for t in range(n)]}
    cache.write_bytes(pickle.dumps(out))
    return out


def _init(path):
    global _COMPACT
    _COMPACT = compact(path)


def match_one(job):
    """Seat `cand` in `seat`, replay the opponent's recorded actions, and count how
    many turns the candidate's actions equal the team's recorded ones."""
    eid, seat, cand = job
    c = _COMPACT[eid]
    me = opponents.get(cand)
    two = fastsim._takes_config(me)
    g = fastsim.Game(c["seed"], {"episodeSteps": c["steps"]})
    cfg = g.env.configuration
    n = c["n"]
    for t in range(n):
        try:
            mine = me(g.obs(seat), cfg) if two else me(g.obs(seat))
        except Exception:
            return eid, seat, cand, t
        if _canon(mine) != _canon(c["acts"][t][seat]):
            return eid, seat, cand, t
        acts = [None, None]
        acts[seat] = mine
        acts[1 - seat] = c["acts"][t][1 - seat]
        g.step(acts)
        if g.done:
            break
    return eid, seat, cand, n


def main() -> int:
    mode, path = sys.argv[1], sys.argv[2]
    if mode == "verify":
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 20
        items = list(load(path, n))
        with Pool() as pool:
            res = pool.map(verify_one, items)
        ok = sum(r[1] for r in res)
        for eid, good, got, want in res:
            if not good:
                print(f"  MISMATCH episode {eid}: fastsim {got} vs live {want}")
        print(f"{ok}/{len(res)} live episodes reproduced exactly")
        return 0 if ok == len(res) else 1

    cands = sys.argv[3].split(",")
    reps = compact(path)
    team_of = {}
    jobs = []
    for eid, c in reps.items():
        for seat in (0, 1):
            team_of[(eid, seat)] = c["teams"][seat]
            jobs += [(eid, seat, cand) for cand in cands]
    with Pool(initializer=_init, initargs=(path,)) as pool:
        res = pool.map(match_one, jobs, chunksize=8)
    best = {}
    for eid, seat, cand, k in res:
        if k > best.get((eid, seat), ("", -1))[1]:
            best[(eid, seat)] = (cand, k)
    Path(str(path) + ".match.json").write_text(json.dumps(
        [{"eid": e, "seat": s, "team": team_of[(e, s)], "cand": c, "prefix": k}
         for (e, s), (c, k) in best.items()]))
    by_team = defaultdict(list)
    for key, (cand, k) in best.items():
        by_team[team_of[key]].append((cand, k))
    print(f"{len(reps)} episodes. Longest identical prefix per team seat (719 = identical all game):\n")
    for team, v in sorted(by_team.items(), key=lambda kv: -len(kv[1]))[:30]:
        ks = sorted(k for _, k in v)
        top = defaultdict(int)
        for c, k in v:
            if k >= 144:
                top[c] += 1
        fam = ", ".join(f"{c}x{n}" for c, n in sorted(top.items(), key=lambda kv: -kv[1])[:3])
        print(f"  {team[:28]:28s} seats={len(v):3d}  median prefix {ks[len(ks)//2]:4d}  "
              f">=day6: {sum(k >= 144 for k in ks):3d}   {fam}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
