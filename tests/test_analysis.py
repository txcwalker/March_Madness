import pandas as pd
import pytest

from march_madness.analysis.region_strength import (
    region_championship_counts,
    region_of_seed,
    region_top_seed_championship_share,
    region_top_seed_final_four_share,
)
from march_madness.analysis.round_advancement import (
    average_wins_by_team,
    benefit_if_team_loses,
    cinderella_probability,
    count_wins_per_bracket,
    final_four_combination_counts,
    round_advancement_counts,
    wins_over_seed_expectation,
)


def make_synthetic_results() -> pd.DataFrame:
    """
    Two simulated brackets over a tiny 4-region field (W/X/Y/Z, one game
    per region reaching R4, then R5/R6). Bracket 1: team 101 (W, seed 1)
    wins it all. Bracket 2: team 102 (W, seed 8) upsets its way to the
    Elite Eight (R3) then loses -- never reaches R4.
    """
    rows = [
        # Bracket 1: 101 (W01) wins every round through the championship
        {"Bracket": 1, "Slot": "R1W1", "TeamID": 101},
        {"Bracket": 1, "Slot": "R2W1", "TeamID": 101},
        {"Bracket": 1, "Slot": "R3W1", "TeamID": 101},
        {"Bracket": 1, "Slot": "R1X1", "TeamID": 201},
        {"Bracket": 1, "Slot": "R2X1", "TeamID": 201},
        {"Bracket": 1, "Slot": "R3X1", "TeamID": 201},
        {"Bracket": 1, "Slot": "R4W1", "TeamID": 101},
        {"Bracket": 1, "Slot": "R4X1", "TeamID": 201},
        {"Bracket": 1, "Slot": "R5WX", "TeamID": 101},
        {"Bracket": 1, "Slot": "R1Y1", "TeamID": 301},
        {"Bracket": 1, "Slot": "R1Z1", "TeamID": 401},
        {"Bracket": 1, "Slot": "R4Y1", "TeamID": 301},
        {"Bracket": 1, "Slot": "R4Z1", "TeamID": 401},
        {"Bracket": 1, "Slot": "R5YZ", "TeamID": 301},
        {"Bracket": 1, "Slot": "R6CH", "TeamID": 101},
        # Bracket 2: 102 (W08, a big underdog) reaches R3 then loses
        {"Bracket": 2, "Slot": "R1W1", "TeamID": 102},
        {"Bracket": 2, "Slot": "R2W1", "TeamID": 102},
        {"Bracket": 2, "Slot": "R3W1", "TeamID": 102},
        {"Bracket": 2, "Slot": "R1X1", "TeamID": 202},
        {"Bracket": 2, "Slot": "R2X1", "TeamID": 202},
        {"Bracket": 2, "Slot": "R3X1", "TeamID": 202},
        {"Bracket": 2, "Slot": "R4X1", "TeamID": 202},
        {"Bracket": 2, "Slot": "R1Y1", "TeamID": 302},
        {"Bracket": 2, "Slot": "R1Z1", "TeamID": 402},
        {"Bracket": 2, "Slot": "R4Y1", "TeamID": 302},
        {"Bracket": 2, "Slot": "R5YZ", "TeamID": 302},
        {"Bracket": 2, "Slot": "R5WX", "TeamID": 202},
        {"Bracket": 2, "Slot": "R6CH", "TeamID": 202},
    ]
    return pd.DataFrame(rows)


SEED_TO_TEAM = {
    "W01": 101, "W08": 102, "X01": 201, "X08": 202,
    "Y01": 301, "Y08": 302, "Z01": 401, "Z08": 402,
}
SEED_BY_TEAM = {team_id: int(seed[1:3]) for seed, team_id in SEED_TO_TEAM.items()}


def test_region_of_seed_is_the_first_character():
    assert region_of_seed("W01") == "W"
    assert region_of_seed("X16a") == "X"


def test_count_wins_per_bracket():
    results = make_synthetic_results()
    wins = count_wins_per_bracket(results)

    team_101_bracket_1 = wins[(wins["Bracket"] == 1) & (wins["TeamID"] == 101)]["Wins"].iloc[0]
    assert team_101_bracket_1 == 6  # R1, R2, R3, R4, R5, R6 -- one win per slot 101 appears as the victor in


def test_average_wins_by_team_counts_zero_win_brackets_in_the_denominator():
    results = make_synthetic_results()
    avg = average_wins_by_team(results, team_ids=list(SEED_BY_TEAM.keys()))

    # 102 won 3 games in bracket 2 but 0 in bracket 1 (never appears there at
    # all) -- the average must be 3/2 = 1.5, not 3/1 from only counting the
    # bracket it appeared in.
    assert avg[102] == 1.5
    assert avg[101] == 3.0  # 101 won 6 games in bracket 1, 0 in bracket 2 -> 6/2 = 3.0


def test_round_advancement_counts_reflects_actual_depth():
    results = make_synthetic_results()
    counts = round_advancement_counts(results).set_index("TeamID")

    assert counts.loc[101, "Champion"] == 1
    assert counts.loc[101, "Final Four"] == 1
    assert counts.loc[102, "Elite Eight"] == 1
    assert "Final Four" not in counts.columns or counts.loc[102, "Final Four"] == 0


def test_wins_over_seed_expectation_flags_the_underdog_as_overperforming():
    results = make_synthetic_results()
    table = wins_over_seed_expectation(results, SEED_BY_TEAM).set_index("TeamID")

    # 102 is a fictional seed 8: 3 wins in bracket 2, 0 in bracket 1 -> average 1.5,
    # still well above a real seed-8's historical average of 0.71 wins.
    assert table.loc[102, "WinsOverSeedExpectation"] > 0
    assert table.loc[102, "SimulatedAverageWins"] == 1.5


