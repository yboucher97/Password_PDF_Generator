from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx

from .config import WorkDriveSettings
from .exceptions import ConfigurationError, WorkDriveError


class ZohoWorkDriveClient:
    def __init__(self, settings: WorkDriveSettings, logger) -> None:
        self.settings = settings
        self.logger = logger
        self._access_token: str | None = None

    def resolve_folder_id(self, request_folder_id: str | None) -> str:
        folder_id = (
            request_folder_id
            or os.getenv("ZOHO_WORKDRIVE_PARENT_FOLDER_ID")
            or self.settings.parent_folder_id
        )
        if not folder_id:
            raise ConfigurationError(
                "WorkDrive upload is enabled but no folder id was provided. "
                "Send workdrive_folder_id in JSON or set ZOHO_WORKDRIVE_PARENT_FOLDER_ID."
            )
        return folder_id

    def _get_access_token(self, client: httpx.Client) -> str:
        if self._access_token:
            return self._access_token

        direct_token = os.getenv("ZOHO_WORKDRIVE_ACCESS_TOKEN")
        if direct_token:
            self._access_token = direct_token
            return direct_token

        refresh_token = os.getenv("ZOHO_WORKDRIVE_REFRESH_TOKEN")
        client_id = os.getenv("ZOHO_WORKDRIVE_CLIENT_ID")
        client_secret = os.getenv("ZOHO_WORKDRIVE_CLIENT_SECRET")
        if not refresh_token or not client_id or not client_secret:
            raise ConfigurationError(
                "Missing Zoho OAuth environment variables. Set ZOHO_WORKDRIVE_ACCESS_TOKEN "
                "or provide ZOHO_WORKDRIVE_REFRESH_TOKEN, ZOHO_WORKDRIVE_CLIENT_ID, and "
                "ZOHO_WORKDRIVE_CLIENT_SECRET."
            )

        response = client.post(
            self.settings.accounts_base_url,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id,
                "client_secret": client_secret,
            },
        )
        if response.status_code >= 400:
            raise WorkDriveError(
                f"Zoho OAuth refresh failed with status {response.status_code}: {response.text}"
            )

        payload = response.json()
        access_token = payload.get("access_token")
        if not access_token:
            raise WorkDriveError(f"Zoho OAuth refresh did not return an access token: {payload}")
        self._access_token = access_token
        return access_token

    def upload_file(self, path: Path, folder_id: str) -> dict[str, Any]:
        timeout = httpx.Timeout(60.0, connect=20.0)
        with httpx.Client(timeout=timeout) as client:
            access_token = self._get_access_token(client)
            headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
            params = {
                "parent_id": folder_id,
                "filename": path.name,
                "override-name-exist": "false",
            }

            with path.open("rb") as file_handle:
                response = client.post(
                    f"{self.settings.api_base_url}/upload",
                    headers=headers,
                    params=params,
                    files={self.settings.upload_field_name: (path.name, file_handle, "application/pdf")},
                )

        if response.status_code >= 400:
            raise WorkDriveError(
                f"WorkDrive upload failed for '{path.name}' with status {response.status_code}: {response.text}"
            )

        try:
            payload = response.json()
        except json.JSONDecodeError:
            payload = {"raw_response": response.text}

        data = payload.get("data")
        file_id = None
        permalink = None
        if isinstance(data, list) and data:
            first = data[0]
            if isinstance(first, dict):
                file_id = first.get("id")
                attributes = first.get("attributes")
                if isinstance(attributes, dict):
                    permalink = attributes.get("permalink")
        elif isinstance(data, dict):
            file_id = data.get("id")
            attributes = data.get("attributes")
            if isinstance(attributes, dict):
                permalink = attributes.get("permalink")

        self.logger.info("Uploaded '%s' to WorkDrive folder %s", path.name, folder_id)
        return {
            "filename": path.name,
            "folder_id": folder_id,
            "file_id": file_id,
            "permalink": permalink,
            "status_code": response.status_code,
        }
