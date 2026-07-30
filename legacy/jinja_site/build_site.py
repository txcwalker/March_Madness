"""
Builds the static public site: articles (from content/articles/*.md) plus
analytics pages (from data/outputs/<year>/, written by scripts/run_pipeline.py).

Reads only already-computed pipeline output -- never re-ingests raw Kaggle/
KenPom data -- so this stays fast and independent of run_pipeline.py's runtime.
Writes to docs/, which GitHub Pages serves directly from the main branch.

Usage:
    python scripts/build_site.py
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import yaml
from jinja2 import Environment, FileSystemLoader
from markdown import markdown as render_markdown

from march_madness.analysis import region_strength, round_advancement
from march_madness.bracket.structure import ROUND_NAMES
from march_madness.config import load_season_config

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTENT_DIR = REPO_ROOT / "content" / "articles"
TEMPLATES_DIR = REPO_ROOT / "site" / "templates"
STATIC_DIR = REPO_ROOT / "site" / "static"
OUTPUT_DIR = REPO_ROOT / "docs"

SITE_NAME = "March Madness Analytics"
TAGLINE = "Tournament predictions, simulation results, and the writing behind them."

CINDERELLA_SEED_THRESHOLDS = [9, 10, 11, 12, 13, 14, 15, 16]
CINDERELLA_ROUNDS = ["R2", "R3", "R4", "R5", "R6"]

# Palette: validated default instance (see dataviz skill references/palette.md).
SERIES_1 = "#2a78d6"
REGION_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]  # categorical slots 1-4
DIVERGING_POS = "#2a78d6"
DIVERGING_NEG = "#e34948"
SEQ_BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
MUTED = "#898781"


def _split_frontmatter(text: str) -> tuple[dict, str]:
    """Splits a '---\\nyaml\\n---\\nbody' file into (frontmatter dict, body). No frontmatter -> ({}, text)."""
    if not text.startswith("---"):
        return {}, text
    _, frontmatter_raw, body = text.split("---", 2)
    return yaml.safe_load(frontmatter_raw) or {}, body.lstrip("\n")


def load_articles() -> list[dict]:
    """Parses every content/articles/*.md file into a dict with rendered HTML, newest first."""
    if not CONTENT_DIR.exists():
        return []
    articles = []
    for path in sorted(CONTENT_DIR.glob("*.md")):
        frontmatter, body = _split_frontmatter(path.read_text(encoding="utf-8"))
        articles.append(
            {
                "slug": path.stem,
                "title": frontmatter.get("title", path.stem),
                "date": str(frontmatter.get("date", "")),
                "summary": frontmatter.get("summary", ""),
                "body_html": render_markdown(body, extensions=["extra"]),
            }
        )
    articles.sort(key=lambda a: a["date"], reverse=True)
    return articles


def load_season_data(outputs_dir: Path) -> dict:
    """Loads every CSV run_pipeline.py writes and derives the lookups every page needs."""
    results = pd.read_csv(outputs_dir / "simulation_results.csv")
    teams = pd.read_csv(outputs_dir / "teams.csv")

    return {
        "results": results,
        "teams": teams,
        "advancement": pd.read_csv(outputs_dir / "round_advancement.csv"),
        "seed_predictions": pd.read_csv(outputs_dir / "seed_predictions.csv"),
        "team_tiers": pd.read_csv(outputs_dir / "team_tiers.csv"),
        "seed_to_team": dict(zip(teams["Seed"], teams["TeamID"])),
        "seed_by_team": {row.TeamID: int(row.Seed[1:3]) for row in teams.itertuples()},
        "id_to_team": dict(zip(teams["TeamID"], teams["TeamName"])),
        "n_brackets": int(results["Bracket"].nunique()),
    }


def chart_html(fig: go.Figure) -> str:
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_family="system-ui, -apple-system, 'Segoe UI', sans-serif",
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig.to_html(full_html=False, include_plotlyjs="cdn", config={"displayModeBar": False})


def build_round_odds_page(data: dict) -> dict:
    advancement = data["advancement"].copy()
    round_cols = [c for c in ROUND_NAMES.values() if c in advancement.columns]
    for col in round_cols:
        advancement[col] = advancement[col] / data["n_brackets"]
    advancement = advancement.sort_values("Champion", ascending=False)

    top15 = advancement.head(15)
    fig = go.Figure(go.Bar(x=top15["Champion"] * 100, y=top15["Team"], orientation="h", marker_color=SERIES_1))
    fig.update_layout(
        title="Top 15 championship odds",
        xaxis_title="Championship probability (%)",
        yaxis=dict(autorange="reversed"),
        height=450,
    )

    headers = ["Team"] + round_cols
    rows = [[row["Team"]] + [f"{row[c]:.1%}" for c in round_cols] for _, row in advancement.iterrows()]
    return {
        "title": "Round Odds",
        "subtitle": f"Probability of reaching each round, from {data['n_brackets']:,} simulated brackets.",
        "chart_html": chart_html(fig),
        "table": {"title": "All teams", "headers": headers, "rows": rows},
    }


def build_over_underperformers_page(data: dict) -> dict:
    table_df = round_advancement.wins_over_seed_expectation(data["results"], data["seed_by_team"])
    table_df["Team"] = table_df["TeamID"].map(data["id_to_team"])
    table_df = table_df.sort_values("WinsOverSeedExpectation", ascending=False)

    top, bottom = table_df.head(12), table_df.tail(12).iloc[::-1]
    combined = pd.concat([top, bottom])
    colors = [DIVERGING_POS if v >= 0 else DIVERGING_NEG for v in combined["WinsOverSeedExpectation"]]
    labels = combined["Team"] + " (seed " + combined["Seed"].astype(int).astype(str) + ")"
    fig = go.Figure(go.Bar(x=combined["WinsOverSeedExpectation"], y=labels, orientation="h", marker_color=colors))
    fig.update_layout(
        title="Biggest over/underperformers vs. seed expectation",
        xaxis_title="Simulated avg. wins minus historical average for that seed",
        yaxis=dict(autorange="reversed"),
        height=650,
    )

    headers = ["Team", "Seed", "Simulated Avg Wins", "Historical Avg (seed)", "Wins Over Expectation"]
    rows = [
        [
            row["Team"], int(row["Seed"]), f"{row['SimulatedAverageWins']:.2f}",
            f"{row['HistoricalAverageWins']:.2f}", f"{row['WinsOverSeedExpectation']:+.2f}",
        ]
        for _, row in table_df.iterrows()
    ]
    return {
        "title": "Over/Underperformers",
        "subtitle": "Simulated average tournament wins compared to the historical average for that seed line (source: bracketodds.cs.illinois.edu).",
        "chart_html": chart_html(fig),
        "table": {"title": "All teams", "headers": headers, "rows": rows},
    }


def build_cinderella_page(data: dict) -> dict:
    matrix = [
        [round_advancement.cinderella_probability(data["results"], data["seed_by_team"], min_seed, r) for r in CINDERELLA_ROUNDS]
        for min_seed in CINDERELLA_SEED_THRESHOLDS
    ]
    round_labels = [ROUND_NAMES[r] for r in CINDERELLA_ROUNDS]

    fig = go.Figure(
        go.Heatmap(
            z=[[v * 100 for v in row] for row in matrix],
            x=round_labels,
            y=[f"Seed {s}+" for s in CINDERELLA_SEED_THRESHOLDS],
            colorscale=[[i / (len(SEQ_BLUE) - 1), c] for i, c in enumerate(SEQ_BLUE)],
            colorbar=dict(title="%"),
        )
    )
    fig.update_layout(title="Odds a seed this bad (or worse) reaches this round", height=420)

    headers = ["Seed threshold"] + round_labels
    rows = [[f"{s}+"] + [f"{p:.1%}" for p in row] for s, row in zip(CINDERELLA_SEED_THRESHOLDS, matrix)]
    return {
        "title": "Cinderella Watch",
        "subtitle": "How often a double-digit (or worse) seed makes a run this deep, across every simulated bracket.",
        "chart_html": chart_html(fig),
        "table": {"title": "Full sweep", "headers": headers, "rows": rows},
    }


def build_final_four_finder_page(data: dict) -> dict:
    combos = round_advancement.final_four_combination_counts(data["results"])
    top20 = combos.head(20)
    id_to_team = data["id_to_team"]

    labels = [", ".join(id_to_team.get(t, str(t)) for t in combo) for combo in top20.index]
    fig = go.Figure(go.Bar(x=top20.to_numpy(), y=labels, orientation="h", marker_color=SERIES_1))
    fig.update_layout(
        title="Most common Final Four combinations",
        xaxis_title=f"Occurrences (of {data['n_brackets']:,} brackets)",
        yaxis=dict(autorange="reversed"),
        height=600,
    )

    headers = ["Final Four", "Occurrences", "Share of brackets"]
    rows = [
        [", ".join(id_to_team.get(t, str(t)) for t in combo), int(count), f"{count / data['n_brackets']:.1%}"]
        for combo, count in top20.items()
    ]
    return {
        "title": "Final Four Finder",
        "subtitle": "The most common combinations of teams reaching the Final Four together.",
        "chart_html": chart_html(fig),
        "table": {"title": "Top 20 combinations", "headers": headers, "rows": rows},
    }


def build_region_strength_page(data: dict) -> dict:
    champs = region_strength.region_championship_counts(data["results"], data["seed_to_team"])
    shares = region_strength.region_top_seed_championship_share(data["results"], data["seed_to_team"])
    regions = sorted(shares.index)

    fig = go.Figure(
        go.Bar(x=regions, y=[shares[r] * 100 for r in regions], marker_color=REGION_COLORS[: len(regions)])
    )
    fig.update_layout(title="Championship share held by each region's #1 seed", yaxis_title="%", height=350)

    headers = ["Region", "Championships", "Top-seed championship share"]
    rows = [[region, int(champs.get(region, 0)), f"{shares[region]:.1%}"] for region in regions]
    return {
        "title": "Region Strength",
        "subtitle": "How top-heavy each region is in the simulation -- a low top-seed share means that region's championships were spread across multiple contenders, not carried by one favorite.",
        "placeholder_note": (
            "Early feature. What's here today: how concentrated each region's simulated championships "
            "are in its #1 seed. This is planned to go deeper -- see the project roadmap."
        ),
        "chart_html": chart_html(fig),
        "table": {"title": f"{data['n_brackets']:,} simulated brackets", "headers": headers, "rows": rows},
    }


def build_seed_prediction_page(data: dict) -> dict:
    preds = data["seed_predictions"].copy()
    preds["Diff"] = preds["PredictedSeed"] - preds["Seed"]
    preds = preds.sort_values("Diff", key=lambda s: s.abs(), ascending=False)

    fig = go.Figure(
        go.Scatter(
            x=preds["Seed"], y=preds["PredictedSeed"], mode="markers", text=preds["Team"],
            marker=dict(color=SERIES_1, size=9),
            hovertemplate="%{text}<br>Actual seed: %{x}<br>Predicted seed: %{y}<extra></extra>",
        )
    )
    fig.add_shape(type="line", x0=1, y0=1, x1=16, y1=16, line=dict(color=MUTED, dash="dot"))
    fig.update_layout(
        title="Predicted seed vs. actual seed",
        xaxis_title="Actual seed", yaxis_title="Predicted seed (KNN, KenPom stats only)",
        height=500,
    )

    headers = ["Team", "Actual Seed", "Predicted Seed", "Difference"]
    rows = [
        [row["Team"], int(row["Seed"]), int(row["PredictedSeed"]), f"{int(row['Diff']):+d}"]
        for _, row in preds.iterrows()
    ]
    return {
        "title": "Seed Prediction",
        "subtitle": "What seed the model would have assigned based on KenPom stats alone, versus the committee's actual seed.",
        "placeholder_note": (
            "Early feature, genuinely data-starved right now -- this repo only has one real season "
            "of labeled tournament seeds to learn from (~4 examples per seed line). Accuracy will "
            "improve automatically as more years of KenPom history accumulate. See the project roadmap."
        ),
        "chart_html": chart_html(fig),
        "table": {"title": "Biggest predicted-vs-actual gaps first", "headers": headers, "rows": rows},
    }


ANALYTICS_PAGES = {
    "round_odds": build_round_odds_page,
    "over_underperformers": build_over_underperformers_page,
    "cinderella": build_cinderella_page,
    "final_four_finder": build_final_four_finder_page,
    "region_strength": build_region_strength_page,
    "seed_prediction": build_seed_prediction_page,
}


def main() -> None:
    config = load_season_config()
    data = load_season_data(config.outputs_dir)
    articles = load_articles()

    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)
    shutil.copytree(STATIC_DIR, OUTPUT_DIR / "static")
    (OUTPUT_DIR / "analytics").mkdir()
    (OUTPUT_DIR / "articles").mkdir()

    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=False)
    base_context = {"site_name": SITE_NAME, "season_year": config.year}

    index_html = env.get_template("index.html").render(
        **base_context, root="", tagline=TAGLINE, articles=articles, n_brackets=f"{data['n_brackets']:,}"
    )
    (OUTPUT_DIR / "index.html").write_text(index_html, encoding="utf-8")
    print(f"wrote index.html ({len(articles)} article(s) listed)")

    article_template = env.get_template("article.html")
    for article in articles:
        html = article_template.render(**base_context, root="../", article=article)
        (OUTPUT_DIR / "articles" / f"{article['slug']}.html").write_text(html, encoding="utf-8")
    if articles:
        print(f"wrote {len(articles)} article page(s)")

    data_page_template = env.get_template("data_page.html")
    for page_slug, builder in ANALYTICS_PAGES.items():
        page_context = builder(data)
        html = data_page_template.render(**base_context, root="../", **page_context)
        (OUTPUT_DIR / "analytics" / f"{page_slug}.html").write_text(html, encoding="utf-8")
        print(f"wrote analytics/{page_slug}.html")

    print(f"\nSite built at {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
