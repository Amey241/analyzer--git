"""
FastAPI entrypoint for Vercel deployment.

This replaces the Streamlit runtime on Vercel by exposing JSON endpoints.
"""

import os
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv

from data.fetcher import GitHubFetcher
from analysis.languages import aggregate_languages
from analysis.activity import build_heatmap_data, peak_hours_summary
from analysis.nlp import sentiment_analysis, lda_topics
from analysis.personality import (
    classify,
    generate_narrative,
    achievement_trophy_case,
    time_capsule_message,
)
from analysis.commit_quality import score_commits
from analysis.comparison import compatibility_score, highlight_differences
from analysis.repo_health import score_repo, aggregate_health
from analysis.career_arc import analyze_career_arc
from analysis.code_dna import analyze_style, generate_dna_svg
from analysis.ecosystem import build_ecosystem_graph
from analysis.ai_insights import AIInsights
from analysis.deep_metrics import (
    estimate_bus_factor,
    calculate_streaks,
    invisible_work_audit,
    ghost_repo_audit,
)

load_dotenv()

app = FastAPI(
    title="GitHub Analyzer API",
    version="1.0.0",
    description="Vercel-compatible API for GitHub profile analysis.",
)


def _configured_token() -> str:
    return os.getenv("GITHUB_TOKEN", "").strip()


def _df_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df is None or df.empty:
        return []
    out = df.where(pd.notnull(df), None).to_dict(orient="records")
    return [dict(row) for row in out]


def _build_user_stats(raw: dict, commits: list[dict], topics: dict, sentiment: dict) -> dict:
    return {
        "commit_hours": [c.get("hour", 0) for c in commits],
        "commit_weekdays": [c.get("weekday", "") for c in commits],
        "repos": raw.get("repos", []),
        "dominant_topic": topics.get("dominant_topic", "unknown"),
        "avg_sentiment": sentiment.get("avg_polarity", 0.0),
        "prs_authored": raw.get("prs_authored", 0),
        "issues_authored": raw.get("issues_authored", 0),
        "followers": raw.get("profile", {}).get("followers", 0),
    }


