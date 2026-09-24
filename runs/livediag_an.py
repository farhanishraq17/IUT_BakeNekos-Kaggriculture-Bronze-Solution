import json, glob, sys, collections
for sub in sys.argv[1:]:
    ids = json.load(open(f"runs/livediag/{sub}.ids"))
    print("==", sub)
    for eid in ids:
        f = glob.glob(f"runs/livediag/{eid}/*.json")
        if not f: continue
        d = json.load(open(f[0], encoding="utf-8"))
        info = d["info"]; agents = info.get("Agents") or []
        seat = next((i for i, t in enumerate(info["TeamNames"]) if t == "Farhan Ishraq"), None)
        if seat is None:
            print(eid, "seat?", [list(a.keys()) for a in agents][:1]); continue
        last = d["steps"][-1]
        st = [s.get("status") for s in last]; rw = [s.get("reward") for s in last]
        # per-step statuses for us: any ERROR/TIMEOUT; also max obs duration if present
        bad = collections.Counter(s[seat].get("status") for s in d["steps"])
        win = "W" if rw[seat] > rw[1-seat] else "L"
        print(eid, win, st, rw, info["TeamNames"][1-seat][:24], dict(bad), len(d["steps"]))
