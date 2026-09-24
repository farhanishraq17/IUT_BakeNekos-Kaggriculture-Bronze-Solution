"""What else does an agent systematically waste? (the guard closed the shed leak)

Instruments the pinned engine's daily refresh to count, per player, per game:
  escapes      animal starved out (2 consecutive unfed days) -- structure stays,
               production gone for the rest of the season
  weeds        plant lost to 2 missed waterings / lifespan
  unfed        animal-days where the animal was not fed (escape precursor)
  uncared      fed animals that missed CARE, i.e. a forgone +1 production bonus
  full_yield   animal at max_held: output is being capped because nobody collected

    python runs/waste_probe.py <agent> <opp,opp> <seed_base> <n_seeds>
"""
import sys, collections
sys.path.insert(0, "opt"); sys.path.insert(0, "engine")
import fastsim, opponents

REF = fastsim.REF
W = collections.Counter()
_ctx = {"calls": 0}
_animals_orig = REF._daily_refresh_animals
_plants_orig = REF._daily_refresh_plants


def animals(farm, day):
    pid = _ctx["calls"] % 2          # engine loops players 0 then 1 each day
    board = len(farm["tiles"])
    before = {}
    for y in range(board):
        for x in range(board):
            t = farm["tiles"][y][x]
            if isinstance(t, dict) and "animal" in t:
                before[(y, x)] = (t["animal"], t["consecutive_unfed"], t["fed_today"],
                                  t["cared_today"], t["yield_units"])
                if not t["fed_today"]:
                    W[(pid, "unfed")] += 1
                elif not t["cared_today"]:
                    W[(pid, "uncared")] += 1
                if t["yield_units"] >= REF.ANIMALS[t["animal"]]["max_held"]:
                    W[(pid, "full_yield")] += 1
    _animals_orig(farm, day)
    for (y, x) in before:
        t = farm["tiles"][y][x]
        if not (isinstance(t, dict) and "animal" in t):
            W[(pid, "escapes")] += 1
    _ctx["calls"] += 1


def plants(farm, day, turns_per_day):
    pid = (_ctx["calls"]) % 2
    board = len(farm["tiles"])
    before = sum(1 for y in range(board) for x in range(board)
                 if isinstance(farm["tiles"][y][x], dict) and farm["tiles"][y][x].get("kind") == "PLANT")
    _plants_orig(farm, day, turns_per_day)
    weeds = sum(1 for y in range(board) for x in range(board)
                if isinstance(farm["tiles"][y][x], dict) and farm["tiles"][y][x].get("kind") == "WEED")
    W[(pid, "weeds_now")] = max(W[(pid, "weeds_now")], weeds)


REF._daily_refresh_animals = animals
REF._daily_refresh_plants = plants

if __name__ == "__main__":
    cand, opps = sys.argv[1], sys.argv[2].split(",")
    base, n = int(sys.argv[3]), int(sys.argv[4])
    games = 0
    tot = collections.Counter()
    wins = 0
    for o in opps:
        opp = opponents.get(o)
        for s in range(base, base + n):
            W.clear(); _ctx["calls"] = 0
            m = fastsim.run(opponents.get(cand), opp, seed=s)
            games += 1
            wins += m[0] > m[1]
            for (pid, k), v in W.items():
                if pid == 0:
                    tot[k] += v
    print(f"{cand}: {games} games, win {wins/games:.0%}")
    for k, v in sorted(tot.items()):
        print(f"   {k:12s} {v/games:8.2f} /game")
