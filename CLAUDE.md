# Kaggriculture — project context

Kaggle simulation competition: two agents farm 10×10 plots for 720 turns (30 days × 24 turns);
most coins at the end wins. Rating is win/loss only — **margin does not matter**, so a +1 coin win
equals a +50k win. Final leaderboard is a Bradley-Terry tournament over your **latest 2 submissions**.

- Competition: https://www.kaggle.com/competitions/kaggriculture
- 5 submissions/day. Entry deadline **2026‑09‑23**, final submission **2026‑09‑30**.
- Prizes: top 10 get $5,000 each.
- **Do not submit without the user's explicit approval** (standing instruction, 2026-09-24).
- **Ratings drift down as the field strengthens: never compare ratings from different days.** The
  byte-identical file that scored 2583.1 on 09-21 scored 2192.5 on 09-23. Compare agents at the same age.

## FINAL SUBMISSION RULES (verified 2026-09-30 against the official Rules and Overview pages)

- **Rules §2:** max **5 submissions per day**; "you may select up to two (2) Final Submissions". For this
  simulation competition the **Overview > Evaluation** page fixes the selection: *"only the latest 2 submissions
  are tracked. The latest 2 submissions are also used for final leaderboard evaluation."* There is no manual
  selection — **the final pair is simply the last two submissions made before the deadline.** Confirmed on the
  logged-in Submissions page (2026-09-30): every submission except the latest two is marked *"Disabled due to the
  competition's active submission limit."*
- **Final Submission Deadline: 2026-09-30 23:59 UTC** (= 2026-10-01 05:59 Bangladesh time, the machine's "BST").
  Games then run ~2 weeks (Oct 1 to ~15); a Bradley-Terry fit over those episodes is the final leaderboard, and the
  team is shown at its **best-scoring** bot of the two.
- **The daily limit resets at 00:00 UTC** (= 06:00 Bangladesh time). This is Kaggle's platform rule, not stated on
  the competition page; confirmed by the logged-in Submit dialog at 22:53 UTC on 2026-09-29: "You have 2
  submissions remaining today. This resets in an hour." (3 of 5 used that UTC day).
- **Every new submission evicts the older of the two tracked ones.** Therefore:
  - **The last two submissions before the deadline ARE the final pair — they must be our two best builds.**
  - On the final day (2026-09-30 UTC, 5 submissions) that leaves **at most 3 submissions for testing**, and the
    **last 2 submissions are reserved for the final pair.**
  - To keep an already-live submission in the final pair, you can make **at most one** more submission after it.
  - Re-submitting a build's file makes a *new* submission that restarts at rating 600; that is acceptable because
    newer bots play more often and the post-deadline games decide the final ranking. Leave a margin: finish the
    final two submissions hours before 23:59 UTC, and confirm both pass Kaggle's validation episode.
- A test submission needs ~3-4 h of live games for a rough read and ~1 day to settle, so final-day tests must
  go in as early as possible after the 00:00 UTC reset.
- Submit only with the user's explicit approval, from the team account (the only credential reachable in
  Secrets.env signs as `didhitinahid`, which is on the team IUT_BakeNekos).

## DAILY RITUAL (do this every session, before anything else)

The leaderboard moves every day on new public features. Falling behind by one day has already cost
us the top spot in our own panel twice.

```bash
python - <<'EOF'   # or: kaggle kernels list --competition kaggriculture --sort-by dateRun --csv
import sys, subprocess, csv, io; sys.path.insert(0,"scripts"); import kfarm
tok = kfarm.accounts()["ISHRAQ"][1]; env = kfarm.env_for("ISHRAQ", tok); env["PYTHONIOENCODING"]="utf-8"
r = subprocess.run(["kaggle","kernels","list","--competition","kaggriculture","--sort-by","dateRun",
                    "--page-size","50","--csv"], capture_output=True, text=True, encoding="utf-8", env=env)
print(r.stdout)
EOF
python runs/fetch_out.py <owner/slug> ...      # the EXACT submitted file, not notebook source
sha256sum runs/newout/*/main.py                # hash-dedupe: 4 notebooks have shipped ONE file
python runs/smoke.py <name>                    # loads + one game vs starter
python runs/discard_probe.py <name> <opps> <seed> <n>   # does it leak? -> is the guard worth testing
python scripts/panel_dataset.py                # push the panel to all accounts before a farm run
```

