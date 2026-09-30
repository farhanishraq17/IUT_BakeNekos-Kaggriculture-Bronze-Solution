"""Wait until every shard of the given tags is complete, then harvest each tag."""
import subprocess, sys, time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, "scripts"); import kfarm
tags = sys.argv[1:]
acc = kfarm.accounts()
while True:
    left = []
    for tag in tags:
        # only shards that actually launched: a push that hit the 5-session cap
        # never produces a kernel, so waiting on it would poll forever.
        jobs = [j for j in kfarm.load_jobs() if j.get("kind") == tag and j.get("ok")]
        with ThreadPoolExecutor(12) as ex:
            st = list(ex.map(lambda j: kfarm.status(j["alias"], acc[j["alias"]][1], j["ref"]), jobs))
        c = Counter(st)
        print(f"{tag}: {dict(c)}", flush=True)
        # error/cancel are terminal too, or one crashed shard means polling forever
        if sum(v for k, v in c.items() if k in ("complete", "error", "cancel_acknowledged", "cancel_requested")) < len(jobs):
            left.append(tag)
    if not left:
        break
    time.sleep(120)
for tag in tags:
    print(subprocess.run([sys.executable, "scripts/kfarm.py", "harvest_we", tag],
                         capture_output=True, text=True).stdout[-200:], flush=True)
