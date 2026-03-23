from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INVALID_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]+")
MULTI_HYPHEN = re.compile(r"-{2,}")


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_json_file(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json_file(path: str | Path, payload: Any) -> Path:
    target = Path(path)
    ensure_directory(target.parent)
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return target


def resolve_repo_path(value: str | Path | None) -> Path | None:
    if value in (None, ""):
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def sanitize_filename(value: str, default: str = "item") -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    cleaned = INVALID_FILENAME_CHARS.sub("-", normalized.strip())
    cleaned = MULTI_HYPHEN.sub("-", cleaned).strip("-.")
    return cleaned or default


def batch_timestamp(now: datetime | None = None) -> str:
    moment = now or datetime.now()
    return moment.strftime("%Y%m%d-%H%M%S-%f")


def relative_to_root(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path.resolve())


def mask_secret(value: str | None, visible_chars: int = 4) -> str:
    if not value:
        return ""
    if len(value) <= visible_chars:
        return "*" * len(value)
    return "*" * (len(value) - visible_chars) + value[-visible_chars:]


def truncate_for_log(value: str, limit: int = 96) -> str:
    if len(value) <= limit:
        return value
    return f"{value[:limit - 3]}..."
