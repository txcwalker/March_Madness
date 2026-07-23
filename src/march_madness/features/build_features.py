"""
Builds matchup-level training features by joining Kaggle game results with
KenPom efficiency ratings, and provides the conference-tier and side-
randomization utilities the models train on. Also reconciles KenPom's team
names against Kaggle's TeamIDs -- deferred here from ingest/kenpom.py since
it's a join concern, not a cleaning concern (see AGENTS.md Fragile Areas).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from march_madness.ingest.kaggle import KaggleData

# KenPom's conference abbreviations don't match Kaggle's ConfAbbrev
# convention (e.g. "B12" vs "big_twelve"). Ported from the legacy project's
# conf_mapping -- the two files there had drifted to use inconsistent key
# conventions for the same concept; this is the one canonical version.
#
# KenPom's own abbreviations drift over time too, the same way "AdjEM"
# became "NetRtg" (see ingest/kenpom.py) -- the legacy dict used "Pat" for
# the Patriot League, but the real 2026 export uses "PL" instead. Verified
# against the real kenpom_2026_raw.csv: without BSth/BW/PL/SC, 10% of
# matchup rows silently got a null conference. Both old and current
# abbreviations are kept where known, since older KenPom history may still
# use the old ones.
KENPOM_TO_KAGGLE_CONFERENCE: dict[str, str] = {
    "SEC": "sec", "CUSA": "cusa", "MAC": "mac", "B12": "big_twelve",
    "B10": "big_ten", "MWC": "mwc", "BSky": "big_sky", "ASun": "a_sun",
    "MVC": "mvc", "BE": "big_east", "Horz": "horizon", "OVC": "ovc",
    "ACC": "acc", "P10": "pac_ten", "Slnd": "southland", "A10": "aac",
    "SB": "sun_belt", "Ivy": "ivy", "WCC": "wcc", "WAC": "wac",
    "CAA": "caa", "Pat": "patriot", "PL": "patriot", "MAAC": "maac",
    "NEC": "nec", "AE": "aec", "SWAC": "swac", "MEAC": "meac",
    "Sum": "summit", "P12": "pac_twelve", "Amer": "americ_east",
    "BW": "big_west", "SC": "southern", "BSth": "big_south",
}

# Power conferences are tier 1, solid mid-majors tier 2, everyone else tier 3.
# Keyed on Kaggle's ConfAbbrev convention (the canonical join target), not
# KenPom's raw abbreviations -- map through KENPOM_TO_KAGGLE_CONFERENCE first.
CONFERENCE_TIERS: dict[str, int] = {
    "sec": 1, "big_twelve": 1, "big_ten": 1, "acc": 1, "big_east": 1,
    "pac_twelve": 1, "mwc": 1,
    "aac": 2, "americ_east": 2, "mvc": 2, "wcc": 2,
}


def conference_tier(conf_abbrev: str) -> int:
    """Tier for a Kaggle-convention conference abbreviation; unlisted conferences default to tier 3."""
    return CONFERENCE_TIERS.get(conf_abbrev, 3)


def match_kenpom_teams(
    kenpom: pd.DataFrame, team_spellings: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Inputs: cleaned KenPom history (Team, Season, ...) and Kaggle's
            MTeamSpellings.csv (TeamNameSpelling, TeamID) -- a lowercase
            lookup of every known alternate spelling for each team,
            including KenPom-style abbreviations ("iowa st.", "n.c. state").
    Outputs: (matched, unmatched) -- matched has TeamID attached (int, no
             NaNs); unmatched is every KenPom (Team, Season) row whose
             lowercased name isn't in the spellings table at all.
    Purpose: an earlier version of this function matched on an exact,
             case-sensitive 'Team' == Kaggle 'TeamName' string (mirroring
             the legacy project) and silently dropped 137 of 365 teams
             (38%) from the real 2026 data -- KenPom's "Iowa St." never
             equals Kaggle's "Iowa State". Matching against
             MTeamSpellings.csv instead recovers 352/365 (96%); the
             remainder is returned as `unmatched` so it stays visible
             instead of silently disappearing.
    """
    kenpom = kenpom.copy()
    kenpom["_team_key"] = kenpom["Team"].str.lower()
    spellings = team_spellings.rename(columns={"TeamNameSpelling": "_team_key"})

    merged = kenpom.merge(spellings, on="_team_key", how="left", indicator=True)

    matched = merged[merged["_merge"] == "both"].drop(columns=["_merge", "_team_key"]).reset_index(
        drop=True
    )
    matched["TeamID"] = matched["TeamID"].astype(int)

    unmatched = (
        merged[merged["_merge"] == "left_only"]
        .drop(columns=["_merge", "_team_key", "TeamID"])
        .reset_index(drop=True)
    )
    return matched, unmatched


