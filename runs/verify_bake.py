"""Baked file must behave exactly like the runtime guard:BASE:MARGIN variant."""
import sys
sys.path.insert(0, "opt"); sys.path.insert(0, "engine")
import fastsim, opponents
# usage: verify_bake.py [baked_path] [runtime_variant] [opponent]
args = sys.argv[1:] + ["runs/sub_frontier_guard/main.py", "guard:c-frontier-0923:14", "c-herdsafe-v3"][len(sys.argv[1:]):]
baked = opponents.get_path(args[0])
runtime = opponents.get(args[1])
opp = opponents.get(args[2])
for seed in (31337, 31338, 31339):
    a = fastsim.run(baked, opp, seed=seed)
    b = fastsim.run(runtime, opp, seed=seed)
    print(f"seed {seed}: baked {a}  runtime {b}  {'MATCH' if a == b else 'MISMATCH'}")
    assert a == b, "baked file differs from the evaluated variant"
print("bake verified identical")
