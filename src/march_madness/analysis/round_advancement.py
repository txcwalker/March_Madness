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


def benefit_if_team_loses(
    results: pd.DataFrame,
    team_ids: list[int],
    team_to_region: dict[int, str],
    elimination_round_code: str = "R4",
    champion_slot: str = "R6CH",
) -> pd.DataFrame:
    """
    Inputs: simulation results, every team's TeamID, a TeamID -> region
            mapping (see analysis/region_strength.py's region_of_seed()),
            the round code marking "reaching the Final Four" (default "R4"
            -- a team that wins this round's game is the one that made
            it), and the champion slot code (default "R6CH").
    Outputs: one row per (TeamX, TeamY) pair with TeamY's baseline
             (unconditional, full-sample) championship AND Final Four
             odds, the same two odds conditioned on TeamX NOT reaching the
             Final Four, and a Benefit (conditioned minus baseline) for
             both. Championship odds are conditioned this way for every
             TeamY regardless of region; Final Four odds are conditioned
             this way only for TeamY in TeamX's own region (see below for
             why these two are treated differently).
    Purpose: "who benefits if team X loses" -- operationalized as "TeamX
             does not reach the Final Four" (a specific, meaningful,
             bracket-relevant loss) rather than any one single game, so it
             reuses the same 10,000-bracket Monte Carlo results every other
             analysis in this module does, with no new simulation needed.
             Final Four odds are included alongside championship odds
             because a team can gain a much clearer path to the Final Four
             (a near-term, high-probability shift) without that translating
             into as large a championship-odds move (a longer-shot,
             low-probability event) -- showing only one hides that
             distinction.

             The baseline is TeamY's real, ordinary odds (computed once
             from the full 10,000-bracket sample), not TeamY's odds
             conditioned on TeamX *reaching* the Final Four -- an earlier
             version used that conditioned value as the baseline, which
             was actively misleading for a big underdog TeamX: the
             "TeamX reaches the Final Four" subset is tiny (or, for a
             TeamX that never reaches it in any simulated bracket, exactly
             empty), so every TeamY's baseline collapsed to ~0% regardless
             of TeamY's real odds -- reading as "TeamY has basically no
             chance today," when the intended baseline is TeamY's normal,
             pretournament odds, the same number every other page on the
             site reports for that team.

             Final Four odds are region-scoped, Championship odds are not
             -- these are genuinely different mathematical situations, not
             an arbitrary choice:

             Final Four odds: a real audit (2026-07-30) found teams
             outside TeamX's own region showing small nonzero Final Four
             benefit (e.g. +0.6 points) that turned out to be pure Monte
             Carlo sampling noise from splitting 10,000 brackets into two
             subsets -- confirmed against the expected standard error for
             that split size, which matched the observed noise almost
             exactly. This isn't a rounding nit: each region resolves its
             own Final Four representative entirely independently of every
             other region (they don't share a single game or a single
             random draw until the national semifinals), so a
             different-region team's Final Four odds are mathematically
             guaranteed to be exactly unaffected by TeamX's fate -- any
             nonzero movement shown there is definitionally noise, not
             signal. For those pairs, the conditioned Final Four column is
             set equal to TeamY's baseline, forcing FinalFourBenefit to
             exactly 0.

             Championship odds: unlike Final Four odds, a different-region
             team's championship odds have a real, structural dependency
             on TeamX regardless of region (2026-07-31 correction -- an
             earlier version zeroed this out too, treating it as
             indistinguishable from noise, which the user correctly
             flagged as wrong for this specific metric). The championship
             game itself is cross-region: TeamY's odds of reaching the
             final are unaffected by TeamX (that's the Final Four
             independence above), but TeamY's odds of *winning* the final
             depend on who they'd face there -- and if TeamX (a strong
             team) is eliminated before the Final Four, whoever emerges
             from TeamX's side of the bracket instead is, on average, a
             weaker team, which is a real (if often small for a distant
             region) boost to every other team's championship odds, not
             sampling noise. So `ChampionShareIfXEliminated` is always
             computed from the real TeamX-eliminated bracket subset, for
             every TeamY -- never forced to match the baseline the way
             Final Four odds are for a different region.
    """
    champion_by_bracket = results.loc[results["Slot"] == champion_slot].set_index("Bracket")["TeamID"]
    final_four_teams_by_bracket = (
        results.loc[results["Slot"].map(round_of) == elimination_round_code].groupby("Bracket")["TeamID"].apply(set)
    )
    n_brackets = results["Bracket"].nunique()

    # Full-sample rates: every TeamY's baseline (see docstring), and also
    # the only correct value for a different-region pair's conditioned
    # column.
    overall_champion_share = champion_by_bracket.value_counts(normalize=True)
    overall_final_four_share = final_four_teams_by_bracket.explode().value_counts() / n_brackets

    rows = []
    for team_x in team_ids:
        reaches_final_four = final_four_teams_by_bracket.apply(lambda teams, tx=team_x: tx in teams)
        eliminated_brackets = reaches_final_four[~reaches_final_four].index
        n_eliminated = len(eliminated_brackets)

        champ_share_if_eliminated = champion_by_bracket.loc[
            champion_by_bracket.index.isin(eliminated_brackets)
        ].value_counts(normalize=True)
        # How often each OTHER team reaches the Final Four within the
        # eliminated-TeamX bracket subset -- explode() turns each
        # bracket's set of Final Four teams into one row per team, so
        # value_counts() over the subset directly gives "how many of these
        # brackets did TeamY reach the Final Four in."
        final_four_counts_if_eliminated = (
            final_four_teams_by_bracket.loc[eliminated_brackets].explode().value_counts()
        )

        for team_y in team_ids:
            if team_y == team_x:
                continue

            champ_baseline = float(overall_champion_share.get(team_y, 0.0))
            ff_baseline = float(overall_final_four_share.get(team_y, 0.0))

            # Championship odds: always the real TeamX-eliminated subset,
            # same-region or not -- see docstring for why this one isn't
            # region-scoped.
            champ_if_eliminated = float(champ_share_if_eliminated.get(team_y, 0.0))

            if team_to_region.get(team_y) == team_to_region.get(team_x):
                ff_if_eliminated = (
                    float(final_four_counts_if_eliminated.get(team_y, 0)) / n_eliminated if n_eliminated else 0.0
                )
            else:
                # Final Four odds ARE mathematically exactly independent of
                # a different-region TeamX -- any movement in the real
                # subset here would be pure sampling noise (see docstring).
                ff_if_eliminated = ff_baseline

            rows.append(
                {
                    "TeamX": team_x,
                    "TeamY": team_y,
                    "ChampionShareBaseline": champ_baseline,
                    "ChampionShareIfXEliminated": champ_if_eliminated,
                    "ChampionBenefit": champ_if_eliminated - champ_baseline,
                    "FinalFourShareBaseline": ff_baseline,
                    "FinalFourShareIfXEliminated": ff_if_eliminated,
                    "FinalFourBenefit": ff_if_eliminated - ff_baseline,
                }
            )

    return pd.DataFrame(rows)
