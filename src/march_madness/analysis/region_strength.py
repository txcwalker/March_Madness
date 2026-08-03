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

from march_madness.analysis.bracket_path import average_win_probability, resolve_slot_winners_by_bracket
from march_madness.bracket.structure import round_of


def region_of_seed(seed: str) -> str:
    """
    The region code is the first character of a Kaggle seed string (e.g.
    "W01" -> "W", "X16a" -> "X"). These are Kaggle's internal region labels
    for the season, not real-world region names like "East"/"Midwest" --
    mapping to real names (if wanted for presentation) is Milestone 2's job.
    """
    return seed[0]


def region_of_main_bracket_slot(slot: str) -> str | None:
    """
    Inputs: a bracket slot code.
    Outputs: the region letter for an R1-R4 slot (e.g. "R2W1" -> "W") --
             the region character always sits right after the round digit
             for these four rounds (confirmed against the real 2026
             MNCAATourneySlots.csv: "R1W1".."R1W8", "R2W1".."R2W4",
             "R3W1"/"R3W2", "R4W1"). None for anything else: a play-in
             slot, or R5/R6 (e.g. "R5WX", "R6CH"), which pair two
             *different* regions together and so don't belong to just one.
    Purpose: region_competitiveness() needs to know which of a season's
             63 main-bracket games belong to which region; slot codes
             encode that directly, no lookup table needed.
    """
    code = round_of(slot)
    if code not in {"R1", "R2", "R3", "R4"}:
        return None
    return slot[len(code)]


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


def region_top_seed_final_four_share(results: pd.DataFrame, seed_to_team: dict[str, int]) -> pd.Series:
    """
    Inputs: bracket.simulate.run_monte_carlo() output and the season's
            Seed -> TeamID mapping.
    Outputs: region -> fraction of ALL simulated brackets (not just the
             ones that region goes on to win nationally) in which that
             region's own #1 seed is the team reaching the Final Four.
    Purpose: this is the actual "how fragile/top-heavy is this region"
             question, and the primary region-strength metric as of
             2026-07-30 -- see region_top_seed_championship_share's
             docstring for why that one is NOT this: it conditions on the
             region also winning the whole national title, which (a) mixes
             in cross-region championship-game strength that has nothing
             to do with how competitive the region itself is, and (b) is
             statistically unstable for any region that rarely wins it all
             (e.g. one real 2026 region's conditional share was computed
             from only ~120 of 10,000 brackets). Conditioning on reaching
             the Final Four instead uses the full 10,000-bracket
             denominator for every region, regardless of how that team
             fares afterward.
    """
    team_to_region = {team_id: region_of_seed(seed) for seed, team_id in seed_to_team.items()}
    top_seed_by_region = {
        region_of_seed(seed): team_id for seed, team_id in seed_to_team.items() if seed[1:3] == "01"
    }

    n_brackets = results["Bracket"].nunique()
    final_four = results[results["Slot"].map(round_of) == "R4"].copy()
    final_four["Region"] = final_four["TeamID"].map(team_to_region)

    shares = {}
    for region, top_seed_team in top_seed_by_region.items():
        region_reps = final_four[final_four["Region"] == region]
        top_seed_reps = (region_reps["TeamID"] == top_seed_team).sum()
        shares[region] = top_seed_reps / n_brackets if n_brackets else 0.0

    return pd.Series(shares, name="TopSeedFinalFourShare")


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

             NOT the primary region-strength metric as of 2026-07-30 --
             see region_top_seed_final_four_share, which answers the same
             question without conditioning on this region also winning the
             whole national title (a real 2026 audit found that
             conditioning made the stat both conceptually conflated with
             cross-region strength and statistically unstable for
             low-championship-share regions). Kept as a distinct,
             still-meaningful secondary stat, not removed.
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


