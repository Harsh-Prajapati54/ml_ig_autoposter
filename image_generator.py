"""
Renders Instagram post cards using Pillow.
Aesthetic: Handwritten engineering study notes on grid paper.
"""
import os
import time
from PIL import Image, ImageDraw, ImageFont

import config

W, H = 1080, 1350
MARGIN_LEFT = 140  # Space for the red margin line
PAD_RIGHT = 80

# Notebook Colors
PAPER_BG = (252, 252, 249)       # Warm off-white
GRID_LINE = (225, 230, 235)      # Light blue/grey
MARGIN_LINE = (255, 140, 140)    # Faded red
INK_BLACK = (30, 32, 35)         # Not pure black
INK_BLUE = (35, 75, 160)         # Ballpoint pen blue
INK_RED = (180, 40, 40)          # Red pen for highlights

def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = os.path.join(config.FONT_DIR, name)
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        print(f"Warning: Could not find {name}. Falling back to default.")
        return ImageFont.load_default()

# UPDATE THESE TO MATCH YOUR DOWNLOADED HANDWRITING FONT
F_EYEBROW = lambda: _font("Kalam-Bold.ttf", 35)
F_HEADING_BIG = lambda: _font("Kalam-Bold.ttf", 85)
F_HEADING = lambda: _font("Kalam-Bold.ttf", 65)
F_BODY = lambda: _font("Kalam-Regular.ttf", 42)
F_FOOTER = lambda: _font("Kalam-Regular.ttf", 30)


def draw_notebook_background(draw: ImageDraw.ImageDraw):
    """Draws the grid paper pattern on the canvas."""
    # Draw horizontal grid lines
    line_spacing = 60
    for y in range(line_spacing, H, line_spacing):
        draw.line([(0, y), (W, y)], fill=GRID_LINE, width=2)
        
    # Draw vertical double red margin
    draw.line([(MARGIN_LEFT - 10, 0), (MARGIN_LEFT - 10, H)], fill=MARGIN_LINE, width=2)
    draw.line([(MARGIN_LEFT, 0), (MARGIN_LEFT, H)], fill=MARGIN_LINE, width=2)


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


def _draw_multiline(draw, lines, font, x, y, fill, line_gap=1.5):
    line_height = font.size * line_gap
    for i, line in enumerate(lines):
        draw.text((x, y + i * line_height), line, font=font, fill=fill)
    return y + len(lines) * line_height


def _footer(draw, handle: str, index: int, total: int):
    y = H - 60
    draw.text((MARGIN_LEFT + 20, y), handle, font=F_FOOTER(), fill=INK_BLACK)
    
    if total > 1:
        text = f"Page {index + 1}/{total}"
        draw.text((W - PAD_RIGHT - 120, y), text, font=F_FOOTER(), fill=INK_BLACK)


def render_slide(
    heading: str,
    body: str = "",
    eyebrow: str = "",
    index: int = 0,
    total: int = 1,
    handle: str = "@your.handle",
    big: bool = False
) -> Image.Image:
    
    img = Image.new("RGB", (W, H), PAPER_BG)
    draw = ImageDraw.Draw(img)
    draw_notebook_background(draw)
    
    max_w = W - MARGIN_LEFT - PAD_RIGHT - 30
    y_cursor = 100

    if eyebrow:
        draw.text((MARGIN_LEFT + 20, y_cursor), f"[{eyebrow.upper()}]", font=F_EYEBROW(), fill=INK_RED)
        y_cursor += 70

    heading_font = F_HEADING_BIG() if big else F_HEADING()
    heading_lines = _wrap(draw, heading, heading_font, max_w)
    
    # Write the heading in Black Ink
    y_cursor = _draw_multiline(draw, heading_lines, heading_font, MARGIN_LEFT + 20, y_cursor, INK_BLACK, line_gap=1.2)
    
    # Write the body text in Blue Ink (like a pen)
    if body:
        # Increase line gap so it roughly aligns with the grid paper lines
        body_lines = _wrap(draw, body, F_BODY(), max_w)
        _draw_multiline(draw, body_lines, F_BODY(), MARGIN_LEFT + 20, y_cursor + 40, INK_BLUE, line_gap=1.4)

    _footer(draw, handle, index, total)
    return img


def render_post(content: dict, handle: str) -> list:
    ts = int(time.time())
    paths = []
    slides_data = content["slides"]
    total = len(slides_data) + 2

    # 1. Cover Slide
    cover = render_slide(
        heading=content["title"],
        body="Swipe for complete notes →",
        eyebrow="ML/AI STUDY NOTES",
        index=0, total=total, handle=handle, big=True
    )
    cover_path = os.path.join(config.OUTPUT_DIR, f"{ts}_00_cover.png")
    cover.save(cover_path)
    paths.append(cover_path)

    # 2. Content Slides
    for i, slide in enumerate(slides_data, start=1):
        # We pass the raw string; Pillow will handle newlines naturally if formatted right, 
        # or we wrap it via our _wrap function.
        img = render_slide(
            heading=slide["heading"],
            body=slide.get("body", "").replace("- ", "\n• "), # Convert hyphens to bullet points
            eyebrow=f"Note {i}",
            index=i, total=total, handle=handle
        )
        path = os.path.join(config.OUTPUT_DIR, f"{ts}_{i:02d}.png")
        img.save(path)
        paths.append(path)

    # 3. CTA Slide
    cta = render_slide(
        heading="Save these notes for later!",
        body="Follow for more daily ML/AI engineering breakdowns.",
        eyebrow="END OF NOTES",
        index=total - 1, total=total, handle=handle
    )
    cta_path = os.path.join(config.OUTPUT_DIR, f"{ts}_{len(slides_data)+1:02d}_cta.png")
    cta.save(cta_path)
    paths.append(cta_path)

    return paths