**Do not judge a new build by its $-vs-starter figure.** harvest-ledger-0925 posted $198,166 (the
highest ever measured) and lost to us by 12.4pp over 162k games. Money vs a passive opponent measures
farming an empty market, not winning a contested one.

## Ground truth

The **engine source is the spec**, not the docs. Pinned copy: `engine/kaggriculture_ref.py`
(from `kaggle-environments==1.32.7`, `kaggle_environments/envs/kaggriculture/`).
Official docs (`kaggriculture/README.md`, `kaggriculture/AGENTS.md`) are accurate but incomplete.
When they disagree, the source wins. Re-read the source before trusting any mechanic below.

## Hard constraints

- Submission is `main.py` with `def agent(observation, configuration=None)` at repo root of the tarball.
- `actTimeout: 1` second per turn, `remainingOverageTime: 60` for the whole episode.
  Budget **< 20 ms/turn**; the reference agent runs 1.4 ms mean / 197 ms worst.
- **Stdlib only** in `main.py`. No numpy, no file reads, no `__file__`, no network. Embed all data as literals.
- Public agents are Apache-2.0. If we fork any of them, keep `NOTICE.txt` and the upstream
  attribution headers intact. Non-negotiable.

## Engine facts that decide the game

Verified against `engine/kaggriculture_ref.py`. Numbers computed in `opt/market_math.py`.

**Market is the whole game.** `price(inv) = base ± amp·f(|inv − 10000|)`, floored at $1, per product.
Every product starts at inventory 10,000. Both players and the town share one market.

| Product | Units you can dump before $1 | Total cash in that dump | Price once town drains 450 / 900 units |
|---|---|---|---|
| EGG | ~unlimited (6000 → still $37) | $220k | $97 / $573 |
| WHEAT | ~unlimited (6000 → still $19) | $111k | $46 / $55 |
| TOMATO | 529 | $11k | **$414 / $2520** |
| CARROT | 842 | $11k | **$70 / $385** |
| MELON | 158 | $26k | $304 / $310 |
| FERTILIZER | 493 | $25k | n/a (town never buys it) |
| MILK | 76 | $6k | $344 / $421 |
| WOOL | 59 | $8k | $252 / $258 |
| STRAWBERRY | 62 | $4k | $298 / $372 |

Consequences:
- **Eggs and wheat never crash** (log glut curve). Goose output is bounded only by labor.
- **Premium goods are traps.** 62 strawberries, 59 wool, 76 milk and the price is $1 — permanently,
  because a sale at $1 does not add to market inventory but nothing restores it either except town demand.
- **Carrot, tomato and egg use a `hinge` scarcity curve.** Town shops drain them for free, so if nobody
  grows them the price runs away quadratically. Two pet cafés drain 24 carrots/day; a pizza shop drains
  6 tomatoes/day. This is the largest exploitable edge in the game and it is fully observable
  via `obs["market"]["inventory"]`.
- Fertilizer is excluded from all town demand, so its inventory only ever grows. Sell it early or not at all.

**Labor, not land or cash, is the binding constraint.** Hire cost is `fib(n)` per day, reset daily:
11 units (1 farmer + 10 hands) costs **$143/day** for 264 actions. 15 hands cost $1596. Hire hard, early.
Movement burns actions — cluster work near the shed.

**Per-action revenue ranking** (the thing to optimize):
- `COLLECT_FERTILIZER` → 1 fertilizer ≈ $50–100 for one action. Best single action in the game while the price holds.
- Goose loop: `FEED`+`CARE` daily banks +1, paid out on the next daily production → **2 eggs/day/goose** at ~$40.
- Melon: 13 actions → 6 melons, but only ~158 melons exist before the floor. Race the opponent to sell them.
- Wheat is mostly animal feed; growing it beats `BUY_PRODUCT WHEAT` (buying drains inventory and raises the price against you).

