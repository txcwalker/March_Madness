import pandas as pd
import pytest

from march_madness.analysis.bracket_path import (
    average_win_probability,
    build_feeds_into,
    path_of_least_resistance,
    resolve_slot_winners_by_bracket,
)

# A 6-team bracket chain where team 11's second hop opponent branch ("R1B")
# is itself a 2-team subtree {13, 14} -- deliberately deep enough that "who
# actually shows up here across many simulated brackets" can vary
# bracket-to-bracket, which a single-slot fixture couldn't exercise.
SLOTS = pd.DataFrame(
    {
        "Slot": ["R1", "R1B", "R2", "R3", "R4"],
        "StrongSeed": ["seed1", "seed3", "R1", "R2", "R3"],
        "WeakSeed": ["seed2", "seed4", "R1B", "seed5", "seed6"],
    }
)
SEED_TO_TEAM = {"seed1": 11, "seed2": 12, "seed3": 13, "seed4": 14, "seed5": 15, "seed6": 16}

# Symmetric win probabilities, strongest (11) to weakest (16):
# P(a beats b) + P(b beats a) == 1 always, matching what
# bracket.simulate.compute_win_probabilities() guarantees post-symmetrization.
_STRENGTH_ORDER = [11, 12, 13, 14, 15, 16]
WIN_PROBABILITIES = {
    a: {b: 0.5 + 0.08 * (_STRENGTH_ORDER.index(b) - _STRENGTH_ORDER.index(a)) for b in _STRENGTH_ORDER if b != a}
    for a in _STRENGTH_ORDER
}

# Three simulated brackets. Team 11's Round-of-64 opponent (seed2 -> 12) and
# Elite-Eight/Final-Four opponents (seed5 -> 15, seed6 -> 16) are raw seed
# codes, fixed regardless of the bracket; only the Sweet-16 hop (whoever
# wins the R1B branch) is bracket-dependent -- 13 wins it twice, 14 once --
# which is exactly what this fixture is built to exercise: the new
# "average over what actually happens" behavior versus the old "always pick
# the single toughest possible team" behavior.
RESULTS = pd.DataFrame(
    [
        {"Bracket": 1, "Slot": "R1", "TeamID": 11},
        {"Bracket": 1, "Slot": "R1B", "TeamID": 13},
        {"Bracket": 1, "Slot": "R2", "TeamID": 11},
        {"Bracket": 1, "Slot": "R3", "TeamID": 11},
        {"Bracket": 1, "Slot": "R4", "TeamID": 11},
        {"Bracket": 2, "Slot": "R1", "TeamID": 11},
        {"Bracket": 2, "Slot": "R1B", "TeamID": 13},
        {"Bracket": 2, "Slot": "R2", "TeamID": 11},
        {"Bracket": 2, "Slot": "R3", "TeamID": 11},
        {"Bracket": 2, "Slot": "R4", "TeamID": 11},
        {"Bracket": 3, "Slot": "R1", "TeamID": 12},
        {"Bracket": 3, "Slot": "R1B", "TeamID": 14},
        {"Bracket": 3, "Slot": "R2", "TeamID": 12},
        {"Bracket": 3, "Slot": "R3", "TeamID": 12},
        {"Bracket": 3, "Slot": "R4", "TeamID": 12},
    ]
)


def test_build_feeds_into_maps_both_sides_of_every_slot():
    feeds_into = build_feeds_into(SLOTS)

    assert feeds_into["seed1"] == ("R1", "seed2")
    assert feeds_into["R1"] == ("R2", "R1B")
    assert feeds_into["R2"] == ("R3", "seed5")


def test_average_win_probability_ranks_teams_by_overall_strength():
    strength = average_win_probability(WIN_PROBABILITIES)

    # Team 11 is the strongest (beats everyone more often than not, on average);
    # team 16 is the weakest. Strength should be strictly decreasing in that order.
    ordered_strengths = [strength[t] for t in _STRENGTH_ORDER]
    assert ordered_strengths == sorted(ordered_strengths, reverse=True)


