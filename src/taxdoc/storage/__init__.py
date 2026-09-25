"""Tầng lưu trữ: các storage adapter ghi tài liệu và xuất danh sách."""

from __future__ import annotations

from .exporter import FileSystemStorageAdapter, StorageAdapter, slugify

__all__ = ["FileSystemStorageAdapter", "StorageAdapter", "slugify"]
