from __future__ import annotations

from pathlib import Path

from pypdf import PdfWriter


def merge_pdfs(pdf_paths: list[Path], output_path: Path) -> Path:
    writer = PdfWriter()
    for path in pdf_paths:
        writer.append(str(path))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as handle:
        writer.write(handle)
    writer.close()
    return output_path
