from __future__ import annotations

import shutil
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import AppSettings, load_settings
from .exceptions import WorkDriveError
from .logging_utils import configure_logging
from .merge import merge_pdfs
from .models import WifiBatchRequest, parse_payload
from .qr import build_wifi_qr_string, generate_qr_png
from .renderer import PdfRenderer
from .utils import (
    batch_timestamp,
    ensure_directory,
    relative_to_root,
    sanitize_filename,
    write_json_file,
)
from .workdrive import ZohoWorkDriveClient


@dataclass(slots=True)
class RecordOutput:
    index: int
    ssid: str
    pdf_path: str
    qr_path: str


@dataclass(slots=True)
class BatchOutput:
    batch_id: str
    building_name: str
    template_name: str
    batch_dir: str
    merged_pdf_path: str
    manifest_path: str
    deleted_local_batch: bool
    record_count: int
    records: list[RecordOutput]
    uploads: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["records"] = [asdict(record) for record in self.records]
        return payload


class WifiPdfPipeline:
    def __init__(self, settings: AppSettings, logger) -> None:
        self.settings = settings
        self.logger = logger
        self.renderer = PdfRenderer(settings, logger)

    def process_payload(self, raw_payload: Any) -> BatchOutput:
        batch = parse_payload(raw_payload)
        return self.process_batch(batch)

    def process_batch(self, batch: WifiBatchRequest) -> BatchOutput:
        batch_id = f"{batch_timestamp()}-{sanitize_filename(batch.building_name)}-{sanitize_filename(batch.template_name)}"
        root_dir = ensure_directory(self.settings.output.root_dir)
        batch_dir = ensure_directory(root_dir / batch_id)
        qr_dir = ensure_directory(batch_dir / "qr")
        individual_dir = ensure_directory(batch_dir / "individual")
        merged_dir = ensure_directory(batch_dir / "merged")

        self.logger.info(
            "Starting batch %s for building '%s' with %s records",
            batch_id,
            batch.building_name,
            len(batch.records),
        )

        record_outputs: list[RecordOutput] = []
        pdf_paths: list[Path] = []

        for index, record in enumerate(batch.records, start=1):
            filename_base = sanitize_filename(
                f"{batch.building_name}-{record.unit_label or record.ssid}-{index}"
            )
            qr_payload = build_wifi_qr_string(record)
            qr_path = qr_dir / f"{filename_base}-qr.png"
            pdf_path = individual_dir / f"{filename_base}.pdf"

            generate_qr_png(qr_payload, qr_path)
            self.renderer.render(
                record=record,
                building_name=batch.building_name,
                qr_path=qr_path,
                output_path=pdf_path,
                template_name=batch.template_name,
                sheet_number=index,
                sheet_total=len(batch.records),
            )

            pdf_paths.append(pdf_path)
            record_outputs.append(
                RecordOutput(
                    index=index,
                    ssid=record.ssid,
                    pdf_path=relative_to_root(pdf_path),
                    qr_path=relative_to_root(qr_path),
                )
            )
            self.logger.info("Generated PDF for SSID '%s'", record.ssid)

        merged_pdf_path = merge_pdfs(
            pdf_paths,
            merged_dir / f"{sanitize_filename(batch.building_name)}-merged.pdf",
        )

        manifest_payload = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "batch_id": batch_id,
            "building_name": batch.building_name,
            "template_name": batch.template_name,
            "record_count": len(batch.records),
            "records": [asdict(record) for record in record_outputs],
            "merged_pdf_path": relative_to_root(merged_pdf_path),
            "workdrive_folder_id_requested": batch.workdrive_folder_id,
        }
        manifest_path = write_json_file(batch_dir / self.settings.output.manifest_filename, manifest_payload)

        uploads: list[dict[str, Any]] = []
        deleted_local_batch = False

        if self.settings.workdrive.enabled:
            client = ZohoWorkDriveClient(self.settings.workdrive, self.logger)
            folder_id = client.resolve_upload_folder_id(batch.workdrive_folder_id)
            upload_candidates: list[Path] = []
            if self.settings.workdrive.upload_individual_pdfs:
                upload_candidates.extend(pdf_paths)
            if self.settings.workdrive.upload_merged_pdf:
                upload_candidates.append(merged_pdf_path)

            for path in upload_candidates:
                uploads.append(client.upload_file(path, folder_id))

            if self.settings.workdrive.cleanup_local_after_upload:
                try:
                    shutil.rmtree(batch_dir)
                    deleted_local_batch = True
                except OSError as exc:
                    raise WorkDriveError(f"Upload succeeded but local cleanup failed: {exc}") from exc

        if not self.settings.output.keep_qr_images and not deleted_local_batch:
            shutil.rmtree(qr_dir, ignore_errors=True)
            for record in record_outputs:
                record.qr_path = ""

        self.logger.info("Completed batch %s", batch_id)
        return BatchOutput(
            batch_id=batch_id,
            building_name=batch.building_name,
            template_name=batch.template_name,
            batch_dir=relative_to_root(batch_dir),
            merged_pdf_path=relative_to_root(merged_pdf_path),
            manifest_path=relative_to_root(manifest_path),
            deleted_local_batch=deleted_local_batch,
            record_count=len(batch.records),
            records=record_outputs,
            uploads=uploads,
        )


def process_payload(
    payload: Any,
    config_path: str | Path | None = None,
    log_level: str = "INFO",
) -> BatchOutput:
    settings = load_settings(config_path)
    logger = configure_logging(settings.output.root_dir / "logs", log_level)
    pipeline = WifiPdfPipeline(settings, logger)
    return pipeline.process_payload(payload)
