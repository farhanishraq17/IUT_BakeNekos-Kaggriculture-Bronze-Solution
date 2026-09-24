import sys, time
sys.path.insert(0, "scripts")
import kfarm
while True:
    live = kfarm.live_accounts()
    jobs = [j for j in kfarm.load_jobs() if j.get("kind") == sys.argv[1] and j["alias"] in live]
    statuses = [kfarm.status(j["alias"], live[j["alias"]][1], j["ref"]) for j in jobs]
    n_done = sum(1 for s in statuses if s == "complete")
    print(f"{n_done}/{len(jobs)} complete", flush=True)
    if n_done == len(jobs):
        break
    time.sleep(90)
