import sys

from PIL import Image, ImageDraw, ImageFont

from src.constants import (
    COLOR_GREEN,
    COLOR_GREY,
    COLOR_RED,
    COLOR_YELLOW,
    THRESHOLD_RED,
    THRESHOLD_YELLOW,
)

# macOS menu bar icons should be 22pt, rendered at 2x for Retina = 44px
# Linux icons are typically 24px
_RENDER_SIZE = 44 if sys.platform == "darwin" else 48


def _color_for_utilization(utilization: float | None) -> str:
    if utilization is None:
        return COLOR_GREY
    if utilization >= THRESHOLD_RED:
        return COLOR_RED
    if utilization >= THRESHOLD_YELLOW:
        return COLOR_YELLOW
    return COLOR_GREEN


def _label_for_utilization(utilization: float | None) -> str:
    if utilization is None:
        return "?"
    pct = int(utilization * 100)
    if pct > 100:
        return "100+"
    return str(pct)


def render_tray_icon(utilization: float | None) -> Image.Image:
    """Render a tray icon showing the usage percentage on a colored circle.

    Returns an image at 2x resolution for Retina support (44x44 on macOS).
    """
    size = _RENDER_SIZE
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    color = _color_for_utilization(utilization)
    draw.ellipse([1, 1, size - 2, size - 2], fill=color)

    label = _label_for_utilization(utilization)

    # Font size proportional to icon, smaller for longer text
    if len(label) <= 2:
        font_size = size * 55 // 100
    elif len(label) == 3:
        font_size = size * 42 // 100
    else:
        font_size = size * 32 // 100

    font = None
    font_paths = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFCompact.ttf",
        "/System/Library/Fonts/SFNSMono.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    for path in font_paths:
        try:
            font = ImageFont.truetype(path, font_size)
            break
        except (OSError, AttributeError):
            continue
    if font is None:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), label, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (size - text_w) // 2
    y = (size - text_h) // 2 - bbox[1]

    draw.text((x, y), label, fill="white", font=font)

    return img
