from __future__ import annotations

import os
from typing import Any

import httpx

from .config import CrmSettings, WorkDriveSettings
from .exceptions import ConfigurationError, WorkDriveError


class ZohoCrmClient:
    def __init__(self, crm_settings: CrmSettings, auth_settings: WorkDriveSettings, logger) -> None:
        self.crm_settings = crm_settings
        self.auth_settings = auth_settings
        self.logger = logger
        self._access_token: str | None = None

    def update_generated_password_fields(self, record_id: str, passwords: list[str]) -> dict[str, Any]:
        if not record_id:
            raise ConfigurationError("CRM update requested but no crm_record_id was provided.")

        primary_limit = self.crm_settings.primary_password_limit
        primary_values = passwords[:primary_limit]
        overflow_values = passwords[primary_limit:]

        payload = {
            "data": [
                {
                    self.crm_settings.primary_password_field: ",".join(primary_values),
                    self.crm_settings.overflow_password_field: ",".join(overflow_values),
                }
            ]
        }

        timeout = httpx.Timeout(60.0, connect=20.0)
        with httpx.Client(timeout=timeout) as client:
            access_token = self._get_access_token(client)
            headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
            response = client.put(
                f"{self.crm_settings.api_base_url}/{self.crm_settings.module_api_name}/{record_id}",
                headers=headers,
                json=payload,
            )

        if response.status_code >= 400:
            raise WorkDriveError(
                f"Zoho CRM update failed for record '{record_id}' with status {response.status_code}: {response.text}"
            )

        data = response.json()
        self.logger.info(
            "Updated CRM record %s with %s generated passwords (%s primary, %s overflow)",
            record_id,
            len(passwords),
            len(primary_values),
            len(overflow_values),
        )
        return {
            "record_id": record_id,
            "status_code": response.status_code,
            "primary_count": len(primary_values),
            "overflow_count": len(overflow_values),
            "response": data,
        }

    def _get_access_token(self, client: httpx.Client) -> str:
        if self._access_token:
            return self._access_token

        refresh_token = os.getenv("ZOHO_WORKDRIVE_REFRESH_TOKEN")
        client_id = os.getenv("ZOHO_WORKDRIVE_CLIENT_ID")
        client_secret = os.getenv("ZOHO_WORKDRIVE_CLIENT_SECRET")
        if not refresh_token or not client_id or not client_secret:
            raise ConfigurationError(
                "Missing Zoho OAuth environment variables. Provide "
                "ZOHO_WORKDRIVE_REFRESH_TOKEN, ZOHO_WORKDRIVE_CLIENT_ID, and "
                "ZOHO_WORKDRIVE_CLIENT_SECRET."
            )

        response = client.post(
            self.auth_settings.accounts_base_url,
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