**Timing and survival rules that kill agents:**
- A new plant starts at `consecutive_unwatered = 1`. **Not watering on the planting day kills it that night.**
- Two consecutive missed days → plant becomes a weed / animal escapes permanently.
- Shed cap is 100 items *including animals and produce*; overflow at end-of-day is **discarded**. Seeds are exempt.
- Hands spawn on a shed-access tile that may be LOCKED; locked tiles are passable, tile ops on them no-op.
- Max 10 market orders/turn; extras are silently dropped.
- 8 town shops unlock on days 3,6,…,24, drawn **with replacement** from 8 types. The draw comes from
  `random.Random((seed*1000003) ^ day)` after one `random()` call per empty unlocked tile on *both* farms.
  The seed is a hidden 31-bit int — not recoverable in-episode. Treat shop draws as unpredictable, and
  **react** to them instead.

**Adversarial market microstructure (proven on the live ladder):**
Orders resolve one unit at a time, in lockstep across both players, at the shared current price.
So your buys raise the price your opponent pays in the same turn, and your sells lower what they receive.
The public meta opens turn 0 with a wheat round-trip sized to make the opponent's second wheat purchase
cost ~$60 more, denying them one melon seed. Optimal size is **~40–65 units; ≥75 backfires on you**.

## The public meta

The top of the leaderboard is one shared lineage of **open-loop action tapes** (V43→V44→V45→V48→V50,
pipe-N, "The 2945 Farm"): a `Chassis` replays a precomputed 720-turn action list, a router picks one of
~64 tapes at step 144 from the first two unlocked shops, switches to a liquidation tape at step 648, and
~30 reactive wrapper layers repair weeds, rescue unwatered tiles and reorder sales.
Nobody appears to be running large-scale offline trajectory optimization. That is our opening.

## The live ladder and community resources

The field moves in *days*. Re-survey before every submission decision:
`kaggle kernels list --competition kaggriculture --sort-by dateRun`, then
`python scripts/fetch_notebooks.py <refs>` and, for notebooks that build `main.py` internally,
`kaggle kernels output <ref>` — the output IS the exact file they submitted.

Live ladder, `georgymamarin/kaggriculture-episodes` snapshot 2026-09-21 (9,575 teams):
**#1 3291 · #10 (prize cutoff) 3014.5 · #50 2869 · #100 2823 · #188 2765 · #1000 2430.**
Those are 09-21 numbers and the whole scale drifts (see the header): use them for shape, not targets.
New submissions start at 600 and need a day or more to converge.

