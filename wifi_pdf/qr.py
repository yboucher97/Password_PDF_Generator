from __future__ import annotations

import re
from pathlib import Path

import qrcode

from .models import WifiRecord


QR_ESCAPE_PATTERN = re.compile(r'([\\;,:"])')


def escape_wifi_value(value: str) -> str:
    return QR_ESCAPE_PATTERN.sub(r"\\\1", value)


def build_wifi_qr_string(record: WifiRecord) -> str:
    fields = [f"T:{record.auth_type}", f"S:{escape_wifi_value(record.ssid)}"]
    if record.auth_type != "nopass" and record.password is not None:
        fields.append(f"P:{escape_wifi_value(record.password)}")
    if record.hidden:
        fields.append("H:true")
    return "WIFI:" + ";".join(fields) + ";;"


def generate_qr_png(payload: str, output_path: Path) -> Path:
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=2)
    qr.add_data(payload)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    return output_path
