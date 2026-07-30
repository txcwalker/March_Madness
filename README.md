# March Madness Tournament Simulator

Status: rebuild in progress | 2026-07-28

## Purpose

Predicts NCAA Division I Men's Basketball Tournament outcomes using historical performance data (Kaggle's March Machine Learning Mania dataset) and KenPom efficiency ratings, trains matchup-win-probability models, and Monte Carlo-simulates full brackets to estimate each team's odds of advancing through every round.

This is a ground-up rebuild of a multi-year project (previously `txcwalker/March_Madness_2024` on GitHub, most recently developed in a sibling folder `March_Madness_2026`). The prior codebase worked but had drifted: a broken import chain, hardcoded season years and bracket sizes scattered across files, a manual Excel step with no code behind it, and duplicate notebook/script pairs that fell out of sync. This rebuild ports the working modeling logic over deliberately, module by module, into a structure designed to survive year-over-year reuse without hand-editing.

See [AGENTS.md](AGENTS.md) for the AI handoff contract, [DEVELOPMENT.md](DEVELOPMENT.md) for the workspace map and setup, and [GOAL_TRACKER.md](GOAL_TRACKER.md) for live status.

## Goals

1. **One-config season changeover, with years kept side by side.** A single `config/season.yaml` (year, bracket size, round count, play-in game count) drives the whole pipeline — no hunting through files for hardcoded years or team counts. Reusing the repo each year means *toggling* between seasons, not overwriting the last one: `data/raw`, `data/processed`, and `data/outputs` are organized per-year (e.g. `data/raw/2026/`) so multiple seasons' data and results coexist, and changing `year` in config is what switches which one a run uses.
2. **Play-in-count-agnostic bracket structure.** The 64-team, 6-round main bracket (`R1`...`R6`) is a fixed convention from Kaggle's own data — that's not going away and isn't something to abstract. What changes with expansion is the play-in stage: `field_size = 64 + num_play_in_games` (68 = 64+4 today; a 76-team format would be 64+12). `bracket/structure.py` derives everything from `num_play_in_games`, so that stays a config change, not a rewrite.
3. **Automated KenPom ingest.** KenPom is subscription-gated and blocks scraping, so pulling the raw export stays a manual copy/paste — but everything after that (stripping repeated header rows from the paginated table, dropping rank-subscript columns, merging into the historical dataset) becomes code, replacing the old by-hand Excel cleanup.
4. **One canonical implementation per model.** Logistic regression, random forest, XGBoost, neural net, and seed-KNN each live in a single source module. Notebooks are exploration-only and are never manually "ported" to `.py` again — that porting step was the root cause of the old project's production code drifting out of sync with working notebook logic.
5. **Real reproducibility.** A real dependency manifest, a `.gitignore`, and git history from the first commit.
6. **Men's tournament first.** Women's tournament support is a deliberate future goal — KenPom has no women's coverage, so it'll need a different ratings source (the Massey Ordinals data already bundled in the Kaggle dataset is the leading candidate). Nothing in the current design should block adding it later, but no women's-specific plumbing is being built yet.

## Roadmap

We already have a working product with real functionality (five prediction models, seed prediction/clustering, bracket simulation, a dashboard). This roadmap has one **standing priority** that never "completes," plus a sequence of **milestones** that add and deepen functionality on top of it.

### Standing Priority — Audit, Cleanup, Reorganization & Modularity
Ongoing for the life of the project, not a phase to finish and move past. Every milestone below is held to it: config-driven instead of hardcoded, one canonical implementation instead of duplicates, no manual steps that could be code. This is the top priority right now because the initial port (Milestone 1) is where the old project's mess gets fixed.

