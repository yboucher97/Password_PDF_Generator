from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request

from .config import load_settings
from .exceptions import ConfigurationError, PayloadValidationError, RenderingError, WorkDriveError
from .logging_utils import configure_logging
from .pipeline import WifiPdfPipeline
from .utils import relative_to_root


settings = load_settings()
logger = configure_logging(settings.output.root_dir / "logs")
pipeline = WifiPdfPipeline(settings, logger)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("WiFi PDF API starting with config %s", relative_to_root(settings.config_path))
    yield
    logger.info("WiFi PDF API shutting down")


app = FastAPI(title="WiFi PDF Generator", version="1.0.0", lifespan=lifespan)


def _validate_api_key(provided_api_key: str | None) -> None:
    expected_api_key = os.getenv(settings.api.api_key_env)
    if expected_api_key and provided_api_key != expected_api_key:
        raise HTTPException(status_code=401, detail="Invalid X-API-Key")


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "config_path": relative_to_root(settings.config_path),
        "output_root": relative_to_root(settings.output.root_dir),
    }


@app.post("/webhooks/zoho/wifi-pdfs")
async def create_wifi_pdfs(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> dict:
    _validate_api_key(x_api_key)

    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON body: {exc}") from exc

    try:
        result = pipeline.process_payload(payload)
    except PayloadValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ConfigurationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except WorkDriveError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except RenderingError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return result.to_dict()
