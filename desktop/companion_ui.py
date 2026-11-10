#!/usr/bin/env python3
"""
Pulsar AI Assistant - Companion UI Renderers
=============================================
High-performance PIL vector/canvas renderers for Win32 32-bit Layered Windows:
- Multi-line Speech Bubble with auto-wrapping
- Rich Notification Cards (Email, WhatsApp, Calendar, Research)
- Interactive Confirmation Dialogs with hit-testable buttons
- 100% transparent backdrops with hardware alpha compositing
"""

from typing import Dict, Any, List, Tuple
from PIL import Image, ImageDraw, ImageFont


def wrap_text(text: str, max_chars_per_line: int = 36) -> List[str]:
    """Splits text into clean lines for dialog presentation"""
    lines = []
    paragraphs = text.split("\n")
    for para in paragraphs:
        words = para.split()
        if not words:
            continue
        cur = ""
        for w in words:
            test = (cur + " " + w).strip()
            if len(test) > max_chars_per_line:
                lines.append(cur)
                cur = w
            else:
                cur = test
        if cur:
            lines.append(cur)
    return lines


def render_speech_bubble(text: str, max_w: int = 280) -> Image.Image:
    """Renders a sleek, dark-glass speech bubble for assistant responses"""
    lines = wrap_text(text, max_chars_per_line=34)
    if not lines:
        lines = ["..."]
    lines = lines[:5]  # Maximum 5 lines for compact floating widget

    pad = 12
    line_h = 17
    h = pad * 2 + len(lines) * line_h + 18
    w = max_w

    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Dark glass card with glowing border
    draw.rounded_rectangle(
        [1, 1, w - 2, h - 2],
        radius=12,
        fill=(15, 23, 42, 245),
        outline=(0, 243, 255, 220),
        width=1
    )

    # 2. Header
    draw.text((pad, pad - 2), "🤖 Pulsar Assistant", fill=(0, 243, 255, 255))

    # 3. Text Body
    y = pad + 18
    for line in lines:
        draw.text((pad, y), line, fill=(241, 245, 249, 240))
        y += line_h

    return img


