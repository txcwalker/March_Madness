"""
One-time import of pre-2026 KenPom history from the legacy project's
already-merged, already-cleaned data/kenpom_fin_df.csv (2003-2026, sourced
from the legacy project's own accumulated manual pastes -- there is no raw
per-year KenPom export left on disk for these seasons to run through
clean_kenpom_export() normally).

Writes data/processed/<year>/kenpom_clean.csv for each season 2003-2025 in
clean_kenpom_export()'s own output shape (column names, W/L already split,
the Excel date-mangling bug already fixed), which
ingest.kenpom.build_kenpom_history() picks up directly for any year that
has no raw export of its own. 2026 is deliberately excluded -- this repo
already has its own independently-pulled, independently-verified raw
kenpom_2026_raw.csv, which is the more trustworthy source for that season.

This is why the finding it fixes matters: with only 2026 populated, the
rebuild's models trained on ~5,300 games instead of the legacy project's
~120,000 across 23 seasons, which hit XGBoost and the neural net far harder
than logistic regression or random forest (see scripts/evaluate_models.py
and WORKLOG.md for the real numbers).

Usage:
    python scripts/backfill_historical_kenpom.py
    python scripts/backfill_historical_kenpom.py --source ../March_Madness_2026/data/kenpom_fin_df.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from march_madness.config import DEFAULT_CONFIG_PATH, load_season_config
from march_madness.ingest.kenpom import parse_win_loss_component

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = REPO_ROOT.parent / "March_Madness_2026" / "data" / "kenpom_fin_df.csv"

# legacy column name -> clean_kenpom_export() output column name. KenPom's
# own column names drifted over time (AdjEM -> NetRtg, etc. -- see
# ingest/kenpom.py's module docstring and AGENTS.md Fragile Areas), and the
# legacy project's merged file kept the older names throughout.
COLUMN_RENAME = {
    "AdjEM": "NetRtg",
    "AdjO": "ORtg",
    "AdjD": "DRtg",
    "AdjEM_SOS": "SOS_NetRtg",
    "OppO": "SOS_ORtg",
    "OppD": "SOS_DRtg",
    "AdjEM_NCSOS": "NCSOS_NetRtg",
}

# Matches clean_kenpom_export()'s actual output column order.
OUTPUT_COLUMNS = [
    "Team", "Conf", "NetRtg", "ORtg", "DRtg", "AdjT", "Luck",
    "SOS_NetRtg", "SOS_ORtg", "SOS_DRtg", "NCSOS_NetRtg", "Seed", "W", "L", "Season",
]

EXCLUDED_SEASON = 2026  # this repo has its own fresher, independently-verified raw pull for this year


def convert_legacy_history(source: pd.DataFrame) -> pd.DataFrame:
    """
    Inputs: the legacy project's data/kenpom_fin_df.csv, already read.
    Outputs: the same data, reshaped into clean_kenpom_export()'s exact
             output schema -- so build_kenpom_history() can include it
             directly, with no further cleaning step.
    Purpose: the legacy file still has the pre-split "W-L" column ("32-4"),
             including the same Excel date-mangling corruption
             ingest/kenpom.py's clean_kenpom_export() already has a fix for
             (verified: ~29% of rows in this file are affected) -- reuses
             that same fix (parse_win_loss_component(), applied to both
             sides) rather than a second copy of it.
    """
    df = source.rename(columns=COLUMN_RENAME).copy()

    wins_losses = df["W-L"].str.split("-", expand=True)
    df["W"] = wins_losses[0].apply(parse_win_loss_component)
    df["L"] = wins_losses[1].apply(parse_win_loss_component)

    return df[OUTPUT_COLUMNS]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    args = parser.parse_args()

    if not args.source.exists():
        raise SystemExit(f"Source file not found: {args.source}")

    config = load_season_config(args.config)
    processed_root = config.raw_dir.parent.parent / "processed"

    source = pd.read_csv(args.source)
    converted = convert_legacy_history(source)

    seasons = sorted(s for s in converted["Season"].unique() if s != EXCLUDED_SEASON)
    print(f"Importing {len(seasons)} seasons ({seasons[0]}-{seasons[-1]}), skipping {EXCLUDED_SEASON}...")

    for season in seasons:
        season_dir = processed_root / str(season)
        season_dir.mkdir(parents=True, exist_ok=True)
        out_path = season_dir / "kenpom_clean.csv"
        converted[converted["Season"] == season].to_csv(out_path, index=False)

    print(f"Wrote {len(seasons)} files under {processed_root}/<year>/kenpom_clean.csv")


if __name__ == "__main__":
    main()
