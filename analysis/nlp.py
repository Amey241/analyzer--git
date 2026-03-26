"""
analysis/nlp.py
NLP analysis on commit messages:
  - TextBlob sentiment (polarity)
  - LDA topic modeling → dominant topic label
"""

import re
import warnings
from textblob import TextBlob
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation
from config import LDA_N_TOPICS

warnings.filterwarnings("ignore")

# Word lists that anchor each topic label heuristically
TOPIC_ANCHORS = {
    "bug":     {"fix", "bug", "error", "crash", "null", "issue", "broken", "fail", "patch", "revert"},
    "feature": {"add", "new", "feature", "implement", "create", "introduce", "support", "enable"},
    "refactor":{"refactor", "cleanup", "clean", "rename", "move", "extract", "restructure", "reorganize"},
    "docs":    {"doc", "docs", "readme", "comment", "typo", "update", "changelog", "license"},
}


def _clean(msg: str) -> str:
    msg = re.sub(r"https?://\S+", "", msg)           # strip URLs
    msg = re.sub(r"[^a-zA-Z\s]", " ", msg).lower()  # keep letters only
    msg = re.sub(r"\s+", " ", msg).strip()
    return msg


def sentiment_analysis(messages: list[str]) -> dict:
    """Return avg polarity and an emoji mood label."""
    if not messages:
        return {"avg_polarity": 0.0, "mood": "Neutral 😐", "polarity_list": []}

    polarities = [TextBlob(m).sentiment.polarity for m in messages]
    avg = sum(polarities) / len(polarities)

    if avg > 0.15:
        mood = "Upbeat 😄"
    elif avg < -0.10:
        mood = "Frustrated 😤"
    else:
        mood = "Neutral 😐"

    return {"avg_polarity": round(avg, 4), "mood": mood, "polarity_list": polarities}


def _label_topic(topic_word_weights: list, feature_names: list[str]) -> str:
    """Score a topic vector against TOPIC_ANCHORS and return best label."""
    top_indices = topic_word_weights.argsort()[-20:][::-1]
    top_words = {feature_names[i] for i in top_indices}

    scores = {label: len(top_words & anchors) for label, anchors in TOPIC_ANCHORS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "other"


def lda_topics(messages: list[str], n_topics: int = LDA_N_TOPICS) -> dict:
    """
    Run LDA on commit messages.
    Returns:
        topics: list of {label, top_words} dicts
        dominant_topic: label of the most common topic
        doc_topics: per-message dominant topic label
    """
    cleaned = [_clean(m) for m in messages]
    cleaned = [m for m in cleaned if len(m.split()) >= 2]

    if len(cleaned) < 10:
        return {
            "topics": [],
            "dominant_topic": "unknown",
            "doc_topics": [],
            "topic_counts": {},
        }

    vectorizer = CountVectorizer(stop_words="english", min_df=2, max_features=500)
    try:
        X = vectorizer.fit_transform(cleaned)
    except ValueError:
        return {"topics": [], "dominant_topic": "unknown", "doc_topics": [], "topic_counts": {}}

    actual_n = min(n_topics, X.shape[1])
    lda = LatentDirichletAllocation(n_components=actual_n, random_state=42, max_iter=20)
    lda.fit(X)

    feature_names = vectorizer.get_feature_names_out().tolist()

    topics = []
    for i, component in enumerate(lda.components_):
        top_word_idxs = component.argsort()[-8:][::-1]
        top_words = [feature_names[j] for j in top_word_idxs]
        label = _label_topic(component, feature_names)
        topics.append({"index": i, "label": label, "top_words": top_words})

    # Per-document dominant topic
    doc_topic_matrix = lda.transform(X)
    doc_topic_indices = doc_topic_matrix.argmax(axis=1)
    doc_topics = [topics[i]["label"] for i in doc_topic_indices]

    # Overall dominant topic
    from collections import Counter
    counts = Counter(doc_topics)
    dominant = counts.most_common(1)[0][0]

    return {
        "topics": topics,
        "dominant_topic": dominant,
        "doc_topics": doc_topics,
        "topic_counts": dict(counts),
    }
