"""
Renders hybrid Instagram post cards using Pillow.
- Cover slides: Uses Hugging Face free Inference API for AI background art + gradient overlay.
- Inner slides: Uses solid dark background + Mermaid.js technical diagrams via mermaid.ink.
"""
import os
import time
import base64
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

# Hugging Face Setup
HF_API_KEY = os.getenv("HF_API_KEY")
HF_API_URL = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = os.path.join(config.FONT_DIR, name)
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


F_EYEBROW = lambda: _font("Poppins-SemiBold.ttf", 30)
F_HEADING_BIG = lambda: _font("Poppins-Bold.ttf", 76)
F_HEADING = lambda: _font("Poppins-Bold.ttf", 58)
F_BODY = lambda: _font("Poppins-Regular.ttf", 38)
F_FOOTER = lambda: _font("Poppins-Medium.ttf", 30)


# --- AI ART & DIAGRAM FETCHERS ---

def generate_ai_background(prompt: str) -> Image.Image:
    """Fetches an AI-generated image from Hugging Face for the cover slide."""
    if not HF_API_KEY:
        print("Warning: No HF_API_KEY found. Falling back to solid background.")
        return Image.new("RGB", (W, H), BG)
        
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    payload = {"inputs": f"Abstract highly detailed glowing 3D render representing {prompt}, dark futuristic tech aesthetic, high quality"}
    
    try:
        response = requests.post(HF_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content)).convert("RGB")
        img = img.resize((int(H * (img.width / img.height)), H), Image.Resampling.LANCZOS)
        left = (img.width - W) / 2
        return img.crop((left, 0, left + W, H))
    except Exception as e:
        print(f"Failed to generate AI image: {e}")
        return Image.new("RGB", (W, H), BG)


def apply_gradient_overlay(base_img: Image.Image) -> Image.Image:
    """Applies a dark gradient to the bottom 70% of the cover image so text is readable."""
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for y in range(H):
        alpha = int(max(0, min(240, (y - (H * 0.2)) / (H * 0.8) * 255)))
        draw.line([(0, y), (W, y)], fill=(11, 14, 20, alpha))
    return Image.alpha_composite(base_img.convert("RGBA"), overlay).convert("RGB")


def fetch_mermaid_diagram(mermaid_code: str) -> Image.Image:
    """Renders Mermaid syntax into a transparent PNG via mermaid.ink API."""
    try:
        encoded = base64.b64encode(mermaid_code.encode('utf-8')).decode('utf-8')
        url = f"https://mermaid.ink/img/{encoded}?bgColor=0B0E14&theme=dark"
        
        response = requests.get(url)
        response.raise_for_status()
        return Image.open(BytesIO(response.content)).convert("RGBA")
    except Exception as e:
        print(f"Failed to render diagram: {e}")
        return None


# --- LAYOUT HELPERS ---

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
        start_x = W - PAD - (total * gap)
        for i in range(total):
            cx = start_x + i * gap
            cy = y + 14
            if i == index:
                draw.ellipse((cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r), fill=accent)
            else:
                draw.ellipse((cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r), outline=MUTED, width=2)


# --- CORE RENDERING ---

