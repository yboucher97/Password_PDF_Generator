from __future__ import annotations

import argparse

from .schema import export_schema
from .utils import PROJECT_ROOT, write_json_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Export the WiFi PDF JSON schema.")
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "wifi_pdf" / "wifi_records.schema.json"),
        help="Path to write the JSON schema.",
    )
    args = parser.parse_args()
    write_json_file(args.output, export_schema())
    print(args.output)


if __name__ == "__main__":
    main()