def _analyze_username(username: str, include_ai: bool) -> dict:
    token = _configured_token()
    fetcher = GitHubFetcher(token)

    raw = fetcher.get_user_data(username)
    commits = raw.get("commits", [])
    commit_messages = [c.get("message", "") for c in commits if c.get("message")]

    lang_df = aggregate_languages(raw.get("lang_totals", {}))
    heatmap_pivot = build_heatmap_data(commits)
    activity = peak_hours_summary(heatmap_pivot)
    sentiment = sentiment_analysis(commit_messages)
    topics = lda_topics(commit_messages)
    quality = score_commits(commit_messages)

    repo_scores = [score_repo(repo) for repo in raw.get("repos", [])]
    health_stats = aggregate_health(repo_scores)
    user_stats = _build_user_stats(raw, commits, topics, sentiment)
    badges = classify(user_stats)
    narrative = generate_narrative(user_stats, raw.get("profile", {}))
    achievements = achievement_trophy_case(user_stats, raw.get("profile", {}), lang_df)

    try:
        code_samples = raw.get("all_samples", [])
        dna_traits = analyze_style(code_samples)
        dna_svg = generate_dna_svg(dna_traits)
    except Exception:
        dna_traits, dna_svg = {}, ""

    try:
        repo_deps = raw.get("all_deps", {})
        ecosystem_html = build_ecosystem_graph(repo_deps)
    except Exception:
        ecosystem_html = ""

    ai_payload: dict[str, Any] = {
        "job_roles": [],
        "review_personality": {
            "archetype": "The Observer",
            "trait": "Neutral",
            "advice": "",
        },
        "rewrites": [],
    }

    if include_ai:
        try:
            ai = AIInsights()
            ai_payload["job_roles"] = ai.get_job_role_suggestions(user_stats, lang_df)
            review_comments = fetcher.get_review_comments(username)
            ai_payload["review_personality"] = ai.analyze_review_personality(review_comments)
            low_q_commits = [m for m, _, _ in quality.get("worst_examples", [])[:3]]
            ai_payload["rewrites"] = ai.suggest_commit_rewrites(low_q_commits)
        except Exception:
            pass

    try:
        bus_stats = estimate_bus_factor(raw.get("repos", []))
        streak_stats = calculate_streaks(commits)
        arc_df = analyze_career_arc(commits)
        capsule = time_capsule_message(arc_df, raw.get("profile", {}))
        invisible_stats = invisible_work_audit(
            {
                "prs_authored": raw.get("prs_authored", 0),
                "issues_authored": raw.get("issues_authored", 0),
                "pr_reviews_count": raw.get("pr_reviews_count", 0),
                "issue_comments_count": raw.get("issue_comments_count", 0),
            }
        )
        ghosts = ghost_repo_audit(raw.get("repos", []))
    except Exception:
        bus_stats = {"factors": [], "avg_factor": 0, "risk": "Unknown"}
        streak_stats = {"current": 0, "longest": 0}
        arc_df, capsule = pd.DataFrame(), ""
        invisible_stats = {
            "prs": 0,
            "issues": 0,
            "reviews": 0,
            "issue_comments": 0,
            "total_impact": 0,
            "invisible_pct": 0,
            "is_empty": True,
        }
        ghosts = []

    return {
        "profile": raw.get("profile", {}),
        "repos": raw.get("repos", []),
        "commits": commits,
        "activity": activity,
        "sentiment": sentiment,
        "topics": topics,
        "quality": quality,
        "repo_scores": repo_scores,
        "health_stats": health_stats,
        "badges": badges,
        "narrative": narrative,
        "achievements": achievements,
        "languages": _df_to_records(lang_df),
        "heatmap": _df_to_records(heatmap_pivot.reset_index()),
        "career_arc": _df_to_records(arc_df),
        "capsule": capsule,
        "dna_traits": dna_traits,
        "dna_svg": dna_svg,
        "ecosystem_html": ecosystem_html,
        "bus_stats": bus_stats,
        "streak_stats": streak_stats,
        "invisible_stats": invisible_stats,
        "ghosts": ghosts,
        "ai": ai_payload,
    }


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def root() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>GitHub Analyzer</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 900px; margin: 24px auto; padding: 0 12px; color: #111; }
    .card { border: 1px solid #ddd; border-radius: 8px; padding: 14px; margin-bottom: 12px; }
    h1 { margin-bottom: 8px; }
    h3 { margin: 0 0 10px 0; }
    input { padding: 8px; margin-right: 8px; margin-bottom: 8px; }
    button { padding: 8px 12px; cursor: pointer; }
    pre { background: #f7f7f7; border-radius: 8px; padding: 12px; overflow: auto; max-height: 460px; }
  </style>
</head>
<body>
  <h1>GitHub Analyzer API</h1>
  <p>Simple UI for your deployed API.</p>

  <div class="card">
    <h3>Analyze One User</h3>
    <input id="u1" placeholder="GitHub username" />
    <button onclick="analyze()">Analyze</button>
  </div>

  <div class="card">
    <h3>Compare Two Users</h3>
    <input id="a" placeholder="Username A" />
    <input id="b" placeholder="Username B" />
    <button onclick="compareUsers()">Compare</button>
  </div>

  <div class="card">
    <h3>Result</h3>
    <pre id="out">Run an action above.</pre>
  </div>

  <script>
    const out = document.getElementById("out");
    async function callApi(url) {
      out.textContent = "Loading...";
      try {
        const r = await fetch(url);
        const data = await r.json();
        out.textContent = JSON.stringify(data, null, 2);
      } catch (e) {
        out.textContent = "Request failed: " + e;
      }
    }
    function analyze() {
      const u = document.getElementById("u1").value.trim();
      if (!u) { out.textContent = "Please enter a username."; return; }
      callApi("/api/analyze?username=" + encodeURIComponent(u));
    }
    function compareUsers() {
      const a = document.getElementById("a").value.trim();
      const b = document.getElementById("b").value.trim();
      if (!a || !b) { out.textContent = "Please enter both usernames."; return; }
      callApi("/api/compare?username_a=" + encodeURIComponent(a) + "&username_b=" + encodeURIComponent(b));
    }
  </script>
</body>
</html>"""


@app.get("/api/analyze")
def analyze(
    username: str = Query(..., min_length=1, max_length=39),
    include_ai: bool = Query(False),
) -> dict:
    try:
        return _analyze_username(username.strip(), include_ai=include_ai)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc


@app.get("/api/compare")
def compare(
    username_a: str = Query(..., min_length=1, max_length=39),
    username_b: str = Query(..., min_length=1, max_length=39),
) -> dict:
    a = _analyze_username(username_a.strip(), include_ai=False)
    b = _analyze_username(username_b.strip(), include_ai=False)

    stats_a = {
        "commit_hours": [c.get("hour", 0) for c in a.get("commits", [])],
        "commit_weekdays": [c.get("weekday", "") for c in a.get("commits", [])],
        "dominant_topic": a.get("topics", {}).get("dominant_topic", "unknown"),
        "avg_sentiment": a.get("sentiment", {}).get("avg_polarity", 0.0),
        "followers": a.get("profile", {}).get("followers", 0),
    }
    stats_b = {
        "commit_hours": [c.get("hour", 0) for c in b.get("commits", [])],
        "commit_weekdays": [c.get("weekday", "") for c in b.get("commits", [])],
        "dominant_topic": b.get("topics", {}).get("dominant_topic", "unknown"),
        "avg_sentiment": b.get("sentiment", {}).get("avg_polarity", 0.0),
        "followers": b.get("profile", {}).get("followers", 0),
    }

    lang_df_a = pd.DataFrame(a.get("languages", []))
    lang_df_b = pd.DataFrame(b.get("languages", []))

    compatibility = compatibility_score(stats_a, stats_b, lang_df_a, lang_df_b)
    differences = highlight_differences(
        stats_a,
        stats_b,
        a.get("profile", {}).get("login", username_a),
        b.get("profile", {}).get("login", username_b),
    )

    return {
        "user_a": {
            "username": username_a,
            "profile": a.get("profile", {}),
            "languages": a.get("languages", []),
            "topics": a.get("topics", {}),
            "sentiment": a.get("sentiment", {}),
        },
        "user_b": {
            "username": username_b,
            "profile": b.get("profile", {}),
            "languages": b.get("languages", []),
            "topics": b.get("topics", {}),
            "sentiment": b.get("sentiment", {}),
        },
        "compatibility": compatibility,
        "differences": differences,
    }
