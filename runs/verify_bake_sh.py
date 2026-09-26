"""Baked file must behave exactly like the runtime guard:BASE:MARGIN variant."""
import sys
sys.path.insert(0, "opt"); sys.path.insert(0, "engine")
import fastsim, opponents
baked = opponents.get_path("runs/sub_shepherds_guard/main.py")
runtime = opponents.get("guard:c-shepherds-0925:14")
opp = opponents.get("c-herdsafe-v3")
for seed in (31337, 31338, 31339):
    a = fastsim.run(baked, opp, seed=seed)
    b = fastsim.run(runtime, opp, seed=seed)
    print(f"seed {seed}: baked {a}  runtime {b}  {'MATCH' if a == b else 'MISMATCH'}")
    assert a == b, "baked file differs from the evaluated variant"
print("bake verified identical")
