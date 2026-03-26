"""
analysis/comparison.py
Developer vs Developer comparison utilities.
"""

import plotly.graph_objects as go
import pandas as pd
from config import ACCENT_COLORS


def overlay_radar(df_a: pd.DataFrame, df_b: pd.DataFrame,
                  name_a: str, name_b: str) -> go.Figure:
    """
    Overlay two language radar charts on the same polar figure.
    df_a, df_b: DataFrames with columns ['language', 'pct']
    """
    fig = go.Figure()

    def _add_trace(df: pd.DataFrame, name: str, color: str, fillcolor: str):
        if df.empty:
            return
        cats = df["language"].tolist()
        vals = df["pct"].tolist()
        cats_c = cats + [cats[0]]
        vals_c = vals + [vals[0]]
        fig.add_trace(go.Scatterpolar(
            r=vals_c, theta=cats_c,
            fill="toself",
            fillcolor=fillcolor,
            line=dict(color=color, width=2),
            name=name,
            hovertemplate="%{theta}: %{r:.1f}%<extra>" + name + "</extra>",
        ))

    _add_trace(df_a, name_a, "#6C63FF", "rgba(108,99,255,0.15)")
    _add_trace(df_b, name_b, "#EC4899", "rgba(236,72,153,0.15)")

    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, showticklabels=False,
                            gridcolor="rgba(255,255,255,0.1)"),
            angularaxis=dict(tickfont=dict(size=11, color="#E2E8F0"),
                             gridcolor="rgba(255,255,255,0.1)"),
        ),
        showlegend=True,
        legend=dict(font=dict(color="#E2E8F0"),
                    bgcolor="rgba(0,0,0,0)"),
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=30, b=20, l=40, r=40),
        font=dict(color="#E2E8F0"),
    )
    return fig


def compatibility_score(stats_a: dict, stats_b: dict,
                        lang_df_a: pd.DataFrame,
                        lang_df_b: pd.DataFrame) -> dict:
    """
    Compute a 0-100 compatibility score and a list of insight strings.
    """
    score = 0
    insights = []

    # 1. Shared languages (up to 40 pts)
    langs_a = set(lang_df_a["language"].tolist()) if not lang_df_a.empty else set()
    langs_b = set(lang_df_b["language"].tolist()) if not lang_df_b.empty else set()
    if langs_a and langs_b:
        shared = langs_a & langs_b
        lang_score = min(40, int(len(shared) / max(len(langs_a), len(langs_b)) * 40))
        score += lang_score
        if shared:
            insights.append(f"🔗 Both write **{', '.join(list(shared)[:3])}**")
        else:
            insights.append("🌐 Complementary tech stacks — no language overlap")

    # 2. Shared dominant topic (20 pts)
    topic_a = stats_a.get("dominant_topic", "unknown")
    topic_b = stats_b.get("dominant_topic", "unknown")
    if topic_a == topic_b and topic_a != "unknown":
        score += 20
        insights.append(f"🧠 Both primarily write **{topic_a}** commits")
    else:
        insights.append(f"🧩 Different focus areas: **{topic_a}** vs **{topic_b}**")

    # 3. Activity hour overlap (20 pts)
    hours_a = set(stats_a.get("commit_hours", []))
    hours_b = set(stats_b.get("commit_hours", []))
    if hours_a and hours_b:
        overlap = hours_a & hours_b
        hour_score = min(20, int(len(overlap) / 24 * 20))
        score += hour_score
        if hour_score > 12:
            insights.append("⏰ Very similar coding schedules")
        else:
            insights.append("🌍 Code at different times of day")

    # 4. Sentiment similarity (20 pts)
    sent_a = stats_a.get("avg_sentiment", 0)
    sent_b = stats_b.get("avg_sentiment", 0)
    diff = abs(sent_a - sent_b)
    if diff < 0.05:
        score += 20
        insights.append("😊 Same commit vibe/mood")
    elif diff < 0.15:
        score += 10
        insights.append("😌 Similar commit mood")
    else:
        insights.append("🎭 Very different commit personalities")

    label = ("🔥 Perfect Match" if score >= 80 else
             "✅ Great Team" if score >= 60 else
             "👍 Decent Pair" if score >= 40 else
             "🌐 Complementary")

    return {"score": score, "label": label, "insights": insights}


def highlight_differences(stats_a: dict, stats_b: dict,
                           name_a: str, name_b: str) -> list[str]:
    """Return human-readable comparison bullet points."""
    bullets = []

    # Commit volume
    ca = len(stats_a.get("commit_hours", []))
    cb = len(stats_b.get("commit_hours", []))
    if ca > 0 and cb > 0:
        ratio = round(max(ca, cb) / min(ca, cb), 1)
        more  = name_a if ca > cb else name_b
        bullets.append(f"📊 **{more}** has analysed **{ratio}×** more commits")

    # Night owl comparison
    def _night_pct(stats):
        h = stats.get("commit_hours", [])
        if not h:
            return 0
        return sum(1 for x in h if 0 <= x <= 4) / len(h) * 100

    na, nb = _night_pct(stats_a), _night_pct(stats_b)
    if abs(na - nb) > 5:
        more_night = name_a if na > nb else name_b
        bullets.append(f"🌙 **{more_night}** commits more at night "
                       f"({max(na,nb):.0f}% vs {min(na,nb):.0f}%)")

    # Weekend warrior
    def _wknd_pct(stats):
        w = stats.get("commit_weekdays", [])
        if not w:
            return 0
        return sum(1 for d in w if d in ("Saturday","Sunday")) / len(w) * 100

    wa, wb = _wknd_pct(stats_a), _wknd_pct(stats_b)
    if abs(wa - wb) > 5:
        more_wknd = name_a if wa > wb else name_b
        bullets.append(f"⚡ **{more_wknd}** is more of a weekend coder "
                       f"({max(wa,wb):.0f}% vs {min(wa,wb):.0f}% weekend commits)")

    # Followers
    fol_a = stats_a.get("followers", 0)
    fol_b = stats_b.get("followers", 0)
    if fol_a != fol_b:
        more_fol = name_a if fol_a > fol_b else name_b
        bullets.append(f"👥 **{more_fol}** has more followers "
                       f"({max(fol_a,fol_b):,} vs {min(fol_a,fol_b):,})")

    return bullets[:5]  # cap
