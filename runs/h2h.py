"""Direct head-to-head, both seats, paired seeds."""
import sys
sys.path.insert(0, "opt"); sys.path.insert(0, "engine")
import fastsim, opponents
a, b = sys.argv[1], sys.argv[2]
base, n = int(sys.argv[3]), int(sys.argv[4])
A, B = opponents.get(a), opponents.get(b)
w = l = d = 0
for s in range(base, base + n):
    for seat in (0, 1):
        m = fastsim.run(A, B, seed=s) if seat == 0 else fastsim.run(B, A, seed=s)
        me, them = (m[0], m[1]) if seat == 0 else (m[1], m[0])
        w += me > them; l += me < them; d += me == them
print(f"{a}\n  vs {b}: {w}W {l}L {d}D  = {w/(w+l+d):.1%} over {w+l+d} games")
