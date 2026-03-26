"""
analysis/wordcloud_gen.py
Generate a styled wordcloud image from commit messages.
"""

import os
import re
from wordcloud import WordCloud, STOPWORDS
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")

EXTRA_STOPWORDS = {
    "merge", "pull", "request", "branch", "commit", "update", "change",
    "changes", "the", "and", "for", "this", "that", "with", "from",
    "into", "also", "added", "adds", "fix", "fixes", "fixed", "use",
    "using", "used", "make", "making", "made",
}


def _purple_color_func(word, font_size, position, orientation, random_state=None, **kwargs):
    """Custom colour function: purple → pink gradient."""
    hues = [270, 280, 290, 300, 310, 330]  # purple to pink
    h = hues[random_state.randint(0, len(hues) - 1)] if random_state else 280
    s = random_state.randint(60, 100) if random_state else 80
    l = random_state.randint(55, 80) if random_state else 65
    return f"hsl({h}, {s}%, {l}%)"


def generate_wordcloud(messages: list[str], username: str = "user") -> str:
    """
    Generate wordcloud PNG, save to assets/, return absolute path.
    Returns empty string if there are too few messages.
    """
    if len(messages) < 5:
        return ""

    os.makedirs(ASSETS_DIR, exist_ok=True)
    out_path = os.path.join(ASSETS_DIR, f"wordcloud_{username}.png")

    # Clean and join
    text = " ".join(messages)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[^a-zA-Z\s]", " ", text)

    stopwords = STOPWORDS | EXTRA_STOPWORDS

    wc = WordCloud(
        width=900,
        height=450,
        background_color=None,
        mode="RGBA",
        stopwords=stopwords,
        max_words=150,
        min_font_size=10,
        font_path=None,           # uses system default
        color_func=_purple_color_func,
        prefer_horizontal=0.85,
        collocations=False,
    ).generate(text)

    fig, ax = plt.subplots(figsize=(9, 4.5), facecolor="none")
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    plt.tight_layout(pad=0)
    plt.savefig(out_path, dpi=120, bbox_inches="tight",
                transparent=True, facecolor="none")
    plt.close(fig)

    return out_path
