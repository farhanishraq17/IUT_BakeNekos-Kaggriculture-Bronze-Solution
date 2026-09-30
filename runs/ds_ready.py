"""Block until every live account's kagri-panel dataset reports ready."""
import sys, time
sys.path.insert(0, "scripts"); import kfarm
live = kfarm.live_accounts()
pending = set(live)
while pending:
    for a in sorted(pending):
        u, t = live[a]
        out = kfarm.kag(a, t, "datasets", "status", f"{u}/kagri-panel", timeout=120).stdout.strip()
        if "ready" in out.lower():
            pending.discard(a); print(a, "ready", flush=True)
        elif "error" in out.lower():
            pending.discard(a); print(a, "ERROR", out[:120], flush=True)
    if pending: time.sleep(30)
print("all ready")
