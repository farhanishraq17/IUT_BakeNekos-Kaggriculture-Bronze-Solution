"""Poll until every kernel of TAG is terminal, then run the given kfarm command.
Status polling only (no harvest), so it never races a wait_tags.py harvester."""
import subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, "scripts"); import kfarm
tag, cmd = sys.argv[1], sys.argv[2:]
acc = kfarm.accounts()
while True:
    jobs = [j for j in kfarm.load_jobs() if j.get("kind") == tag and j.get("ok")]
    with ThreadPoolExecutor(12) as ex:
        st = list(ex.map(lambda j: kfarm.status(j["alias"], acc[j["alias"]][1], j["ref"]), jobs))
    if jobs and all(s in ("complete", "error", "cancel_acknowledged", "cancel_requested") for s in st):
        break
    time.sleep(90)
print(f"{tag} done; launching: {' '.join(cmd[:3])} ...", flush=True)
print(subprocess.run([sys.executable, "scripts/kfarm.py", *cmd], capture_output=True, text=True).stdout[-300:], flush=True)
