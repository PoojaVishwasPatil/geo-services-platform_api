import csv
import io
import json
from typing import Any, Dict, List
from fastapi import UploadFile
from backend.app.schemas.service import ServiceCreate
from backend.app.schemas.bulk import BulkUploadResponse, BulkUploadErrorRow
from backend.app.repositories.service_repository import ServiceRepository
from backend.app.services.cache_service import cache_service
from backend.app.core.exceptions import AppException
from backend.app.core.logging import logger


class BulkUploadService:
    def __init__(self, repository: ServiceRepository):
        self.repository = repository

    async def process_file(self, file: UploadFile) -> BulkUploadResponse:
        content = await file.read()
        filename = file.filename or ""

        if filename.endswith(".csv"):
            return await self._process_csv(content)
        elif filename.endswith(".json"):
            return await self._process_json(content)
        else:
            raise AppException("Unsupported file format. Please upload a .csv or .json file.")

    async def _process_csv(self, content_bytes: bytes) -> BulkUploadResponse:
        try:
            text = content_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = content_bytes.decode("latin-1")

        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)

        successful_inserts = 0
        failed_inserts = 0
        errors: List[BulkUploadErrorRow] = []

        for idx, row in enumerate(rows, start=1):
            try:
                # Handle numeric conversions
                lat_str = row.get("latitude") or row.get("lat")
                lng_str = row.get("longitude") or row.get("lng")
                rating_str = row.get("rating")

                if not lat_str or not lng_str:
                    raise ValueError("Latitude and Longitude are mandatory.")

                lat = float(lat_str)
                lng = float(lng_str)
                rating = float(rating_str) if rating_str and rating_str.strip() else None

                # Handle metadata
                metadata_raw = row.get("metadata", "{}")
                if isinstance(metadata_raw, str) and metadata_raw.strip():
                    try:
                        metadata = json.loads(metadata_raw)
                    except json.JSONDecodeError:
                        metadata = {"raw": metadata_raw}
                else:
                    metadata = {}

                service_in = ServiceCreate(
                    name=row.get("name", "").strip(),
                    category=row.get("category", "").strip().lower(),
                    latitude=lat,
                    longitude=lng,
                    address=row.get("address", "").strip() or None,
                    rating=rating,
                    contact_phone=row.get("contact_phone", "").strip() or None,
                    metadata=metadata
                )

                await self.repository.create(service_in)
                successful_inserts += 1

            except Exception as e:
                failed_inserts += 1
                errors.append(
                    BulkUploadErrorRow(
                        row_number=idx,
                        data=dict(row),
                        error=str(e)
                    )
                )

        if successful_inserts > 0:
            await cache_service.invalidate_service_caches()

        return BulkUploadResponse(
            total_records=len(rows),
            successful_inserts=successful_inserts,
            failed_inserts=failed_inserts,
            errors=errors
        )

    async def _process_json(self, content_bytes: bytes) -> BulkUploadResponse:
        try:
            data = json.loads(content_bytes.decode("utf-8"))
        except Exception as e:
            raise AppException(f"Invalid JSON format: {e}")

        if not isinstance(data, list):
            raise AppException("JSON file must contain an array of service objects.")

        successful_inserts = 0
        failed_inserts = 0
        errors: List[BulkUploadErrorRow] = []

        for idx, item in enumerate(data, start=1):
            try:
                if not isinstance(item, dict):
                    raise ValueError("Item must be a JSON object.")

                service_in = ServiceCreate(
                    name=item.get("name", "").strip(),
                    category=str(item.get("category", "")).strip().lower(),
                    latitude=float(item.get("latitude")),
                    longitude=float(item.get("longitude")),
                    address=item.get("address"),
                    rating=float(item.get("rating")) if item.get("rating") is not None else None,
                    contact_phone=item.get("contact_phone"),
                    metadata=item.get("metadata", {})
                )

                await self.repository.create(service_in)
                successful_inserts += 1

            except Exception as e:
                failed_inserts += 1
                errors.append(
                    BulkUploadErrorRow(
                        row_number=idx,
                        data=item if isinstance(item, dict) else {"val": str(item)},
                        error=str(e)
                    )
                )

        if successful_inserts > 0:
            await cache_service.invalidate_service_caches()

        return BulkUploadResponse(
            total_records=len(data),
            successful_inserts=successful_inserts,
            failed_inserts=failed_inserts,
            errors=errors
        )

