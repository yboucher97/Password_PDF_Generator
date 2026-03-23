from __future__ import annotations

from .models import WifiBatchRequest


def export_schema() -> dict:
    schema = WifiBatchRequest.model_json_schema()
    schema["title"] = "WiFi PDF Batch Request"
    schema["description"] = (
        "Recommended top-level schema for tenant WiFi PDF generation. "
        "A raw array of records is also accepted for backward compatibility."
    )
    return schema
