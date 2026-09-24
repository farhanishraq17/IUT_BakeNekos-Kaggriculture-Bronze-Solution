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
        jobs = [j for j in kfarm.load_jobs() if j.get("kind") == tag]
        with ThreadPoolExecutor(12) as ex:
            st = list(ex.map(lambda j: kfarm.status(j["alias"], acc[j["alias"]][1], j["ref"]), jobs))
        c = Counter(st)
        print(f"{tag}: {dict(c)}", flush=True)
        if c.get("complete", 0) < len(jobs):
            left.append(tag)
    if not left:
        break
    time.sleep(120)
for tag in tags:
    print(subprocess.run([sys.executable, "scripts/kfarm.py", "harvest_we", tag],
                         capture_output=True, text=True).stdout[-200:], flush=True)
