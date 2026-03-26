"""
analysis/personality.py
Rule-based personality badge classifier.
"""

from config import (
    NIGHT_OWL_THRESHOLD,
    DOC_LOVER_THRESHOLD,
    PROLIFIC_COMMITTER_THRESHOLD,
    WEEKEND_WARRIOR_THRESHOLD,
)


def classify(user_stats: dict) -> list[dict]:
    """
    user_stats keys expected:
      commit_hours: list[int]
      commit_weekdays: list[str]
      repos: list[dict]  (each has 'has_readme', 'commit_count')
      dominant_topic: str
      avg_sentiment: float
      prs_authored: int
      issues_authored: int

    Returns list of {badge, label, description} dicts.
    """
    badges = []
    commits = user_stats.get("commit_hours", [])
    weekdays = user_stats.get("commit_weekdays", [])
    repos = user_stats.get("repos", [])
    dominant_topic = user_stats.get("dominant_topic", "unknown")
    avg_sentiment = user_stats.get("avg_sentiment", 0.0)
    prs = user_stats.get("prs_authored", 0)
    issues = user_stats.get("issues_authored", 0)

    n = len(commits)
    n_repos = len(repos)

    # ---- Night Owl ----
    if n > 0:
        night = sum(1 for h in commits if 0 <= h <= 4)
        if night / n > NIGHT_OWL_THRESHOLD:
            badges.append({
                "badge": "🦉 Night Owl",
                "label": "Night Owl",
                "description": f"{night/n*100:.0f}% of commits happen between midnight and 4 AM.",
            })

    # ---- Weekend Warrior ----
    if weekdays:
        wknd = sum(1 for d in weekdays if d in ("Saturday", "Sunday"))
        if wknd / len(weekdays) > WEEKEND_WARRIOR_THRESHOLD:
            badges.append({
                "badge": "⚡ Weekend Warrior",
                "label": "Weekend Warrior",
                "description": f"{wknd/len(weekdays)*100:.0f}% of commits happen on weekends.",
            })

    # ---- Refactoring Ninja ----
    if dominant_topic == "refactor":
        badges.append({
            "badge": "🥷 Refactoring Ninja",
            "label": "Refactoring Ninja",
            "description": "Commit messages are dominated by cleanup, restructuring, and renaming.",
        })

    # ---- Documentation Lover ----
    if n_repos > 0:
        doc_repos = sum(1 for r in repos if r.get("has_readme"))
        if doc_repos / n_repos > DOC_LOVER_THRESHOLD:
            badges.append({
                "badge": "📖 Documentation Lover",
                "label": "Documentation Lover",
                "description": f"{doc_repos}/{n_repos} repos have a README file.",
            })

    # ---- Prolific Committer ----
    if n_repos > 0:
        avg_commits = sum(r.get("commit_count", 0) for r in repos) / n_repos
        if avg_commits > PROLIFIC_COMMITTER_THRESHOLD:
            badges.append({
                "badge": "🔥 Prolific Committer",
                "label": "Prolific Committer",
                "description": f"Averages {avg_commits:.0f} commits per repo.",
            })

    # ---- Bug Hunter ----
    if dominant_topic == "bug":
        badges.append({
            "badge": "🐛 Bug Hunter",
            "label": "Bug Hunter",
            "description": "Most commit messages are focused on fixing bugs and crashes.",
        })

    # ---- Feature Builder ----
    if dominant_topic == "feature":
        badges.append({
            "badge": "🚀 Feature Builder",
            "label": "Feature Builder",
            "description": "Commit history is full of 'add', 'implement', and 'create' — a maker's mindset.",
        })

    # ---- Open Source Contributor ----
    if prs > 50:
        badges.append({
            "badge": "🌍 Open Source Hero",
            "label": "Open Source Hero",
            "description": f"Has authored {prs} pull requests across GitHub.",
        })

    # ---- Issue Tracker ----
    if issues > 100:
        badges.append({
            "badge": "🎯 Issue Tracker",
            "label": "Issue Tracker",
            "description": f"Has filed {issues} issues — a thorough quality-minded developer.",
        })

    # ---- Zen Coder (very positive sentiment) ----
    if avg_sentiment > 0.20:
        badges.append({
            "badge": "🧘 Zen Coder",
            "label": "Zen Coder",
            "description": "Commit messages are overwhelmingly upbeat and positive.",
        })

    # Fallback
    if not badges:
        badges.append({
            "badge": "💻 Dedicated Developer",
            "label": "Dedicated Developer",
            "description": "A consistent, steady contributor to open source.",
        })

    return badges
