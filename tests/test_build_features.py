import numpy as np
import pandas as pd
import pytest

from march_madness.features.build_features import (
    CONFERENCE_TIERS,
    KENPOM_TO_KAGGLE_CONFERENCE,
    build_matchup_history,
    conference_tier,
    generate_matchup_pairs,
    match_kenpom_teams,
    randomize_matchup_sides,
)
from march_madness.ingest.kaggle import KaggleData

EMPTY_DF = pd.DataFrame()
EMPTY_RESULTS_DF = pd.DataFrame(
    columns=["Season", "DayNum", "WTeamID", "WScore", "LTeamID", "LScore", "WLoc", "NumOT"]
)


def make_kaggle_data(
    regular_season_results=None, tourney_results=None, teams=None, team_spellings=None
) -> KaggleData:
    return KaggleData(
        teams=teams if teams is not None else EMPTY_DF,
        team_spellings=team_spellings if team_spellings is not None else EMPTY_DF,
        seeds=EMPTY_DF,
        slots=EMPTY_DF,
        regular_season_results=(
            regular_season_results if regular_season_results is not None else EMPTY_RESULTS_DF
        ),
        tourney_results=tourney_results if tourney_results is not None else EMPTY_RESULTS_DF,
        conferences=EMPTY_DF,
        team_conferences=EMPTY_DF,
    )


def spellings_for(team_names: dict[str, int]) -> pd.DataFrame:
    """team_name -> TeamID, as MTeamSpellings.csv stores them: lowercase."""
    return pd.DataFrame(
        {"TeamNameSpelling": [name.lower() for name in team_names], "TeamID": list(team_names.values())}
    )


def make_kenpom_row(team: str, season: int, net_rtg: float) -> dict:
    return {
        "Team": team, "Conf": "SEC", "NetRtg": net_rtg, "ORtg": 110.0, "DRtg": 95.0,
        "AdjT": 68.0, "Luck": 0.0, "SOS_NetRtg": 5.0, "SOS_ORtg": 108.0, "SOS_DRtg": 100.0,
        "NCSOS_NetRtg": 2.0, "Seed": np.nan, "W": 20, "L": 10, "Season": season,
    }


def test_conference_tier_known_and_unknown():
    assert conference_tier("sec") == 1
    assert conference_tier("wcc") == 2
    assert conference_tier("some_small_conf") == 3


def test_every_tier_1_and_2_conference_has_a_kenpom_mapping():
    # every Kaggle-convention tier 1/2 conference should be reachable through
    # the kenpom->kaggle mapping, or the tier list is dead weight
    kaggle_convention_values = set(KENPOM_TO_KAGGLE_CONFERENCE.values())
    for conf, tier in CONFERENCE_TIERS.items():
        assert conf in kaggle_convention_values, f"{conf} (tier {tier}) unreachable via KENPOM_TO_KAGGLE_CONFERENCE"


def test_match_kenpom_teams_splits_matched_and_unmatched():
    kenpom = pd.DataFrame([make_kenpom_row("Duke", 2026, 30.0), make_kenpom_row("Not A Real Team", 2026, 10.0)])
    spellings = spellings_for({"Duke": 1181})

    matched, unmatched = match_kenpom_teams(kenpom, spellings)

    assert len(matched) == 1
    assert matched.iloc[0]["TeamID"] == 1181
    assert matched["TeamID"].dtype == int
    assert len(unmatched) == 1
    assert unmatched.iloc[0]["Team"] == "Not A Real Team"


def test_match_kenpom_teams_matches_kenpom_style_abbreviations_via_spellings():
    # this is the real case that broke with a plain exact-name match: KenPom
    # writes "Iowa St." while Kaggle's canonical TeamName is "Iowa State" --
    # MTeamSpellings.csv is the only thing that bridges the two.
    kenpom = pd.DataFrame([make_kenpom_row("Iowa St.", 2026, 22.0)])
    spellings = spellings_for({"Iowa St.": 1235, "Iowa State": 1235})

    matched, unmatched = match_kenpom_teams(kenpom, spellings)

    assert len(matched) == 1
    assert matched.iloc[0]["TeamID"] == 1235
    assert len(unmatched) == 0