def test_cinderella_probability_counts_brackets_not_games():
    results = make_synthetic_results()

    # seed 8 (102) reaches R3 (Elite Eight) in bracket 2 but not bracket 1 -> 1 of 2 brackets = 0.5
    prob = cinderella_probability(results, SEED_BY_TEAM, min_seed=8, round_code="R3")
    assert prob == 0.5

    # in bracket 2, team 202 (seed 8) actually wins the whole thing -> 1 of 2 brackets = 0.5
    prob_champion = cinderella_probability(results, SEED_BY_TEAM, min_seed=8, round_code="R6")
    assert prob_champion == 0.5

    # but no seed >= 9 ever reaches the championship
    assert cinderella_probability(results, SEED_BY_TEAM, min_seed=9, round_code="R6") == 0.0


def test_final_four_combination_counts():
    results = make_synthetic_results()
    combos = final_four_combination_counts(results, round_code="R4")

    assert combos[tuple(sorted([101, 201, 301, 401]))] == 1
    assert combos[tuple(sorted([202, 302]))] == 1  # bracket 2 only had 2 teams reach R4 in this synthetic fixture


def test_benefit_if_team_loses_flags_who_gains_when_a_team_is_eliminated():
    results = make_synthetic_results()
    team_ids = [101, 102, 201, 202, 301, 302, 401, 402]
    team_to_region = {tid: region_of_seed(seed) for seed, tid in SEED_TO_TEAM.items()}

    benefit = benefit_if_team_loses(results, team_ids, team_to_region).set_index(["TeamX", "TeamY"])

    # 201 (region X) reaches the Final Four (R4) only in bracket 1; its own
    # regional rival 202 (also region X) reaches it instead in bracket 2,
    # winning outright. 202's baseline is its unconditional rate across
    # both brackets (reaches R4 in 1 of 2 -> 0.5, wins the championship in
    # 1 of 2 -> 0.5); conditioned on 201 being eliminated (bracket 2 only),
    # 202 reaches R4 and wins it every time in that subset -> 1.0. Same
    # region -> a real structural effect: only one region-X team can reach
    # the Final Four per bracket, so 201 missing it directly means more
    # room for 202.
    same_region_row = benefit.loc[(201, 202)]
    assert same_region_row["ChampionShareBaseline"] == 0.5
    assert same_region_row["ChampionShareIfXEliminated"] == 1.0
    assert same_region_row["ChampionBenefit"] == 0.5
    assert same_region_row["FinalFourShareBaseline"] == 0.5
    assert same_region_row["FinalFourShareIfXEliminated"] == 1.0
    assert same_region_row["FinalFourBenefit"] == 0.5

    # 101 (region W) and 202 (region X) are in DIFFERENT regions.
    # Final Four odds: each region resolves its own Final Four
    # representative independently, so 202's conditioned Final Four column
    # must equal its own baseline (unconditional rate), with exactly zero
    # FinalFourBenefit, regardless of what 101 does. (Naively conditioning
    # here would show a nonzero "effect" driven entirely by this fixture's
    # tiny 2-bracket sample -- exactly the kind of sampling-noise artifact
    # this region check exists to prevent; see the function's docstring.)
    # Championship odds: NOT region-scoped -- 101 being eliminated (bracket
    # 2, where 202 wins the whole thing) is a real conditioned effect on
    # 202's championship odds even though the two teams are in different
    # regions, so ChampionShareIfXEliminated uses the real subset value
    # (1.0, same as the same-region row above) rather than being forced to
    # match the baseline.
    cross_region_row = benefit.loc[(101, 202)]
    assert cross_region_row["ChampionShareBaseline"] == 0.5
    assert cross_region_row["ChampionShareIfXEliminated"] == 1.0
    assert cross_region_row["ChampionBenefit"] == 0.5
    assert cross_region_row["FinalFourBenefit"] == 0.0
    assert cross_region_row["FinalFourShareBaseline"] == cross_region_row["FinalFourShareIfXEliminated"] == 0.5

    # No row for a team against itself.
    assert (101, 101) not in benefit.index


def test_region_championship_counts():
    results = make_synthetic_results()
    counts = region_championship_counts(results, SEED_TO_TEAM)

    assert counts["W"] == 1  # 101 (W) won bracket 1
    assert counts["X"] == 1  # 202 (X) won bracket 2


def test_region_top_seed_championship_share():
    results = make_synthetic_results()
    shares = region_top_seed_championship_share(results, SEED_TO_TEAM)

    assert shares["W"] == 1.0  # W's only championship was won by its #1 seed (101)
    assert shares["X"] == 0.0  # X's championship was won by its #8 seed (202), not its #1 seed (201)


def test_region_top_seed_final_four_share_uses_all_brackets_as_the_denominator():
    results = make_synthetic_results()
    shares = region_top_seed_final_four_share(results, SEED_TO_TEAM)

    # Every region's #1 seed reaches R4 in bracket 1 only (not bracket 2, where
    # either an upset seed represents the region instead, or the region's team
    # lost before R4 at all) -> 1 of 2 brackets for every region, unlike
    # region_top_seed_championship_share which only looks at brackets a
    # region actually won outright.
    assert shares["W"] == 0.5
    assert shares["X"] == 0.5
    assert shares["Y"] == 0.5
    assert shares["Z"] == 0.5
