"""
analysis/commit_quality.py
Score commit messages on a hygiene rubric and produce an A-F grade.
"""

import re
from dataclasses import dataclass, field

# Common imperative verbs that signal good commit hygiene
IMPERATIVE_VERBS = {
    "add", "fix", "update", "remove", "refactor", "improve", "implement",
    "create", "delete", "rename", "move", "merge", "revert", "bump",
    "clean", "change", "replace", "extract", "split", "integrate",
    "enable", "disable", "configure", "document", "optimize", "test",
    "release", "deploy", "init", "initialize", "set", "reset", "resolve",
    "handle", "support", "allow", "prevent", "ensure", "migrate", "upgrade",
}

CONVENTIONAL_PREFIXES = {
    "feat", "fix", "chore", "docs", "style", "refactor",
    "test", "perf", "ci", "build", "revert", "wip",
}


@dataclass
class ScoreBreakdown:
    length_score: int = 0        # 0-20
    imperative_score: int = 0    # 0-25
    reference_score: int = 0     # 0-15
    conventional_score: int = 0  # 0-20
    no_period_score: int = 0     # 0-10
    capitalised_score: int = 0   # 0-10
    total: int = 0
    grade: str = "F"
    tips: list = field(default_factory=list)


def _score_message(msg: str) -> ScoreBreakdown:
    s = ScoreBreakdown()
    tips = []
    msg = msg.strip()
    if not msg:
        return s

    # 1. Length (20 pts) — ideal 20–72 chars
    ln = len(msg)
    if 20 <= ln <= 72:
        s.length_score = 20
    elif ln < 10:
        s.length_score = 0
        tips.append("Message too short — be more descriptive (aim for 20–72 chars)")
    elif ln < 20:
        s.length_score = 10
        tips.append("Message a bit short — aim for 20–72 characters")
    elif ln <= 100:
        s.length_score = 12
        tips.append("Message slightly long — keep subject line under 72 chars")
    else:
        s.length_score = 5
        tips.append("Subject too long — use a short subject + body after a blank line")

    # 2. Imperative mood (25 pts) — first word is an imperative verb
    first_word = msg.split()[0].lower().rstrip(".:,")
    if first_word in IMPERATIVE_VERBS:
        s.imperative_score = 25
    elif first_word.endswith("ing") or first_word.endswith("ed"):
        s.imperative_score = 8
        tips.append(f'Use imperative mood — prefer "{first_word.rstrip("inged").capitalize()}…" over "{msg.split()[0]}"')
    else:
        s.imperative_score = 0
        tips.append('Start with an imperative verb: "Add", "Fix", "Remove", "Update"…')

    # 3. Issue / PR reference (15 pts)
    if re.search(r"(#\d+|closes?\s+#\d+|fixes?\s+#\d+|resolves?\s+#\d+)", msg, re.I):
        s.reference_score = 15
    else:
        s.reference_score = 0
        # Only suggest if it looks like a bug fix or feature
        if any(w in msg.lower() for w in ("fix", "bug", "issue", "close", "resolve")):
            tips.append("Link the related issue — e.g. 'Fix login crash (#42)'")

    # 4. Conventional Commits format (20 pts) — feat: / fix: / chore: etc.
    conv_match = re.match(r"^(\w+)(\(.+?\))?!?:", msg)
    if conv_match and conv_match.group(1).lower() in CONVENTIONAL_PREFIXES:
        s.conventional_score = 20
    else:
        s.conventional_score = 0
        tips.append("Consider Conventional Commits format: feat: / fix: / refactor: etc.")

    # 5. No trailing period (10 pts)
    if not msg.rstrip().endswith("."):
        s.no_period_score = 10
    else:
        s.no_period_score = 0
        tips.append("Don't end the subject line with a period")

    # 6. Capitalised first word (10 pts)
    if msg[0].isupper():
        s.capitalised_score = 10
    else:
        s.capitalised_score = 0
        tips.append("Capitalise the first word of the commit message")

    s.total = (s.length_score + s.imperative_score + s.reference_score +
               s.conventional_score + s.no_period_score + s.capitalised_score)

    # Grade
    if s.total >= 85:   s.grade = "A"
    elif s.total >= 70: s.grade = "B"
    elif s.total >= 55: s.grade = "C"
    elif s.total >= 40: s.grade = "D"
    else:               s.grade = "F"

    s.tips = tips
    return s


def score_commits(messages: list[str]) -> dict:
    """
    Score all commit messages and return aggregate stats.
    Returns a dict with grade, avg_score, breakdown averages, top_tips.
    """
    if not messages:
        return {
            "grade": "N/A", "avg_score": 0,
            "length_avg": 0, "imperative_avg": 0,
            "reference_avg": 0, "conventional_avg": 0,
            "no_period_avg": 0, "capitalised_avg": 0,
            "top_tips": [], "sample_scores": [],
        }

    scores = [_score_message(m) for m in messages]

    def _avg(attr):
        return round(sum(getattr(s, attr) for s in scores) / len(scores), 1)

    avg_total = round(sum(s.total for s in scores) / len(scores), 1)

    if avg_total >= 85:   overall_grade = "A"
    elif avg_total >= 70: overall_grade = "B"
    elif avg_total >= 55: overall_grade = "C"
    elif avg_total >= 40: overall_grade = "D"
    else:                 overall_grade = "F"

    # Most common tips (top 3)
    from collections import Counter
    all_tips = [tip for s in scores for tip in s.tips]
    top_tips = [tip for tip, _ in Counter(all_tips).most_common(3)]

    # Sample: worst 3 and best 3 messages by score
    sorted_scores = sorted(zip(messages, scores), key=lambda x: x[1].total)
    worst = [(m, s.total, s.grade) for m, s in sorted_scores[:3]]
    best  = [(m, s.total, s.grade) for m, s in sorted_scores[-3:][::-1]]

    return {
        "grade": overall_grade,
        "avg_score": avg_total,
        "length_avg": _avg("length_score"),
        "imperative_avg": _avg("imperative_score"),
        "reference_avg": _avg("reference_score"),
        "conventional_avg": _avg("conventional_score"),
        "no_period_avg": _avg("no_period_score"),
        "capitalised_avg": _avg("capitalised_score"),
        "top_tips": top_tips,
        "worst_examples": worst,
        "best_examples": best,
        "total_scored": len(scores),
    }