def test_build_matchup_history_pairs_games_correctly_when_one_side_is_missing_kenpom_data():
    # Game 0: team 101 beats 102 (both have kenpom data)
    # Game 1: team 103 beats 104 (104 has NO kenpom data -- must drop the
    # whole game, not silently pair team 103 with team 102 via misaligned rows)
    regular_season = pd.DataFrame(
        {
            "Season": [2026, 2026],
            "DayNum": [10, 11],
            "WTeamID": [101, 103],
            "WScore": [80, 90],
            "LTeamID": [102, 104],
            "LScore": [70, 60],
            "WLoc": ["H", "A"],
            "NumOT": [0, 0],
        }
    )
    spellings = spellings_for({"Team101": 101, "Team102": 102, "Team103": 103, "Team104": 104})
    kenpom = pd.DataFrame(
        [
            make_kenpom_row("Team101", 2026, 25.0),
            make_kenpom_row("Team102", 2026, 20.0),
            make_kenpom_row("Team103", 2026, 15.0),
            # Team104 deliberately missing
        ]
    )
    kaggle = make_kaggle_data(regular_season_results=regular_season, team_spellings=spellings)

    history = build_matchup_history(kaggle, kenpom)

    assert len(history) == 1
    row = history.iloc[0]
    assert row["TeamID_A"] == 101
    assert row["TeamID_B"] == 102
    assert row["Season"] == 2026
    assert "Season_B" not in history.columns


def test_build_matchup_history_maps_conference_to_kaggle_convention():
    regular_season = pd.DataFrame(
        {
            "Season": [2026], "DayNum": [10], "WTeamID": [101], "WScore": [80],
            "LTeamID": [102], "LScore": [70], "WLoc": ["H"], "NumOT": [0],
        }
    )
    spellings = spellings_for({"Team101": 101, "Team102": 102})
    kenpom = pd.DataFrame([make_kenpom_row("Team101", 2026, 25.0), make_kenpom_row("Team102", 2026, 20.0)])
    kaggle = make_kaggle_data(regular_season_results=regular_season, team_spellings=spellings)

    history = build_matchup_history(kaggle, kenpom)

    assert history.iloc[0]["Conf_A"] == "sec"  # SEC -> sec via KENPOM_TO_KAGGLE_CONFERENCE


def test_randomize_matchup_sides_winner_matches_swap_direction():
    games = pd.DataFrame(
        {
            "TeamID_A": [1, 2, 3, 4, 5],
            "TeamID_B": [10, 20, 30, 40, 50],
            "NetRtg_A": [1.0, 2.0, 3.0, 4.0, 5.0],
            "NetRtg_B": [10.0, 20.0, 30.0, 40.0, 50.0],
        }
    )

    result = randomize_matchup_sides(games, random_state=0)

    for _, row in result.iterrows():
        # NetRtg_A/_B were set equal to their TeamID by construction -- this
        # only holds after a swap if the whole _A/_B column GROUP moved
        # together, not just TeamID (i.e. the swap is internally consistent).
        assert row["NetRtg_A"] == row["TeamID_A"]
        assert row["NetRtg_B"] == row["TeamID_B"]
        if row["Winner"] == 1:
            assert row["TeamID_A"] in {1, 2, 3, 4, 5}
        else:
            assert row["TeamID_A"] in {10, 20, 30, 40, 50}


def test_randomize_matchup_sides_is_reproducible_with_random_state():
    games = pd.DataFrame({"TeamID_A": range(20), "TeamID_B": range(100, 120)})

    result1 = randomize_matchup_sides(games, random_state=42)
    result2 = randomize_matchup_sides(games, random_state=42)

    pd.testing.assert_frame_equal(result1, result2)


def test_generate_matchup_pairs_excludes_self_pairs_and_covers_all_combinations():
    pairs = generate_matchup_pairs([1, 2, 3])

    assert len(pairs) == 6  # 3 teams -> 3*2 ordered pairs
    assert (1, 1) not in pairs
    assert (1, 2) in pairs
    assert (2, 1) in pairs
