"""
Cleans KenPom's raw pasted export and merges it into a multi-year history.

KenPom is subscription-gated and blocks scraping, so getting the raw export
each year stays a manual copy/paste into data/raw/<year>/kenpom_raw.csv.
Everything after that -- which used to be done by hand in Excel -- is here:
stripping the rank number printed next to every stat, dropping any stray
repeated header row from copying a paginated table, and splitting the
Team/Seed and W-L fields apart.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

# KenPom's raw export repeats NetRtg/ORtg/DRtg once for the main stat and
# again for Strength-of-Schedule / Non-Conference-SOS, always in this fixed
# group order. pandas suffixes the repeats as NetRtg, NetRtg.1, NetRtg.2 --
# this maps each occurrence, in order, to a distinct name.
_DUPLICATE_STAT_RENAME_SCHEDULE: dict[str, list[str]] = {
    "NetRtg": ["NetRtg", "SOS_NetRtg", "NCSOS_NetRtg"],
    "ORtg": ["ORtg", "SOS_ORtg"],
    "DRtg": ["DRtg", "SOS_DRtg"],
}

# Excel silently reformats a "W-L" value like "20-12" into a date ("20-Dec")
# whenever the loss count looks like a month number (1-12) -- a real
# corruption confirmed in the raw export (~90 teams/year), not a hypothetical.
_MONTH_ABBREVIATION_TO_LOSSES = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}


def _parse_losses(value: str) -> float:
    """Recovers the real loss count when Excel has date-mangled it into a month abbreviation."""
    month = _MONTH_ABBREVIATION_TO_LOSSES.get(value)
    if month is not None:
        return float(month)
    return pd.to_numeric(value, errors="coerce")


def read_kenpom_csv(path: Path | str) -> pd.DataFrame:
    """Reads a raw KenPom export CSV, handling the UTF-8 BOM the copy/paste leaves behind."""
    return pd.read_csv(path, encoding="utf-8-sig")


def _rename_duplicate_stat_columns(columns: list[str]) -> list[str]:
    occurrence_counts: dict[str, int] = {}
    renamed = []
    for col in columns:
        base = col.split(".")[0]
        schedule = _DUPLICATE_STAT_RENAME_SCHEDULE.get(base)
        if schedule is None:
            renamed.append(col)
            continue
        index = occurrence_counts.get(base, 0)
        occurrence_counts[base] = index + 1
        renamed.append(schedule[index] if index < len(schedule) else col)
    return renamed


def clean_kenpom_export(raw: pd.DataFrame, season: int) -> pd.DataFrame:
    """
    Inputs: this year's raw pasted KenPom export, as read from the CSV, and
            the season it represents (the raw export itself has no year
            column -- it's a snapshot of one point in time).
    Outputs: a cleaned DataFrame -- one row per team, numeric stat columns,
             Team/Seed split apart, W/L split apart, a Season column added.
    Purpose: codifies the cleanup previously done by hand in Excel every
             year: dropping rank-subscript columns and any stray repeated
             header row from copying KenPom's paginated table.
    """
    df = raw.copy()

    # A repeated header row (from copying a paginated table) has the literal
    # string "Rk" in the first column instead of a rank number.
    df = df[df.iloc[:, 0].astype(str) != "Rk"].reset_index(drop=True)

    # Rank-subscript columns have no header text; pandas names them "Unnamed: N".
    df = df.loc[:, ~df.columns.str.match(r"^Unnamed")]

    df.columns = _rename_duplicate_stat_columns(list(df.columns))

    # KenPom appends a team's actual tournament seed to its name once the
    # bracket is set (e.g. "Duke 1"). Before Selection Sunday there's no
    # digit to extract and Seed is simply missing.
    extracted = df["Team"].astype(str).str.extract(r"^(.*?)\s*(\d*)\*?$")
    df["Team"] = extracted[0].str.strip()
    df["Seed"] = pd.to_numeric(extracted[1], errors="coerce")

    wins_losses = df["W-L"].str.split("-", expand=True)
    df["W"] = pd.to_numeric(wins_losses[0], errors="coerce")
    df["L"] = wins_losses[1].apply(_parse_losses)
    df = df.drop(columns=["W-L", "Rk"])

    df["Season"] = season

    return df


def build_kenpom_history(raw_root: Path | str) -> pd.DataFrame:
    """
    Inputs: the repo's data/raw directory, containing one subfolder per
            season (e.g. data/raw/2026/kenpom_raw.csv).
    Outputs: every available season's raw export, cleaned and concatenated
             into one DataFrame, sorted by Season.
    Purpose: replaces re-pasting the full multi-year history by hand each
             season -- every past year's raw export stays on disk under its
             own year folder, so this merged history is always regenerable
             from scratch.
    """
    raw_root = Path(raw_root)
    cleaned_seasons = [
        clean_kenpom_export(read_kenpom_csv(export_path), season=int(export_path.parent.name))
        for export_path in sorted(raw_root.glob("*/kenpom_raw.csv"))
    ]

    if not cleaned_seasons:
        raise FileNotFoundError(f"No kenpom_raw.csv found under any year folder in {raw_root}")

    return (
        pd.concat(cleaned_seasons, ignore_index=True)
        .sort_values("Season")
        .reset_index(drop=True)
    )
