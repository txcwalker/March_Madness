# DEVELOPMENT.md

Workspace map for humans and AI. Update when the skeleton or setup changes.

## Status

Skeleton stage. Folder structure and dependency manifest exist; modules are still empty (`__init__.py` placeholders only). No config schema, ingest, features, models, or bracket logic has been ported yet.

## Active Code Areas

```
config/                      # season.yaml: year, bracket_size, num_rounds, num_play_in_games
src/march_madness/
  config.py                  # loads config/season.yaml
  ingest/
    kaggle.py                # loads Kaggle competition CSVs
    kenpom.py                # cleans pasted KenPom export, merges into history
  features/
    build_features.py        # matchup pairing, conference tiers, stat_swap/random_id
  models/
    logistic_regression.py, random_forest.py, xgboost_model.py, neural_net.py, seed_knn.py
  bracket/
    structure.py             # generates rounds/slots from config (format-agnostic)
    simulate.py               # Monte Carlo bracket simulation
  analysis/
    region_strength.py, upsets.py, round_odds.py
scripts/                      # thin CLI entry points (run_pipeline.py, build_dashboard.py)
notebooks/                    # exploration only, never imported by src/
tests/
data/{raw,processed,outputs}  # raw = hand-supplied inputs; processed/outputs = generated, gitignored
reports/                       # generated dashboard/presentation output
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
pytest                     # run the test suite (currently: tests/test_config.py)
```

No pipeline entry point yet — will be added here the moment `scripts/run_pipeline.py` exists.

## Generated Files

Planned: `data/processed/`, `data/outputs/`, `reports/`. All gitignored once `.gitignore` is created — nothing in these paths should ever be hand-edited or committed.

## Model & Data Artifacts

None yet. Data sources will be:
- Kaggle: [March Machine Learning Mania 2026](https://www.kaggle.com/competitions/march-machine-learning-mania-2026) — teams, seeds, results, slots, conferences, ordinals. Dropped into `data/raw/` by hand each season.
- KenPom.com — subscription-gated efficiency ratings, manually copy/pasted into `data/raw/` each season (see [AGENTS.md](AGENTS.md) Fragile Areas for the cleanup this requires).

## DB Schema

N/A — flat CSV/YAML files only, no database.

## AI Onboarding Notes

- This repo is a deliberate rebuild of `../March_Madness_2026` (outside this repo, read-only reference). Don't copy files wholesale from it — port specific logic, cleaned up, module by module.
- Before writing any ingest/feature/model code, check [GOAL_TRACKER.md](GOAL_TRACKER.md) and [WORKLOG.md](WORKLOG.md) for the latest status — this file describes the target shape, not necessarily what exists right now.
