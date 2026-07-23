# DEVELOPMENT.md

Workspace map for humans and AI. Update when the skeleton or setup changes.

## Status

Documentation-only stage. No source code, config, or dependency manifest exists yet in this repo. This file describes the *planned* layout (agreed in design discussion) until each piece actually lands — planned items are marked accordingly.

## Active Code Areas (planned)

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

Not yet defined — no `pyproject.toml`/`requirements.txt` exists in this repo. First implementation task: stand up a manifest covering the dependencies observed in the legacy project's `.venv` (pandas, numpy, scikit-learn, xgboost, matplotlib, seaborn, tqdm, rapidfuzz, plotly, kaleido) and pare it down to what this rebuild actually uses.

## Run Commands

None yet — will be added here the moment `scripts/run_pipeline.py` exists. Do not reference commands that don't exist.

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
