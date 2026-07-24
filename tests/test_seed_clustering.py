import numpy as np
import pandas as pd

from march_madness.models.seed_clustering import cluster_teams


def make_two_tier_kenpom(n_per_tier: int = 15, seed: int = 0) -> pd.DataFrame:
    """
    Two clearly separated groups of teams. Every feature that should
    realistically differ between a strong and a weak team does (NetRtg,
    ORtg, DRtg, W, L) -- AdjT/Luck stay neutral since tempo/luck don't
    inherently correlate with quality. Varying only one of seven features
    (as an earlier version of this fixture did) lets the other six
    contribute pure noise that can swamp the real signal in KMeans.
    """
    rng = np.random.default_rng(seed)

    def make_group(is_strong: bool, label: str) -> pd.DataFrame:
        sign = 1 if is_strong else -1
        return pd.DataFrame(
            {
                "Team": [f"{label}{i}" for i in range(n_per_tier)],
                "NetRtg": rng.normal(sign * 20, 1.5, n_per_tier),
                "ORtg": rng.normal(115 if is_strong else 95, 2, n_per_tier),
                "DRtg": rng.normal(90 if is_strong else 105, 2, n_per_tier),
                "AdjT": rng.normal(68, 2, n_per_tier),
                "Luck": rng.normal(0, 0.02, n_per_tier),
                "W": rng.integers(24, 32, n_per_tier) if is_strong else rng.integers(5, 15, n_per_tier),
                "L": rng.integers(2, 8, n_per_tier) if is_strong else rng.integers(15, 25, n_per_tier),
            }
        )

    strong = make_group(True, "Strong")
    weak = make_group(False, "Weak")
    return pd.concat([strong, weak], ignore_index=True)


def test_cluster_teams_adds_cluster_and_tier_columns():
    kenpom = make_two_tier_kenpom()

    result = cluster_teams(kenpom, n_clusters=2)

    assert "Cluster" in result.columns
    assert "Tier" in result.columns
    assert len(result) == len(kenpom)


def test_tier_zero_is_the_stronger_group_by_net_rtg():
    kenpom = make_two_tier_kenpom()

    result = cluster_teams(kenpom, n_clusters=2)

    tier_0_teams = result[result["Tier"] == 0]["Team"]
    tier_1_teams = result[result["Tier"] == 1]["Team"]
    assert all(team.startswith("Strong") for team in tier_0_teams)
    assert all(team.startswith("Weak") for team in tier_1_teams)


def test_cluster_means_are_ordered_descending_by_tier():
    kenpom = make_two_tier_kenpom()

    result = cluster_teams(kenpom, n_clusters=2)

    tier_means = result.groupby("Tier")["NetRtg"].mean()
    assert tier_means.is_monotonic_decreasing
