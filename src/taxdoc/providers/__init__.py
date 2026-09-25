"""Khởi tạo provider từ cấu hình.

Đây là điểm duy nhất quyết định dùng lớp xác thực/nguồn tài liệu nào. Bản public
chỉ có provider ``mock``; thêm một nguồn thật thì đăng ký tại đây mà không phải
sửa pipeline hay tầng lưu trữ.
"""

from __future__ import annotations

from ..core.config import MOCK_PROVIDER, Settings
from ..core.errors import ConfigError
from .base import AuthenticationProvider, DocumentProvider
from .mock_provider import MockAuthenticationProvider, MockDocumentProvider


def build_authentication(settings: Settings) -> AuthenticationProvider:
    """Tạo lớp xác thực tương ứng với cấu hình."""
    return MockAuthenticationProvider()


def build_provider(settings: Settings) -> DocumentProvider:
    """Tạo nguồn tài liệu tương ứng với cấu hình."""
    if settings.provider == MOCK_PROVIDER:
        return MockDocumentProvider(
            total_records=settings.mock_records,
            page_size=settings.page_size,
        )
    raise ConfigError(
        f"Provider {settings.provider!r} không có trong bản public. "
        f"Bản này chỉ hỗ trợ {MOCK_PROVIDER!r}."
    )


__all__ = ["build_authentication", "build_provider"]
