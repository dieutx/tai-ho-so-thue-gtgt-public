"""Storage adapter: ghi tài liệu và xuất danh sách có cấu trúc.

Mọi nơi cần lưu trữ đều đi qua lớp trừu tượng :class:`StorageAdapter`, nên có
thể đổi sang kho lưu trữ khác (S3, cơ sở dữ liệu, thư mục mạng...) mà không
đụng tới pipeline. Bản kèm theo ghi xuống thư mục cục bộ và xuất ``index.csv`` /
``index.json``.

Tài liệu đã có trên đĩa sẽ được bỏ qua ở lần chạy sau, nên có thể chạy tiếp khi
bị gián đoạn.
"""

from __future__ import annotations

import csv
import json
import logging
import re
from abc import ABC, abstractmethod
from collections.abc import Iterable
from pathlib import Path

from ..core.errors import StorageError
from ..core.models import DocumentRecord

LOGGER_NAME = "taxdoc.storage"
INDEX_CSV = "index.csv"
INDEX_JSON = "index.json"
DEFAULT_EXTENSION = "json"


def slugify(value: str, maximum: int = 60) -> str:
    """Chuyển một chuỗi thành phần tên file an toàn trên mọi hệ điều hành."""
    text = re.sub(r"[^A-Za-z0-9._-]+", "-", (value or "").strip()).strip("-._")
    return text[:maximum] or "unknown"


class StorageAdapter(ABC):
    """Hợp đồng cho mọi tầng lưu trữ."""

    @abstractmethod
    def exists(self, record: DocumentRecord) -> bool:
        """Trả ``True`` nếu tài liệu đã có sẵn và còn nguyên vẹn."""

    @abstractmethod
    def save(self, record: DocumentRecord, payload: bytes) -> Path:
        """Ghi tài liệu và trả về đường dẫn đã ghi."""

    @abstractmethod
    def export_index(self, records: Iterable[DocumentRecord]) -> tuple[Path, Path] | None:
        """Xuất danh sách tài liệu; trả ``None`` nếu không có tài liệu nào."""

    def close(self) -> None:
        """Giải phóng tài nguyên. Mặc định không làm gì."""
        return None


class FileSystemStorageAdapter(StorageAdapter):
    """Ghi tài liệu xuống một thư mục và xuất danh sách CSV/JSON."""

    def __init__(
        self,
        directory: str | Path,
        *,
        extension: str = DEFAULT_EXTENSION,
        logger: logging.Logger | None = None,
    ) -> None:
        self.directory = Path(directory)
        self.extension = extension.lstrip(".")
        self.logger = logger or logging.getLogger(LOGGER_NAME)

    def filename_for(self, record: DocumentRecord) -> str:
        """Tên file tất định theo mã tài liệu (kèm kỳ và loại nếu có)."""
        parts = [slugify(record.record_id, 50)]
        for value in (record.period, record.category):
            if value:
                parts.append(slugify(value, 30))
        return f"{'-'.join(parts)}.{self.extension}"

    def path_for(self, record: DocumentRecord) -> Path:
        return self.directory / self.filename_for(record)

    def exists(self, record: DocumentRecord) -> bool:
        path = self.path_for(record)
        return path.is_file() and path.stat().st_size > 0

    def save(self, record: DocumentRecord, payload: bytes) -> Path:
        if not payload:
            raise StorageError(f"nội dung rỗng cho {record.record_id}")
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.path_for(record)
        path.write_bytes(payload)
        record.filename = path.name
        self.logger.info("Đã lưu %s (%s bytes)", path.name, f"{len(payload):,}")
        return path

    def export_index(
        self, records: Iterable[DocumentRecord]
    ) -> tuple[Path, Path] | None:
        ordered = sorted(records, key=lambda item: item.record_id)
        if not ordered:
            return None
        rows = [record.to_dict() for record in ordered]
        self.directory.mkdir(parents=True, exist_ok=True)

        csv_path = self.directory / INDEX_CSV
        with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

        json_path = self.directory / INDEX_JSON
        json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        return csv_path, json_path


__all__ = [
    "DEFAULT_EXTENSION",
    "INDEX_CSV",
    "INDEX_JSON",
    "FileSystemStorageAdapter",
    "StorageAdapter",
    "slugify",
]
