"""
analysis/card_generator.py
Generate a 1200x630px "GitHub Wrapped" shareable card using Pillow.
"""

import io
import os
import requests
from PIL import Image, ImageDraw, ImageFont
from config import ACCENT_COLORS

CARD_W, CARD_H = 1200, 630
ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")


# ── Colour palette ─────────────────────────────────────────────────────────────
BG_TOP    = (15,  12,  41)   # #0f0c29
BG_BOT    = (36,  36,  62)   # #24243e
PURPLE    = (108, 99, 255)   # #6C63FF
PINK      = (236, 72, 153)   # #EC4899
GOLD      = (249, 168, 38)   # #F9A826
WHITE     = (226, 232, 240)  # #E2E8F0
MUTED     = (148, 163, 184)  # #94A3B8
DARK_CARD = (255, 255, 255, 15)  # RGBA glass


def _gradient_bg(draw: ImageDraw.Draw, w: int, h: int):
    """Vertical gradient from BG_TOP to BG_BOT."""
    for y in range(h):
        t = y / h
        r = int(BG_TOP[0] + t * (BG_BOT[0] - BG_TOP[0]))
        g = int(BG_TOP[1] + t * (BG_BOT[1] - BG_TOP[1]))
        b = int(BG_TOP[2] + t * (BG_BOT[2] - BG_TOP[2]))
        draw.line([(0, y), (w, y)], fill=(r, g, b))


def _get_font(size: int):
    """Return a PIL font — falls back to default if no TTF available."""
    try:
        # Try common system fonts
        for name in ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf",
                     "C:/Windows/Fonts/arial.ttf",
                     "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
            if os.path.exists(name):
                return ImageFont.truetype(name, size)
    except Exception:
        pass
    return ImageFont.load_default()


def _download_avatar(url: str, size: int = 120) -> Image.Image | None:
    try:
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        img = Image.open(io.BytesIO(r.content)).convert("RGBA")
        img = img.resize((size, size), Image.LANCZOS)
        # Circular crop
        mask = Image.new("L", (size, size), 0)
        from PIL import ImageDraw as _D
        _D.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
        img.putalpha(mask)
        return img
    except Exception:
        return None


