"""
Round-advancement analysis on bracket.simulate's Monte Carlo output.
Generalizes the legacy sims_mens.py's round-count/"Cinderella" analysis,
which hardcoded specific team names and only worked for one season's
bracket -- here every function takes the simulation results and a
Seed -> TeamID mapping, so it works for any season without editing code.
"""

from __future__ import annotations

import pandas as pd

from march_madness.bracket.structure import round_name, round_of

# Historical average tournament wins by seed line, source:
# https://bracketodds.cs.illinois.edu/seedadv.html -- a real, cited external
# baseline (not something this project computes), used to judge whether a
# team's simulated performance beat or missed what its seed typically does.
HISTORICAL_AVERAGE_WINS_BY_SEED: dict[int, float] = {
    1: 3.30, 2: 2.33, 3: 1.84, 4: 1.56, 5: 1.15, 6: 1.04, 7: 0.90, 8: 0.71,
    9: 0.62, 10: 0.60, 11: 0.67, 12: 0.51, 13: 0.25, 14: 0.16, 15: 0.10, 16: 0.013,
}


def count_wins_per_bracket(results: pd.DataFrame) -> pd.DataFrame:
    """
    Inputs: bracket.simulate.run_monte_carlo() output (Bracket, Slot, TeamID).
    Outputs: one row per (Bracket, TeamID) with a Wins count -- how many
             games that team won in that single simulated bracket.
    """
    return (
        results.groupby(["Bracket", "TeamID"])
        .size()
        .reset_index(name="Wins")
    )


def average_wins_by_team(results: pd.DataFrame, team_ids: list[int]) -> pd.Series:
    """
    Inputs: bracket.simulate.run_monte_carlo() output, and the full list of
            TeamIDs in the bracket's field.
    Outputs: TeamID -> average wins per bracket.
    Purpose: a team that loses its first game in every single bracket never
             appears as a winner in `results` at all -- averaging only over
             the brackets a team *does* appear in (as the legacy project's
             simplest possible approach would) silently inflates weak
             teams' averages by excluding their 0-win brackets from the
             denominator. `team_ids` must be passed explicitly because
             `results` alone can't tell you about a team that never won
             anything -- summing total wins and dividing by the total
             bracket count (rather than reindexing then averaging) gets the
             same correct answer more directly.
    """
    n_brackets = results["Bracket"].nunique()
    total_wins_by_team = count_wins_per_bracket(results).groupby("TeamID")["Wins"].sum()
    return total_wins_by_team.reindex(team_ids, fill_value=0) / n_brackets


def wins_over_seed_expectation(results: pd.DataFrame, seed_by_team: dict[int, int]) -> pd.DataFrame:
    """
    Inputs: simulation results and a TeamID -> seed number mapping (e.g.
            derived from bracket.simulate.build_seed_to_team, inverted).
    Outputs: one row per team with simulated average wins, the historical
             average for that seed line, and the difference -- positive
             means the model expects this team to outperform its seed.
    Purpose: generalizes the legacy "Wins Over Seed Expectation" analysis,
             which only worked for whatever teams happened to be hardcoded
             into that one run.
    """
    avg_wins = (
        average_wins_by_team(results, team_ids=list(seed_by_team.keys()))
        .rename("SimulatedAverageWins")
        .reset_index()
    )
    avg_wins["Seed"] = avg_wins["TeamID"].map(seed_by_team)
    avg_wins["HistoricalAverageWins"] = avg_wins["Seed"].map(HISTORICAL_AVERAGE_WINS_BY_SEED)
    avg_wins["WinsOverSeedExpectation"] = (
        avg_wins["SimulatedAverageWins"] - avg_wins["HistoricalAverageWins"]
    )
    return avg_wins


def round_advancement_counts(results: pd.DataFrame) -> pd.DataFrame:
    """
    Inputs: bracket.simulate.run_monte_carlo() output.
    Outputs: one row per TeamID, one column per round name, counting how
             many simulated brackets that team reached that round in.
             Play-in slots (round_of() returns None for them) are excluded
             -- winning a play-in game isn't "reaching a round."
    """
    games = results[results["Slot"].map(round_of).notna()].copy()
    games["Round"] = games["Slot"].map(round_name)

    counts = games.groupby(["TeamID", "Round"]).size().unstack(fill_value=0)
    return counts.reset_index()


def cinderella_probability(results: pd.DataFrame, seed_by_team: dict[int, int], min_seed: int, round_code: str) -> float:
    """
    Inputs: simulation results, a TeamID -> seed number mapping, a minimum
            seed number (e.g. 10 for "10-seed or worse"), and a round code
            ("R1".."R6", see bracket.structure.ROUND_NAMES).
    Outputs: the fraction of simulated brackets in which at least one team
             seeded `min_seed` or worse reached that round.
    Purpose: generalizes the legacy cinderella() function -- same question
             ("how often does a Cinderella team make a deep run"), computed
             from the actual seed mapping instead of a hand-edited column.
    """
    round_games = results[results["Slot"].map(round_of) == round_code].copy()
    round_games["Seed"] = round_games["TeamID"].map(seed_by_team)

    brackets_with_cinderella = round_games.groupby("Bracket")["Seed"].apply(lambda seeds: (seeds >= min_seed).any())
    return float(brackets_with_cinderella.mean())


def final_four_combination_counts(results: pd.DataFrame, round_code: str = "R4") -> pd.Series:
    """
    Inputs: simulation results and the round code marking arrival at that
            round (default "R4", the legacy project's Final Four).
    Outputs: value counts of each unique combination of teams that reached
             that round together, most common first.
    Purpose: which specific groups of teams end up together deep in the
             bracket most often -- ported directly from the legacy project,
             which already generalized cleanly (no hardcoded team names).
    """
    round_games = results[results["Slot"].map(round_of) == round_code]
    combos = round_games.groupby("Bracket")["TeamID"].apply(lambda teams: tuple(sorted(teams)))
    return combos.value_counts()
