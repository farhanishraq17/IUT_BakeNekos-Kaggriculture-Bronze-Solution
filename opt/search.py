"""Population hill-climber over the policy genome. Runs identically local and on Kaggle.

Stdlib only, checkpoints to JSON so islands can be merged between rounds.

    python opt/search.py --gens 40 --pop 48 --seeds 6 --out runs/local.json
    python opt/search.py --resume runs/local.json --minutes 60
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "engine"))

import fastsim  # noqa: E402
import opponents  # noqa: E402
import policy  # noqa: E402


def evaluate(args):
    """(genome, seeds, opp_names, mode) -> fitness. Runs in a worker process.

    Every seed is played from both seats against every panel member, because the
    seats are not symmetric (player 0 acts first in the market lockstep).

    `cash` mode is the bootstrap: raw money is dense and gets a genome from "dies
    on day 3" to "runs a farm". `win` mode is the real objective -- the ladder
    scores wins only, so margin is a tiebreak, not the target."""
    genome, seeds, opp_names, mode = args
    me = policy.make_agent(genome)
    cash = score = 0.0
    n = 0
    for opp_name in opp_names:
        opp = opponents.get(opp_name)
        for s in seeds:
            for swap in (False, True):
                m = fastsim.run(opp, me, s) if swap else fastsim.run(me, opp, s)
                a, b = (m[1], m[0]) if swap else (m[0], m[1])
                cash += a
                score += 1.0 if a > b else (0.5 if a == b else 0.0)
                n += 1
    return (cash / n) if mode == "cash" else (score / n * 1e6 + cash / n)


def mutate(g, rng, sigma):
    out = []
    for i, v in enumerate(g):
        span = policy.HI[i] - policy.LO[i]
        out.append(v + rng.gauss(0, sigma * span) if rng.random() < 0.35 else v)
    return policy.clamp_genome(out)


def crossover(a, b, rng):
    return [a[i] if rng.random() < 0.5 else b[i] for i in range(policy.N)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gens", type=int, default=30)
    ap.add_argument("--pop", type=int, default=48)
    ap.add_argument("--elite", type=int, default=8)
    ap.add_argument("--seeds", type=int, default=6)
    ap.add_argument("--seed-base", type=int, default=1000)
    ap.add_argument("--opp", default="starter",
                    help="comma-separated opponent names (see opt/opponents.py)")
    ap.add_argument("--mode", default="cash", choices=["cash", "win"])
    ap.add_argument("--sigma", type=float, default=0.18)
    ap.add_argument("--procs", type=int, default=0)
    ap.add_argument("--minutes", type=float, default=0.0, help="wall-clock budget; 0 = use --gens")
    ap.add_argument("--rng", type=int, default=0)
    ap.add_argument("--out", default="runs/search.json")
    ap.add_argument("--resume", default="")
    ap.add_argument("--island", default="local")
    args = ap.parse_args()

    opp_names = [o.strip() for o in args.opp.split(",") if o.strip()]
    for o in opp_names:
        opponents.get(o)  # fail fast in the parent, not 48 times in the pool
    rng = random.Random(args.rng or int(time.time()))
    procs = args.procs or os.cpu_count()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    pop = []
    if args.resume and Path(args.resume).exists():
        ck = json.loads(Path(args.resume).read_text())
        pop = [policy.clamp_genome(g) for g in ck.get("elites", [])]
        print(f"resumed {len(pop)} elites from {args.resume}")
    # Seed the pool with the hand-written genome so the search starts from
    # "plays the game badly" rather than "does nothing at all".
    if len(policy.SEED_GENOME) == policy.N:
        pop.append(policy.clamp_genome(policy.SEED_GENOME))
    while len(pop) < args.pop:
        pop.append(policy.random_genome(rng))

    t_start = time.time()
    best_g, best_f = None, -1e18
    history = []
    gen = 0
    with Pool(procs) as pool:
        while True:
            if args.minutes and (time.time() - t_start) / 60 >= args.minutes:
                break
            if not args.minutes and gen >= args.gens:
                break
            # Rotate the seed block each generation: a genome that only wins on
            # one town-shop draw is not a genome we want.
            seeds = [args.seed_base + gen * args.seeds + i for i in range(args.seeds)]
            fits = pool.map(evaluate, [(g, seeds, opp_names, args.mode) for g in pop])
            ranked = sorted(zip(fits, pop), key=lambda p: -p[0])
            if ranked[0][0] > best_f:
                best_f, best_g = ranked[0][0], list(ranked[0][1])
            elites = [g for _f, g in ranked[: args.elite]]
            mean = sum(fits) / len(fits)
            history.append({"gen": gen, "best": ranked[0][0], "mean": mean,
                            "t": round(time.time() - t_start, 1)})
            print(f"gen {gen:3d}  best={ranked[0][0]:12,.0f}  mean={mean:12,.0f}  "
                  f"({time.time()-t_start:6.0f}s)", flush=True)

            nxt = list(elites)
            while len(nxt) < args.pop:
                a, b = rng.choice(elites), rng.choice(elites)
                nxt.append(mutate(crossover(a, b, rng), rng, args.sigma))
            pop = nxt
            gen += 1

            out.write_text(json.dumps({
                "island": args.island, "gen": gen, "best_fitness": best_f,
                "best": best_g, "elites": elites, "history": history[-50:],
                "args": vars(args),
            }, indent=1))

    print(f"\nbest fitness {best_f:,.0f} after {gen} generations")
    print("genome:", json.dumps(dict(zip(policy.NAMES, [round(v, 3) for v in best_g]))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