def _split_and_join_results(results: pd.DataFrame, matched_kenpom: pd.DataFrame) -> pd.DataFrame:
    """Winner/loser rows of one results table, each joined to KenPom stats, paired back up by GameID."""
    results = results.reset_index(drop=True).rename_axis("GameID").reset_index()

    winners = results.rename(columns={"WTeamID": "TeamID", "WScore": "Score"})[
        ["GameID", "Season", "TeamID", "Score"]
    ].merge(matched_kenpom, on=["TeamID", "Season"], how="inner")

    losers = results.rename(columns={"LTeamID": "TeamID", "LScore": "Score"})[
        ["GameID", "Season", "TeamID", "Score"]
    ].merge(matched_kenpom, on=["TeamID", "Season"], how="inner")

    # Joining on the explicit GameID key (not positional/row-index alignment)
    # matters: winners and losers each go through their own inner join with
    # KenPom stats, which can drop different rows from each side. The legacy
    # project's tournament-game merge used left_index/right_index alignment
    # instead of a real key, which would silently pair up unrelated games
    # the moment the two sides' row counts diverged.
    return winners.merge(losers, on="GameID", suffixes=("_A", "_B"))


def build_matchup_history(kaggle: KaggleData, kenpom_history: pd.DataFrame) -> pd.DataFrame:
    """
    Inputs: a season's KaggleData bundle (regular_season_results,
            tourney_results, team_spellings) and the full multi-year
            KenPom history.
    Outputs: one row per historical game with the winning team's stats
            suffixed _A and the losing team's suffixed _B (before any side
            randomization -- see randomize_matchup_sides), Conf already
            mapped to Kaggle's convention.
    Purpose: joins Kaggle's game results to KenPom's per-team-per-season
             ratings via TeamID+Season, for both regular-season and
             tournament games -- this is the training set the win-
             probability models learn from.
    """
    matched_kenpom, _unmatched = match_kenpom_teams(kenpom_history, kaggle.team_spellings)
    matched_kenpom = matched_kenpom.copy()
    matched_kenpom["Conf"] = matched_kenpom["Conf"].map(KENPOM_TO_KAGGLE_CONFERENCE)

    regular_season = _split_and_join_results(kaggle.regular_season_results, matched_kenpom)
    tourney = _split_and_join_results(kaggle.tourney_results, matched_kenpom)

    games = pd.concat([regular_season, tourney], ignore_index=True)
    games = games.drop(columns=["Season_B"]).rename(columns={"Season_A": "Season"})
    return games


def randomize_matchup_sides(games: pd.DataFrame, random_state: int | None = None) -> pd.DataFrame:
    """
    Inputs: a games DataFrame where every row's *_A columns describe the
            actual winner and *_B columns describe the actual loser (true
            by construction of build_matchup_history).
    Outputs: a copy where each row's _A/_B columns are independently
             swapped with 50% probability, plus a binary `Winner` column
             (1 if the "A" side -- post-swap -- is the actual winner).
    Purpose: a classifier trained directly on build_matchup_history's output
             could trivially learn "A always wins." This is the anti-
             leakage step, ported from the legacy stat_swap but vectorized
             instead of a per-row Python loop -- behaviorally identical,
             meaningfully faster on the full multi-decade game history.
    """
    rng = np.random.default_rng(random_state)
    should_swap = rng.random(len(games)) < 0.5

    columns_a = [c for c in games.columns if c.endswith("_A")]
    columns_b = [c[: -len("_A")] + "_B" for c in columns_a]

    result = games.copy()
    a_values = games.loc[should_swap, columns_a].to_numpy()
    b_values = games.loc[should_swap, columns_b].to_numpy()
    result.loc[should_swap, columns_a] = b_values
    result.loc[should_swap, columns_b] = a_values

    result["Winner"] = (~should_swap).astype(int)
    return result


def generate_matchup_pairs(team_ids: list[int]) -> list[tuple[int, int]]:
    """All ordered pairs of distinct team IDs -- every hypothetical matchup for a set of teams."""
    return [(a, b) for a in team_ids for b in team_ids if a != b]
