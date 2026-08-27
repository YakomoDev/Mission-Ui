# Prepared with love by YakomoDev - https://ko-fi.com/yakomodev
import os
import math
import datetime
from PIL import Image, ImageDraw, ImageFont
import theme_manager as tm

# Styling Constants
BLUE = (0, 51, 204)       # Medium blue ink color
GREEN = (34, 139, 34)     # Forest green for the Note badge background
WHITE = (255, 255, 255)

def draw_dashed_line(draw, pt1, pt2, color, width=2, dash_length=12, gap_length=8):
    """Draw a dashed line between pt1 and pt2."""
    x1, y1 = pt1
    x2, y2 = pt2
    dx = x2 - x1
    dy = y2 - y1
    distance = math.sqrt(dx*dx + dy*dy)
    if distance == 0:
        return
    
    ux = dx / distance
    uy = dy / distance
    
    step = dash_length + gap_length
    num_steps = int(distance / step)
    
    for i in range(num_steps + 1):
        start_dist = i * step
        end_dist = min(start_dist + dash_length, distance)
        sx = x1 + ux * start_dist
        sy = y1 + uy * start_dist
        ex = x1 + ux * end_dist
        ey = y1 + uy * end_dist
        draw.line([(sx, sy), (ex, ey)], fill=color, width=width)

def shape_arabic_for_pil(text):
    return shape(text)

def shape(text):
    if not text:
        return ""
    # If string already contains shaped presentation forms, return as-is
    if any('\ufb50' <= c <= '\ufeff' for c in text):
        return text
    # Shape raw logical Arabic text
    if any('\u0600' <= c <= '\u06ff' for c in text):
        try:
            import arabic_reshaper
            from bidi.algorithm import get_display
            reshaper = arabic_reshaper.ArabicReshaper()
            return get_display(reshaper.reshape(text))
        except Exception:
            return text
    return text

def draw_centered_text(draw, text, cx, y, font, fill):
    """Draw text centered horizontally at cx, properly handling Arabic shaping."""
    is_ar = tm._current_language == "Arabic" and any('\u0600' <= c <= '\u06ff' for c in text)
    if is_ar:
        text = shape_arabic_for_pil(text)
    bbox = draw.textbbox((0, 0), text, font=font, direction="ltr")
    w = bbox[2] - bbox[0]
    draw.text((cx - w/2, y), text, font=font, fill=fill, direction="ltr")

def wrap_text_pil(text, font, max_width, draw, is_rtl=False):
    """Wrap text to fit a maximum width. For RTL Arabic, measure words with direction='rtl'."""
    words = text.split()
    lines = []
    current_line = []
    direction = "rtl" if is_rtl else "ltr"
    for word in words:
        test_line = " ".join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font, direction=direction)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))
    return lines

def format_stars(val):
    """Format star values cleanly (e.g. 3 instead of 3.0)."""
    if val.is_integer():
        return f"{int(val)}"
    return f"{val:.1f}"

def calculate_stats(main_tasks, side_tasks):
    """
    Calculate star ratios and group ratios based on task weight and completion percentage.
    """
    # 1. Main Tasks Stars
    total_main_stars = 0.0
    earned_main_stars = 0.0
    for g in main_tasks:
        g_stars = float(g.get("stars", 0))
        total_main_stars += g_stars
        items = g.get("items", [])
        if items:
            for item in items:
                if item.get("done"):
                    earned_main_stars += g_stars * (float(item.get("percent", 0.0)) / 100.0)
        else:
            if g.get("done", False):
                earned_main_stars += g_stars
                
    # 2. Side Tasks Groups Count
    total_side_groups = len(side_tasks)
    completed_side_groups = 0
    for g in side_tasks:
        items = g.get("items", [])
        if items:
            if all(item.get("done") for item in items):
                completed_side_groups += 1
        else:
            # If no items, completed if group itself marked done (default false)
            if g.get("done", False):
                completed_side_groups += 1

    # 3. Side Tasks Stars
    total_side_stars = 0.0
    earned_side_stars = 0.0
    for g in side_tasks:
        g_stars = float(g.get("stars", 0))
        total_side_stars += g_stars
        items = g.get("items", [])
        if items:
            for item in items:
                if item.get("done"):
                    earned_side_stars += g_stars * (float(item.get("percent", 0.0)) / 100.0)
        else:
            if g.get("done", False):
                earned_side_stars += g_stars
                
    # 4. Totals Across Both
    total_all_stars = total_main_stars + total_side_stars
    earned_all_stars = earned_main_stars + earned_side_stars
    
    return {
        "total_main_stars": total_main_stars,
        "earned_main_stars": earned_main_stars,
        "total_side_groups": total_side_groups,
        "completed_side_groups": completed_side_groups,
        "total_side_stars": total_side_stars,
        "earned_side_stars": earned_side_stars,
        "total_all_stars": total_all_stars,
        "earned_all_stars": earned_all_stars
    }

