"""
Renders dark-themed Instagram post cards (single image or carousel) with
Pillow. No external design tool needed — everything is drawn from text.
"""
import os
import time

from PIL import Image, ImageDraw, ImageFont

import config

W, H = 1080, 1350
PAD = 90

BG = (11, 14, 20)
ACCENT = (124, 92, 255)      # purple
ACCENT_2 = (0, 217, 255)     # cyan (used on the CTA slide)
WHITE = (245, 245, 247)
MUTED = (156, 163, 175)


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = os.path.join(config.FONT_DIR, name)
    return ImageFont.truetype(path, size)


F_EYEBROW = lambda: _font("Poppins-SemiBold.ttf", 30)
F_HEADING_BIG = lambda: _font("Poppins-Bold.ttf", 76)
F_HEADING = lambda: _font("Poppins-Bold.ttf", 58)
F_BODY = lambda: _font("Poppins-Regular.ttf", 38)
F_FOOTER = lambda: _font("Poppins-Medium.ttf", 30)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list:
    words = text.split()
    lines, current = [], ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _draw_multiline(draw, lines, font, x, y, fill, line_gap=1.3):
    line_height = font.size * line_gap
    for i, line in enumerate(lines):
        draw.text((x, y + i * line_height), line, font=font, fill=fill)
    return y + len(lines) * line_height


def _footer(draw, handle: str, index: int, total: int, accent=ACCENT):
    y = H - PAD - 10
    draw.text((PAD, y), handle, font=F_FOOTER(), fill=MUTED)

    if total > 1:
        # dot page-indicator, right aligned
        dot_r, gap = 7, 22
        total_w = total * gap
        start_x = W - PAD - total_w
        for i in range(total):
            cx = start_x + i * gap
            cy = y + 14
            if i == index:
                draw.ellipse((cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r), fill=accent)
            else:
                draw.ellipse((cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r), outline=MUTED, width=2)


def _accent_bar(draw, x, y, w=64, h=8, color=ACCENT):
    draw.rounded_rectangle((x, y, x + w, y + h), radius=4, fill=color)


def render_slide(
    heading: str,
    body: str = "",
    eyebrow: str = "",
    index: int = 0,
    total: int = 1,
    handle: str = "@your.handle",
    big: bool = False,
    accent=ACCENT,
) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    max_w = W - 2 * PAD

    top_y = PAD + 20
    if eyebrow:
        top_y += 60  # room for eyebrow label, drawn later at a fixed top position
    footer_top = H - PAD - 60

    # --- measure heading + body block so it can be vertically centered ---
    heading_font = F_HEADING_BIG() if big else F_HEADING()
    heading_lines = _wrap(draw, heading, heading_font, max_w)
    heading_h = len(heading_lines) * heading_font.size * 1.15

    body_lines = _wrap(draw, body, F_BODY(), max_w) if body else []
    body_h = len(body_lines) * F_BODY().size * 1.4 if body_lines else 0

    block_h = heading_h + (30 + body_h if body_lines else 0)
    available_h = footer_top - top_y
    y = top_y + max((available_h - block_h) / 2, 0)

    # --- draw eyebrow + accent bar at a fixed spot near the top ---
    if eyebrow:
        draw.text((PAD, PAD + 20), eyebrow.upper(), font=F_EYEBROW(), fill=accent)
    _accent_bar(draw, PAD, PAD + 78, color=accent)

    # --- draw the (vertically centered) heading + body ---
    y = _draw_multiline(draw, heading_lines, heading_font, PAD, y, WHITE, line_gap=1.15)
    if body_lines:
        _draw_multiline(draw, body_lines, F_BODY(), PAD, y + 30, MUTED, line_gap=1.4)

    _footer(draw, handle, index, total, accent=accent)
    return img


def render_post(content: dict, handle: str) -> list:
    """
    Renders the full post (1 image for 'single', N+2 images for 'carousel')
    and returns a list of saved file paths, in posting order.
    """
    ts = int(time.time())
    paths = []

    if content["format"] == "single":
        slide = content["slides"][0]
        img = render_slide(
            heading=content["title"],
            body=slide.get("body", ""),
            eyebrow=slide.get("heading", "ML/AI EXPLAINED"),
            index=0,
            total=1,
            handle=handle,
            big=True,
        )
        path = os.path.join(config.OUTPUT_DIR, f"{ts}_single.png")
        img.save(path)
        paths.append(path)
        return paths

    # carousel: cover + content slides + CTA
    slides_data = content["slides"]
    total = len(slides_data) + 2

    cover = render_slide(
        heading=content["title"],
        body="Swipe to learn the full breakdown →",
        eyebrow="ML/AI EXPLAINED",
        index=0,
        total=total,
        handle=handle,
        big=True,
    )
    cover_path = os.path.join(config.OUTPUT_DIR, f"{ts}_00_cover.png")
    cover.save(cover_path)
    paths.append(cover_path)

    for i, slide in enumerate(slides_data, start=1):
        img = render_slide(
            heading=slide["heading"],
            body=slide.get("body", ""),
            eyebrow=f"STEP {i} / {len(slides_data)}",
            index=i,
            total=total,
            handle=handle,
        )
        path = os.path.join(config.OUTPUT_DIR, f"{ts}_{i:02d}.png")
        img.save(path)
        paths.append(path)

    cta = render_slide(
        heading="Follow for more ML/AI breakdowns",
        body="One concept at a time — clear, practical, no fluff.",
        eyebrow="THAT'S A WRAP",
        index=total - 1,
        total=total,
        handle=handle,
        accent=ACCENT_2,
    )
    cta_path = os.path.join(config.OUTPUT_DIR, f"{ts}_{len(slides_data)+1:02d}_cta.png")
    cta.save(cta_path)
    paths.append(cta_path)

    return paths