def _pill(draw: ImageDraw.Draw, x: int, y: int, text: str,
          bg=(108, 99, 255, 80), font=None, text_color=WHITE):
    """Rounded rectangle pill label."""
    if font is None:
        font = _get_font(22)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad_x, pad_y = 18, 8
    rx, ry = x, y
    rw, rh = tw + pad_x * 2, th + pad_y * 2
    # Draw rounded pill on a temp layer
    layer = Image.new("RGBA", (rw + 2, rh + 2), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.rounded_rectangle([0, 0, rw, rh], radius=rh // 2, fill=bg)
    draw._image.alpha_composite(layer, (rx, ry))
    draw.text((rx + pad_x, ry + pad_y), text, font=font, fill=text_color)
    return rw  # return width for chaining


def generate_card(profile: dict, badges: list[dict],
                  lang_df, sentiment: dict,
                  commits: list, username: str) -> bytes:
    """
    Return PNG bytes of the 1200×630 shareable card.
    """
    img = Image.new("RGBA", (CARD_W, CARD_H), BG_TOP)
    draw = ImageDraw.Draw(img)

    # ── Background gradient ───────────────────────────────────────────────────
    _gradient_bg(draw, CARD_W, CARD_H)

    # ── Decorative circles (blurred glow) ─────────────────────────────────────
    glow = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((-100, -100, 450, 450), fill=(*PURPLE, 30))
    gd.ellipse((800, 300, 1400, 900), fill=(*PINK, 25))
    gd.ellipse((400, -80, 900, 350), fill=(67, 221, 230, 15))
    img.alpha_composite(glow)
    draw = ImageDraw.Draw(img)  # refresh after composite

    # ── Fonts ─────────────────────────────────────────────────────────────────
    f_big   = _get_font(60)
    f_med   = _get_font(36)
    f_small = _get_font(26)
    f_tiny  = _get_font(22)

    # ── Avatar ────────────────────────────────────────────────────────────────
    avatar = _download_avatar(profile.get("avatar_url", ""), size=130)
    ax, ay = 60, 60
    if avatar:
        # Purple ring
        ring = Image.new("RGBA", (138, 138), (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse((0, 0, 137, 137), fill=(*PURPLE, 200))
        img.alpha_composite(ring, (ax - 4, ay - 4))
        img.alpha_composite(avatar, (ax, ay))

    # ── Name & handle ─────────────────────────────────────────────────────────
    nx = ax + 150
    name = profile.get("name", username)[:28]
    draw.text((nx, ay + 10), name, font=f_big, fill=WHITE)
    draw.text((nx, ay + 75), f"@{username}", font=f_small, fill=(*MUTED, 255))

    # ── Divider ───────────────────────────────────────────────────────────────
    draw.line([(60, 210), (CARD_W - 60, 210)], fill=(*PURPLE, 60), width=1)

    # ── Stats row ─────────────────────────────────────────────────────────────
    stats = [
        ("💬", f"{len(commits):,}", "commits"),
        ("📁", str(profile.get("public_repos", 0)), "repos"),
        ("👥", str(profile.get("followers", 0)), "followers"),
    ]
    sx = 60
    for icon, val, label in stats:
        draw.text((sx, 230), icon, font=f_med, fill=WHITE)
        draw.text((sx + 45, 228), val, font=f_med, fill=WHITE)
        draw.text((sx + 45, 268), label, font=f_tiny, fill=(*MUTED, 255))
        sx += 230

    # ── Top language ──────────────────────────────────────────────────────────
    if not lang_df.empty:
        top_lang = lang_df.iloc[0]
        draw.text((800, 230), "Top Language", font=f_tiny, fill=(*MUTED, 255))
        draw.text((800, 258), top_lang["language"], font=f_med, fill=(*PURPLE, 255))
        draw.text((800, 298), f"{top_lang['pct']:.1f}% of code", font=f_tiny,
                  fill=(*MUTED, 255))

    # ── Horizontal divider ────────────────────────────────────────────────────
    draw.line([(60, 335), (CARD_W - 60, 335)], fill=(*PURPLE, 60), width=1)

    # ── Personality badges ────────────────────────────────────────────────────
    draw.text((60, 350), "Personality", font=f_small, fill=(*MUTED, 255))
    bx = 60
    for b in badges[:4]:
        text = b["badge"]
        bw = _pill(draw, bx, 385, text, bg=(*PURPLE, 80), font=f_tiny,
                   text_color=WHITE)
        bx += bw + 14

    # ── Sentiment ─────────────────────────────────────────────────────────────
    polarity = sentiment.get("avg_polarity", 0)
    mood     = sentiment.get("mood", "Neutral 😐")
    draw.text((60, 450), "Commit Mood", font=f_tiny, fill=(*MUTED, 255))
    draw.text((60, 478), mood, font=f_med, fill=WHITE)

    # Sentiment bar
    bar_x, bar_y, bar_w, bar_h = 60, 525, 500, 14
    draw.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h],
                            radius=7, fill=(255, 255, 255, 25))
    filled = int((polarity + 1) / 2 * bar_w)
    bar_color = (67, 221, 230) if polarity > 0.1 else \
                (255, 101, 132) if polarity < -0.05 else (249, 168, 38)
    if filled > 0:
        draw.rounded_rectangle([bar_x, bar_y, bar_x + filled, bar_y + bar_h],
                                radius=7, fill=(*bar_color, 220))

    # ── Branding ──────────────────────────────────────────────────────────────
    brand_text = "GitHub Profile Analyzer"
    draw.text((CARD_W - 60, CARD_H - 40), brand_text,
              font=f_tiny, fill=(*MUTED, 140), anchor="rm")

    # ── Watermark line ────────────────────────────────────────────────────────
    draw.line([(60, CARD_H - 55), (CARD_W - 60, CARD_H - 55)],
              fill=(*PURPLE, 40), width=1)

    # Convert to RGB for PNG (removes alpha for compatibility)
    out = img.convert("RGB")
    buf = io.BytesIO()
    out.save(buf, format="PNG", quality=95)
    return buf.getvalue()
