"""
Renders handwritten engineering study notes on grid paper.
Includes smart text wrapping, bullet point indentation, and transparent diagrams.
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
    """Fetches a Mermaid diagram with a transparent background to blend into the paper."""
    try:
        encoded = base64.b64encode(mermaid_code.encode('utf-8')).decode('utf-8')
        # Using transparent background so the grid lines show through!
        url = f"https://mermaid.ink/img/{encoded}?bgColor=!transparent"
        
        response = requests.get(url)
        response.raise_for_status()
        return Image.open(BytesIO(response.content)).convert("RGBA")
    except Exception as e:
        print(f"Failed to render diagram: {e}")
        return None

def sanitize_text(text: str) -> str:
    """Removes weird unicode boxes and normalizes dashes."""
    text = text.replace('—', '-').replace('–', '-').replace('•', '-')
    return text.encode('ascii', 'ignore').decode('ascii')

def _wrap_line(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list:
    """Wraps a single line of text."""
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

def _draw_smart_text(draw, raw_text, font, x, y, max_w, fill):
    """Draws text paragraph by paragraph, handling bullet indents and spacing."""
    if not raw_text:
        return y
        
    text = sanitize_text(raw_text)
    paragraphs = text.split('\n')
    current_y = y
    line_height = font.size * 1.4

    for p in paragraphs:
        p = p.strip()
        if not p:
            current_y += line_height * 0.5  # Add half a line of space for empty newlines
            continue
            
        # Check if it's a bullet point
        is_bullet = p.startswith('-') or p.startswith('*')
        indent = 40 if is_bullet else 0
        
        # Wrap this specific paragraph considering the indent
        wrapped_lines = _wrap_line(draw, p, font, max_w - indent)
        
        for line in wrapped_lines:
            draw.text((x + indent, current_y), line, font=font, fill=fill)
            current_y += line_height
            
        current_y += 10  # Tiny bit of breathing room between paragraphs

    return current_y

def render_slide(
    heading: str,
    body: str = "",
    eyebrow: str = "",
    index: int = 0,
    total: int = 1,
    handle: str = "@your.handle",
    big: bool = False,
    diagram_code: str = None
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
    heading_text = sanitize_text(heading)
    heading_lines = _wrap_line(draw, heading_text, heading_font, max_w)
    
    # --- NEW HIGHLIGHTER CODE ---
    highlight_color = (255, 255, 150) # Bright yellow
    temp_y = y_cursor
    for line in heading_lines:
        # Get the width of the text to know how wide to draw the highlight
        line_w = draw.textlength(line, font=heading_font)
        # Draw the yellow rectangle slightly taller and wider than the text
        draw.rectangle(
            [MARGIN_LEFT + 15, temp_y + 10, MARGIN_LEFT + 25 + line_w, temp_y + heading_font.size + 5], 
            fill=highlight_color
        )
        temp_y += heading_font.size * 1.2
    # ----------------------------
    
    for line in heading_lines:
        draw.text((MARGIN_LEFT + 20, y_cursor), line, font=heading_font, fill=INK_BLACK)
        y_cursor += heading_font.size * 1.2
        
    y_cursor += 30 # Space below header

    # Insert Diagram if it exists
    if diagram_code:
        diagram_img = fetch_mermaid_diagram(diagram_code)
        if diagram_img:
            target_w = max_w
            scale = target_w / diagram_img.width
            target_h = int(diagram_img.height * scale)
            
            # Keep diagram from eating the whole page
            max_diagram_h = int(H * 0.35)
            if target_h > max_diagram_h:
                target_h = max_diagram_h
                target_w = int(diagram_img.width * (max_diagram_h / diagram_img.height))
                
            diagram_img = diagram_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
            
            # Center the diagram in the readable area
            x_offset = MARGIN_LEFT + 20 + int((max_w - target_w) / 2)
            
            # Paste using the image itself as a mask to preserve transparency
            img.paste(diagram_img, (x_offset, int(y_cursor)), diagram_img)
            y_cursor += target_h + 40

    # Draw body text with the smart renderer
    y_cursor = _draw_smart_text(draw, body, F_BODY(), MARGIN_LEFT + 20, y_cursor, max_w, INK_BLUE)

    # Footer
    footer_y = H - 60
    draw.text((MARGIN_LEFT + 20, footer_y), handle, font=F_FOOTER(), fill=INK_BLACK)
    if total > 1:
        draw.text((W - PAD_RIGHT - 120, footer_y), f"Page {index + 1}/{total}", font=F_FOOTER(), fill=INK_BLACK)

    return img

def render_post(content: dict, handle: str) -> dict:
    ts = int(time.time())
    
    # 1. Create a clean, dedicated subfolder for this specific post
    safe_title = "".join(c if c.isalnum() else "_" for c in content.get("title", "AI_Topic"))[:30].strip("_")
    folder_name = f"{ts}_{safe_title}"
    post_dir = os.path.join(config.OUTPUT_DIR, folder_name)
    os.makedirs(post_dir, exist_ok=True)

    paths = []
    slides_data = content["slides"]
    total = len(slides_data) + 2

    # 2. Render and save Cover Slide into the subfolder
    cover = render_slide(
        heading=content["title"],
        body="Swipe for complete notes \n\n- Definitions\n- Architectures\n- Key takeaways",
        eyebrow="ML/AI STUDY NOTES",
        index=0, total=total, handle=handle, big=True
    )
    cover_path = os.path.join(post_dir, f"{ts}_00_cover.png")
    cover.save(cover_path)
    paths.append(cover_path)

    # 3. Render and save Content Slides into the subfolder
    for i, slide in enumerate(slides_data, start=1):
        img = render_slide(
            heading=slide["heading"],
            body=slide.get("body", ""),
            eyebrow=f"Note {i}",
            index=i, total=total, handle=handle,
            diagram_code=slide.get("diagram")
        )
        path = os.path.join(post_dir, f"{ts}_{i:02d}.png")
        img.save(path)
        paths.append(path)

    # 4. Render and save CTA Slide into the subfolder
    cta = render_slide(
        heading="Save these notes!",
        body="Follow for more daily ML/AI engineering breakdowns.",
        eyebrow="END OF NOTES",
        index=total - 1, total=total, handle=handle
    )
    cta_path = os.path.join(post_dir, f"{ts}_{len(slides_data)+1:02d}_cta.png")
    cta.save(cta_path)
    paths.append(cta_path)

    # 5. Create the Caption file in the same folder
    caption_path = os.path.join(post_dir, "caption.txt")
    with open(caption_path, "w", encoding="utf-8") as f:
        f.write(content.get("title", "ML Concept") + "\n\n")
        f.write(content.get("caption", "") + "\n\n")
        f.write(" ".join(content.get("hashtags", [])))

    # Return the folder details so the uploader knows where to look
    return {
        "post_dir": post_dir,
        "folder_name": folder_name
    }