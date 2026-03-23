from __future__ import annotations

from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.pdfgen.canvas import Canvas

from ..models import WifiRecord
from .common import draw_sheet_layout


LEGACY_THEME = {
    "variant": "legacy",
    "page_background": colors.HexColor("#F8FBFF"),
    "header_background": colors.white,
    "header_accent": colors.HexColor("#0F66C3"),
    "header_secondary": colors.HexColor("#53A8FF"),
    "header_rule": colors.HexColor("#A7D0FF"),
    "panel_background": colors.white,
    "panel_border": colors.HexColor("#B9D4F2"),
    "label_band": colors.HexColor("#0F66C3"),
    "label_text": colors.white,
    "value_text": colors.HexColor("#0B2B4D"),
    "section_background": colors.white,
    "section_border": colors.HexColor("#C6DAEF"),
    "section_title_band": colors.HexColor("#E7F1FC"),
    "section_title_text": colors.HexColor("#0B2B4D"),
    "title_text": colors.HexColor("#0B2B4D"),
    "body_text": colors.HexColor("#223548"),
    "bullet": colors.HexColor("#0F66C3"),
    "note_background": colors.HexColor("#EAF4FF"),
    "note_text": colors.HexColor("#0B2B4D"),
    "support_background": colors.white,
    "support_border": colors.HexColor("#C6DAEF"),
    "footer_background": colors.HexColor("#0F66C3"),
    "footer_text": colors.white,
    "qr_border": colors.HexColor("#7DB7F0"),
}


def draw_legacy_template(
    canvas: Canvas,
    record: WifiRecord,
    building_name: str,
    qr_path: Path,
    settings: Any,
    fonts: dict[str, str],
    sheet_number: int,
    sheet_total: int,
) -> None:
    draw_sheet_layout(canvas, record, building_name, qr_path, settings, fonts, LEGACY_THEME)
