"""
Renders handwritten engineering study notes on grid paper.
Includes smart text wrapping, bullet point indentation, transparent diagrams,
and automatic multi-slide splitting to prevent text overflow.
"""
import os
import time
import base64
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

import config

W, H = 1080, 1350
MARGIN_LEFT = 140  
PAD_RIGHT = 80
MAX_CONTENT_Y = H - 120  # Keep text away from the very bottom footer

# Notebook Colors
PAPER_BG = (252, 252, 249)       
GRID_LINE = (225, 230, 235)      
MARGIN_LINE = (255, 140, 140)    
INK_BLACK = (30, 32, 35)         
INK_BLUE = (35, 75, 160)         
INK_RED = (180, 40, 40)          

def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = os.path.join(config.FONT_DIR, name)
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()

F_EYEBROW = lambda: _font("Kalam-Bold.ttf", 35)
F_HEADING_BIG = lambda: _font("Kalam-Bold.ttf", 85)
F_HEADING = lambda: _font("Kalam-Bold.ttf", 65)
F_BODY = lambda: _font("Kalam-Regular.ttf", 42)
F_FOOTER = lambda: _font("Kalam-Regular.ttf", 30)

def draw_notebook_background(draw: ImageDraw.ImageDraw):
    line_spacing = 60
    for y in range(line_spacing, H, line_spacing):
        draw.line([(0, y), (W, y)], fill=GRID_LINE, width=2)
    draw.line([(MARGIN_LEFT - 10, 0), (MARGIN_LEFT - 10, H)], fill=MARGIN_LINE, width=2)
    draw.line([(MARGIN_LEFT, 0), (MARGIN_LEFT, H)], fill=MARGIN_LINE, width=2)

def fetch_mermaid_diagram(mermaid_code: str) -> Image.Image:
    try:
        encoded = base64.b64encode(mermaid_code.encode('utf-8')).decode('utf-8')
        url = f"https://mermaid.ink/img/{encoded}?bgColor=!transparent"
        response = requests.get(url)
        response.raise_for_status()
        return Image.open(BytesIO(response.content)).convert("RGBA")
    except Exception as e:
        print(f"Failed to render diagram: {e}")
        return None

def sanitize_text(text: str) -> str:
    text = text.replace('—', '-').replace('–', '-').replace('•', '-')
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
    """Pre-calculates text layouts and splits them across pages if they overflow."""
    if not raw_text:
        return [[]]
        
    text = sanitize_text(raw_text)
    paragraphs = text.split('\n')
    line_height = font.size * 1.4
    
    pages = []
    current_page_lines = []
    
    # Estimate starting room on a slide (roughly 400px used by margins/headers)
    available_height = MAX_CONTENT_Y - 350 
    current_y = 0

    for p in paragraphs:
        p = p.strip()
        if not p:
            # Handle explicit empty newlines safely
            if current_y + (line_height * 0.5) > available_height:
                pages.append(current_page_lines)
                current_page_lines = []
                available_height = MAX_CONTENT_Y - 200 # Reset height for a fresh slide
                current_y = 0
            current_page_lines.append(("", 0))
            current_y += line_height * 0.5
            continue
            
        is_bullet = p.startswith('-') or p.startswith('*')
        indent = 40 if is_bullet else 0
        wrapped_lines = _wrap_line(draw, p, font, max_w - indent)
        
        for line in wrapped_lines:
            if current_y + line_height > available_height:
                pages.append(current_page_lines)
                current_page_lines = []
                available_height = MAX_CONTENT_Y - 200 
                current_y = 0
            
            current_page_lines.append((line, indent))
            current_y += line_height
            
        current_y += 10 # Post-paragraph spacing

    if current_page_lines:
        pages.append(current_page_lines)
        
    return pages

def render_base_slide(heading: str, eyebrow: str, handle: str, big: bool = False):
    """Helper to generate a blank canvas with background elements and headings."""
    img = Image.new("RGB", (W, H), PAPER_BG)
    draw = ImageDraw.Draw(img)
    draw_notebook_background(draw)
    
    max_w = W - MARGIN_LEFT - PAD_RIGHT - 30
    y_cursor = 100

    if eyebrow:
        draw.text((MARGIN_LEFT + 20, y_cursor), f"[{eyebrow.upper()}]", font=F_EYEBROW(), fill=INK_RED)
        y_cursor += 70

    heading_font = F_HEADING_BIG() if big else F_HEADING()
    heading_text = sanitize_text(heading)
    heading_lines = _wrap_line(draw, heading_text, heading_font, max_w)
    
    for line in heading_lines:
        draw.text((MARGIN_LEFT + 20, y_cursor), line, font=heading_font, fill=INK_BLACK)
        y_cursor += heading_font.size * 1.2
        
    y_cursor += 30
    return img, draw, y_cursor, max_w

