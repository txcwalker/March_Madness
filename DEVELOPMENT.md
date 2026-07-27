# DEVELOPMENT.md

Workspace map for humans and AI. Update when the skeleton or setup changes.

## Status

Milestone 1 complete: the full pipeline (ingest → features → models → bracket simulation → analysis) is built, tested, and runnable end-to-end via `scripts/run_pipeline.py`, verified against real 2026 data. Next up is Milestone 2 (presentation/visualization) — see [README.md](README.md) Roadmap.

## Active Code Areas

```
config/season.yaml              # year, bracket size/rounds/play-in count -- the one place a season starts
src/march_madness/
  config.py                     # loads config/season.yaml -> SeasonConfig (incl. per-year data paths)
  ingest/
    kaggle.py                   # loads Kaggle competition CSVs -> KaggleData bundle
    kenpom.py                   # cleans pasted KenPom export, merges every year into one history
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
  run_pipeline.py                # the actual entry point -- see Run Commands
notebooks/                       # exploration only, never imported by src/
tests/                           # one test file per src/ module, see AGENTS.md
data/{raw,processed,outputs}     # all gitignored; raw = hand-supplied inputs (Kaggle download + KenPom paste)
reports/                         # generated dashboard/presentation output (Milestone 2, not built yet)
```

## Local Setup

Requires **Python 3.10+** (matches the legacy project's interpreter; the system default `python` may resolve to an older version — use `py -3.10` or a full path if so).

```
python -m venv .venv
.venv\Scripts\activate     # Windows
pip install --upgrade pip  # old pip can't do editable installs from pyproject.toml alone
pip install -e ".[dev]"
```

`pyproject.toml` lists dependencies carried over from the legacy project's `.venv` (pandas, numpy, scikit-learn, xgboost, matplotlib, seaborn, tqdm, rapidfuzz, plotly, kaleido) plus `pyyaml` for the config loader. The `dev` extra adds `pytest`. Pare the main list down as porting proceeds and it becomes clear what's actually used.

## Run Commands

```
pytest                                          # full test suite
python scripts/run_pipeline.py                  # ingest -> features -> train -> simulate -> analyze
python scripts/run_pipeline.py --model random_forest --n-brackets 5000   # override defaults
```

`run_pipeline.py` defaults to `logistic_regression` (currently the best performer on real data — see WORKLOG) and 10,000 simulated brackets. Requires `data/raw/<year>/kaggle/*.csv` and `data/raw/<year>/kenpom_raw.csv` to exist locally first (see Model & Data Artifacts below) — `data/raw/` is gitignored, so this needs repopulating after a fresh clone.

## Generated Files

`data/outputs/<year>/simulation_results.csv` (one row per simulated game) and `round_advancement.csv` (per-team round-reach counts), written by `run_pipeline.py`. `data/processed/` and `reports/` are reserved for later pipeline stages, not used yet. All gitignored — nothing in these paths should ever be hand-edited or committed.

## Model & Data Artifacts

Nothing is tracked in git — `data/raw/` is gitignored (Kaggle competition data may carry redistribution restrictions; see WORKLOG for the decision). To run the pipeline locally:
- Kaggle: download [March Machine Learning Mania 2026](https://www.kaggle.com/competitions/march-machine-learning-mania-2026) and drop the CSVs into `data/raw/<year>/kaggle/` (needs at minimum: `MTeams.csv`, `MTeamSpellings.csv`, `MNCAATourneySeeds.csv`, `MNCAATourneySlots.csv`, `MRegularSeasonCompactResults.csv`, `MNCAATourneyCompactResults.csv`, `Conferences.csv`, `MTeamConferences.csv` — see `ingest/kaggle.py`'s `_FILES`).
- KenPom.com — subscription-gated, paste the raw export into `data/raw/<year>/kenpom_raw.csv` (see [AGENTS.md](AGENTS.md) Fragile Areas for the cleanup `ingest/kenpom.py` does automatically). Every past year's paste that's ever added stays useful — `build_kenpom_history()` picks up every year found.

## DB Schema

N/A — flat CSV/YAML files only, no database.

## AI Onboarding Notes

- This repo is a deliberate rebuild of `../March_Madness_2026` (outside this repo, read-only reference). Don't copy files wholesale from it — port specific logic, cleaned up, module by module.
- Before writing any ingest/feature/model code, check [GOAL_TRACKER.md](GOAL_TRACKER.md) and [WORKLOG.md](WORKLOG.md) for the latest status — this file describes the target shape, not necessarily what exists right now.
