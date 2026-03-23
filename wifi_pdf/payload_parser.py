from __future__ import annotations

import csv
import json
from io import StringIO
from typing import Any
from urllib.parse import parse_qs, urlparse

from .exceptions import PayloadValidationError


BUILDING_NAME_KEYS = ("building_name", "Building_Name", "Deal_Name", "deal_name", "name", "Name")
TEMPLATE_NAME_KEYS = ("template_name", "Template_Name")
WORKDRIVE_KEYS = (
    "workdrive_folder_id",
    "Workdrive_folder_id",
    "workdrive_folder",
    "Workdrive_folder",
    "WorkDrive_folder",
    "workdrive_url",
)
SSID_PREFIX_KEYS = ("ssid_prefix", "SSID_Prefix")
UNITS_KEYS = ("units", "Units", "unit_s", "Unit_s", "unit_list")
SSIDS_KEYS = ("ssids", "SSIDs", "ssid_list", "SSID_List", "SSID_s")
PASSWORDS_KEYS = ("passwords", "Passwords", "password_list", "Mots_de_passes", "PASSWORD_List")
UNIT_LABEL_KEYS = ("unit_labels", "Unit_Labels", "unit_label_list")
AUTH_TYPE_KEYS = ("auth_type", "AUTH_TYPE")
HIDDEN_KEYS = ("hidden", "Hidden")

WORKDRIVE_QUERY_KEYS = ("id", "folder_id", "resource_id", "parent_id")


