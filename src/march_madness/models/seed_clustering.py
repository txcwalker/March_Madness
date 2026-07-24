"""
Unsupervised team-tier clustering via KMeans on KenPom stats. Complements
seed_knn.py: doesn't need a labeled tournament seed, so it can tier every
team KenPom covers, not just the ~68 that made the tournament -- useful
while seed_knn is data-starved (see AGENTS.md Fragile Areas).

Ported from the legacy seed_clustering.py, minus its own KenPom-cleaning
logic: that duplicated (and was less correct than) ingest/kenpom.py, so
this now takes already-cleaned KenPom data as input instead.
"""

from __future__ import annotations

import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

CLUSTER_FEATURE_COLUMNS = ["NetRtg", "ORtg", "DRtg", "AdjT", "Luck", "W", "L"]


def cluster_teams(kenpom: pd.DataFrame, n_clusters: int = 5, random_state: int = 42) -> pd.DataFrame:
    """
    Inputs: cleaned KenPom data (from ingest.kenpom) with at least
            CLUSTER_FEATURE_COLUMNS present.
    Outputs: the input plus two new columns -- Cluster (raw KMeans label)
             and Tier (0 = best, ranked by each cluster's mean NetRtg).
    Purpose: groups teams into quality tiers from their stats alone, with
             no tournament-seed label required.
    """
    features = kenpom[CLUSTER_FEATURE_COLUMNS]
    scaled = StandardScaler().fit_transform(features)

    kmeans = KMeans(n_clusters=n_clusters, random_state=random_state, n_init="auto")
    result = kenpom.copy()
    result["Cluster"] = kmeans.fit_predict(scaled)

    cluster_means = result.groupby("Cluster")["NetRtg"].mean().sort_values(ascending=False)
    tier_mapping = {cluster: rank for rank, cluster in enumerate(cluster_means.index)}
    result["Tier"] = result["Cluster"].map(tier_mapping)

    return result
