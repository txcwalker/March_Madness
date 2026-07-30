# DEVELOPMENT.md

Workspace map for humans and AI. Update when the skeleton or setup changes.

## Status

Milestone 1 complete and stable. Milestone 2 (presentation) is a working Vite + React frontend in the **Minimal Editorial** design (typography-first, no card chrome, both light and dark themes) — six of seven analytics pages built and verified against real data: Home, Round Odds, Over/Underperformers, Cinderella Watch, Final Four Finder, Region Strength. Seed Prediction deliberately left as a placeholder (user wants to redo it before the 2027 publish, not ship the old KNN approach). A Jinja2 static-site attempt (now `legacy/jinja_site/`) and a glassmorphism/blue-orange direction (matching `../NFL_Exploration`/`../CaravanserAI`) were both tried and superseded before React + Minimal Editorial won out — see WORKLOG 2026-07-28/30 for the full history if picking this up cold.

## Active Code Areas

```
config/season.yaml              # year, bracket size/rounds/play-in count -- the one place a season starts
src/march_madness/
  config.py                     # loads config/season.yaml -> SeasonConfig (incl. per-year data paths)
  ingest/
    kaggle.py                   # loads Kaggle competition CSVs -> KaggleData bundle
    kenpom.py                   # cleans pasted KenPom export, merges every year into one history
                                 # (raw exports under data/raw/, plus already-cleaned historical
                                 # imports under data/processed/ -- see backfill_historical_kenpom.py)
  features/
    build_features.py           # matchup history, KenPom<->Kaggle team matching, conference tiers
  models/
    common.py                   # shared split/evaluate/feature-prep for the 4 classifiers below
    logistic_regression.py, random_forest.py, xgboost_model.py, neural_net.py
    seed_knn.py                 # separate: per-team-season seed prediction (KNN)
    seed_clustering.py          # separate: unsupervised KMeans team tiering
  bracket/
    structure.py                # round classification, play-in-count-agnostic validation
    simulate.py                 # Monte Carlo bracket simulation
  analysis/
    round_advancement.py, region_strength.py
scripts/
  run_pipeline.py                # ingest -> features -> train -> simulate -> analyze -> data/outputs/<year>/
  export_site_data.py            # data/outputs/<year>/*.csv -> frontend/public/data/{<year>.json, current.json}
  evaluate_models.py              # compares all 4 models on an identical split; writes reports/model_calibration.png
  backfill_historical_kenpom.py   # one-time import: legacy project's 2003-2025 KenPom history -> data/processed/
frontend/                        # Vite + React (plain JS), Minimal Editorial design, port 5181 -- see AGENTS.md
legacy/jinja_site/                # SUPERSEDED, not deleted -- the rejected Jinja2 build (content/, site/, docs/, build_site.py)
notebooks/                       # exploration only, never imported by src/
tests/                           # one test file per src/ module, see AGENTS.md
data/{raw,processed,outputs}     # all gitignored; raw = hand-supplied inputs, processed = backfilled history
reports/                         # model_calibration.png so far
```

## Local Setup