def _get_first(mapping: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in mapping:
            return mapping[key]
    return None


def _stringify(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _clean_scalar(value: Any) -> str | None:
    text = _stringify(value)
    if text is None:
        return None
    cleaned = text.strip()
    return cleaned or None


def _load_json_list(text: str, field_name: str) -> list[str] | None:
    if not text.startswith("["):
        return None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise PayloadValidationError(f"{field_name} looks like JSON but could not be parsed: {exc}") from exc
    if not isinstance(payload, list):
        raise PayloadValidationError(f"{field_name} JSON input must be an array.")
    return [_clean_csv_token(item, field_name) for item in payload if _clean_csv_token(item, field_name) is not None]


def _clean_csv_token(value: Any, field_name: str) -> str | None:
    text = _stringify(value)
    if text is None:
        return None
    cleaned = text.strip()
    if cleaned in {"", "null", "None"}:
        return None
    return cleaned


def _parse_delimited_string(text: str, field_name: str) -> list[str]:
    json_list = _load_json_list(text, field_name)
    if json_list is not None:
        return json_list

    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if normalized == "":
        return []

    if "\n" in normalized:
        return [token for line in normalized.split("\n") if (token := _clean_csv_token(line, field_name)) is not None]

    delimiter = ","
    if ";" in normalized and "," not in normalized:
        delimiter = ";"

    reader = csv.reader(StringIO(normalized), delimiter=delimiter, skipinitialspace=True)
    try:
        row = next(reader)
    except StopIteration:
        return []
    return [token for token in (_clean_csv_token(item, field_name) for item in row) if token is not None]


def parse_string_list(value: Any, field_name: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [token for token in (_clean_csv_token(item, field_name) for item in value) if token is not None]

    text = _stringify(value)
    if text is None:
        return []
    return _parse_delimited_string(text, field_name)


def normalize_ssid_prefix(value: Any) -> str:
    text = _clean_scalar(value)
    if text is None or text == "null":
        return "app"
    if text in {"None", "Nada"}:
        return ""
    return text


def extract_workdrive_folder_id(value: Any) -> str | None:
    text = _clean_scalar(value)
    if text is None:
        return None

    if "/" not in text and "?" not in text and "#" not in text:
        return text

    parsed = urlparse(text)
    query = parse_qs(parsed.query)
    for key in WORKDRIVE_QUERY_KEYS:
        values = query.get(key)
        if values:
            candidate = _clean_scalar(values[0])
            if candidate:
                return candidate

    fragment = parsed.fragment.strip("/")
    if fragment:
        fragment_parts = [part for part in fragment.split("/") if part]
        if fragment_parts:
            return fragment_parts[-1]

    path_parts = [part for part in parsed.path.split("/") if part]
    if path_parts:
        return path_parts[-1]

    raise PayloadValidationError(f"Could not extract a WorkDrive folder id from '{text}'.")


def _build_records_from_ssids(
    mapping: dict[str, Any],
    ssids: list[str],
    passwords: list[str],
    unit_labels: list[str],
) -> list[dict[str, Any]]:
    if not ssids:
        raise PayloadValidationError("No SSIDs were provided.")
    if len(ssids) != len(passwords):
        raise PayloadValidationError(
            f"SSID count ({len(ssids)}) does not match password count ({len(passwords)})."
        )
    if unit_labels and len(unit_labels) != len(ssids):
        raise PayloadValidationError(
            f"unit_labels count ({len(unit_labels)}) does not match SSID count ({len(ssids)})."
        )

    auth_type = _clean_scalar(_get_first(mapping, AUTH_TYPE_KEYS)) or "WPA"
    hidden_value = _get_first(mapping, HIDDEN_KEYS)
    hidden = bool(hidden_value) if isinstance(hidden_value, bool) else str(hidden_value).strip().lower() == "true"

    records: list[dict[str, Any]] = []
    for index, ssid in enumerate(ssids):
        record = {
            "ssid": ssid,
            "password": passwords[index],
            "auth_type": auth_type,
            "hidden": hidden,
        }
        if unit_labels:
            record["unit_label"] = unit_labels[index]
        records.append(record)
    return records


def _build_records_from_units(mapping: dict[str, Any], units: list[str], passwords: list[str]) -> list[dict[str, Any]]:
    if not units:
        raise PayloadValidationError("No units were provided.")
    if len(units) != len(passwords):
        raise PayloadValidationError(
            f"Unit count ({len(units)}) does not match password count ({len(passwords)})."
        )

    prefix = normalize_ssid_prefix(_get_first(mapping, SSID_PREFIX_KEYS))
    auth_type = _clean_scalar(_get_first(mapping, AUTH_TYPE_KEYS)) or "WPA"
    hidden_value = _get_first(mapping, HIDDEN_KEYS)
    hidden = bool(hidden_value) if isinstance(hidden_value, bool) else str(hidden_value).strip().lower() == "true"

    records: list[dict[str, Any]] = []
    for index, unit in enumerate(units):
        records.append(
            {
                "ssid": f"{prefix}{unit}",
                "password": passwords[index],
                "auth_type": auth_type,
                "hidden": hidden,
                "unit_label": unit,
            }
        )
    return records


def normalize_payload(raw_payload: Any) -> dict[str, Any]:
    if isinstance(raw_payload, list):
        return {"building_name": "wifi-batch", "records": raw_payload}
    if not isinstance(raw_payload, dict):
        raise PayloadValidationError("Payload must be a JSON object or an array of records.")

    payload = dict(raw_payload)
    building_name = _clean_scalar(_get_first(payload, BUILDING_NAME_KEYS))
    template_name = _clean_scalar(_get_first(payload, TEMPLATE_NAME_KEYS)) or "basic_template"
    workdrive_folder_id = extract_workdrive_folder_id(_get_first(payload, WORKDRIVE_KEYS))

    if "records" in payload:
        normalized = dict(payload)
        if building_name is not None:
            normalized["building_name"] = building_name
        if workdrive_folder_id is not None:
            normalized["workdrive_folder_id"] = workdrive_folder_id
        normalized["template_name"] = template_name
        return normalized

    passwords = parse_string_list(_get_first(payload, PASSWORDS_KEYS), "passwords")
    ssids = parse_string_list(_get_first(payload, SSIDS_KEYS), "ssids")
    units = parse_string_list(_get_first(payload, UNITS_KEYS), "units")
    unit_labels = parse_string_list(_get_first(payload, UNIT_LABEL_KEYS), "unit_labels")

    if not building_name:
        raise PayloadValidationError("Missing building_name or Deal_Name.")
    if not passwords:
        raise PayloadValidationError("No passwords were provided. Send records, passwords, or Mots_de_passes.")

    if ssids:
        records = _build_records_from_ssids(payload, ssids, passwords, unit_labels or units)
    elif units:
        records = _build_records_from_units(payload, units, passwords)
    else:
        raise PayloadValidationError(
            "No SSIDs or units were provided. Send records, ssids/ssid_list, or units/Unit_s."
        )

    normalized = {
        "building_name": building_name,
        "template_name": template_name,
        "records": records,
    }
    if workdrive_folder_id is not None:
        normalized["workdrive_folder_id"] = workdrive_folder_id
    return normalized