def render_slide(
    heading: str,
    body: str = "",
    eyebrow: str = "",
    index: int = 0,
    total: int = 1,
    handle: str = "@your.handle",
    big: bool = False,
    accent=ACCENT,
    diagram_code: str = None,
    topic_prompt: str = "AI Technology",
    is_cover: bool = False
) -> Image.Image:
    
    # 1. Background Setup
    if is_cover:
        bg = generate_ai_background(topic_prompt)
        img = apply_gradient_overlay(bg)
    else:
        img = Image.new("RGB", (W, H), BG)
        
    draw = ImageDraw.Draw(img)
    max_w = W - 2 * PAD

    # 2. Layout Measurements
    top_y = PAD + 20
    if eyebrow:
        top_y += 100

    heading_font = F_HEADING_BIG() if big else F_HEADING()
    heading_lines = _wrap(draw, heading, heading_font, max_w)
    heading_h = len(heading_lines) * heading_font.size * 1.15

    diagram_img = None
    diagram_h = 0
    if diagram_code and not is_cover:
        diagram_img = fetch_mermaid_diagram(diagram_code)
        if diagram_img:
            target_w = max_w
            scale = target_w / diagram_img.width
            target_h = int(diagram_img.height * scale)
            
            # Limit diagram height to 40% of canvas
            max_diagram_h = int(H * 0.4)
            if target_h > max_diagram_h:
                target_h = max_diagram_h
                target_w = int(diagram_img.width * (max_diagram_h / diagram_img.height))
                
            diagram_img = diagram_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
            diagram_h = target_h + 40

    body_lines = _wrap(draw, body, F_BODY(), max_w) if body else []
    body_h = len(body_lines) * F_BODY().size * 1.4 if body_lines else 0

    # 3. Placement (Cover slides push text down over the gradient; Inner slides flow from top)
    if is_cover:
        block_h = heading_h + (30 + body_h if body_lines else 0)
        footer_top = H - PAD - 60
        available_h = footer_top - top_y
        y_cursor = top_y + available_h - block_h
    else:
        y_cursor = top_y

    # 4. Drawing Elements
    if eyebrow:
        eyebrow_y = PAD + 20 if not is_cover else y_cursor - 100
        draw.text((PAD, eyebrow_y), eyebrow.upper(), font=F_EYEBROW(), fill=accent)
        draw.rounded_rectangle((PAD, eyebrow_y + 58, PAD + 64, eyebrow_y + 66), radius=4, fill=accent)

    y_cursor = _draw_multiline(draw, heading_lines, heading_font, PAD, y_cursor, WHITE, line_gap=1.15)
    
    if diagram_img:
        x_offset = int((W - diagram_img.width) / 2)
        img.paste(diagram_img, (x_offset, int(y_cursor + 40)), diagram_img)
        y_cursor += diagram_h + 40

    if body_lines:
        _draw_multiline(draw, body_lines, F_BODY(), PAD, y_cursor + (40 if not is_cover else 30), MUTED, line_gap=1.4)

    _footer(draw, handle, index, total, accent=accent)
    return img


def render_post(content: dict, handle: str) -> list:
    ts = int(time.time())
    paths = []
    topic = content.get("title", "Artificial Intelligence")

    # Single format post
    if content["format"] == "single":
        slide = content["slides"][0]
        img = render_slide(
            heading=content["title"],
            body=slide.get("body", ""),
            eyebrow=slide.get("heading", "ML/AI EXPLAINED"),
            index=0, total=1, handle=handle, big=True,
            topic_prompt=topic, is_cover=True
        )
        path = os.path.join(config.OUTPUT_DIR, f"{ts}_single.png")
        img.save(path)
        paths.append(path)
        return paths

    # Carousel format post
    slides_data = content["slides"]
    total = len(slides_data) + 2

    # 1. Cover Slide (Uses AI Image)
    cover = render_slide(
        heading=content["title"],
        body="Swipe to learn the full breakdown →",
        eyebrow="ML/AI EXPLAINED",
        index=0, total=total, handle=handle, big=True,
        topic_prompt=topic, is_cover=True
    )
    cover_path = os.path.join(config.OUTPUT_DIR, f"{ts}_00_cover.png")
    cover.save(cover_path)
    paths.append(cover_path)

    # 2. Content Slides (Uses Solid BG + Diagrams)
    for i, slide in enumerate(slides_data, start=1):
        img = render_slide(
            heading=slide["heading"],
            body=slide.get("body", ""),
            eyebrow=f"STEP {i} / {len(slides_data)}",
            index=i, total=total, handle=handle,
            diagram_code=slide.get("diagram"),
            is_cover=False
        )
        path = os.path.join(config.OUTPUT_DIR, f"{ts}_{i:02d}.png")
        img.save(path)
        paths.append(path)

    # 3. CTA Slide (Solid BG)
    cta = render_slide(
        heading="Follow for more ML/AI breakdowns",
        body="One concept at a time — clear, practical, no fluff.",
        eyebrow="THAT'S A WRAP",
        index=total - 1, total=total, handle=handle, accent=ACCENT_2,
        is_cover=False
    )
    cta_path = os.path.join(config.OUTPUT_DIR, f"{ts}_{len(slides_data)+1:02d}_cta.png")
    cta.save(cta_path)
    paths.append(cta_path)

    return paths