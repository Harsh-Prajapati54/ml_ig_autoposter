"""
Renders premium, ultra-modern dark-mode tech infographics for AI/ML concepts.
Features a clean dark background, rounded glassmorphism cards, syntax-friendly code blocks,
neon accent typography highlights, and automatic multi-slide pagination.
"""
import os
import time
import base64
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

import config

W, H = 1080, 1350
MARGIN_LEFT = 80  
PAD_RIGHT = 80
MAX_CONTENT_Y = H - 140  # Keep away from clean bottom footer

# Premium Dark Tech Palette
BG_COLOR = (11, 15, 25)          # Deep slate space background
CARD_BG = (22, 28, 45)           # Elevated card background
CARD_BORDER = (40, 50, 75)       # Subtle card strokes
TEXT_MAIN = (240, 245, 255)      # Clean crisp white
TEXT_MUTED = (140, 155, 185)     # Readable secondary gray
ACCENT_BLUE = (0, 210, 255)      # Neon blue for headers/highlights
ACCENT_PURPLE = (160, 90, 255)   # Neon violet for sub-elements/eyebrows

def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = os.path.join(config.FONT_DIR, name)
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        # Fallback to standard system sans-serif fonts if custom ones aren't present
        return ImageFont.load_default()

# Update your config.FONT_DIR to contain clean modern fonts like "Inter" or "PlusJakartaSans"
F_EYEBROW = lambda: _font("PlusJakartaSans-Bold.ttf", 26)
F_HEADING_BIG = lambda: _font("PlusJakartaSans-ExtraBold.ttf", 72)
F_HEADING = lambda: _font("PlusJakartaSans-Bold.ttf", 52)
F_BODY = lambda: _font("Inter-Medium.ttf", 36)
F_CODE = lambda: _font("JetBrainsMono-Regular.ttf", 32)
F_FOOTER = lambda: _font("Inter-SemiBold.ttf", 26)

def draw_background_grid(draw: ImageDraw.ImageDraw):
    """Draws a subtle, premium tech dot-grid pattern."""
    dot_spacing = 60
    for x in range(dot_spacing, W, dot_spacing):
        for y in range(dot_spacing, H, dot_spacing):
            draw.rectangle([x, y, x+2, y+2], fill=(30, 40, 60))

def fetch_mermaid_diagram(mermaid_code: str) -> Image.Image:
    try:
        encoded = base64.b64encode(mermaid_code.encode('utf-8')).decode('utf-8')
        # Using a dark theme setup for the diagram to match our dark template
        url = f"https://mermaid.ink/img/{encoded}?bgColor=!110f19"
        response = requests.get(url)
        response.raise_for_status()
        return Image.open(BytesIO(response.content)).convert("RGBA")
    except Exception as e:
        print(f"Failed to render diagram: {e}")
        return None

def sanitize_text(text: str) -> str:
    return text.encode('ascii', 'ignore').decode('ascii')

def _wrap_line(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list:
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

def _paginate_body_text(draw, raw_text, font, max_w):
    if not raw_text:
        return [[]]
        
    text = sanitize_text(raw_text)
    paragraphs = text.split('\n')
    line_height = font.size * 1.5
    
    pages = []
    current_page_lines = []
    available_height = MAX_CONTENT_Y - 340 
    current_y = 0

    for p in paragraphs:
        p = p.strip()
        if not p:
            if current_y + (line_height * 0.5) > available_height:
                pages.append(current_page_lines)
                current_page_lines = []
                available_height = MAX_CONTENT_Y - 200 
                current_y = 0
            current_page_lines.append(("", 0, False))
            current_y += line_height * 0.5
            continue
            
        is_bullet = p.startswith('-') or p.startswith('*')
        is_code = p.startswith('`') and p.endswith('`')
        
        display_text = p[1:].strip() if is_bullet else p
        if is_code:
            display_text = display_text.replace('`', '')
            
        indent = 45 if is_bullet else 15
        wrapped_lines = _wrap_line(draw, display_text, font, max_w - indent)
        
        for line in wrapped_lines:
            if current_y + line_height > available_height:
                pages.append(current_page_lines)
                current_page_lines = []
                available_height = MAX_CONTENT_Y - 200 
                current_y = 0
            
            current_page_lines.append((line, indent, is_code))
            current_y += line_height
            
        current_y += 12 

    if current_page_lines:
        pages.append(current_page_lines)
        
    return pages

def render_base_slide(heading: str, eyebrow: str, handle: str, big: bool = False):
    img = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)
    draw_background_grid(draw)
    
    max_w = W - MARGIN_LEFT - PAD_RIGHT
    y_cursor = 90

    if eyebrow:
        draw.text((MARGIN_LEFT, y_cursor), eyebrow.upper(), font=F_EYEBROW(), fill=ACCENT_PURPLE)
        y_cursor += 55

    heading_font = F_HEADING_BIG() if big else F_HEADING()
    heading_lines = _wrap_line(draw, sanitize_text(heading), heading_font, max_w)
    
    for line in heading_lines:
        draw.text((MARGIN_LEFT, y_cursor), line, font=heading_font, fill=TEXT_MAIN)
        y_cursor += heading_font.size * 1.25
        
    y_cursor += 40
    return img, draw, y_cursor, max_w

