from __future__ import annotations

from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.pdfgen.canvas import Canvas

from ..models import WifiRecord
from .common import draw_sheet_layout


MODERN_THEME = {
    "variant": "modern",
    "page_background": colors.HexColor("#F3F8FE"),
    "header_background": colors.HexColor("#0A4F94"),
    "header_accent": colors.HexColor("#25A4FF"),
    "header_secondary": colors.HexColor("#1D84E6"),
    "header_rule": colors.HexColor("#80D0FF"),
    "panel_background": colors.white,
    "panel_border": colors.HexColor("#B8D6F6"),
    "label_band": colors.HexColor("#0A4F94"),
    "label_text": colors.white,
    "value_text": colors.HexColor("#082845"),
    "section_background": colors.white,
    "section_border": colors.HexColor("#BCD8F4"),
    "section_title_band": colors.HexColor("#0A4F94"),
    "section_title_text": colors.white,
    "title_text": colors.HexColor("#0D2A47"),
    "body_text": colors.HexColor("#203347"),
    "bullet": colors.HexColor("#1D84E6"),
    "note_background": colors.HexColor("#E1F0FF"),
    "note_text": colors.HexColor("#0B3B68"),
    "support_background": colors.white,
    "support_border": colors.HexColor("#BCD8F4"),
    "footer_background": colors.HexColor("#0D2A47"),
    "footer_text": colors.white,
    "qr_border": colors.HexColor("#D6EBFF"),
}


def draw_modern_template(
    canvas: Canvas,
    record: WifiRecord,
    building_name: str,
    qr_path: Path,
    settings: Any,
    fonts: dict[str, str],
    sheet_number: int,
    sheet_total: int,
) -> None:
    draw_sheet_layout(canvas, record, building_name, qr_path, settings, fonts, MODERN_THEME)