def region_competitiveness(
    slots: pd.DataFrame,
    seed_to_team: dict[str, int],
    win_probabilities: dict[int, dict[int, float]],
    results: pd.DataFrame,
) -> pd.Series:
    """
    Inputs: one season's slots, its Seed -> TeamID mapping, the
            (symmetrized) win-probability matrix from
            bracket.simulate.compute_win_probabilities(), and the raw
            long-format Monte Carlo results from
            bracket.simulate.run_monte_carlo().
    Outputs: {region: average outcome uncertainty across every game
             actually played within that region (R1-R4 only -- R5/R6 pair
             two different regions and aren't "that region's" game),
             across all 10,000 simulated brackets}. Closeness for a single
             game is `2 * (1 - favorite's win probability)`: 1.0 at a
             50/50 tossup, 0.0 at a lock. Averaging across every
             region-internal game gives a 0-1 score per region: 1.0 means
             every game in that region was close to a coin flip, 0.0 means
             every game was a near-certainty.

             This measures how UNPREDICTABLE THE WINNER is, not margin of
             victory -- a 90/10 favorite can still win by one point, and a
             55/45 game can be a blowout. This metric only ever looks at
             pregame win probability, never a simulated score, so don't
             read it as "how close the games were on the scoreboard."

             Deliberately distinct from region_top_seed_final_four_share/
             region_top_seed_championship_share, which measure whether the
             *presumed-best* team actually succeeds. A region can score low
             here (every game a near-lock) while still looking "fragile" by
             those metrics if the team doing all the winning isn't the top
             seed; a region can score high here (every game a tossup) while
             still looking "dominant" by those metrics if the same team
             keeps winning its coin flips anyway. Neither metric replaces
             the other -- see WORKLOG for the "Duke keeps winning, but the
             other games are all coin flips" case that motivated this.

             The first round's games don't actually need the 10,000-bracket
             loop (both teams are directly seeded, identical in every
             bracket), but this doesn't special-case that -- looping
             uniformly keeps the logic simple and the redundant work is
             cheap relative to the whole pipeline.
    """
    region_games = slots[slots["Slot"].map(region_of_main_bracket_slot).notna()].copy()
    region_games["Region"] = region_games["Slot"].map(region_of_main_bracket_slot)
    brackets = resolve_slot_winners_by_bracket(results)

    closeness_by_region: dict[str, list[float]] = {}
    for row in region_games.itertuples():
        for bracket_winners in brackets.values():
            team1 = (
                seed_to_team[row.StrongSeed] if row.StrongSeed in seed_to_team else bracket_winners[row.StrongSeed]
            )
            team2 = seed_to_team[row.WeakSeed] if row.WeakSeed in seed_to_team else bracket_winners[row.WeakSeed]
            favorite_win_prob = max(win_probabilities[team1][team2], win_probabilities[team2][team1])
            closeness = 2 * (1 - favorite_win_prob)
            closeness_by_region.setdefault(row.Region, []).append(closeness)

    return pd.Series(
        {region: sum(values) / len(values) for region, values in closeness_by_region.items()},
        name="Competitiveness",
    )


def strongest_team_by_region(
    team_to_region: dict[int, str], win_probabilities: dict[int, dict[int, float]]
) -> dict[str, int]:
    """
    Inputs: TeamID -> region mapping and the (symmetrized) win-probability
            matrix from bracket.simulate.compute_win_probabilities().
    Outputs: {region: TeamID of that region's model-implied strongest
             team} -- ranked by average_win_probability() (mean win
             probability against the whole field), not by seed number.
    Purpose: the "favorite" to condition region_effective_contenders() on.
             Deliberately not just "whichever team has Seed == 1" the way
             region_top_seed_*_share() picks its reference team -- the
             seed-prediction discussion in WORKLOG.md concluded a seed
             number isn't a reliable stand-in for actual team strength, and
             this metric shouldn't inherit that problem just because the
             other region metrics (which are specifically ABOUT the top
             seed, on purpose) do.
    """
    strength = average_win_probability(win_probabilities)
    strongest: dict[str, int] = {}
    for team_id, region in team_to_region.items():
        if region not in strongest or strength[team_id] > strength[strongest[region]]:
            strongest[region] = team_id
    return strongest


def region_effective_contenders(
    benefit: pd.DataFrame, team_to_region: dict[int, str], favorite_by_region: dict[str, int]
) -> pd.Series:
    """
    Inputs: analysis.round_advancement.benefit_if_team_loses()'s output,
            TeamID -> region, and {region: favorite TeamID} (see
            strongest_team_by_region()).
    Outputs: {region: effective number of realistic Final Four contenders
             if that region's favorite doesn't make it}. Computed as the
             reciprocal of the Herfindahl-Hirschman Index (a standard
             market-concentration statistic): HHI = the sum of squared
             FinalFourShareIfXEliminated across the region's other teams,
             with TeamX fixed to that region's favorite. These shares
             already form a real probability distribution -- they sum to
             ~1.0 across the region's other teams, since exactly one
             non-favorite team represents the region in every bracket
             where the favorite doesn't. 1/HHI ranges from 1 (one
             overwhelming backup, nobody else has a real shot) up toward
             the number of teams in the region (every team equally live).
             A region with a clean 50% favorite and three genuinely equal
             backups scores almost exactly 3 here -- see WORKLOG for the
             worked textbook check.
    """
    contenders: dict[str, float | None] = {}
    for region, team_x in favorite_by_region.items():
        rows = benefit[(benefit["TeamX"] == team_x) & (benefit["TeamY"].map(team_to_region) == region)]
        hhi = float((rows["FinalFourShareIfXEliminated"] ** 2).sum())
        contenders[region] = (1 / hhi) if hhi > 0 else None
    return pd.Series(contenders, name="EffectiveContenders")
