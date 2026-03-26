"""
analysis/activity.py
Parse commit timestamps into pivot tables and build a Plotly heatmap.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

WEEKDAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def build_heatmap_data(commits: list[dict]) -> pd.DataFrame:
    """
    Given list of commit dicts with 'weekday' and 'hour' keys,
    return a (weekday × hour) count pivot table.
    """
    if not commits:
        return pd.DataFrame()

    df = pd.DataFrame(commits)
    df["weekday"] = pd.Categorical(df["weekday"], categories=WEEKDAY_ORDER, ordered=True)
    pivot = (
        df.groupby(["weekday", "hour"])
        .size()
        .unstack(fill_value=0)
        .reindex(WEEKDAY_ORDER, fill_value=0)
    )
    # Ensure all 24 hours are present
    for h in range(24):
        if h not in pivot.columns:
            pivot[h] = 0
    pivot = pivot[sorted(pivot.columns)]
    return pivot


def activity_heatmap(pivot: pd.DataFrame) -> go.Figure:
    """Build an interactive Plotly heatmap from the pivot table."""
    if pivot.empty:
        fig = go.Figure()
        fig.add_annotation(text="No commit data", x=0.5, y=0.5, showarrow=False)
        return fig

    hour_labels = [
        f"{h:02d}:00" if h % 3 == 0 else "" for h in range(24)
    ]

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=[f"{h:02d}:00" for h in range(24)],
        y=pivot.index.tolist(),
        colorscale=[
            [0.0,  "rgba(108,99,255,0.05)"],
            [0.25, "rgba(108,99,255,0.3)"],
            [0.5,  "rgba(108,99,255,0.6)"],
            [0.75, "rgba(168,85,247,0.8)"],
            [1.0,  "rgba(236,72,153,1.0)"],
        ],
        showscale=True,
        colorbar=dict(
            title=dict(text="Commits", font=dict(color="#E2E8F0")),
            tickfont=dict(color="#E2E8F0"),
        ),
        hovertemplate="<b>%{y}</b> at <b>%{x}</b><br>Commits: %{z}<extra></extra>",
    ))
    fig.update_layout(
        xaxis=dict(title="Hour of Day", tickangle=-45, color="#E2E8F0"),
        yaxis=dict(title="Day of Week", color="#E2E8F0"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E2E8F0"),
        margin=dict(t=10, b=60, l=10, r=10),
    )
    return fig


def peak_hours_summary(pivot: pd.DataFrame) -> dict:
    """Return a short summary dict of activity patterns."""
    if pivot.empty:
        return {}

    total = pivot.values.sum()
    night = pivot[[h for h in range(24) if h in pivot.columns and 0 <= h <= 4]].values.sum()
    morning = pivot[[h for h in range(24) if h in pivot.columns and 5 <= h <= 11]].values.sum()
    afternoon = pivot[[h for h in range(24) if h in pivot.columns and 12 <= h <= 17]].values.sum()
    evening = pivot[[h for h in range(24) if h in pivot.columns and 18 <= h <= 23]].values.sum()

    weekday_totals = pivot.loc[["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]].values.sum()
    weekend_totals = pivot.loc[["Saturday", "Sunday"]].values.sum()

    busiest_hour = int(pivot.sum(axis=0).idxmax())
    busiest_day = pivot.sum(axis=1).idxmax()

    return {
        "total": int(total),
        "night_pct": round(night / total * 100, 1) if total else 0,
        "morning_pct": round(morning / total * 100, 1) if total else 0,
        "afternoon_pct": round(afternoon / total * 100, 1) if total else 0,
        "evening_pct": round(evening / total * 100, 1) if total else 0,
        "weekday_pct": round(weekday_totals / total * 100, 1) if total else 0,
        "weekend_pct": round(weekend_totals / total * 100, 1) if total else 0,
        "busiest_hour": busiest_hour,
        "busiest_day": busiest_day,
    }
