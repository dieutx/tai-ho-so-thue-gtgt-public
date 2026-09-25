"""Tiện ích dùng chung cho test.

Bộ test chạy hoàn toàn offline: không có request nào ra Internet, dữ liệu do
provider mock sinh ra là tất định.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from taxdoc.core.config import Settings
from taxdoc.core.models import DocumentRecord


def make_settings(output_dir: str | Path, **overrides) -> Settings:
    """Tạo :class:`Settings` cho test với giá trị mặc định hợp lý."""
    values = {
        "from_date": date(2026, 1, 1),
        "to_date": date(2026, 1, 31),
        "output_dir": Path(output_dir),
        "provider": "mock",
    }
    values.update(overrides)
    return Settings(**values)


def make_record(record_id: str = "DOC-0001", **overrides) -> DocumentRecord:
    """Tạo một :class:`DocumentRecord` mẫu."""
    values = {
        "record_id": record_id,
        "category": "Declaration",
        "subject": "Sample document",
        "period": "01/2026",
        "submitted_on": "05/01/2026",
        "status": "available",
    }
    values.update(overrides)
    return DocumentRecord(**values)


def payload_for(record: DocumentRecord) -> bytes:
    """Nội dung JSON tất định cho một bản ghi."""
    return json.dumps({"record_id": record.record_id}).encode("utf-8")
