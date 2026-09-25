"""Mô hình dữ liệu dùng chung.

Các mô hình ở đây cố tình **không phụ thuộc** vào một provider cụ thể:
:class:`DocumentProvider` trả về :class:`DocumentRecord`, và tầng lưu trữ cũng
chỉ nhìn thấy đúng kiểu bản ghi đó. Nhờ vậy thêm một provider mới không phải sửa
lại phần lưu trữ hay xuất danh sách.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date


@dataclass
class DocumentRecord:
    """Thông tin mô tả một tài liệu do provider trả về."""

    record_id: str
    category: str = ""
    subject: str = ""
    period: str = ""
    submitted_on: str = ""
    status: str = ""
    #: Được storage adapter điền vào sau khi ghi tài liệu xuống đĩa.
    filename: str = ""

    def to_dict(self) -> dict[str, str]:
        """Trả về ``dict`` thuần để ghi CSV/JSON."""
        return asdict(self)


@dataclass(frozen=True)
class CollectionPeriod:
    """Một khoảng thời gian sẽ được tra cứu trên provider."""

    start: date
    end: date

    @property
    def label(self) -> str:
        return f"{self.start:%d/%m/%Y} - {self.end:%d/%m/%Y}"


@dataclass
class PageResult:
    """Kết quả tra cứu một trang từ provider."""

    records: list[DocumentRecord] = field(default_factory=list)
    total_pages: int | None = None
    status: int = 0


@dataclass
class RunSummary:
    """Số liệu tổng kết của một lần chạy pipeline."""

    collected: int = 0
    expected: int = 0
    periods: int = 0
    dry_run: bool = False

    @property
    def complete(self) -> bool:
        return self.expected > 0 and self.collected == self.expected


__all__ = [
    "CollectionPeriod",
    "DocumentRecord",
    "PageResult",
    "RunSummary",
]