def draw_footer_and_progress(draw, handle, index, total):
    # Top progress bar tracker
    bar_y = 30
    bar_width = (W - 160) // total
    for i in range(total):
        x_start = 80 + (i * bar_width) + (i * 4)
        x_end = x_start + bar_width
        color = ACCENT_BLUE if i <= index else (40, 50, 70)
        draw.line([(x_start, bar_y), (x_end, bar_y)], fill=color, width=4)

    # Bottom footer details
    footer_y = H - 75
    draw.text((MARGIN_LEFT, footer_y), handle.lower(), font=F_FOOTER(), fill=TEXT_MUTED)
    if total > 1:
        draw.text((W - PAD_RIGHT - 100, footer_y), f"{index + 1}/{total}", font=F_FOOTER(), fill=ACCENT_BLUE)

def render_post(content: dict, handle: str) -> dict:
    ts = int(time.time())
    safe_title = "".join(c if c.isalnum() else "_" for c in content.get("title", "AI_Topic"))[:30].strip("_")
    folder_name = f"{ts}_{safe_title}"
    post_dir = os.path.join(config.OUTPUT_DIR, folder_name)
    os.makedirs(post_dir, exist_ok=True)

    raw_slides = content["slides"]
    processed_slides = []

    for i, slide in enumerate(raw_slides, start=1):
        heading = slide["heading"]
        body = slide.get("body", "")
        diagram_code = slide.get("diagram")
        
        dummy_img = Image.new("RGB", (W, H))
        dummy_draw = ImageDraw.Draw(dummy_img)
        body_pages = _paginate_body_text(dummy_draw, body, F_BODY(), W - MARGIN_LEFT - PAD_RIGHT - 40)
        
        for p_idx, page_lines in enumerate(body_pages):
            eyebrow_text = f"CORE CONCEPT {i}" if len(body_pages) == 1 else f"CONCEPT {i} • STEP {p_idx + 1}"
            processed_slides.append({
                "heading": heading if p_idx == 0 else f"{heading} (Cont.)",
                "eyebrow": eyebrow_text,
                "lines": page_lines,
                "diagram": diagram_code if p_idx == 0 else None
            })

    total_slides = len(processed_slides) + 2
    paths = []
    current_index = 0

    # 1. Cover Slide
    img, draw, y_cursor, max_w = render_base_slide(content["title"], "EXPERT MACHINE LEARNING BREAKDOWN", handle, big=True)
    
    # Modern layout card decoration on cover
    card_top = y_cursor + 20
    draw.rounded_rectangle([MARGIN_LEFT, card_top, W - PAD_RIGHT, card_top + 320], radius=16, fill=CARD_BG, outline=CARD_BORDER, width=2)
    
    cover_body = [("📌 Inside this breakdown:", 25, False), 
                  ("• Advanced architecture insights", 45, False), 
                  ("• Code implementations & logic", 45, False), 
                  ("• Deep-dive visualizations", 45, False)]
    
    card_y = card_top + 40
    for line, indent, _ in cover_body:
        color = ACCENT_BLUE if "📌" in line else TEXT_MAIN
        draw.text((MARGIN_LEFT + indent, card_y), line, font=F_BODY(), fill=color)
        card_y += F_BODY().size * 1.5

    draw_footer_and_progress(draw, handle, current_index, total_slides)
    cover_path = os.path.join(post_dir, f"{ts}_00_cover.png")
    img.save(cover_path)
    paths.append(cover_path)
    current_index += 1

    # 2. Render Processed Content Slides
    for slide in processed_slides:
        img, draw, y_cursor, max_w = render_base_slide(slide["heading"], slide["eyebrow"], handle)
        
        if slide["diagram"]:
            diagram_img = fetch_mermaid_diagram(slide["diagram"])
            if diagram_img:
                target_w = max_w
                scale = target_w / diagram_img.width
                target_h = int(diagram_img.height * scale)
                max_diagram_h = int(H * 0.35)
                if target_h > max_diagram_h:
                    target_h = max_diagram_h
                    target_w = int(diagram_img.width * (max_diagram_h / diagram_img.height))
                diagram_img = diagram_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
                x_offset = MARGIN_LEFT + int((max_w - target_w) / 2)
                img.paste(diagram_img, (x_offset, int(y_cursor)), diagram_img)
                y_cursor += target_h + 40
                
        # Draw text inside elevated modern geometric frames
        line_height = F_BODY().size * 1.5
        for line, indent, is_code in slide["lines"]:
            if not line:
                y_cursor += line_height * 0.5
                continue
                
            if is_code:
                # Syntax style container box
                box_h = int(F_CODE().size * 1.6)
                draw.rounded_rectangle([MARGIN_LEFT, y_cursor - 6, W - PAD_RIGHT, y_cursor + box_h - 6], radius=8, fill=(18, 22, 34), outline=CARD_BORDER, width=1)
                draw.text((MARGIN_LEFT + 25, y_cursor), line, font=F_CODE(), fill=ACCENT_BLUE)
                y_cursor += box_h + 10
            else:
                # Standard high contrast clean print
                if indent > 15:  # Custom stylish geometric bullet point
                    draw.rectangle([MARGIN_LEFT + 15, y_cursor + 14, MARGIN_LEFT + 25, y_cursor + 24], fill=ACCENT_BLUE)
                draw.text((MARGIN_LEFT + indent, y_cursor), line, font=F_BODY(), fill=TEXT_MAIN)
                y_cursor += line_height
            
        draw_footer_and_progress(draw, handle, current_index, total_slides)
        path = os.path.join(post_dir, f"{ts}_{current_index:02d}.png")
        img.save(path)
        paths.append(path)
        current_index += 1

    # 3. CTA Slide
    img, draw, y_cursor, max_w = render_base_slide("Join the Journey", "SUBSCRIBE & SAVE", handle)
    
    cta_box_top = y_cursor + 40
    draw.rounded_rectangle([MARGIN_LEFT, cta_box_top, W - PAD_RIGHT, cta_box_top + 280], radius=20, fill=CARD_BG, outline=ACCENT_BLUE, width=3)
    
    draw.text((MARGIN_LEFT + 40, cta_box_top + 60), "Found this breakdown helpful?", font=F_HEADING(), fill=TEXT_MAIN)
    draw.text((MARGIN_LEFT + 40, cta_box_top + 150), "🔖 Save for reference | 📲 Share with an engineer", font=F_BODY(), fill=TEXT_MUTED)
    
    draw_footer_and_progress(draw, handle, current_index, total_slides)
    cta_path = os.path.join(post_dir, f"{ts}_{current_index:02d}_cta.png")
    img.save(cta_path)
    paths.append(cta_path)

    # 4. Save the Caption file
    caption_path = os.path.join(post_dir, "caption.txt")
    with open(caption_path, "w", encoding="utf-8") as f:
        f.write(content.get("title", "ML Concept") + "\n\n")
        f.write(content.get("caption", "") + "\n\n")
        f.write(" ".join(content.get("hashtags", [])))

    return {
        "post_dir": post_dir,
        "folder_name": folder_name
    }
    
    