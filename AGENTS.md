# AGENTS.md

AI-to-AI handoff contract. Keep this current and terse — dense facts, no prose padding.

## Core Purpose

Rebuild of a March Madness bracket prediction/simulation project. Ground-up restructure of a working-but-tangled prior codebase (see Frozen/Legacy Zones). Goal: config-driven, format-agnostic, reusable every season without hand-editing.

## Current Priorities

1. `ingest/kaggle.py` and `ingest/kenpom.py` (the latter automates the header-row/rank-column cleanup described below)
2. `features/build_features.py`, then `models/`
3. `bracket/simulate.py` (consumes `bracket/structure.py`, which is done)

Repo skeleton, `pyproject.toml`, config module, and bracket structure module are done (see Active Files). Do not assume any other module is implemented until it appears here.

## Active Files

- `config/season.yaml` — year + bracket format (size, num_rounds, num_play_in_games). Per-year data paths derive from `year`; edit this file to change season.
- `src/march_madness/config.py` — `load_season_config()` returns a `SeasonConfig` (year, bracket settings, `raw_dir`/`processed_dir`/`outputs_dir` under `data/<kind>/<year>/`). This is the only place that should ever construct a year-specific data path — don't hardcode `data/raw/...` elsewhere.
- `src/march_madness/bracket/structure.py` — round classification for the fixed R1-R6/64-team bracket, `validate_bracket_config()`/`validate_slots()`, and `order_slots_for_simulation()` (fixes the play-in ordering bug — see Fragile Areas). Any code that consumes `MNCAATourneySlots.csv`-shaped data should go through this module rather than reimplementing round parsing.
- `tests/test_config.py`, `tests/test_bracket_structure.py` — the latter is verified against both synthetic data and the real 2024 `MNCAATourneySlots.csv` from the legacy project.
- `src/march_madness/{ingest,features,models,analysis}/` — empty `__init__.py` placeholders, not yet implemented.

## Frozen / Legacy Zones

- `../March_Madness_2026/` (sibling folder, outside this repo) — the prior implementation. **Read-only reference, never import from it or copy it wholesale.** Pull specific working logic in deliberately (feature engineering, KenPom parsing quirks, bracket slot mechanics, conference tier mapping) and rewrite it into this repo's structure.
- Known issues in that legacy code — do not reintroduce them here: broken import chain (`sims_mens.py` imports a name `seed_prediction.py` no longer defines); hardcoded season year and bracket size (`Season==2024`, `Year==2026`, `index<64`) scattered across files instead of centralized in config; `.py`/`.ipynb` twins that drifted out of sync because notebook changes were manually "ported" to scripts; import-time side effects (training models / plotting on `import`).

## Rules & Coding Style

- No import-time side effects. Modules define functions/classes; execution happens via `scripts/` entry points or `if __name__ == "__main__"`.
- Notebooks (`notebooks/`) are exploration-only. Nothing in `src/` imports from a notebook, and notebook logic is never hand-copied into `src/` without being rewritten as tested functions.
- Season year, bracket size, round count, and play-in count come from `config/season.yaml` — never hardcode a year or team count in `src/`.
- One canonical implementation per model — no duplicate `.py`/`.ipynb` versions of the same logic.
- Comment aggressively per global standards: docstrings state Inputs, Outputs, Purpose, and any non-obvious logic (e.g., KenPom pagination quirks).

## Verification & Test Commands

```
pytest
```

Run this after any change to `src/march_madness/`. Add a corresponding test under `tests/` for every new module — `test_config.py` is the pattern to follow (temp-dir fixtures, no reliance on real season data).

## Fragile Areas

- **KenPom ingest**: raw export is manually copy/pasted (KenPom is subscription-gated and blocks scraping — do not attempt to automate the fetch itself). The paginated source table repeats its header row every ~40 teams and prints a rank subscript next to every stat column. `ingest/kenpom.py` must strip both before merging into history. Get this wrong and every downstream model silently trains on garbage rows.
- **Bracket structure**: `R1`..`R6` and the 64-team main bracket are a *fixed* convention from Kaggle's own data (`MNCAATourneySlots.csv`) — coding them as constants in `bracket/structure.py` is correct, not something to abstract away. What's config-driven is `num_play_in_games`; the invariant `bracket.size == 64 + num_play_in_games` is enforced by `validate_bracket_config()`. A 76-team format is `num_play_in_games=12`, not a different round structure.
- **Play-in slot ordering in raw Kaggle data**: in `MNCAATourneySlots.csv`, play-in slots (e.g. `X16`, defined by `X16a`/`X16b`) are listed *after* the R1 rows that reference them as a seed — confirmed against the real 2024 file. The legacy simulator (`sims_mens.py`) iterated rows in raw file order with no sort, so it would look up an unresolved play-in winner for any R1 slot involving a play-in team. Always run slot data through `order_slots_for_simulation()` before simulating — never assume raw file order is resolution order.
- **Women's tournament**: KenPom has no women's coverage. Do not assume the men's ingest pipeline generalizes — a different ratings source (candidate: Massey Ordinals, already in the Kaggle bundle) will be needed when this is tackled.

## Generated Artifacts

None yet. Once the pipeline exists: `data/processed/`, `data/outputs/`, and `reports/` will hold pipeline-generated files — gitignored, never hand-edited, always safe to delete and regenerate.