def generate_paper_image(date_str, day_data, app_dir):
    """
    Generate an A4 paper image (1240 x 1754) matching the style of 5-07.png dynamically.
    """
    # 1. Create a blank white canvas
    img = Image.new("RGB", (1240, 1754), "white")
    draw = ImageDraw.Draw(img)
    
    font_path, font_bold_path = tm.get_best_font_paths(app_dir)
    
    try:
        font_date = ImageFont.truetype(font_bold_path, 28)
        font_header = ImageFont.truetype(font_bold_path, 22)
        font_body = ImageFont.truetype(font_path, 18)
        font_body_bold = ImageFont.truetype(font_bold_path, 18)
        font_small = ImageFont.truetype(font_path, 14)
        font_title = ImageFont.truetype(font_bold_path, 24)
        font_giant = ImageFont.truetype(font_bold_path, 40)
    except Exception:
        # Fallback to default
        font_date = font_header = font_body = font_body_bold = font_small = font_title = font_giant = ImageFont.load_default()

    # Load a Latin-capable fallback font for task items that contain English text
    try:
        _dv_reg = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        _dv_bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if os.path.exists(_dv_reg):
            font_body_latin = ImageFont.truetype(_dv_reg, 18)
            font_body_bold_latin = ImageFont.truetype(_dv_bold, 18) if os.path.exists(_dv_bold) else font_body_latin
            font_giant_latin = ImageFont.truetype(_dv_bold, 40)
        else:
            font_body_latin = font_body
            font_body_bold_latin = font_body_bold
            font_giant_latin = font_giant
    except Exception:
        font_body_latin = font_body
        font_body_bold_latin = font_body_bold
        font_giant_latin = font_giant
        
    # Calculate stars stats
    main_tasks = day_data.get("main_tasks", [])
    side_tasks = day_data.get("side_tasks", [])
    stats = calculate_stats(main_tasks, side_tasks)
    
    # 3. Dynamic note box height based on text volume
    note_text = ""
    if tm._current_language != "Arabic":
        if day_data.get("ai_comment"):
            note_text = day_data["ai_comment"]
        elif day_data.get("small_advice"):
            note_text = day_data["small_advice"]
        
    if note_text:
        wrapped_note = []
        if _ar_pre := tm._current_language == "Arabic":
            for para in note_text.split("\n"):
                para = para.strip()
                if not para:
                    continue
                has_arabic = any('\u0600' <= c <= '\u06ff' or '\ufb50' <= c <= '\ufeff' for c in para)
                has_latin = any('a' <= c.lower() <= 'z' for c in para)
                para_font = font_body_latin if has_latin else font_body
                for line in wrap_text_pil(para, para_font, 760, draw, is_rtl=has_arabic):
                    wrapped_note.append((line, para_font))
        else:
            for para in note_text.split("\n"):
                para = para.strip()
                if para:
                    for line in wrap_text_pil(para, font_body, 760, draw):
                        wrapped_note.append((line, font_body))
        note_height = max(130, 65 + len(wrapped_note) * 26)
    else:
        wrapped_note = []
        note_height = 130
        
    y_note_top = 1480 - note_height
    
    # 4. Draw Outer Border and Grid Lines
    # Margin: 40px, bottom summary box starts at y = 1480
    draw.rectangle([(40, 40), (1200, 1714)], outline=BLUE, width=3)
    
    # Vertical Line at x = 868
    draw.line([(868, 40), (868, 1714)], fill=BLUE, width=3)
    
    # Left dividers
    draw.line([(40, y_note_top), (868, y_note_top)], fill=BLUE, width=3)
    draw.line([(40, 1480), (868, 1480)], fill=BLUE, width=3)
    draw.line([(40, 1600), (868, 1600)], fill=BLUE, width=3)
    
    # Right dividers
    draw.line([(868, 1480), (1200, 1480)], fill=BLUE, width=3)
    
    _ar = tm._current_language == "Arabic"

    # Local helper to shape Arabic text - now a no-op!
    def shape(txt):
        return txt

    # Helper: right-align x for Arabic, left-align otherwise
    # col_right = right boundary of the column (pixels)
    def text_x(text, font, col_right=860, col_left=60):
        is_ar_txt = _ar and any('\u0600' <= c <= '\u06ff' or '\ufb50' <= c <= '\ufeff' for c in text)
        if is_ar_txt:
            bb = draw.textbbox((0, 0), text, font=font, direction="rtl")
            return col_right - (bb[2] - bb[0])
        return col_left

    # Local helper to draw text with correct direction
    def draw_t(xy, txt, font, fill):
        x, y = xy
        is_ar_txt = _ar and any('\u0600' <= c <= '\u06ff' or '\ufb50' <= c <= '\ufeff' for c in txt)
        if is_ar_txt:
            draw.text((x, y), txt, font=font, fill=fill, direction="rtl")
        else:
            draw.text((x, y), txt, font=font, fill=fill)

    # Helper: pick font based on whether text contains Arabic/Latin characters
    def pick_font(text, arabic_font, latin_font):
        """Use latin_font if any Latin characters found, else arabic_font if Arabic."""
        if _ar:
            if any('a' <= c.lower() <= 'z' for c in text):
                return latin_font
            if any('\u0600' <= c <= '\u06ff' or '\ufb50' <= c <= '\ufeff' for c in text):
                return arabic_font
        return latin_font

    # 5. Render Left Column Header (Date)
    try:
        dt = datetime.date.fromisoformat(date_str)
        formatted_date = shape(tm._format_date_raw(dt))
    except Exception:
        formatted_date = shape(date_str)

    date_x = text_x(formatted_date, font_date, col_right=850)
    draw_t((date_x, 60), formatted_date, font_date, fill=BLUE)
    draw.line([(60, 95), (850, 95)], fill=BLUE, width=2)
    
    # 6. Render Left Column Main Tasks (fit dynamically)
    y = 120
    available_main_height = y_note_top - 120
    
    # Spacing parameters
    spacing_item = 35
    spacing_group = 15
    
    if main_tasks:
        # Pre-calculate needed height
        needed_height = 40 # title
        for g in main_tasks:
            needed_height += 30 # group title
            needed_height += len(g.get("items", [])) * 35
            needed_height += 15 # spacing between groups
            
        if needed_height > available_main_height:
            scale = available_main_height / needed_height
            spacing_item = max(24, int(35 * scale))
            spacing_group = max(5, int(15 * scale))
            
        hdr = shape(tm.tr_raw("main_missions") + " :")
        draw_t((text_x(hdr, font_header), y), hdr, font_header, fill=BLUE)
        y += spacing_item + 5
        
        for g in main_tasks:
            g_stars = float(g.get("stars", 0))
            title_text = f"• {g.get('title')} (✩ {format_stars(g_stars)})"
            s_title = shape(title_text)
            title_font = pick_font(g.get('title'), font_body_bold, font_body_bold_latin)
            draw_t((text_x(s_title, title_font), y), s_title, title_font, fill=BLUE)
            y += spacing_item - 5
            
            for item in g.get("items", []):
                # Checkbox: right side for Arabic, left side for LTR
                box_x = 820 if _ar else 80
                box_y = y
                draw.rectangle([(box_x, box_y), (box_x + 22, box_y + 22)], outline=BLUE, width=2)
                
                if item.get("done"):
                    draw.line([(box_x + 4, box_y + 11), (box_x + 10, box_y + 17)], fill=BLUE, width=3)
                    draw.line([(box_x + 10, box_y + 17), (box_x + 19, box_y + 5)], fill=BLUE, width=3)
                    
                # Draw item name
                item_lbl = f"{item.get('name')} ({item.get('percent', 0)}%)"
                s_item = shape(item_lbl)
                item_col_right = box_x - 8 if _ar else 860
                item_col_left  = 115 if not _ar else 60
                item_font = pick_font(item.get('name'), font_body, font_body_latin)
                draw_t((text_x(s_item, item_font, col_right=item_col_right, col_left=item_col_left), y),
                          s_item, item_font, fill=BLUE)
                y += spacing_item
                
            y += spacing_group
            
    # 7. Note ( mémo ) section (dynamic position)
    # Draw Green Note Badge — right side for Arabic, left side otherwise
    if _ar:
        draw.rectangle([(720, y_note_top + 15), (800, y_note_top + 45)], fill=GREEN)
        draw_t((730, y_note_top + 21), shape(tm.tr_raw("note")), font_small, fill=WHITE)
        memo_lbl = shape("( " + tm.tr_raw("memo") + " ) :")
        draw_t((text_x(memo_lbl, font_body_latin, col_right=715), y_note_top + 20), memo_lbl, font=font_body_latin, fill=BLUE)
    else:
        draw.rectangle([(60, y_note_top + 15), (140, y_note_top + 45)], fill=GREEN)
        draw_t((75, y_note_top + 21), shape(tm.tr_raw("note")), font_small, fill=WHITE)
        draw_t((150, y_note_top + 20), shape("( " + tm.tr_raw("memo") + " ) :"), font=font_body_latin, fill=BLUE)
    
    if wrapped_note:
        ny = y_note_top + 55
        for line_item in wrapped_note:
            if isinstance(line_item, tuple):
                line, line_font = line_item
            else:
                line, line_font = line_item, font_body
            has_arabic = any('\u0600' <= c <= '\u06ff' or '\ufb50' <= c <= '\ufeff' for c in line)
            if _ar and has_arabic:
                bbox = draw.textbbox((0, 0), line, font=line_font, direction="rtl")
                w = bbox[2] - bbox[0]
                draw_t((840 - w, ny), line, line_font, fill=BLUE)
            else:
                draw_t((60, ny), line, line_font, fill=BLUE)
            ny += 26
    else:
        # Draw blank lines for writing notes
        draw.line([(60, y_note_top + 75), (840, y_note_top + 75)], fill=BLUE, width=1)
        draw.line([(60, y_note_top + 110), (840, y_note_top + 110)], fill=BLUE, width=1)
        
    # 8. Left Column Footer Calculation
    # Main Tasks row (y = 1480 to 1600)
    ftr_hdr = shape(tm.tr_raw("main_missions") + " :")
    draw_t((text_x(ftr_hdr, font_header), 1520), ftr_hdr, font_header, fill=BLUE)
    
    # Display main tasks star ratio (e.g. 0 / 3)
    val_main_str = f"{format_stars(stats['earned_main_stars'])} / {format_stars(stats['total_main_stars'])}" if stats['total_main_stars'] > 0 else "0"
    s_val_main = shape(val_main_str)
    draw_t((text_x(s_val_main, font_giant_latin, col_right=850, col_left=450), 1510), s_val_main, font_giant_latin, fill=BLUE)
    
    # Totale row (y = 1600 to 1714)
    tot_lbl = shape(tm.tr_raw("total") + " :")
    draw_t((text_x(tot_lbl, font_header), 1640), tot_lbl, font_header, fill=BLUE)
    val_total_str = f"{format_stars(stats['earned_all_stars'])} / {format_stars(stats['total_all_stars'])}"
    draw_t((450, 1630), shape(val_total_str), font_giant_latin, fill=BLUE)
    
    # 9. Render Right Column Side Tasks (y = 40 to y = 1480)
    if side_tasks:
        box_h = 1440 / len(side_tasks)
        for idx, g in enumerate(side_tasks):
            y_start = 40 + idx * box_h
            y_end = y_start + box_h
            
            # Divider
            if idx < len(side_tasks) - 1:
                draw_dashed_line(draw, (868, y_end), (1200, y_end), BLUE, width=2)
                
            # Group Header: "[Actual Title] : ✩"
            g_stars = float(g.get("stars", 0))
            stars_suffix = f" {format_stars(g_stars)}" if g_stars != 1 else ""
            header_txt = f"{g.get('title')} : ✩{stars_suffix}"
            g_font = pick_font(g.get('title'), font_body_bold, font_body_bold_latin)
            draw_t((890, y_start + 15), shape(header_txt), g_font, fill=BLUE)
            
            # Underline header
            draw.line([(890, y_start + 40), (1180, y_start + 40)], fill=BLUE, width=2)
            
            # Render items
            items = g.get("items", [])
            if len(items) == 0:
                # If no items, the group title itself is the task.
                # Center checkbox vertically in the box.
                box_y = y_start + (box_h - 40) / 2
                draw.rectangle([(1130, box_y), (1170, box_y + 40)], outline=BLUE, width=2)
            elif len(items) == 1:
                # Center vertically
                item = items[0]
                text_y = y_start + (box_h - 24) / 2
                box_y = y_start + (box_h - 40) / 2
                
                # Checkbox
                draw.rectangle([(1130, box_y), (1170, box_y + 40)], outline=BLUE, width=2)
                if item.get("done"):
                    # Draw checkmark
                    draw.line([(1136, box_y + 20), (1148, box_y + 32)], fill=BLUE, width=4)
                    draw.line([(1148, box_y + 32), (1164, box_y + 8)], fill=BLUE, width=4)
                    
                # Text
                item_font = pick_font(item.get("name", ""), font_body, font_body_latin)
                wrapped_item = wrap_text_pil(item.get("name", ""), item_font, 220, draw)
                for line_idx, line in enumerate(wrapped_item[:3]):
                    draw_t((890, text_y + line_idx * 24), shape(line), item_font, fill=BLUE)
            else:
                # Multiple items stacked
                item_spacing = (box_h - 60) / len(items)
                
                # Dynamically calculate font size and checkbox size based on spacing
                fs = min(18, max(8, int(item_spacing - 2)))
                box_size = min(32, max(8, int(item_spacing - 2)))
                
                # Load dynamic-sized fonts
                try:
                    dynamic_arabic_font = ImageFont.truetype(font_path, fs)
                except Exception:
                    dynamic_arabic_font = ImageFont.load_default()
                    
                try:
                    if os.path.exists(_dv_reg):
                        dynamic_latin_font = ImageFont.truetype(_dv_reg, fs)
                    else:
                        dynamic_latin_font = dynamic_arabic_font
                except Exception:
                    dynamic_latin_font = ImageFont.load_default()
                
                for item_idx, item in enumerate(items):
                    box_y = y_start + 50 + item_idx * item_spacing
                    
                    # Checkbox
                    draw.rectangle([(1135, box_y), (1165, box_y + box_size)], outline=BLUE, width=2)
                    if item.get("done"):
                        # Draw checkmark
                        draw.line([(1140, box_y + int(box_size * 0.5)), (1149, box_y + int(box_size * 0.8))], fill=BLUE, width=3)
                        draw.line([(1149, box_y + int(box_size * 0.8)), (1161, box_y + int(box_size * 0.2))], fill=BLUE, width=3)
                        
                    # Text
                    item_name = item.get("name", "")
                    
                    # Dynamically calculate max length based on font size to avoid overlap
                    max_len = int(22 * (18 / fs))
                    if len(item_name) > max_len:
                        item_name = item_name[:max_len - 2] + ".."
                        
                    item_font = pick_font(item_name, dynamic_arabic_font, dynamic_latin_font)
                    draw_t((890, box_y + max(0, (box_size - fs) // 2)), shape(item_name), item_font, fill=BLUE)
    else:
        # Placeholder boxes if empty
        box_h = 1440 / 8
        for idx in range(8):
            y_start = 40 + idx * box_h
            y_end = y_start + box_h
            if idx < 7:
                draw_dashed_line(draw, (868, y_end), (1200, y_end), BLUE, width=2)
            draw_t((890, y_start + 15), shape(tm.tr_raw("side_missions") + " : ✩"), font_body_bold, fill=BLUE)
            draw.line([(890, y_start + 40), (1050, y_start + 40)], fill=BLUE, width=2)
            draw.rectangle([(1130, y_start + 65), (1170, y_start + 105)], outline=BLUE, width=2)
            
    # 10. Render Right Column Footer (Unified single block)
    draw_centered_text(draw, shape(tm.tr_raw("side_missions") + " :"), 1034, 1530, font_body_bold, BLUE)
    # Render the score in giant font centered vertically
    val_side_str = f"{stats['completed_side_groups']} / {stats['total_side_groups']}"
    draw_centered_text(draw, shape(val_side_str), 1034, 1575, font_giant_latin, BLUE)
    
    return img


def generate_memo_page_images(date_str, diary_data, app_dir):
    """
    Generate an A4 memo page image array (1240 x 1754) with a lined notebook style.
    Handles rich text formatting (bold, italic, colors) and wraps lines properly.
    """
    import json
    
    def shape_arabic_ligatures(txt):
        return shape_arabic_for_pil(txt)
    # 1. Create a blank white canvas
    img = Image.new("RGB", (1240, 1754), "white")
    draw = ImageDraw.Draw(img)
    
    font_path, font_bold_path = tm.get_best_font_paths(app_dir)
    
    # 2. Draw Outer Blue Border
    draw.rectangle([(40, 40), (1200, 1714)], outline=BLUE, width=3)
    
    # 3. Draw Header Double Lines
    draw.line([(40, 180), (1200, 180)], fill=BLUE, width=2)
    draw.line([(40, 190), (1200, 190)], fill=BLUE, width=2)
    
    # Header Text (Date & Title)
    try:
        dt = datetime.date.fromisoformat(date_str)
        raw_date = tm._format_date_raw(dt)
    except Exception:
        raw_date = date_str
        
    if tm._current_language == "Arabic":
        title_text = f"{raw_date}  -  {tm.tr_raw('daily_diary')}"
    else:
        title_text = f"{tm.tr_raw('daily_diary')}  -  {raw_date}"
    
    try:
        font_header = ImageFont.truetype(font_bold_path, 28)
    except Exception:
        font_header = ImageFont.load_default()
        
    # Center header text
    draw_centered_text(draw, title_text, 620, 95, font_header, BLUE)
    
    # 5. Lined Paper Guidelines
    # Lines from y=235 to y=1680 spaced 45px
    for y in range(235, 1714, 45):
        draw.line([(40, y), (1200, y)], fill=(180, 200, 255), width=1)
        
    # Red Notebook Margin Line at x=120
    draw.line([(120, 190), (120, 1714)], fill=(220, 80, 80), width=2)
    
    # 6. Parse and Render styled text
    plain_text = diary_data.get("text", "")
    tags_dict = diary_data.get("tags", {})
    
    char_styles = []
    for c in plain_text:
        char_styles.append({
            "bold": False,
            "italic": False,
            "size": 22,  # Default export size (roughly 12 screen size scaled)
            "color": BLUE
        })
        
    def tk_index_to_offset(index_str):
        try:
            line_part, char_part = index_str.split('.')
            ln = int(line_part)
            ch = int(char_part)
            lines = plain_text.split('\n')
            offset = 0
            for i in range(ln - 1):
                offset += len(lines[i]) + 1
            offset += ch
            return min(offset, len(plain_text))
        except:
            return 0

    for tag_name, ranges in tags_dict.items():
        bold = False
        italic = False
        size = 22
        color = BLUE
        if tag_name.startswith("style_"):
            parts = tag_name.split('_')
            if len(parts) == 5:
                bold = parts[1] == "1"
                italic = parts[2] == "1"
                size = int(int(parts[3]) * 1.833)
                color_hex = parts[4] if parts[4] != "default" else None
                if color_hex:
                    try:
                        h = color_hex.lstrip('#')
                        color = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
                    except: pass
        elif tag_name in ("bold", "italic", "bold_italic") or tag_name.startswith("color_"):
            if "bold" in tag_name: bold = True
            if "italic" in tag_name: italic = True
            if tag_name.startswith("color_"):
                try:
                    h = tag_name[6:].lstrip('#')
                    color = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
                except: pass
        else:
            continue

        for i in range(0, len(ranges), 2):
            if i + 1 < len(ranges):
                try:
                    start = tk_index_to_offset(ranges[i])
                    end = tk_index_to_offset(ranges[i+1])
                    if start > end: start, end = end, start
                    for idx in range(start, end):
                        if idx < len(char_styles):
                            if bold: char_styles[idx]["bold"] = True
                            if italic: char_styles[idx]["italic"] = True
                            if size != 22: char_styles[idx]["size"] = size
                            if color != BLUE: char_styles[idx]["color"] = color
                except: pass

    font_ar_path, font_ar_bold_path = tm.get_best_font_paths(app_dir)
    font_lat_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    if not os.path.exists(font_lat_path): font_lat_path = font_ar_path

    font_cache = {}
    def get_font(is_ar, bold, italic, size=22):
        family = font_ar_path if is_ar else font_lat_path
        key = (family, bold, italic, size)
        if key not in font_cache:
            path = family
            if family == font_lat_path:
                if bold and italic: p = family.replace("DejaVuSans.ttf", "DejaVuSans-BoldOblique.ttf")
                elif bold: p = family.replace("DejaVuSans.ttf", "DejaVuSans-Bold.ttf")
                elif italic: p = family.replace("DejaVuSans.ttf", "DejaVuSans-Oblique.ttf")
                else: p = family
                path = p if os.path.exists(p) else family
            try: font_cache[key] = ImageFont.truetype(path, size)
            except: font_cache[key] = ImageFont.load_default()
        return font_cache[key]

    dummy_img = Image.new("RGB", (1, 1))
    draw_dummy = ImageDraw.Draw(dummy_img)
    def is_arabic_char(c): return '\u0600' <= c <= '\u06ff' or '\ufb50' <= c <= '\ufeff'

    lines = []
    max_w = 1020
    curr_off = 0
    for l in plain_text.split('\n'):
        tokens = []
        curr_t, curr_i = "", []
        for idx in range(curr_off, curr_off + len(l)):
            char = plain_text[idx]
            if char in (' ', '\t'):
                if curr_t: tokens.append((curr_t, curr_i)); curr_t, curr_i = "", []
                tokens.append((char, [idx]))
            else: curr_t += char; curr_i.append(idx)
        if curr_t: tokens.append((curr_t, curr_i))
        
        current_line, current_x = [], 0
        for tok_text, tok_indices in tokens:
            chunks = []
            curr_s = None
            curr_c = []
            for idx in tok_indices:
                st = char_styles[idx]
                key = (is_arabic_char(plain_text[idx]), st["bold"], st["italic"], st["size"], st["color"])
                if curr_s is None: curr_s = key; curr_c = [idx]
                elif key == curr_s: curr_c.append(idx)
                else: chunks.append((curr_s, curr_c)); curr_s = key; curr_c = [idx]
            if curr_s: chunks.append((curr_s, curr_c))
            
            tok_w = 0
            for s, c in chunks:
                txt = "".join(plain_text[i] for i in c)
                if s[0]: txt = shape_arabic_ligatures(txt)
                f = get_font(*s[:4])
                tok_w += draw_dummy.textlength(txt, font=f)
                
            if tok_w > max_w:
                for s, c in chunks:
                    for char_idx in c:
                        ch_str = plain_text[char_idx]
                        if s[0]: ch_str = shape_arabic_ligatures(ch_str)
                        f = get_font(*s[:4])
                        ch_w = draw_dummy.textlength(ch_str, font=f)
                        if current_x + ch_w > max_w and current_line:
                            lines.append(current_line)
                            current_line = []
                            current_x = 0
                        if current_line and current_line[-1][0] == s:
                            current_line[-1][1].append(char_idx)
                        else:
                            current_line.append((s, [char_idx]))
                        current_x += ch_w
            else:
                if current_x + tok_w > max_w and current_line:
                    lines.append(current_line)
                    if tok_text.strip() == "":
                        current_line = []
                        current_x = 0
                    else:
                        current_line = list(chunks)
                        current_x = tok_w
                else:
                    current_line.extend(chunks)
                    current_x += tok_w
        if current_line: lines.append(current_line)
        curr_off += len(l) + 1

    page_line_groups = [lines[i : i + 32] for i in range(0, len(lines), 32)] or [[]]
    total_pages, page_images = len(page_line_groups), []
    
    try: dt = datetime.date.fromisoformat(date_str); raw_date = tm._format_date_raw(dt)
    except: raw_date = date_str

    for page_idx, page_chunks in enumerate(page_line_groups):
        img = Image.new("RGB", (1240, 1754), "white")
        draw = ImageDraw.Draw(img)
        draw.rectangle([(40, 40), (1200, 1714)], outline=BLUE, width=3)
        draw.line([(40, 180), (1200, 180)], fill=BLUE, width=2)
        draw.line([(40, 190), (1200, 190)], fill=BLUE, width=2)
        
        p_lbl = "الصفحة" if tm._current_language == "Arabic" else "Page"
        if tm._current_language == "Arabic":
            title = f"{tm.tr_raw('daily_diary')} : {raw_date}"
            if total_pages > 1:
                title = f"{tm.tr_raw('daily_diary')} : {p_lbl} {page_idx+1} من {total_pages}"
        else:
            title = f"{tm.tr_raw('daily_diary')} : {raw_date}"
            if total_pages > 1:
                title = f"{tm.tr_raw('daily_diary')} : {p_lbl} {page_idx+1} of {total_pages}"
        
        draw_centered_text(draw, title, 620, 95, ImageFont.truetype(font_bold_path, 28), BLUE)
        for y in range(235, 1714, 45): draw.line([(40, y), (1200, y)], fill=(180, 200, 255), width=1)
        draw.line([(120, 190), (120, 1714)], fill=(255, 120, 120), width=2)

        y_start = 235
        for line_chunks in page_chunks:
            is_ar = any(is_arabic_char(plain_text[i]) for s, c in line_chunks for i in c)
            x = 1160 if is_ar else 140
            if is_ar:
                for (ia, b, it, sz, col), c in line_chunks:
                    txt = shape_arabic_ligatures("".join(plain_text[i] for i in c))
                    f = get_font(ia, b, it, sz)
                    w = draw.textlength(txt, font=f)
                    draw.text((x - w, y_start - 30), txt, font=f, fill=col)
                    x -= w
            else:
                for (ia, b, it, sz, col), c in line_chunks:
                    txt = "".join(plain_text[i] for i in c)
                    f = get_font(ia, b, it, sz)
                    draw.text((x, y_start - 30), txt, font=f, fill=col)
                    x += draw.textlength(txt, font=f)
            y_start += 45
        page_images.append(img)
    return page_images


def generate_memo_page_image(date_str, diary_data, app_dir):
    imgs = generate_memo_page_images(date_str, diary_data, app_dir)
    return imgs[0] if imgs else None


def generate_monthly_comment_image(month_str, comment_text, app_dir):
    """
    Generate an A4 page image (1240 x 1754) containing the monthly comment/summary.
    """
    img = Image.new("RGB", (1240, 1754), "white")
    draw = ImageDraw.Draw(img)
    
    font_path, font_bold_path = tm.get_best_font_paths(app_dir)
    
    # Draw Outer Blue Border
    draw.rectangle([(40, 40), (1200, 1714)], outline=BLUE, width=3)
    
    # Draw Header Double Lines
    draw.line([(40, 180), (1200, 180)], fill=BLUE, width=2)
    draw.line([(40, 190), (1200, 190)], fill=BLUE, width=2)
    
    title_text = f"MONTHLY AI SUMMARY - {month_str}"
    if tm._current_language == "French":
        title_text = f"RÉSUMÉ MENSUEL IA - {month_str}"
    
    try:
        font_header = ImageFont.truetype(font_bold_path, 28)
        font_body = ImageFont.truetype(font_path, 22)
    except Exception:
        font_header = ImageFont.load_default()
        font_body = ImageFont.load_default()
        
    draw_centered_text(draw, title_text, 620, 95, font_header, BLUE)
    
    # Lined Paper Guidelines
    for y in range(235, 1714, 45):
        draw.line([(40, y), (1200, y)], fill=(180, 200, 255), width=1)
        
    # Red Notebook Margin Line
    draw.line([(120, 190), (120, 1714)], fill=(220, 80, 80), width=2)
    
    # Wrap and draw text
    wrapped_lines = []
    for para in comment_text.split("\n"):
        para = para.strip()
        if para:
            for line in wrap_text_pil(para, font_body, 1020, draw):
                wrapped_lines.append(line)
                
    ny = 235 + 10
    for line in wrapped_lines:
        if ny > 1680:
            break # Avoid drawing off-page
        draw.text((140, ny - 6), line, font=font_body, fill=BLUE)
        ny += 45
        
    return img