def render_transcription_pill(text: str, is_partial: bool = True, max_w: int = 280) -> Image.Image:
    """
    Renders a sleek, frosted live transcription subtitle pill while speaking.
    - is_partial=True: Cyan pulsing border and cyan mic indicator dot
    - is_partial=False: Green confirmation border indicating final speech capture
    """
    lines = wrap_text(text, max_chars_per_line=32)[:2]
    if not lines:
        lines = ["Listening..."]

    pad_x = 12
    pad_y = 8
    line_h = 16
    h = pad_y * 2 + len(lines) * line_h + 2
    w = max_w

    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Frosted pill backdrop
    border_color = (0, 243, 255, 230) if is_partial else (34, 197, 94, 230)
    draw.rounded_rectangle(
        [1, 1, w - 2, h - 2],
        radius=min(12, h // 2),
        fill=(15, 23, 42, 240),
        outline=border_color,
        width=1
    )

    # 2. Glowing Indicator Dot
    dot_color = (0, 243, 255, 255) if is_partial else (34, 197, 94, 255)
    dot_cy = h // 2
    draw.ellipse([pad_x, dot_cy - 4, pad_x + 8, dot_cy + 4], fill=dot_color)

    # 3. Streamed Text
    y = pad_y + 1
    for idx, line in enumerate(lines):
        color = (203, 213, 225, 230) if (is_partial and idx == len(lines) - 1) else (255, 255, 255, 255)
        draw.text((pad_x + 16, y), line, fill=color)
        y += line_h

    return img


def render_notification_card(notif: Dict[str, Any], max_w: int = 310) -> Tuple[Image.Image, List[Dict[str, Any]]]:
    """
    Renders a notification alert card.
    Returns: (PIL.Image, button_hit_boxes)
    button_hit_box = {"action": str, "rect": (x0, y0, x1, y1)}
    """
    title = notif.get("title", "Notification")
    body = notif.get("body", "")
    n_type = notif.get("type", "info")
    actions = notif.get("actions", ["Show", "Dismiss"])

    # Color themes
    color_map = {
        "whatsapp": ((37, 211, 102), (37, 211, 102, 220)),   # Green
        "email": ((56, 189, 248), (56, 189, 248, 220)),       # Sky blue
        "calendar": ((245, 158, 11), (245, 158, 11, 220)),    # Amber
        "research": ((168, 85, 247), (168, 85, 247, 220)),    # Purple
        "action": ((0, 243, 255), (0, 243, 255, 220)),        # Cyan
    }
    accent_rgb, accent_rgba = color_map.get(n_type, ((0, 243, 255), (0, 243, 255, 220)))

    lines = wrap_text(body, max_chars_per_line=38)[:3]  # Up to 3 lines
    pad = 12
    h = 120
    w = max_w

    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Background Card
    draw.rounded_rectangle(
        [1, 1, w - 2, h - 2],
        radius=12,
        fill=(15, 23, 42, 248),
        outline=accent_rgba,
        width=1
    )

    # 2. Left colored indicator bar
    draw.rounded_rectangle([2, 8, 6, h - 8], radius=2, fill=accent_rgba)

    # 3. Title
    draw.text((pad + 4, pad - 2), title[:35], fill=(255, 255, 255, 255))

    # 4. Body Lines
    y = pad + 18
    for line in lines:
        draw.text((pad + 4, y), line, fill=(203, 213, 225, 230))
        y += 16

    # 5. Buttons at bottom
    buttons = []
    btn_y0 = h - 34
    btn_y1 = h - 10
    btn_w = 78
    start_x = pad + 4

    for i, act in enumerate(actions[:3]):
        bx0 = start_x + i * (btn_w + 10)
        bx1 = bx0 + btn_w
        # Button box
        draw.rounded_rectangle(
            [bx0, btn_y0, bx1, btn_y1],
            radius=6,
            fill=(*accent_rgb, 40),
            outline=(*accent_rgb, 180),
            width=1
        )
        # Center text
        draw.text((bx0 + 10, btn_y0 + 5), act, fill=(*accent_rgb, 255))
        buttons.append({"action": act, "rect": (bx0, btn_y0, bx1, btn_y1)})

    return img, buttons


def render_confirmation_dialog(action_summary: str, max_w: int = 300) -> Tuple[Image.Image, List[Dict[str, Any]]]:
    """
    Renders a Tier 3 confirmation prompt.
    Returns: (PIL.Image, button_hit_boxes)
    """
    lines = wrap_text(action_summary, max_chars_per_line=36)[:2]
    h = 115
    w = max_w
    pad = 12

    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Rose alert border
    rose_rgb = (244, 63, 94)
    draw.rounded_rectangle(
        [1, 1, w - 2, h - 2],
        radius=12,
        fill=(15, 23, 42, 250),
        outline=(*rose_rgb, 230),
        width=1
    )

    # Title
    draw.text((pad, pad - 2), "⚠️ Confirm Action", fill=(*rose_rgb, 255))

    # Summary
    y = pad + 18
    for line in lines:
        draw.text((pad, y), line, fill=(241, 245, 249, 240))
        y += 16

    # Two action buttons: [✓ Confirm]  [✕ Cancel]
    buttons = []
    btn_y0 = h - 36
    btn_y1 = h - 10

    # Confirm Button
    draw.rounded_rectangle(
        [pad, btn_y0, pad + 110, btn_y1],
        radius=6,
        fill=(34, 197, 94, 50),
        outline=(34, 197, 94, 200),
        width=1
    )
    draw.text((pad + 16, btn_y0 + 6), "✓ Confirm", fill=(34, 197, 94, 255))
    buttons.append({"action": "confirm", "rect": (pad, btn_y0, pad + 110, btn_y1)})

    # Cancel Button
    draw.rounded_rectangle(
        [pad + 125, btn_y0, pad + 235, btn_y1],
        radius=6,
        fill=(244, 63, 94, 50),
        outline=(244, 63, 94, 200),
        width=1
    )
    draw.text((pad + 145, btn_y0 + 6), "✕ Cancel", fill=(244, 63, 94, 255))
    buttons.append({"action": "cancel", "rect": (pad + 125, btn_y0, pad + 235, btn_y1)})

    return img, buttons

