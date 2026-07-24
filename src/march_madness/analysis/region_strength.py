"""
Region-level analysis on bracket.simulate's Monte Carlo output. The legacy
sims_mens.py hardcoded a 56-team name-to-region dictionary that had to be
rebuilt by hand every season, plus a "Fragility_Score" formula that
hardcoded which specific team was the top seed in each region. Neither is
necessary: Kaggle's seed codes already encode region as the first
character (e.g. "W01" -> region "W"), and the top seed in a region is
whichever team has Seed == 1 there -- both derivable from data.
"""

from __future__ import annotations

import pandas as pd


def region_of_seed(seed: str) -> str:
    """
    The region code is the first character of a Kaggle seed string (e.g.
    "W01" -> "W", "X16a" -> "X"). These are Kaggle's internal region labels
    for the season, not real-world region names like "East"/"Midwest" --
    mapping to real names (if wanted for presentation) is Milestone 2's job.
    """
    return seed[0]


def region_championship_counts(results: pd.DataFrame, seed_to_team: dict[str, int]) -> pd.Series:
    """
    Inputs: bracket.simulate.run_monte_carlo() output and the season's
            Seed -> TeamID mapping.
    Outputs: region -> number of simulated brackets that region's teams
             won the national championship in.
    """
    team_to_region = {team_id: region_of_seed(seed) for seed, team_id in seed_to_team.items()}

    champions = results[results["Slot"] == "R6CH"].copy()
    champions["Region"] = champions["TeamID"].map(team_to_region)
    return champions["Region"].value_counts()


def region_top_seed_championship_share(results: pd.DataFrame, seed_to_team: dict[str, int]) -> pd.Series:
    """
    Inputs: same as region_championship_counts.
    Outputs: region -> fraction of that region's simulated championships
             won specifically by the region's #1 seed.
    Purpose: generalizes the legacy "Fragility_Score" -- how top-heavy a
             region is, i.e. how much of its championship share rests on
             one team, versus being spread across multiple contenders. A
             region near 1.0 is entirely carried by its top seed; a region
             near 0 had its championships spread across several teams.
    """
    # Kaggle seed codes are always a region letter + a zero-padded 2-digit
    # seed number (+ an optional play-in "a"/"b" suffix), e.g. "W01", "X16a".
    top_seed_by_region = {
        region_of_seed(seed): team_id for seed, team_id in seed_to_team.items() if seed[1:3] == "01"
    }

    region_counts = region_championship_counts(results, seed_to_team)
    team_to_region = {team_id: region_of_seed(seed) for seed, team_id in seed_to_team.items()}
    champions = results[results["Slot"] == "R6CH"].copy()
    champions["Region"] = champions["TeamID"].map(team_to_region)

    shares = {}
    for region, total in region_counts.items():
        top_seed_team = top_seed_by_region.get(region)
        top_seed_wins = (champions.loc[champions["Region"] == region, "TeamID"] == top_seed_team).sum()
        shares[region] = top_seed_wins / total if total > 0 else 0.0

    return pd.Series(shares, name="TopSeedChampionshipShare")