Requires **Python 3.10+** (matches the legacy project's interpreter; the system default `python` may resolve to an older version — use `py -3.10` or a full path if so).

```
python -m venv .venv
.venv\Scripts\activate     # Windows
pip install --upgrade pip  # old pip can't do editable installs from pyproject.toml alone
pip install -e ".[dev]"
```

`pyproject.toml` lists dependencies carried over from the legacy project's `.venv` (pandas, numpy, scikit-learn, xgboost, matplotlib, seaborn, tqdm, rapidfuzz, plotly, kaleido) plus `pyyaml` for the config loader. The `dev` extra adds `pytest`. `jinja2`/`markdown` were removed 2026-07-28 when the Jinja2 site was superseded.

For the frontend: **Node.js** (whatever version `../NFL_Exploration/frontend` uses), then `cd frontend && npm install`.

## Run Commands

```
pytest                                          # full test suite (83 tests)
python scripts/run_pipeline.py                  # ingest -> features -> train -> simulate -> analyze
python scripts/run_pipeline.py --model random_forest --n-brackets 5000   # override defaults
python scripts/export_site_data.py              # data/outputs/<year>/*.csv -> frontend/public/data/*.json
python scripts/evaluate_models.py               # compares all 4 models, writes reports/model_calibration.png
python scripts/backfill_historical_kenpom.py    # re-run only if kenpom_fin_df.csv changes or processed/ is deleted

cd frontend && npm run dev                      # Vite dev server, http://localhost:5181
cd frontend && npm run build                    # static production build
```

`run_pipeline.py` defaults to `xgboost_model` (see AGENTS.md "Current Priorities" for the model-selection history — briefly `xgboost_model`, reverted to `logistic_regression` after a bad calibration comparison, root-caused to training-data starvation, fixed via the historical backfill, then switched back to `xgboost_model` once the comparison was fair) and 10,000 simulated brackets. Requires `data/raw/<year>/kaggle/*.csv` and `data/raw/<year>/kenpom_raw.csv` to exist locally first (see Model & Data Artifacts below) — `data/raw/` is gitignored, so this needs repopulating after a fresh clone. `data/processed/<year>/kenpom_clean.csv` (2003-2025, from the historical backfill) is also gitignored but **not regenerable from a fresh Kaggle/KenPom pull** — only from `scripts/backfill_historical_kenpom.py` re-reading `../March_Madness_2026/data/kenpom_fin_df.csv`, which itself won't exist on a fresh clone of just this repo. Treat `data/processed/` as needing a real backup plan eventually, not "safe to delete, just re-run the pipeline."

Always run `python scripts/export_site_data.py` after `run_pipeline.py` — the frontend only ever reads the JSON export, never the CSVs directly.

## Generated Files

`data/outputs/<year>/{simulation_results,round_advancement,teams,seed_predictions,team_tiers}.csv`, written by `run_pipeline.py` — gitignored, hand-edited never, safe to delete and regenerate (from a fresh Kaggle/KenPom pull). `data/processed/<year>/kenpom_clean.csv` (2003-2025) — gitignored, but see the caveat above, it's not trivially regenerable. `frontend/public/data/{<year>.json, current.json}`, written by `export_site_data.py`. `reports/model_calibration.png`, written by `evaluate_models.py`.

## Model & Data Artifacts

Nothing is tracked in git — `data/raw/` and `data/processed/` are both gitignored (Kaggle competition data may carry redistribution restrictions; see WORKLOG for the decision). To run the pipeline locally:
- Kaggle: download [March Machine Learning Mania 2026](https://www.kaggle.com/competitions/march-machine-learning-mania-2026) and drop the CSVs into `data/raw/<year>/kaggle/` (needs at minimum: `MTeams.csv`, `MTeamSpellings.csv`, `MNCAATourneySeeds.csv`, `MNCAATourneySlots.csv`, `MRegularSeasonCompactResults.csv`, `MNCAATourneyCompactResults.csv`, `Conferences.csv`, `MTeamConferences.csv` — see `ingest/kaggle.py`'s `_FILES`).
- KenPom.com — subscription-gated, paste the raw export into `data/raw/<year>/kenpom_raw.csv` for the *current* season (see [AGENTS.md](AGENTS.md) Fragile Areas for the cleanup `ingest/kenpom.py` does automatically).
- Historical seasons (2003-2025): run `python scripts/backfill_historical_kenpom.py`, sourced from `../March_Madness_2026/data/kenpom_fin_df.csv` (the legacy project's own accumulated manual pastes). There is no raw KenPom export left on disk for these years — this is the only way to get them back if `data/processed/` is lost.

## DB Schema

N/A — flat CSV/YAML files only, no database.

## Frontend

`frontend/` — Vite + React (plain JS, no TypeScript), port 5181 (registered in `../LOCALHOST_PORT_REGISTRY.md`). No router: `src/pagesConfig.js` (page metadata array) + hash-based page switching in `src/App.jsx`, mirroring `../NFL_Exploration/frontend`'s pattern (that project's own dark-glassmorphism/blue-orange visual system was considered and **not** adopted — see below). No Tailwind or component library, hand-written CSS — `src/index.css` defines the **Minimal Editorial** design tokens (warm clay/rust `--accent`, Georgia serif display, mono for data, hairline rules instead of card borders) as CSS custom properties, both light and dark themes designed with equal care (`:root`, `@media (prefers-color-scheme: dark)`, `[data-theme]` override — the last wins in both directions). `src/useSiteData.js` fetches `public/data/current.json`. `src/components/SortableTable.jsx` is shared by Round Odds and Over/Underperformers.

Nine style directions were prototyped and compared before Minimal Editorial won (see `../March_Madness_2026`'s design-exploration session and WORKLOG 2026-07-28): the glassmorphism system from `../NFL_Exploration`/`../CaravanserAI` was one of the options considered, not the default followed — don't assume this project shares those projects' visual identity just because it shares their architectural pattern (no router, hand-written CSS, no Tailwind).

## AI Onboarding Notes

- This repo is a deliberate rebuild of `../March_Madness_2026` (outside this repo, read-only reference). Don't copy files wholesale from it — port specific logic, cleaned up, module by module. It's also now the source for the historical KenPom backfill (`data/kenpom_fin_df.csv`) — don't assume that file will always be there; see the Model & Data Artifacts caveat above.
- Before writing any ingest/feature/model code, check [GOAL_TRACKER.md](GOAL_TRACKER.md) and [WORKLOG.md](WORKLOG.md) for the latest status — this file describes the target shape, not necessarily what exists right now.
- If you're picking this up fresh: read WORKLOG.md's most recent entries first, especially 2026-07-30 — a lot happened in one session (frontend build, a region-strength metric fix, a model evaluation that reverted then re-applied a default-model change, a real historical data backfill, and two Excel-parsing bug fixes). The "what's built" and "what's planned" states move fast here.
