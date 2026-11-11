"""The DRAFT stamp of a preview: a large diagonal "DRAFT, NOT FILED" in light
grey across every page, and a small footer line saying when the preview was
printed. Drawn after the figures, translucent, so every figure stays readable
through it. The time comes in from the caller: the engine never reads a clock."""

import math
from datetime import datetime
from zoneinfo import ZoneInfo

DRAFT_STAMP = "DRAFT, NOT FILED"
# light enough that every figure under it stays readable
STAMP_OPACITY = 0.15
# how much of the page's diagonal the stamp spans
STAMP_SPAN = 0.8
FOOTER_SIZE = 7
# the footer's baseline, above the paper's bottom edge and below every form's frame
FOOTER_Y = 10
MANILA = ZoneInfo("Asia/Manila")


def manila_stamp(at: datetime) -> str:
    """"11 Oct 2026, 2:05 PM", on Manila's clock."""
    if at.tzinfo is None:
        at = at.replace(tzinfo=MANILA)
    local = at.astimezone(MANILA)
    hour = local.hour % 12 or 12
    return f"{local:%d %b %Y}, {hour}:{local:%M} {local:%p}"


def preview_footer(printed_at: datetime) -> str:
    return f"Preview printed {manila_stamp(printed_at)} (Manila) from Sentire Ledger. Not the filed return."


def stamp_draft(c, width: float, height: float, font: str, met, printed_at: datetime) -> None:
    """Stamp one page: the diagonal DRAFT mark centred on the page, and the footer."""
    angle = math.atan2(height, width)
    size = STAMP_SPAN * math.hypot(width, height) / met.width(DRAFT_STAMP, 1)
    w = met.width(DRAFT_STAMP, size)
    h = met.cap_height(size)
    cos, sin = math.cos(angle), math.sin(angle)
    c.saveState()
    c.setFillColorRGB(0, 0, 0)
    c.setFillAlpha(STAMP_OPACITY)
    c.setFont(font, size)
    c.translate(width / 2 - (w / 2) * cos + (h / 2) * sin, height / 2 - (w / 2) * sin - (h / 2) * cos)
    c.rotate(math.degrees(angle))
    c.drawString(0, 0, DRAFT_STAMP)
    c.restoreState()
    footer = preview_footer(printed_at)
    c.setFillColorRGB(0, 0, 0)
    c.setFont(font, FOOTER_SIZE)
    c.drawString(width / 2 - met.width(footer, FOOTER_SIZE) / 2, FOOTER_Y, footer)
