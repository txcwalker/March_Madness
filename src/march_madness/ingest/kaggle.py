"""Loads the men's-tournament Kaggle CSVs for a season from data/raw/<year>/kaggle/."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

_FILES = {
    "teams": "MTeams.csv",
    "seeds": "MNCAATourneySeeds.csv",
    "slots": "MNCAATourneySlots.csv",
    "regular_season_results": "MRegularSeasonCompactResults.csv",
    "tourney_results": "MNCAATourneyCompactResults.csv",
    "conferences": "Conferences.csv",
    "team_conferences": "MTeamConferences.csv",
}


@dataclass(frozen=True)
class KaggleData:
    teams: pd.DataFrame
    seeds: pd.DataFrame
    slots: pd.DataFrame
    regular_season_results: pd.DataFrame
    tourney_results: pd.DataFrame
    conferences: pd.DataFrame
    team_conferences: pd.DataFrame


def load_kaggle_data(kaggle_dir: Path | str) -> KaggleData:
    """
    Inputs: path to a directory containing this year's Kaggle competition CSVs
            (data/raw/<year>/kaggle/, dropped in by hand each season from
            https://www.kaggle.com/competitions/march-machine-learning-mania-<year>).
    Outputs: a KaggleData bundle of the men's-tournament frames the pipeline uses.
    Purpose: one explicit list of which Kaggle files this project depends on
             and where they live -- adding a new file means adding one line
             here, not another scattered pd.read_csv call.
    """
    kaggle_dir = Path(kaggle_dir)
    missing = [name for name in _FILES.values() if not (kaggle_dir / name).exists()]
    if missing:
        raise FileNotFoundError(
            f"Missing Kaggle file(s) in {kaggle_dir}: {', '.join(missing)}. "
            "Download this season's competition data and drop the CSVs here."
        )

    frames = {key: pd.read_csv(kaggle_dir / filename) for key, filename in _FILES.items()}
    return KaggleData(**frames)
