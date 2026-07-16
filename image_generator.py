"""
Renders visually rich Instagram post cards using Pillow.
Integrates Hugging Face's free Inference API for AI-generated background art,
applying a gradient overlay to keep typography readable.
"""
import os
import time
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

import config

W, H = 1080, 1350
PAD = 90

# Core Brand Colors
BG = (11, 14, 20)
ACCENT = (124, 92, 255)      # Purple
ACCENT_2 = (0, 217, 255)     # Cyan
WHITE = (245, 245, 247)
MUTED = (156, 163, 175)

# Hugging Face Setup (Add HF_API_KEY to your .env)
HF_API_KEY = os.getenv("HF_API_KEY")
HF_API_URL = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = os.path.join(config.FONT_DIR, name)
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        # Fallback if custom fonts aren't found
        return ImageFont.load_default()


F_EYEBROW = lambda: _font("Poppins-SemiBold.ttf", 30)
F_HEADING_BIG = lambda: _font("Poppins-Bold.ttf", 76)
F_HEADING = lambda: _font("Poppins-Bold.ttf", 58)
F_BODY = lambda: _font("Poppins-Regular.ttf", 38)
F_FOOTER = lambda: _font("Poppins-Medium.ttf", 30)


def generate_ai_background(prompt: str) -> Image.Image:
    """Fetches an AI-generated image from Hugging Face to use as a background."""
    if not HF_API_KEY:
        print("Warning: No HF_API_KEY found. Falling back to solid background.")
        return Image.new("RGB", (W, H), BG)
        
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    payload = {"inputs": f"Abstract highly detailed glowing 3D render representing {prompt}, dark futuristic aesthetic, high quality"}
    
    try:
        response = requests.post(HF_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content)).convert("RGB")
        # Resize and crop to fill the 1080x1350 canvas
        img = img.resize((int(H * (img.width / img.height)), H), Image.Resampling.LANCZOS)
        left = (img.width - W) / 2
        return img.crop((left, 0, left + W, H))
    except Exception as e:
        print(f"Failed to generate image: {e}")
        return Image.new("RGB", (W, H), BG)


def apply_gradient_overlay(base_img: Image.Image) -> Image.Image:
    """Applies a dark gradient to the bottom 70% of the image so text is readable."""
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    for y in range(H):
        # Start fading in from top (0 alpha) to dark at the bottom (240 alpha)
        alpha = int(max(0, min(240, (y - (H * 0.2)) / (H * 0.8) * 255)))
        draw.line([(0, y), (W, y)], fill=(11, 14, 20, alpha))
        
    return Image.alpha_composite(base_img.convert("RGBA"), overlay).convert("RGB")


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


def render_slide(
    heading: str,
    body: str = "",
    eyebrow: str = "",
    index: int = 0,
    total: int = 1,
    handle: str = "@your.handle",
    big: bool = False,
    accent=ACCENT,
    topic_prompt: str = "Machine Learning data flow",
    is_cover: bool = False
) -> Image.Image:
    
    # 1. Generate or set background
    if is_cover or index == 0:
        # Fetch an AI image for the cover to grab attention
        bg = generate_ai_background(topic_prompt)
        img = apply_gradient_overlay(bg)
    else:
        # Keep inside slides clean and dark to focus on information
        img = Image.new("RGB", (W, H), BG)
        
    draw = ImageDraw.Draw(img)
    max_w = W - 2 * PAD

    top_y = PAD + 20
    if eyebrow:
        top_y += 60  
    footer_top = H - PAD - 60

    heading_font = F_HEADING_BIG() if big else F_HEADING()
    heading_lines = _wrap(draw, heading, heading_font, max_w)
    heading_h = len(heading_lines) * heading_font.size * 1.15

    body_lines = _wrap(draw, body, F_BODY(), max_w) if body else []
    body_h = len(body_lines) * F_BODY().size * 1.4 if body_lines else 0

    block_h = heading_h + (30 + body_h if body_lines else 0)
    available_h = footer_top - top_y
    
    # Push text lower if it's a cover to show off the art, otherwise center it
    y = (top_y + available_h - block_h) if is_cover else (top_y + max((available_h - block_h) / 2, 0))

    if eyebrow:
        draw.text((PAD, PAD + 20), eyebrow.upper(), font=F_EYEBROW(), fill=accent)
        draw.rounded_rectangle((PAD, PAD + 78, PAD + 64, PAD + 86), radius=4, fill=accent)

    y = _draw_multiline(draw, heading_lines, heading_font, PAD, y, WHITE, line_gap=1.15)
    if body_lines:
        _draw_multiline(draw, body_lines, F_BODY(), PAD, y + 30, MUTED, line_gap=1.4)

    _footer(draw, handle, index, total, accent=accent)
    return img


def render_post(content: dict, handle: str) -> list:
    ts = int(time.time())
    paths = []
    
    # Pass the post title to the image generator to get a relevant background
    topic = content.get("title", "Artificial Intelligence")

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
            topic_prompt=topic,
            is_cover=True
        )
        path = os.path.join(config.OUTPUT_DIR, f"{ts}_single.png")
        img.save(path)
        paths.append(path)
        return paths

    slides_data = content["slides"]
    total = len(slides_data) + 2

    # Cover Slide
    cover = render_slide(
        heading=content["title"],
        body="Swipe to learn the full breakdown →",
        eyebrow="ML/AI EXPLAINED",
        index=0,
        total=total,
        handle=handle,
        big=True,
        topic_prompt=topic,
        is_cover=True
    )
    cover_path = os.path.join(config.OUTPUT_DIR, f"{ts}_00_cover.png")
    cover.save(cover_path)
    paths.append(cover_path)

    # Content Slides
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

    # CTA Slide
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