from __future__ import annotations

from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.pdfgen.canvas import Canvas

from ..models import WifiRecord
from .common import draw_sheet_layout


BASIC_THEME = {
    "variant": "basic",
    "page_background": colors.white,
    "header_background": colors.white,
    "header_accent": colors.HexColor("#0A4F94"),
    "header_secondary": colors.HexColor("#DCEBFA"),
    "header_rule": colors.HexColor("#0A4F94"),
    "panel_background": colors.white,
    "panel_border": colors.HexColor("#C9D6E2"),
    "label_band": colors.HexColor("#F3F7FB"),
    "label_text": colors.HexColor("#1F2937"),
    "value_text": colors.HexColor("#111827"),
    "section_background": colors.white,
    "section_border": colors.HexColor("#D7E0E8"),
    "section_title_band": colors.white,
    "section_title_text": colors.HexColor("#0A4F94"),
    "title_text": colors.HexColor("#0F172A"),
    "body_text": colors.HexColor("#1F2937"),
    "bullet": colors.HexColor("#0A4F94"),
    "note_background": colors.HexColor("#F8FAFC"),
    "note_text": colors.HexColor("#0F172A"),
    "support_background": colors.white,
    "support_border": colors.HexColor("#D7E0E8"),
    "footer_background": colors.HexColor("#F8FAFC"),
    "footer_text": colors.HexColor("#0F172A"),
    "qr_border": colors.HexColor("#D7E0E8"),
}


def draw_basic_template(
    canvas: Canvas,
    record: WifiRecord,
    building_name: str,
    qr_path: Path,
    settings: Any,
    fonts: dict[str, str],
    sheet_number: int,
    sheet_total: int,
) -> None:
    draw_sheet_layout(canvas, record, building_name, qr_path, settings, fonts, BASIC_THEME)
