"""Lớp trừu tượng cho xác thực và thu thập tài liệu.

Đây là "hợp đồng" mà mọi tích hợp phải tuân theo. Nhờ tách hai interface riêng,
có thể thay cách xác thực mà không đụng tới cách tìm tài liệu và ngược lại.

Bản public chỉ kèm provider mock; các tích hợp với hệ thống thật nằm ngoài
repository này (xem ``README.md``).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..core.models import CollectionPeriod, DocumentRecord, PageResult


class AuthenticationProvider(ABC):
    """Thiết lập một phiên làm việc trước khi thu thập tài liệu."""

    #: Tên dùng trong cấu hình và log.
    name: str = "base"

    @abstractmethod
    def authenticate(self) -> bool:
        """Trả ``True`` khi phiên đã sẵn sàng để thu thập."""

    def close(self) -> None:
        """Giải phóng tài nguyên (kết nối, phiên...). Mặc định không làm gì."""
        return None


class DocumentProvider(ABC):
    """Nguồn tài liệu: tra cứu theo trang và tải nội dung từng tài liệu."""

    #: Định danh nguồn, dùng trong log và trong :class:`DocumentRecord`.
    source: str = "base"

    @abstractmethod
    def search(self, period: CollectionPeriod, page: int) -> PageResult:
        """Tra cứu một trang tài liệu trong một khoảng thời gian."""

    @abstractmethod
    def fetch(self, record: DocumentRecord) -> bytes | None:
        """Tải nội dung một tài liệu; trả ``None`` nếu không có nội dung."""

    def close(self) -> None:
        """Giải phóng tài nguyên. Mặc định không làm gì."""
        return None


__all__ = ["AuthenticationProvider", "DocumentProvider"]
