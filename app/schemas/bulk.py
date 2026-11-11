from typing import List, Optional
from pydantic import BaseModel


class BulkUploadErrorRow(BaseModel):
    row_number: int
    data: dict
    error: str


class BulkUploadResponse(BaseModel):
    total_records: int
    successful_inserts: int
    failed_inserts: int
    errors: List[BulkUploadErrorRow]

