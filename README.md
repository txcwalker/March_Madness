# March Madness Tournament Simulator

Status: rebuild in progress | 2026-07-22

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

### Standing Priority — Year-over-Year Reuse & Post-Mortem Evaluation
Also ongoing, not a one-time milestone: this repo needs to work the same way every March, indefinitely. Two concrete pieces:
- **Multi-year data layout.** `data/{raw,processed,outputs}` are organized per-year rather than flat, so old seasons' data and results aren't overwritten and `config/season.yaml`'s `year` field is a genuine toggle, not a one-way door. This gets decided alongside `config/season.yaml` and the ingest modules (Milestone 1).
- **Post-mortem / performance evaluation tooling.** Once a tournament concludes, compare the season's predictions against actual results to see how the model actually did (accuracy, calibration, which upsets were missed, etc.), and accumulate that across years. Design TBD — to be scoped together once there's at least one real season of predictions to evaluate against.

### Milestone 1 — Port & Modularize the Existing Product *(current focus)*
Bring what already works — data ingest, feature engineering, the five prediction models, seed prediction, seed clustering, bracket simulation, round-advancement/fragility analysis — into the new modular structure at feature parity. Nothing new yet; this is the foundation everything else builds on.
- [x] Repo skeleton: `config/`, `src/march_madness/`, `scripts/`, `notebooks/`, `tests/`, `data/{raw,processed,outputs}`, `reports/`
- [x] Dependency manifest (`pyproject.toml`)
- [x] `config/season.yaml` schema + `src/march_madness/config.py` loader — includes the per-year data layout (`data/raw/<year>/`, etc.)
- [x] `src/march_madness/bracket/structure.py` — round classification (R1-R6, fixed), play-in-count-agnostic validation, and a fix for a real ordering bug found in the legacy simulator (see WORKLOG)
- [x] `src/march_madness/ingest/kaggle.py` and `ingest/kenpom.py` (automates the header-row/rank-column cleanup, plus a real Excel date-mangling bug found and fixed — see WORKLOG)
- [x] `src/march_madness/features/build_features.py` — matchup history construction, team-name reconciliation via `MTeamSpellings.csv` (fixed a 38%→4% match failure rate — see WORKLOG), conference tiers, vectorized side-randomization
- [x] `src/march_madness/models/` — logistic regression, random forest, XGBoost, neural net, seed KNN, plus a shared `common.py` for split/evaluate (replacing five near-duplicate copies — see WORKLOG)
- [x] `src/march_madness/bracket/simulate.py` — Monte Carlo engine ported and cleaned from the old `sims_mens.py`, verified end-to-end on the real 2026 bracket (see WORKLOG)
- [ ] Port seed clustering (`seed_clustering.py`) and existing round-count/fragility analysis

### Milestone 2 — Presentation of Findings & Visualization
Rebuild and extend the dashboard concept (`project_dashboard.html` in the old project) with better visualizations of simulation results, region strength, and bracket odds.

### Milestone 3 — Seed Prediction
Deepen seed prediction beyond the old KNN baseline, building on the unsupervised clustering approach already prototyped in `seed_clustering.py`.

### Milestone 4 — Upset Finder & Cinderella Stories
New analysis surface: surface likely upsets and long-shot deep-run candidates from model/seed disagreement. The old project's round-advancement "fragility" analysis in `sims_mens.py` is a starting point.

### Milestone 5 — Sportsbook & Prediction Market Integration
Compare model output against betting lines and prediction markets via API. (This was already on the original project's "future work" list.)

### Milestone 6 — In-Season Predictive Modeling *(future, ~2 years out)*
A preseason model is inherently weak — no in-season data to project from. Longer-term direction: predict not just tournament bracket outcomes but bubble-team at-large selection (who makes/misses the tournament) using accumulating in-season data. Explicitly a multi-year-out stretch goal, not near-term.

### Future: Women's Tournament & Format Changes
Tracked as standing constraints on the design (see Goals below), not scheduled milestones yet:
- Evaluate Massey Ordinals (or another source) as a KenPom substitute for women's ratings, then mirror the men's pipeline.
- Validate the bracket structure module against a 76-team format once the NCAA finalizes it.

## Plan of Attack

Docs backbone (done) → repo skeleton + dependency manifest → config module → KenPom ingest automation → feature/model porting → bracket simulation → seed clustering/analysis porting (completes Milestone 1) → presentation layer (Milestone 2) → seed prediction depth (Milestone 3) → upset/Cinderella analysis (Milestone 4) → sportsbook/market APIs (Milestone 5) → in-season modeling (Milestone 6, future). Each step is pulled deliberately from the old project (`../March_Madness_2026`), not copied wholesale.
