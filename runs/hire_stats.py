"""Do our live opponents hire more than we do? Count HIRE orders per game, per seat."""
import json, glob, statistics, collections
rows = []
for f in sorted(glob.glob("runs/livediag/*/*.json")):
    rep = json.load(open(f, encoding="utf-8"))
    names = rep["info"]["TeamNames"]
    us = next((i for i, t in enumerate(names) if t == "Farhan Ishraq"), None)
    if us is None:
        continue
    hire = [0, 0]
    for t in range(1, len(rep["steps"])):
        for p in (0, 1):
            a = rep["steps"][t][p].get("action")
            if isinstance(a, dict):
                for o in (a.get("market") or []):
                    if isinstance(o, list) and o and o[0] == "HIRE":
                        hire[p] += 1
    rw = [float(s.get("reward") or 0) for s in rep["steps"][-1]]
    rows.append((hire[us], hire[1 - us], rw[us] > rw[1 - us]))
mine = [r[0] for r in rows]; theirs = [r[1] for r in rows]
won = [r for r in rows if r[2]]; lost = [r for r in rows if not r[2]]
print(f"games {len(rows)}  (won {len(won)}, lost {len(lost)})")
print(f"  our HIRE/game        mean {statistics.mean(mine):6.1f}  median {statistics.median(mine):6.1f}")
print(f"  opponent HIRE/game   mean {statistics.mean(theirs):6.1f}  median {statistics.median(theirs):6.1f}")
if won:  print(f"  when we WIN : us {statistics.mean([r[0] for r in won]):6.1f}  them {statistics.mean([r[1] for r in won]):6.1f}")
if lost: print(f"  when we LOSE: us {statistics.mean([r[0] for r in lost]):6.1f}  them {statistics.mean([r[1] for r in lost]):6.1f}")
