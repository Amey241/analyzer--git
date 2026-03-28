"""
analysis/career_arc.py
Year-by-year analysis of developer growth.
"""

import pandas as pd
import plotly.express as px
from collections import Counter
from analysis.nlp import sentiment_analysis, lda_topics

def analyze_career_arc(commits: list[dict]) -> pd.DataFrame:
    """
    Group commits by year and compute metrics for each year.
    Returns a DataFrame with columns: [year, language, topic, sentiment, count]
    """
    if not commits:
        return pd.DataFrame()

    df = pd.DataFrame(commits)
    if "year" not in df.columns:
        return pd.DataFrame()

    years = sorted(df["year"].unique())
    arc_data = []

    for year in years:
        year_commits = df[df["year"] == year]
        messages = year_commits["message"].tolist()
        
        # 1. Dominant Language
        # We use repo_lang as a proxy for the language of the commit
        lang_counts = Counter(year_commits["repo_lang"])
        dominant_lang = lang_counts.most_common(1)[0][0] if lang_counts else "Unknown"
        
        # 2. Avg Sentiment
        sent = sentiment_analysis(messages)
        avg_sent = sent["avg_polarity"]
        
        # 3. Dominant Topic (LDA)
        # To save time, we only run LDA if there are enough messages
        if len(messages) >= 10:
            topics = lda_topics(messages, n_topics=1)
            dominant_topic = topics["dominant_topic"]
        else:
            # Heuristic fallback if too few commits for LDA
            dominant_topic = "General"

        arc_data.append({
            "year": int(year),
            "language": dominant_lang,
            "topic": dominant_topic,
            "sentiment": avg_sent,
            "commit_count": len(year_commits)
        })

    return pd.DataFrame(arc_data)

def career_arc_timeline(arc_df: pd.DataFrame) -> any:
    """
    Create an animated Plotly timeline of the career arc.
    """
    if arc_df.empty:
        return None

    # We use a scatter plot where x is year, y is sentiment, size is commit_count, and color is language
    # We add 'topic' as a hover label
    fig = px.scatter(
        arc_df,
        x="year",
        y="sentiment",
        size="commit_count",
        color="language",
        hover_name="topic",
        text="language",
        title="Career Evolution Timeline",
        labels={"sentiment": "Commit Sentiment (Mood)", "year": "Year", "commit_count": "Commit Volume"},
        range_y=[-1, 1],
        template="plotly_dark"
    )

    fig.update_traces(textposition='top center')
    fig.update_layout(
        showlegend=True,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E2E8F0"),
        height=400
    )
    
    return fig
