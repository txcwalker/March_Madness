"""
Path of Least Resistance: how tough is each team's actual draw on the way
to the Final Four, and is the team still favored despite it. Walks each
team's own chalk-advancement chain (assuming it keeps winning) across every
one of the already-run Monte Carlo bracket simulations (bracket.simulate.
run_monte_carlo()'s long-format results), and at each of the four rounds
looks up whichever team *actually* emerged from the opposing bracket branch
in that specific simulation -- not a single best- or worst-case guess, and
weighted implicitly by how often each possible opponent really shows up.

Two scores come out of that walk:

PathStrengthFaced averages the opponents' own field-wide strength scores
(average_win_probability()), never the team's own -- so a 1-seed's already
-high win probability against almost everyone can't mechanically make its
draw look "easy." It answers "how good, on paper, are the teams standing in
the way," on the same scale regardless of seed: a team that has to get past
several genuinely strong opponents scores high here no matter how strong it
is itself.

PathEase is the complementary, team-relative number: for each simulated
bracket, the team's own win probability against that bracket's real
round-by-round opponents is multiplied across the four rounds (these are
sequential elimination games that compound, not independent draws), then
that per-bracket product is averaged across every simulated bracket --
"given the draws that actually happen, how likely is this team to survive
to the Final Four."
"""

from __future__ import annotations

import pandas as pd

# Rounds a team must win, in order, to reach the Final Four.
PATH_ROUNDS = ("R1", "R2", "R3", "R4")

ROUND_STRENGTH_COLUMNS = {
    "R1": "RoundOf32Strength",
    "R2": "SweetSixteenStrength",
    "R3": "EliteEightStrength",
    "R4": "FinalFourStrength",
}


def build_feeds_into(slots: pd.DataFrame) -> dict[str, tuple[str, str]]:
    """
    Inputs: one season's slots (Slot, StrongSeed, WeakSeed).
    Outputs: {input_code: (resulting_slot, opponent_code)} for every seed
             code or slot code that feeds into a later slot as either side.
    Purpose: lets path_of_least_resistance() walk forward from a team's own
             seed code through the bracket tree without re-deriving it from
             the slots table on every call.
    """
    feeds_into: dict[str, tuple[str, str]] = {}
    for row in slots.itertuples():
        feeds_into[row.StrongSeed] = (row.Slot, row.WeakSeed)
        feeds_into[row.WeakSeed] = (row.Slot, row.StrongSeed)
    return feeds_into


def average_win_probability(win_probabilities: dict[int, dict[int, float]]) -> dict[int, float]:
    """
    Inputs: the (symmetrized) win-probability matrix from
            bracket.simulate.compute_win_probabilities().
    Outputs: {TeamID: that team's average win probability against the rest
             of the full field} -- a simple, self-contained strength score
             that needs no external rating data. Used both to build
             PathStrengthFaced (an opponent's own strength, independent of
             whoever they end up facing) and, historically, to pick a
             worst-case opponent -- see this module's docstring.
    """
    return {team: sum(opponents.values()) / len(opponents) for team, opponents in win_probabilities.items()}


def resolve_slot_winners_by_bracket(results: pd.DataFrame) -> dict[int, dict[str, int]]:
    """
    Inputs: long-format Monte Carlo results (Bracket, Slot, TeamID) from
            bracket.simulate.run_monte_carlo().
    Outputs: {bracket_num: {slot: winning_team_id}} -- one resolved-winners
             lookup per simulated bracket, in the same shape
             bracket.simulate.simulate_bracket() returns for a single run.
    Purpose: lets path_of_least_resistance() ask "who actually won this
             slot" in each already-run simulation, instead of falling back
             to a single hypothetical (best- or worst-case) opponent.
    """
    return {bracket_num: dict(zip(group["Slot"], group["TeamID"])) for bracket_num, group in results.groupby("Bracket")}


def path_of_least_resistance(
    slots: pd.DataFrame,
    seed_to_team: dict[str, int],
    win_probabilities: dict[int, dict[int, float]],
    results: pd.DataFrame,
) -> pd.DataFrame:
    """
    Inputs: one season's slots, its Seed -> TeamID mapping, the
            (symmetrized) win-probability matrix from
            bracket.simulate.compute_win_probabilities(), and the raw
            long-format Monte Carlo results from
            bracket.simulate.run_monte_carlo() (the same simulated brackets
            already used for every other Monte-Carlo-based analysis).
    Outputs: one row per team -- TeamID, its average opponent strength
             faced at each of the four rounds before the Final Four
             (RoundOf32Strength .. FinalFourStrength), PathStrengthFaced
             (the average of those four -- the headline "how tough is the
             draw" number, see module docstring), and PathEase (the team's
             own average survival probability against the opponents it
             actually drew, see module docstring). Sorted by
             PathStrengthFaced ascending -- weakest opponents faced, i.e.
             the actual "path of least resistance," first.
    """
    feeds_into = build_feeds_into(slots)
    strength = average_win_probability(win_probabilities)
    brackets = resolve_slot_winners_by_bracket(results)

    rows = []
    for seed, team_id in seed_to_team.items():
        round_strengths: dict[str, list[float]] = {rnd: [] for rnd in PATH_ROUNDS}
        path_ease_samples: list[float] = []

        for bracket_winners in brackets.values():
            current = seed
            bracket_ease = 1.0
            hops = 0
            for rnd in PATH_ROUNDS:
                if current not in feeds_into:
                    break
                next_slot, opponent_code = feeds_into[current]
                opponent_team = (
                    seed_to_team[opponent_code] if opponent_code in seed_to_team else bracket_winners[opponent_code]
                )
                round_strengths[rnd].append(strength[opponent_team])
                bracket_ease *= win_probabilities[team_id][opponent_team]
                current = next_slot
                hops += 1
            if hops == len(PATH_ROUNDS):
                path_ease_samples.append(bracket_ease)

        row: dict[str, float | int | None] = {"TeamID": team_id}
        all_strengths: list[float] = []
        for rnd in PATH_ROUNDS:
            values = round_strengths[rnd]
            row[ROUND_STRENGTH_COLUMNS[rnd]] = sum(values) / len(values) if values else None
            all_strengths.extend(values)
        row["PathStrengthFaced"] = sum(all_strengths) / len(all_strengths) if all_strengths else None
        row["PathEase"] = sum(path_ease_samples) / len(path_ease_samples) if path_ease_samples else None
        rows.append(row)

    return pd.DataFrame(rows).sort_values("PathStrengthFaced", ascending=True).reset_index(drop=True)