Use `runs/fetch_out.py <owner/slug> ...` to pull kernel **outputs** — the exact submitted `main.py`
or `submission.tar.gz`. That is always preferable to extracting an agent from notebook source.
`scripts/fetch_notebooks.py` is for reading the authors' *method notes*, which is where the feature
ideas live (see progress.md section 5 for the current meta's features).

Community datasets (downloaded to `data/`, gitignored):
- `destbreso/kaggriculture-donor-agents-20260902` → `data/donors/`: 93 runnable agents with
  provenance, licence and sha (`donors.csv`), `arena.py`, a bit-exact C++ engine (`kagsim`, ~50 µs/game —
  irrelevant to us because the *agents* cost ~1 s/game, not the engine), and finished result matrices
  in `examples/` (`window_matrix_20260921.csv`: 40 recent agents × 3,354 games each).
- `georgymamarin/kaggriculture-episodes` → `data/episodes/`: every live game's outcome and
  ratings (`episodes.csv`, `agents.csv`, `teams.csv`). Replays are 20+ GB; not downloaded.

Current best public agents — **this list goes stale in ~24 h; re-survey daily.**
2026-09-26 (farm `broad`, 339,857 games, 16 lineages): **guard:c-frontier-0923:14:sMILK (ours) 93.7%** ·
c-frontier-0923 93.1% · c-shepherds-0925 85.7% · c-masterhybrid-2965 78.8% · guard:shoprouter 53.3% ·
c-shoprouter-v7 48.4% · c-v49 22.5% · c-utils-v1 (= v43-local-confirmed) 3.1%.
The 09-21 ranking (koshinm 79.6%, tetsutani 76.9%) is obsolete: both are now bottom of the field.

**Notebook score badges are frozen at submission time and mean nothing today.** v43 shows 2550.5 and
wins 3.1%; v49 shows 2467.0 and wins 22.5%; shop-router shows 2689.9 and wins 48.4%.

**Evaluation rule learned the hard way: the opponent field must be fixed and disjoint from the
candidate list.** Including a candidate's own base as an opponent credits the variant for beating its
own mirror and inflates the delta (it turned a true +2.48pp into a reported +4.34pp). See
progress.md section 3.

koshinm's notebook was **withdrawn** after the donor library captured it (403 now). It was
published under Kaggle's default Apache-2.0, so the donor copy is usable with attribution. The code
is 6 nested lzma layers of koshinm's own "market operators" with **no licence notice at any level**,
so attribution must be *added* (see `runs/sub_koshinm/main.py`). Verify its sha against `donors.csv`.

Some agents declare `agent(obs, config)` with no default. Kaggle's runner passes the configuration
as a second argument, so fastsim now does too (`_takes_config`). Before that fix, the 2887 agent raised
on every turn. Parity and all prior results were unchanged by the fix.

## Findings, 2026-09-22 (these supersede anything older above)

**Live ladder agrees with world-eval, not with the 216-game tournament.** Live: tetsutani-0921 2606,
koshinm-0921 2466 (both still climbing; fork-2801 1935). World-eval (254 seeds, ~5.5k games each vs the
12-agent panel): **tetsutani 74.7% > koshinm 71.0%**; head-to-head 52/48 over 426 games.
Small tournaments rank these agents wrongly: use `opt/worldeval.py` + the farm, never < ~1k games.

**koshinm collapses in carrot/tomato worlds** (PET_CAFE / PIZZA / FARMERS_MARKET early): 58.7% there
vs 73.3% elsewhere. tetsutani is *stronger* there (78.6%): it has a built-in carrot layer (`V9_CARROT_*`).

**tetsutani's blind spot is shop-router-v7: 1.9% (8/426)**. That is ~39% of all its panel losses. It is a
composition gap, not front-running: shop-router out-produces it on milk/strawberry/fertilizer.
But shop-router is not in the ~3000 field (below), so this matters only on the way up.

**Routing within an opening family is worthless here.** Family H (tetsutani / wheat-seller /
one-more-wheat) has a per-game oracle equal to the default: when tetsutani loses, its siblings lose the
same game. Family K oracle +0.7 pts; CV gain 0. `scripts/build_router.py` is verified lossless (forced
routes reproduce each candidate to the coin) if a future family has real spread.

**The top-10 are private and reactive.** Replays: `ashok205/kaggriculture-top10-replay-archive`
(`data/top10/`, daily parquet, `info.seed` + every action). 40/40 live games reproduce exactly in fastsim.
No top team matches any public agent even on turn 0 (Majkel1337/DSM open "buy COW 1 + WHEAT 5", a turn
ahead of the public lineage). Majkel has 12 distinct openings by turn 24, so it reacts from the start;
**open-loop replay cloning of top teams will not work**. Top-10 games are ~all top-vs-top, so the
~3000 field is private agents that no offline panel of ours represents; the live ladder is the only
evaluator there. The "vs top-10 tapes" test (`opt/tapeeval.py`) is **uninformative**: every candidate
scores ~80-90% because an open-loop reactive agent breaks, and the top six land within 0.6 pts.

**Both top agents already liquidate perfectly** ($0 unsold at the end, `opt/leftover.py`). tetsutani's
losses are close (median deficit $1,239; 338/1,065 losses under $500), so the lever is small systematic
edges, measured paired: `opt/sweep_eval.py` + runtime variants (`name@KNOB=VALUE`, see `opponents.py`).
Knobs must be assigned exactly once; `_RACE_HORIZON_CLONE` is assigned twice in tetsutani (excluded).

**Shops can be shaped but barely steered** ("God's mode" notebook): a legal one-cell DIG before an
unlock changes the next shop 76.6% of the time; *directed* control reaches ~10-18% of matches;
score impact unmeasured. The same seed produced different shop sequences in two of our games because
empty-tile counts differ. Parked.

## The opponent panel

`scripts/extract_agents.py` pulls runnable agents out of the downloaded notebooks
(three embedding styles: `gzip+b64`, `zlib+b85`, plain `%%writefile`). It works off the
AST, not regex, because the notebooks use implicit multi-line string concatenation and
lists of byte chunks. It writes **bytes** — several of these pin a SHA over their own
source including line endings, and text-mode writing corrupts them (this cost an hour once).

Extracted and verified running (`python opt/opponents.py`), scored against `starter`:

| Agent | vs starter | ms/game | note |
|---|---|---|---|
| v50-early-yarn-commit | $195,915 | 1910 | strongest; sha matches its notebook's pin |
| v54-idle-workers | $195,250 | 2357 | 1 MB source, too big to bundle into a worker |
| 2820-score / cloning-agent / **pipe-7** | $187,493 | 760–1180 | **identical output — same tape** |
| shop-router-reactive-v7 | $186,809 | 922 | |
| 95-5-win-rate-via-replay-routing | $185,641 | **190** | cheapest useful panel member |
| starter (baseline) | $3,585 | 96 | |

**Money vs starter is the wrong ranking.** Head-to-head round-robin (`python opt/tournament.py`,
8 held-out seeds × both seats, 2026-09-21):

| Agent | Overall win % | Notable |
|---|---|---|
| **v50-early-yarn-commit** | **89.3%** | beats fork-2801 16-0; only loses to v54 (31%) |
| v54-idle-workers | 83.0% | beats v50 69%, but loses to shop-router 88% |
| shop-router-reactive-v7 | 75.0% | |
| fork-2801 (the "2801" notebook build) | 48.2% | a 16-Sept rating; the lineage has moved on |
| pipe-7 | 44.6% | |
| 2820-score (V44 base, no layers) | 17.9% | the layers are worth ~30 points of win rate |

It is **non-transitive** (v54 > v50 > shop-router > v54), so no single agent dominates —
which is why the two tracked submissions should cover each other's losses.

Strong agents crash each other's markets: the fork makes $187k vs starter but ~$80k vs itself.
The harness is sound for these agents — verified no state leaks across sequential games or
between seats in self-play (they key state per player and reset at step 0).

Three of them produce byte-identical results against a passive opponent, confirming the
notebooks' own claim that the lineage shares one tape; they only diverge when the opponent
interacts with the market. **Don't spend panel slots on more than one of them.**

Panel games cost ~1–2 s each versus 140 ms for a self-play game, so the panel is a direct
tax on generations/hour. Hence the two-stage fitness: `--mode cash --opp starter` to
bootstrap, then `--mode win --opp <panel>` to refine.

Agents in `opponents/` are Apache-2.0 benchmarks: never edited, never shipped in our submission.

## Compute

Measured, not assumed.

| Resource | Capacity |
|---|---|
| Local | 20 logical cores, ~11 effective. 73 games/s for our own light policies; **~2-4 games/s** for the 1 MB public agents (~700 ms each per game) |
| Kaggle CPU session | 4 vCPU (~2.5 effective), 32 GB, Python 3.12, **12h** max |
| Concurrency | **5 batch CPU sessions per account** — a hard cap, pushing a 6th errors |
| Live accounts (2026-09-26) | ISHRAQ, DIDHITI, TASHIN, SALAM, Eshad, Mashrafi, Samin, **Nasif** → **40 concurrent kernels** |
| Pin a job to free accounts | `KAGRI_ACCOUNTS=Nasif python scripts/kfarm.py worldeval ...` |

`scripts/kfarm.py` drives it. Each account gets its own `KAGGLE_CONFIG_DIR`, so calls
run in parallel without fighting over `~/.kaggle/access_token` — never use
`use_kaggle_account.py` (global switch) inside the farm.

```bash
python scripts/kfarm.py accounts          # which tokens still authenticate
python scripts/kfarm.py run 240 5         # 5 islands/account, 240 min each
python scripts/kfarm.py status            # poll
python scripts/kfarm.py harvest           # pull islands -> runs/best.json
```

Gotchas that cost time once already:
- **Kaggle derives the kernel slug from the TITLE, not from metadata `id`.** Title must
  equal the slug or `kernels status` 404s with a misleading permissions error.
- Workers are one self-contained `.py` with the engine bundled in — no pip, no dataset,
  no internet, so nothing can fail on a missing input.
- Kernel output is retrievable with `kernels output` even though the kernel has no internet.
- **Submit only from ISHRAQ.** Training on teammates' accounts is fine; submitting the same
  agent from several accounts is multi-account abuse and disqualifies the team.

## What the strongest public agent actually does

From `python opt/analyze.py v50-early-yarn-commit` — instrumenting it beats decoding its
route tape. Consistent across every seed tried:

- **It is an animal farm, not a crop farm.** Finishes with 15–19 sheep + 4–8 cows and
  ~0 crop tiles, leaving ~73 tiles empty. Land is not the constraint; labour is.
- **Sheep count tracks YARN_STORE count** (3 yarn stores → 19 sheep; 2 → 6 sheep + 8 cows).
  Production follows the shop draw, because town demand is the only thing holding a premium
  price off the floor. Wool floors after 59 units with no yarn store and sustains 400+ with three.
- **It buys wheat rather than growing it** — 6–27 units/day via `BUY_PRODUCT`, and sells
  330–790 units. Wheat's glut curve is log-flat while the town drains it hard, so wheat
  *appreciates* ($25 → $46). It is a tradeable asset, not just feed.
- **Fertilizer is its highest-volume product** (350–470 units/season), free from animals,
  one action each.
- **Hires a flat ~10/day, ~300 per season.** Never a cash-fraction rule.
- Buys 2–3 land quadrants by day 12, mostly to unlock the other shed-access tiles.
- Sells concentrated at hours 0–1 (right after the town-centre tick) and 20–23 (shed-overflow guard).
- Plants carrots on days 25–26 and sells day 28 — a late flip into a town-drained hinge market.

All of this is encoded in the v2 genome tail. `opt/analyze.py <agent>` re-runs the analysis
on any panel member.

## Bugs this policy has already had

Each cost real money and none raised an exception. Check for them in any new policy code:

1. **Mutating the observation** (`shed[item] -= n`) — fastsim shares live state, so this grants
   free goods and corrupts every downstream result.
2. **All-or-nothing purchases** — `if money > price * need: buy(need)` buys *zero* when the
   bank is short, so the herd misses a feed, and two missed feeds lose the animal permanently.
   A $20k farm became $1k by day 29 from this one line. Always buy `min(need, affordable)`.
3. **Housing leading purchases** — building a structure per *wanted* animal carpets the farm in
   empty pastures on day 0. Housing must follow animals already bought, plus a small lookahead.

## Measurement discipline

The search rotates its seed block every generation, so its reported "best" is a high-water
mark on a lucky block — it read $93.5k for a genome that scores **$51k** on held-out seeds.
`python opt/evaluate.py <checkpoint...>` is the number that decides what gets submitted:
fixed seeds (31337+), both seats, never used during search.

## Layout

```
engine/    kaggriculture_ref.py (pinned) · kaggriculture.json · fastsim.py
           test_parity.py (the gate) · bench.py (throughput)
opt/       policy.py (genome -> agent) · search.py (island hill-climber)
scripts/   kfarm.py (multi-account kernel farm) · use_kaggle_account.py (manual switch)
agents/    main.py (submission)
opponents/ decoded public agents + their notebooks, the evaluation panel
runs/      jobs.json, island checkpoints, best.json (gitignored)
```

## Windows traps

- `multiprocessing` uses **spawn**: pool workers re-import `__main__`. Never run a
  pool from `python - <<HEREDOC` (it forks forever); always a real file with a
  `if __name__ == "__main__":` guard, and the worker function must be importable
  at module level (not defined in `__main__`).
- `fastsim` deliberately does **not** import `kaggle_environments` — that import
  enumerates every env on disk and costs ~8 s, which made pool startup dominate a
  140 ms game and pinned effective parallelism at 1.0x. Only `test_parity.py` imports it.

## Working rules

- **Never trust a change without the arena.** Every candidate is judged by win rate over
  ≥200 paired games (both seats, same seeds) against the `opponents/` panel. Margin is not the metric;
  win rate is. Local wins do not guarantee live rating — see `PLAN.md` for what we accept as evidence.
- `fastsim.py` must stay identical in behaviour to `kaggriculture_ref.py`.
  `python engine/test_parity.py` is the gate — full state digest at every step, three agent
  pairings per seed. Run it after every engine or fastsim edit.
- **Agents must never mutate the observation.** fastsim hands them the live state for speed,
  so `shed[item] -= n` inside a policy silently grants free goods and corrupts every result.
  This has already happened once. Track intended consumption in a local dict.
- Rollouts are embarrassingly parallel — always use the pool, never a bare loop.
- Before submitting: run the real `kaggle_environments` runner end-to-end, check DONE/DONE, 720 states,
  and worst-case per-call latency.

## Current state (2026-09-26) — read `progress.md` before acting

Live pair: **56558912** (Frontier-0923 + guard 14 + skip-MILK) and **56558917** (Shepherd's Herd-Safe
+ guard 14) — deliberately two *different lineages*. Best rating ever seen was 2583.1 on 09-21, which
is unreachable now: the scale drifts (section 3 of progress.md).

**Two wrappers pay and are shipped**, everything else is a measured negative:
- shed guard margin 14: **+1.72pp, z=18.78, 98,671 paired games**
- never sell MILK: **+0.64pp, z=9.47, 181,478 fresh-seed games** (milk floors at $1 after ~76 units;
  skipping STRAWBERRY instead is −1.84pp, so it is item-specific)

Ship with `scripts/bake_guard.py <base> 14 --skip MILK --out runs/<n>/main.py`, then
`runs/verify_bake.py` and `build_submission.validate()`.

**Closed levers — do not retry without a new hypothesis:** guard knobs (328k games, ±0.22pp),
cheap-first ordering (−1.89pp), sale-advance forecast (−2.9 to −28.8pp), idle-worker layer (+$7/game),
wheat speculation (8.3% vs 100%), cross-family routing (impossible — divergence at step 0),
fertilizer cutoff (0.00 on this base), our own from-scratch policy (6× behind).

**The live field is forks of our own base.** `runs/opp_id.py` over 30 replays: 23/30 opponents share
our lineage, diverging at step 150 (match depth must exceed 400 — the lineage shares one tape until
the router branches at 144). We beat the *public* versions ~100% and win 43% live, so their private
layers are worth about as much as ours.

**The meta is rock-paper-scissors:** shop-router beats our Frontier build 92.5%, Herd-Safe beats
shop-router 95-100%, we beat Herd-Safe 77.5%. Hence the cross-lineage pair.

## koshinm's internals (investigated) -- fixed via an EXTERNAL wrapper instead

koshinm-0921 shares the same "V9" lineage as tetsutani (identical header text: "RACEPX gate, RACE
..., COURIER, CARROT and HERD"; same constant names `_SR_MARGIN`, `V9_RACE_MARGIN`, `V9_CARROT_RATIO`
appear in its decoded source). Its own `_SR_MARGIN = 4`, even more conservative than tetsutani's
original 8 — circumstantial evidence the same fix might help, but **not actionable**: koshinm is 6
nested lzma/base85 layers deep with multiple sibling branches at each level, and the branch that
decodes+compiles cleanly (`def agent` present, valid Python) does **not** reproduce the real agent's
behavior (verified: differs on identical seed+opponent). The live branch was not found. Modifying and
repacking through 6 layers also risks tripping an internal `EXPECTED_MAIN_SHA256`-style assertion seen
in a sibling branch. Not worth the effort/risk given the confirmed tetsutani win already shipped.

**Resolved differently:** instead of editing koshinm, `opt/shed_guard.py` wraps ANY agent externally --
runs the base agent's action unchanged, then appends proactive SELL orders if projected shed+carried
would exceed the 100-item cap. Needs zero access to internals. Confirmed on koshinm: **+2.86pp, z=8.12,
n=7240**, positive on all 8 panel opponents (submitted as 56455306). Use `opponents.get("guard:NAME:MARGIN")`
to evaluate this on any other agent; `scripts/bake_guard.py` to ship it.
