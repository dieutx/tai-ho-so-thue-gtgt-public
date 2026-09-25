"""Provider mock chạy hoàn toàn offline, dùng cho demo và kiểm thử.

Provider này sinh dữ liệu **tất định** trong bộ nhớ: không gọi mạng, không cần
tài khoản. Nó cũng mô phỏng được lỗi tạm thời để kiểm chứng cơ chế thử lại.
"""

from __future__ import annotations

import json
import math

from ..core.errors import CollectionError
from ..core.models import CollectionPeriod, DocumentRecord, PageResult
from .base import AuthenticationProvider, DocumentProvider

#: Vài loại tài liệu mẫu, chỉ mang tính minh hoạ.
CATEGORIES = ("Declaration", "Acknowledgement", "Notice")


class MockAuthenticationProvider(AuthenticationProvider):
    """Luôn thiết lập phiên thành công, trừ khi bị cấu hình để thất bại."""

    name = "mock"

    def __init__(self, *, succeed: bool = True) -> None:
        self.succeed = succeed
        self.authenticated = False

    def authenticate(self) -> bool:
        if not self.succeed:
            return False
        self.authenticated = True
        return True


class MockDocumentProvider(DocumentProvider):
    """Sinh danh sách tài liệu tất định, hỗ trợ phân trang và lỗi tạm thời.

    ``transient_failures`` là số lần gọi ``search`` đầu tiên sẽ ném lỗi, dùng để
    kiểm chứng :func:`taxdoc.core.retry.call_with_retries`.
    """

    source = "mock"

    def __init__(
        self,
        *,
        total_records: int = 6,
        page_size: int = 10,
        transient_failures: int = 0,
    ) -> None:
        self.total_records = max(0, total_records)
        self.page_size = max(1, page_size)
        self.transient_failures = max(0, transient_failures)
        #: Số tài liệu đã được tải về (để test kiểm tra không tải trùng).
        self.fetched = 0
        self._failures_served = 0

    def search(self, period: CollectionPeriod, page: int) -> PageResult:
        if self._failures_served < self.transient_failures:
            self._failures_served += 1
            raise CollectionError("nguồn tài liệu tạm thời không phản hồi")

        catalog = self._catalog(period)
        total_pages = max(1, math.ceil(len(catalog) / self.page_size))
        start = (page - 1) * self.page_size
        return PageResult(
            records=catalog[start : start + self.page_size],
            total_pages=total_pages,
            status=200,
        )

    def fetch(self, record: DocumentRecord) -> bytes | None:
        self.fetched += 1
        payload = {
            "record_id": record.record_id,
            "category": record.category,
            "subject": record.subject,
            "period": record.period,
            "status": record.status,
        }
        return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")

    def _catalog(self, period: CollectionPeriod) -> list[DocumentRecord]:
        """Sinh danh sách tài liệu mẫu; mã gắn với khoảng để nhiều khoảng không trùng."""
        stamp = f"{period.start:%Y%m%d}"
        return [
            DocumentRecord(
                record_id=f"DOC-{stamp}-{index:04d}",
                category=CATEGORIES[(index - 1) % len(CATEGORIES)],
                subject=f"Sample document {index}",
                period=f"{period.start:%m/%Y}",
                submitted_on=f"{period.start:%d/%m/%Y}",
                status="available",
            )
            for index in range(1, self.total_records + 1)
        ]


__all__ = ["CATEGORIES", "MockAuthenticationProvider", "MockDocumentProvider"]
