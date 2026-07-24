"""
Monte Carlo bracket simulation, ported and cleaned from the legacy
sims_mens.py. Requires slots already ordered via
bracket.structure.order_slots_for_simulation() -- see that module's
docstring for why raw Kaggle file order is not resolution order.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from march_madness.features.build_features import generate_matchup_pairs
from march_madness.models.common import build_prediction_matrix


def build_seed_to_team(seeds: pd.DataFrame, season: int) -> dict[str, int]:
    """
    Inputs: Kaggle's seeds table (Season, Seed, TeamID) for all seasons.
    Outputs: {Seed: TeamID} for one season, e.g. {"W01": 1181, "X16a": 1224, ...}.
    Purpose: seed codes (including play-in participants' "a"/"b" suffixed
             codes) are the starting points a bracket simulation resolves
             from -- see simulate_bracket.
    """
    season_seeds = seeds[seeds["Season"] == season]
    return dict(zip(season_seeds["Seed"], season_seeds["TeamID"]))


def compute_win_probabilities(
    model, team_stats: pd.DataFrame, team_ids: list[int]
) -> dict[int, dict[int, float]]:
    """
    Inputs: a fitted win-probability classifier, per-team stats indexed by
            TeamID, and every TeamID that could appear in the bracket.
    Outputs: probs[team1][team2] = P(team1 beats team2), for every ordered
             pair of distinct teams.
    Purpose: precomputes every matchup once, up front -- this is what makes
             running thousands of bracket simulations fast, rather than
             calling the model mid-simulation for every single game of
             every bracket.
    """
    pairs = generate_matchup_pairs(team_ids)
    X = build_prediction_matrix(team_stats, pairs)
    win_prob_team1 = model.predict_proba(X)[:, 1]

    probs: dict[int, dict[int, float]] = {}
    for (team1, team2), p in zip(pairs, win_prob_team1):
        probs.setdefault(team1, {})[team2] = float(p)
    return probs


def simulate_bracket(
    ordered_slots: pd.DataFrame,
    seed_to_team: dict[str, int],
    win_probabilities: dict[int, dict[int, float]],
    rng: np.random.Generator,
    deterministic: bool = False,
) -> dict[str, int]:
    """
    Inputs: slots already ordered via bracket.structure.order_slots_for_simulation
            (play-in first, then R1..R6); a Seed -> TeamID mapping for one
            season; win probabilities from compute_win_probabilities; an rng.
    Outputs: {slot: winning_team_id} for every slot in the bracket,
             including the play-in slots.
    Purpose: plays out one full bracket. `winners` starts as a copy of the
             seed->team mapping and grows one entry per slot as each game
             resolves -- a later round's StrongSeed/WeakSeed can reference
             either a raw seed code or an earlier slot's winner, and this
             dict serves both lookups in the same namespace (they never
             collide: raw seed codes and game slot codes use different
             formats). `deterministic=True` always takes the model's
             favorite instead of sampling -- useful for a single "expected"
             bracket rather than a Monte Carlo run.
    """
    winners: dict[str, int] = dict(seed_to_team)

    for slot, strong_seed, weak_seed in zip(
        ordered_slots["Slot"], ordered_slots["StrongSeed"], ordered_slots["WeakSeed"]
    ):
        team1, team2 = winners[strong_seed], winners[weak_seed]
        win_prob_team1 = win_probabilities[team1][team2]

        if deterministic:
            winner = team1 if win_prob_team1 >= 0.5 else team2
        else:
            winner = team1 if rng.random() < win_prob_team1 else team2

        winners[slot] = winner

    return winners


def run_monte_carlo(
    ordered_slots: pd.DataFrame,
    seed_to_team: dict[str, int],
    win_probabilities: dict[int, dict[int, float]],
    n_brackets: int,
    random_state: int | None = None,
) -> pd.DataFrame:
    """
    Inputs: same as simulate_bracket, plus how many brackets to simulate.
    Outputs: one row per (Bracket, Slot) with the winning TeamID -- long
             format, ready for round-advancement aggregation (see
             analysis/, not built yet).
    Purpose: the Monte Carlo loop -- runs simulate_bracket() n_brackets
             times with independent randomness from one seeded generator.
    """
    rng = np.random.default_rng(random_state)
    records = []

    for bracket_num in range(1, n_brackets + 1):
        winners = simulate_bracket(ordered_slots, seed_to_team, win_probabilities, rng)
        for slot in ordered_slots["Slot"]:
            records.append({"Bracket": bracket_num, "Slot": slot, "TeamID": winners[slot]})

    return pd.DataFrame(records)