def draw_footer(draw, handle, index, total):
    footer_y = H - 60
    draw.text((MARGIN_LEFT + 20, footer_y), handle, font=F_FOOTER(), fill=INK_BLACK)
    if total > 1:
        draw.text((W - PAD_RIGHT - 120, footer_y), f"Page {index + 1}/{total}", font=F_FOOTER(), fill=INK_BLACK)

def render_post(content: dict, handle: str) -> dict:
    ts = int(time.time())
    safe_title = "".join(c if c.isalnum() else "_" for c in content.get("title", "AI_Topic"))[:30].strip("_")
    folder_name = f"{ts}_{safe_title}"
    post_dir = os.path.join(config.OUTPUT_DIR, folder_name)
    os.makedirs(post_dir, exist_ok=True)

    # First, let's look through slides and build out the pagination sequences
    raw_slides = content["slides"]
    processed_slides = []

    for i, slide in enumerate(raw_slides, start=1):
        heading = slide["heading"]
        body = slide.get("body", "")
        diagram_code = slide.get("diagram")
        
        # Determine pagination split using dummy image setup
        dummy_img = Image.new("RGB", (W, H))
        dummy_draw = ImageDraw.Draw(dummy_img)
        
        body_pages = _paginate_body_text(dummy_draw, body, F_BODY(), W - MARGIN_LEFT - PAD_RIGHT - 30)
        
        for p_idx, page_lines in enumerate(body_pages):
            eyebrow_text = f"Note {i}" if len(body_pages) == 1 else f"Note {i} ({p_idx + 1}/{len(body_pages)})"
            processed_slides.append({
                "heading": heading if p_idx == 0 else f"{heading} (Cont.)",
                "eyebrow": eyebrow_text,
                "lines": page_lines,
                "diagram": diagram_code if p_idx == 0 else None  # Only draw diagram on the first page
            })

    total_slides = len(processed_slides) + 2 # Add Cover + CTA
    paths = []
    current_index = 0

    # 1. Cover Slide
    img, draw, y_cursor, max_w = render_base_slide(content["title"], "ML/AI STUDY NOTES", handle, big=True)
    _ = _paginate_body_text(draw, "Swipe for complete notes \n\n- Definitions\n- Architectures\n- Key takeaways", F_BODY(), max_w)
    # Basic quick draw for short static cover content
    cover_body = [("Swipe for complete notes", 0), ("", 0), ("- Definitions", 40), ("- Architectures", 40), ("- Key takeaways", 40)]
    for line, indent in cover_body:
        draw.text((MARGIN_LEFT + 20 + indent, y_cursor), line, font=F_BODY(), fill=INK_BLUE)
        y_cursor += F_BODY().size * 1.4
    draw_footer(draw, handle, current_index, total_slides)
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
                x_offset = MARGIN_LEFT + 20 + int((max_w - target_w) / 2)
                img.paste(diagram_img, (x_offset, int(y_cursor)), diagram_img)
                y_cursor += target_h + 40
                
        # Draw the pre-calculated safe text block for this page
        line_height = F_BODY().size * 1.4
        for line, indent in slide["lines"]:
            if not line:
                y_cursor += line_height * 0.5
                continue
            draw.text((MARGIN_LEFT + 20 + indent, y_cursor), line, font=F_BODY(), fill=INK_BLUE)
            y_cursor += line_height
            
        draw_footer(draw, handle, current_index, total_slides)
        path = os.path.join(post_dir, f"{ts}_{current_index:02d}.png")
        img.save(path)
        paths.append(path)
        current_index += 1

    # 3. CTA Slide
    img, draw, y_cursor, max_w = render_base_slide("Save these notes!", "END OF NOTES", handle)
    draw.text((MARGIN_LEFT + 20, y_cursor), "Follow for more daily ML/AI engineering breakdowns.", font=F_BODY(), fill=INK_BLUE)
    draw_footer(draw, handle, current_index, total_slides)
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