Concrete standards enforced everywhere:
- Season year, bracket size, round count, and play-in count come from one config (`config/season.yaml`), never hardcoded.
- `R1`...`R6` and the 64-team main bracket are fixed (Kaggle's actual data format) and coded as such — what's config-driven is `num_play_in_games`, since `field_size = 64 + num_play_in_games` is the part that actually changes with tournament expansion.
- KenPom's raw export stays a manual copy/paste (subscription-gated, blocks scraping) but everything downstream of that paste — stripping repeated header rows, dropping rank-subscript columns, merging into history — is code, not an Excel step.
- One canonical module per model/feature — notebooks are exploration-only and are never manually "ported" to `.py` again.
- Real dependency manifest, `.gitignore`, and git history from the first commit.

### Standing Priority — Year-over-Year Reuse
Also ongoing, not a one-time milestone: this repo needs to work the same way every March, indefinitely.
- **Multi-year data layout.** `data/{raw,processed,outputs}` are organized per-year rather than flat, so old seasons' data and results aren't overwritten and `config/season.yaml`'s `year` field is a genuine toggle, not a one-way door. This gets decided alongside `config/season.yaml` and the ingest modules (Milestone 1).

Post-mortem/performance evaluation (comparing a season's predictions against actual results once the tournament concludes) is a concrete deliverable now, not just a standing idea — see Milestone 5.

`scripts/run_pipeline.py --model` briefly defaulted to `xgboost_model` on 2026-07-30, then was reverted to `logistic_regression` the same day after `scripts/evaluate_models.py` (new — trains all four candidate models on an identical held-out split and plots a real reliability diagram to `reports/model_calibration.png`) showed xgboost_model was worse on every metric measured. Traced further before assuming it was a tuning problem: the real cause was **training-data starvation**, not model choice. `data/raw/` had only one populated season (2026, 5,265 games) against the legacy project's 23 seasons (2003-2025, ~120,000 games) — a ~23x reduction that hits high-variance learners (gradient boosting, neural nets) far harder than a regularized linear model, exactly matching the pattern observed (logistic regression and random forest barely moved; XGBoost and the neural net cratered).

Fixed with a real historical backfill, not a workaround: `scripts/backfill_historical_kenpom.py` imports the legacy project's already-merged `data/kenpom_fin_df.csv` (2003-2025; 2026 deliberately excluded in favor of this repo's own fresher, independently-verified raw pull) into `data/processed/<year>/kenpom_clean.csv`, and `ingest/kenpom.py`'s `build_kenpom_history()` now also reads those for any year without a raw export of its own (raw still wins if both exist). This surfaced a second, previously-unknown variant of the Excel W-L date-mangling bug along the way: the existing fix only recovered a mangled *loss* count (`"20-12"` → `"20-Dec"`); real 2010/2012 data had mangled *win* counts too (`"2-29"` → `"Feb-29"`), silently producing `NaN` and crashing model training. Fixed by applying the recovery (renamed `parse_win_loss_component`, was `parse_losses`) to both sides, with tests.

Post-backfill, on 24 seasons instead of 1: xgboost_model accuracy 0.681→0.744, expected calibration error 0.145→0.024; neural_net accuracy 0.701→0.753, ECE 0.077→**0.007** (now the best-calibrated model of the four). Logistic regression is still marginally best on every metric (0.755/0.843/0.012), close enough to xgboost_model (0.744/0.830/0.024) that the user chose `xgboost_model` as the live default anyway, judging it captures real nonlinear structure the linear model can't.

**Flagged concern, investigated further, and fixed — a real bug, not a modeling nuance.** With the historical backfill in place, `xgboost_model` still gave Duke an implausible title share (67.5%, even higher than the 62.6% originally flagged) despite Duke/Arizona/Michigan having nearly identical KenPom NetRtg. A per-game calibration check ruled out simple overconfidence (well-calibrated even in the 90-100% predicted bucket). Investigated further rather than accepting "maybe it's just a compounding effect": tested whether the model's predictions are symmetric to which team's stats land in the "_A" feature slot vs. "_B" for the same real matchup — they're not. Arizona vs. Michigan (nearly identical ratings) came back 64%/38% one way and ~38%/62% reversed; Duke vs. Arizona came back 93%/72% (should sum to ~100%, summed to ~165%). `bracket/simulate.py`'s `compute_win_probabilities()` always resolved each game with the bracket's "StrongSeed" position in slot "_A," so this un-symmetrized bias gave whichever team's bracket position was structurally labeled StrongSeed a compounding, unearned edge every single round — nothing to do with real team strength. `randomize_matchup_sides()` (training-time) doesn't prevent this; it only stops the model learning "A tends to win" from historical winner-first data ordering, it doesn't guarantee the fitted model treats any specific matchup symmetrically. Fixed by averaging the forward prediction against the complementary probability implied by the reverse-slot prediction (`probs[a][b] + probs[b][a] == 1.0`, enforced). Result: Duke's title share dropped from 67.5% to **41.0%**, with Arizona (21.1%) and Michigan (17.2%) both coming up to much more sensible numbers given how close their underlying ratings are. New test: `test_compute_win_probabilities_symmetrizes_away_a_slot_position_bias`.

One deliberate omission, discussed with the user: the legacy project's `TeamID_A`/`TeamID_B` features were left out of the rebuild's feature set on purpose (see `models/common.py`) — partly because they were a real identity-leakage bug in the legacy code (a row-random train/test split let the same team's ID appear on both sides, letting memorization-capable models partially "look up" a team rather than learn from its stats), which inflated legacy's old RF/XGBoost/NN numbers. The user agrees TeamID stays out for now, but flagged that college basketball's NIL/transfer-portal era (post ~2021) has made sustained program-level talent acquisition a more legitimate, less arbitrary signal than it was in the one-and-done era — worth deliberately testing a non-leaky program-identity feature in Milestone 3, not assumed away.

### Milestone 1 — Port & Modularize the Existing Product *(complete)*
Bring what already works — data ingest, feature engineering, the five prediction models, seed prediction, seed clustering, bracket simulation, round-advancement/fragility analysis — into the new modular structure at feature parity. Nothing new yet; this is the foundation everything else builds on.
- [x] Repo skeleton: `config/`, `src/march_madness/`, `scripts/`, `notebooks/`, `tests/`, `data/{raw,processed,outputs}`, `reports/`
- [x] Dependency manifest (`pyproject.toml`)
- [x] `config/season.yaml` schema + `src/march_madness/config.py` loader — includes the per-year data layout (`data/raw/<year>/`, etc.)
- [x] `src/march_madness/bracket/structure.py` — round classification (R1-R6, fixed), play-in-count-agnostic validation, and a fix for a real ordering bug found in the legacy simulator (see WORKLOG)
- [x] `src/march_madness/ingest/kaggle.py` and `ingest/kenpom.py` (automates the header-row/rank-column cleanup, plus a real Excel date-mangling bug found and fixed — see WORKLOG)
- [x] `src/march_madness/features/build_features.py` — matchup history construction, team-name reconciliation via `MTeamSpellings.csv` (fixed a 38%→4% match failure rate — see WORKLOG), conference tiers, vectorized side-randomization
- [x] `src/march_madness/models/` — logistic regression, random forest, XGBoost, neural net, seed KNN, plus a shared `common.py` for split/evaluate (replacing five near-duplicate copies — see WORKLOG)
- [x] `src/march_madness/bracket/simulate.py` — Monte Carlo engine ported and cleaned from the old `sims_mens.py`, verified end-to-end on the real 2026 bracket (see WORKLOG)
- [x] `src/march_madness/models/seed_clustering.py` — unsupervised KMeans tiering, ported from `seed_clustering.py` (now reuses `ingest/kenpom.py` instead of its own redundant cleaning)
- [x] `src/march_madness/analysis/round_advancement.py` and `analysis/region_strength.py` — round-count, "wins over seed expectation," Cinderella probability, Final Four combinations, and region strength, all generalized from the legacy project's hardcoded-per-season versions (see WORKLOG)

- [x] `scripts/run_pipeline.py` — one command: ingest → features → train → simulate → analyze. Run with `python scripts/run_pipeline.py` (see [DEVELOPMENT.md](DEVELOPMENT.md) for setup and the data it needs locally first).

Milestone 1 is fully built, tested, and verified end-to-end against real 2026 data — including a genuine "drop in this year's data and run one command" pipeline, not just one-off verification scripts.

### Milestone 2 — Presentation of Findings & Visualization
`project_dashboard.html` in the old project turned out to be unrelated to March Madness — a general project-portfolio tracker that happened to be saved in that folder, not a results dashboard. This milestone is a real public-facing site instead: long-form articles (the user's own writing) plus analytics pages generated from the pipeline's output.

**Presentation layer pivoted.** A first pass built this as a Python-generated static site (Jinja2 + Markdown, embedded Plotly charts, hosted on GitHub Pages). It was fully built and verified against real data, but after actually seeing it rendered, the look didn't hold up — flat and generic next to the design language already established in this user's other frontends. Nothing from it was ever committed, so this was a clean pivot, not a revert. Superseded, not deleted: the whole Jinja2 build (`content/`, `site/`, `docs/`, `scripts/build_site.py`) now lives in `legacy/jinja_site/` pending eventual deletion; `jinja2`/`markdown` are dropped from `pyproject.toml`. GitHub Pages was discussed as a hosting target for that build but never actually enabled — there's nothing live to remove.

Current direction: a **Vite + React** frontend, adopting the glassmorphism system already used in `../NFL_Exploration/frontend` and `../CaravanserAI/frontend` (dark background, blurred translucent cards via `backdrop-filter`, gradient "glow" headings, blue/orange accent colors, hand-written CSS custom properties — explicitly not Tailwind or a component library). Several alternate visual styles were prototyped for comparison (neo-brutalist, Material 3, minimal editorial, bento grid, plus a few sports-specific looks); the user picked **Minimal Editorial**, designed properly in both light and dark themes rather than dropping the light/dark toggle. Hosting: local only for now, matching `NFL_Exploration`/`CaravanserAI` — neither of those is deployed publicly yet, so there's no established pattern to match beyond that.

- [x] `content/articles/*.md`, `site/templates/`, `site/static/`, `scripts/build_site.py` — the superseded Jinja2 build, now in `legacy/jinja_site/`.
- [x] `run_pipeline.py` extended to also write `teams.csv`, `seed_predictions.csv`, `team_tiers.csv` — still valid and needed regardless of frontend choice.
- [x] Site architecture decision: Vite + React + glassmorphism-derived design system.
- [x] Visual design direction: Minimal Editorial, both light and dark themes.
- [x] `frontend/` scaffold (Vite + React, port 5181 — see `../LOCALHOST_PORT_REGISTRY.md` — mirroring `NFL_Exploration/frontend`'s no-router, `pagesConfig.js`-driven page-switching pattern).
- [x] `scripts/export_site_data.py` — the CSV → frontend data hand-off, decided as a JSON export (not the frontend parsing CSV). Reruns `simulation_results.csv` back through `analysis/round_advancement.py` and `analysis/region_strength.py`, the same "stays fast, decoupled from `run_pipeline.py`'s runtime" role the superseded `build_site.py` played, and writes `frontend/public/data/{<year>.json, current.json}`.
- [x] Home page (executive summary: stat strip, region outlook, Final Four + championship-odds teasers) and Round Odds page (all teams, every round, click-to-sort columns) — verified end-to-end against real 2026 output in the running dev server, zero console errors.
- [x] Over/Underperformers (sortable table + a diverging bar chart of the biggest over/underperformers), Cinderella Watch (seed-threshold x round heatmap), Final Four Finder (rebuilt around four region dropdowns for a partial-or-full team selection, with a bar chart + list of matching Final Fours — `export_site_data.py` now exports the full ~266-combo list instead of a top-N slice, so any selection is answered honestly, including "never occurred"), and Region Strength (championship-share bar chart + a "fragile → competitive" table). All verified in the running dev server against real 2026 data, zero console errors.
- [x] **Region Strength audit finding, fixed**: the original top-heaviness stat conditioned on the region winning the whole national title, which conflated a region's own competitiveness with cross-region championship-game strength and was statistically unstable for any region that rarely won it all (one region's figure was computed from ~120 of 10,000 brackets). Added `region_top_seed_final_four_share()` (unconditional, all 10,000 brackets) as the primary fragility metric; the old conditional stat is kept as a secondary figure, not deleted. See `src/march_madness/analysis/region_strength.py` docstrings and `tests/test_analysis.py`.
- [x] Fixed a real bug surfaced by the model switch: a team that never wins a single simulated game (e.g. Furman, Prairie View, under `xgboost_model`'s more confident predictions) was silently dropped from the entire site export instead of showing at ~0% — the same class of bug `average_wins_by_team()` already guards against in `analysis/round_advancement.py`. `export_site_data.py`'s team payload now anchors on the full `teams.csv`, not on whichever teams happened to win at least one game.
- [ ] Seed Prediction — deliberately deferred, not a blocked-on-a-bug item anymore: the user has learned more about clustering since the original design and wants to redo this page properly rather than ship the old approach. Target: done before the 2027 season publish, not this pass.

"Who benefits most if team X loses" and the post-mortem/evaluation page have moved to Milestone 5 (below), alongside two related new tools.

### Milestone 3 — Seed Prediction
Deepen seed prediction beyond the old KNN baseline, building on the unsupervised clustering approach already prototyped in `seed_clustering.py`.

### Milestone 4 — Upset Finder & Cinderella Stories
New analysis surface: surface likely upsets and long-shot deep-run candidates from model/seed disagreement. The old project's round-advancement "fragility" analysis in `sims_mens.py` is a starting point.

### Milestone 5 — Bracket Path & Historical Tools *(new)*
Four items, agreed as distinct tools rather than variations on one idea:
- **Path of Least Resistance** — which team has the weakest projected path to the Final Four, based on the strength of the opponents standing between them and it.
- **Who Benefits if Team X Loses** — the flip side of the same bracket-path question: given a specific team losing, which other teams gain the most. Moved here from Milestone 2, where it was originally parked as "needs new analysis, not just a page."
- **Post-Mortem / Year Retrospective** — compare a concluded season's predictions against actual results (accuracy, calibration, biggest misses). Also moved here from Milestone 2/the Year-over-Year Reuse standing priority; design still TBD with the user, now that there's a real season of predictions to eventually evaluate against.
- **Previous-Years History** — a side-by-side view across seasons, building on the per-year `data/{raw,processed,outputs}` layout already in place from Milestone 1.

### Milestone 6 — Sportsbook & Prediction Market Integration
Compare model output against betting lines and prediction markets via API. (This was already on the original project's "future work" list.)

### Milestone 7 — In-Season Predictive Modeling *(future, ~2 years out)*
A preseason model is inherently weak — no in-season data to project from. Longer-term direction: predict not just tournament bracket outcomes but bubble-team at-large selection (who makes/misses the tournament) using accumulating in-season data. Explicitly a multi-year-out stretch goal, not near-term.

### Future: Women's Tournament & Format Changes
Tracked as standing constraints on the design (see Goals below), not scheduled milestones yet:
- Evaluate Massey Ordinals (or another source) as a KenPom substitute for women's ratings, then mirror the men's pipeline.
- Validate the bracket structure module against a 76-team format once the NCAA finalizes it.

## Plan of Attack

Docs backbone (done) → repo skeleton + dependency manifest → config module → KenPom ingest automation → feature/model porting → bracket simulation → seed clustering/analysis porting (completes Milestone 1) → presentation layer, now Vite + React + Minimal Editorial after the Jinja2 pivot (Milestone 2) → seed prediction depth (Milestone 3) → upset/Cinderella analysis (Milestone 4) → bracket path & historical tools (Milestone 5, new) → sportsbook/market APIs (Milestone 6) → in-season modeling (Milestone 7, future). Each step is pulled deliberately from the old project (`../March_Madness_2026`), not copied wholesale.
