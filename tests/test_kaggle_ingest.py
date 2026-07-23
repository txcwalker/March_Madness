import pandas as pd
import pytest

from march_madness.ingest.kaggle import load_kaggle_data

FIXTURES = {
    "MTeams.csv": "TeamID,TeamName,FirstD1Season,LastD1Season\n1101,Abilene Chr,2014,2026\n",
    "MNCAATourneySeeds.csv": "Season,Seed,TeamID\n2024,W01,1163\n",
    "MNCAATourneySlots.csv": "Season,Slot,StrongSeed,WeakSeed\n2024,R1W1,W01,W16\n",
    "MRegularSeasonCompactResults.csv": (
        "Season,DayNum,WTeamID,WScore,LTeamID,LScore,WLoc,NumOT\n2024,20,1228,81,1328,64,N,0\n"
    ),
    "MNCAATourneyCompactResults.csv": (
        "Season,DayNum,WTeamID,WScore,LTeamID,LScore,WLoc,NumOT\n2024,136,1116,63,1234,54,N,0\n"
    ),
    "Conferences.csv": "ConfAbbrev,Description\na_sun,Atlantic Sun Conference\n",
    "MTeamConferences.csv": "Season,TeamID,ConfAbbrev\n2024,1102,wac\n",
}


def write_fixture_dir(tmp_path, exclude: set[str] = frozenset()) -> "Path":
    kaggle_dir = tmp_path / "kaggle"
    kaggle_dir.mkdir()
    for filename, content in FIXTURES.items():
        if filename in exclude:
            continue
        (kaggle_dir / filename).write_text(content, encoding="utf-8")
    return kaggle_dir


def test_loads_all_expected_frames(tmp_path):
    data = load_kaggle_data(write_fixture_dir(tmp_path))

    assert isinstance(data.teams, pd.DataFrame)
    assert data.teams.iloc[0]["TeamName"] == "Abilene Chr"
    assert data.seeds.iloc[0]["Seed"] == "W01"
    assert data.slots.iloc[0]["Slot"] == "R1W1"
    assert data.regular_season_results.iloc[0]["WScore"] == 81
    assert data.tourney_results.iloc[0]["LScore"] == 54
    assert data.conferences.iloc[0]["ConfAbbrev"] == "a_sun"
    assert data.team_conferences.iloc[0]["ConfAbbrev"] == "wac"


def test_missing_file_raises_a_clear_error(tmp_path):
    kaggle_dir = write_fixture_dir(tmp_path, exclude={"MTeams.csv"})

    with pytest.raises(FileNotFoundError, match="MTeams.csv"):
        load_kaggle_data(kaggle_dir)


def test_missing_directory_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_kaggle_data(tmp_path / "does_not_exist")
