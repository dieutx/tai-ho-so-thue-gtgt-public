"""Cây ngoại lệ của framework.

Mọi lỗi có thể dự đoán đều kế thừa :class:`TaxdocError` để CLI chỉ cần bắt một
gốc duy nhất rồi trả về mã thoát phù hợp.
"""

from __future__ import annotations


class TaxdocError(Exception):
    """Lỗi chung của framework."""


class ConfigError(TaxdocError):
    """Cấu hình thiếu hoặc không hợp lệ."""


class AuthenticationError(TaxdocError):
    """Không thiết lập được phiên làm việc qua lớp xác thực."""


class CollectionError(TaxdocError):
    """Một bước tra cứu hoặc tải tài liệu thất bại sau khi đã thử lại hết."""


class StorageError(TaxdocError):
    """Không lưu được tài liệu đã thu thập."""


__all__ = [
    "AuthenticationError",
    "CollectionError",
    "ConfigError",
    "StorageError",
    "TaxdocError",
]