def test_resolve_slot_winners_by_bracket_groups_by_bracket_number():
    winners = resolve_slot_winners_by_bracket(RESULTS)

    assert winners[1] == {"R1": 11, "R1B": 13, "R2": 11, "R3": 11, "R4": 11}
    assert winners[3] == {"R1": 12, "R1B": 14, "R2": 12, "R3": 12, "R4": 12}


def test_path_of_least_resistance_averages_the_bracket_dependent_opponent():
    result = path_of_least_resistance(SLOTS, SEED_TO_TEAM, WIN_PROBABILITIES, RESULTS).set_index("TeamID")
    strength = average_win_probability(WIN_PROBABILITIES)
    row = result.loc[11]

    # Round of 32 and Elite Eight/Final Four opponents are raw seed codes --
    # fixed no matter what the rest of the bracket does.
    assert row["RoundOf32Strength"] == pytest.approx(strength[12])
    assert row["EliteEightStrength"] == pytest.approx(strength[15])
    assert row["FinalFourStrength"] == pytest.approx(strength[16])

    # Sweet 16 opponent is whoever actually won the R1B branch in each
    # simulated bracket: 13 twice, 14 once. PathStrengthFaced averages that
    # -- it does not pick a single worst- or best-case team the way the old
    # subtree-max implementation did.
    expected_sweet_sixteen_strength = (2 * strength[13] + strength[14]) / 3
    assert row["SweetSixteenStrength"] == pytest.approx(expected_sweet_sixteen_strength)

    expected_path_strength_faced = (
        strength[12] + expected_sweet_sixteen_strength + strength[15] + strength[16]
    ) / 4
    assert row["PathStrengthFaced"] == pytest.approx(expected_path_strength_faced)

    # PathEase averages, across brackets, team 11's own win probability
    # against the opponents it actually drew in that specific bracket (not
    # the opponents' strength scores, and not a single hypothetical path).
    def bracket_ease(sweet_sixteen_opponent: int) -> float:
        return (
            WIN_PROBABILITIES[11][12]
            * WIN_PROBABILITIES[11][sweet_sixteen_opponent]
            * WIN_PROBABILITIES[11][15]
            * WIN_PROBABILITIES[11][16]
        )

    expected_path_ease = (bracket_ease(13) + bracket_ease(13) + bracket_ease(14)) / 3
    assert row["PathEase"] == pytest.approx(expected_path_ease)


def test_path_of_least_resistance_does_not_let_a_strong_team_s_own_quality_lower_its_strength_faced():
    # Teams 11 and 12 face an identical set of possible opponents in this
    # fixture (only who's on the *other* side of the bracket differs
    # between them, not their own strength) -- so PathStrengthFaced, which
    # never looks at a team's own win probability, should treat their
    # otherwise-comparable draws consistently rather than rewarding team 11
    # simply for being the stronger team the way raw PathEase would.
    result = path_of_least_resistance(SLOTS, SEED_TO_TEAM, WIN_PROBABILITIES, RESULTS).set_index("TeamID")
    strength = average_win_probability(WIN_PROBABILITIES)

    # Team 11's Round of 32 opponent is 12; team 12's is 11 -- their
    # PathStrengthFaced Round-of-32 columns reflect the *opponent's*
    # strength, so they differ (as they should, since the opponents
    # differ), unlike PathEase which would also be pulled apart by whose
    # own win probability is being multiplied.
    assert result.loc[11, "RoundOf32Strength"] == pytest.approx(strength[12])
    assert result.loc[12, "RoundOf32Strength"] == pytest.approx(strength[11])


def test_path_of_least_resistance_sorts_easiest_draw_first():
    result = path_of_least_resistance(SLOTS, SEED_TO_TEAM, WIN_PROBABILITIES, RESULTS)

    assert list(result["PathStrengthFaced"]) == sorted(result["PathStrengthFaced"])
