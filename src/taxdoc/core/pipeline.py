"""Pipeline: ghép các giai đoạn thành một luồng chạy hoàn chỉnh.

Các giai đoạn::

    Giai đoạn 1  Xác thực                                  AuthenticationProvider
    Giai đoạn 2  Lập kế hoạch khoảng thời gian             Settings.windows()
    Giai đoạn 3  Duyệt trang, thu thập tài liệu            DataCollector + DocumentProvider
    Giai đoạn 4  Lưu từng tài liệu                         StorageAdapter
    Giai đoạn 5  Xuất danh sách tài liệu (CSV/JSON)        StorageAdapter

``DataCollector`` gom phần "duyệt nhiều trang" vào một chỗ; ``Pipeline`` chỉ còn
việc điều phối xác thực, thu thập, lưu trữ và xuất danh sách.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Iterator

from .config import format_date
from .errors import AuthenticationError, CollectionError
from .models import DocumentRecord, PageResult, RunSummary
from .retry import call_with_retries

LOGGER_NAME = "taxdoc.pipeline"


class DataCollector:
    """Duyệt từng khoảng thời gian và từng trang, hỏi provider để lấy tài liệu.

    Mỗi tài liệu tìm được sẽ được đưa cho ``handle`` kèm nội dung đã tải (hoặc
    ``None`` khi chạy dry-run). Nhờ vậy phần "tìm" và phần "lưu" tách rời nhau.
    """

    def __init__(
        self,
        provider,
        settings,
        *,
        is_stored: Callable[[DocumentRecord], bool] | None = None,
        logger: logging.Logger | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.provider = provider
        self.settings = settings
        #: Cho phép bỏ qua bước tải khi tài liệu đã có sẵn (do pipeline truyền vào).
        self.is_stored = is_stored
        self.logger = logger or logging.getLogger(LOGGER_NAME)
        self.sleep = sleep

    def collect(self, handle: Callable[[DocumentRecord, bytes | None], None]) -> int:
        """Thu thập mọi tài liệu trong mọi khoảng; trả về số tài liệu tìm được."""
        discovered = 0
        for period in self.settings.windows():
            self.logger.info("=== Khoảng thời gian %s ===", period.label)
            for record in self._iter_records(period):
                discovered += 1
                payload = self._load(record)
                handle(record, payload)
        return discovered

    def _load(self, record: DocumentRecord) -> bytes | None:
        """Tải nội dung tài liệu, trừ khi dry-run hoặc tài liệu đã có sẵn."""
        if self.settings.dry_run:
            return None
        if self.is_stored is not None and self.is_stored(record):
            return None
        return self._fetch(record)

    def _iter_records(self, period) -> Iterator[DocumentRecord]:
        """Duyệt hết các trang của một khoảng thời gian."""
        page = 1
        total_pages: int | None = None

        while total_pages is None or page <= total_pages:
            result = self._search(period, page)
            if result.total_pages is not None:
                total_pages = result.total_pages
            self.logger.info("Trang %s: %s tài liệu", page, len(result.records))
            yield from result.records

            if total_pages is None and not result.records:
                break
            page += 1
            if total_pages is None or page <= total_pages:
                self._pause()

    def _search(self, period, page: int) -> PageResult:
        """Tra cứu một trang, tự thử lại khi provider lỗi tạm thời trả về rỗng."""

        def query() -> PageResult:
            result = self.provider.search(period, page)
            if not result.records and result.total_pages is None:
                raise CollectionError(f"trang {page} không trả về dữ liệu")
            return result

        return call_with_retries(
            query,
            description=f"tra cứu trang {page}",
            attempts=self.settings.request_attempts,
            backoff=self.settings.retry_backoff,
            retry_on=(CollectionError, OSError),
            logger=self.logger,
            sleep=self.sleep,
        )

    def _fetch(self, record: DocumentRecord) -> bytes:
        """Tải nội dung một tài liệu, tự thử lại khi lỗi tạm thời."""

        def load() -> bytes:
            payload = self.provider.fetch(record)
            if not payload:
                raise CollectionError(f"không có nội dung cho {record.record_id}")
            return payload

        return call_with_retries(
            load,
            description=f"tải {record.record_id}",
            attempts=self.settings.request_attempts,
            backoff=self.settings.retry_backoff,
            retry_on=(CollectionError, OSError),
            logger=self.logger,
            sleep=self.sleep,
        )

    def _pause(self) -> None:
        seconds = self.settings.pause_between_pages
        if seconds > 0:
            self.sleep(seconds)


class Pipeline:
    """Điều phối một lần chạy: xác thực → thu thập → lưu → xuất danh sách."""

    def __init__(
        self,
        settings,
        *,
        authentication,
        provider,
        storage,
        collector: DataCollector | None = None,
        logger: logging.Logger | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.settings = settings
        self.authentication = authentication
        self.provider = provider
        self.storage = storage
        self.collector = collector or DataCollector(
            provider, settings, is_stored=storage.exists, logger=logger, sleep=sleep
        )
        self.logger = logger or logging.getLogger(LOGGER_NAME)
        self.sleep = sleep

    def run(self) -> RunSummary:
        summary = RunSummary(dry_run=self.settings.dry_run)
        self.logger.info(
            "Bắt đầu: %s → %s",
            format_date(self.settings.from_date),
            format_date(self.settings.to_date),
        )

        if not self.authentication.authenticate():
            raise AuthenticationError("Xác thực thất bại")

        records: dict[str, DocumentRecord] = {}
        collected: set[str] = set()

        def handle(record: DocumentRecord, payload: bytes | None) -> None:
            records.setdefault(record.record_id, record)
            if self._persist(record, payload):
                collected.add(record.record_id)

        summary.periods = len(self.settings.windows())
        self.collector.collect(handle)

        if not self.settings.dry_run:
            exported = self.storage.export_index(records.values())
            if exported:
                self.logger.info(
                    "Danh sách tài liệu: %s, %s", exported[0].name, exported[1].name
                )

        summary.expected = len(records)
        summary.collected = len(collected)
        return summary

    def _persist(self, record: DocumentRecord, payload: bytes | None) -> bool:
        """Lưu một tài liệu; trả ``True`` nếu nó đã có trên đĩa sau bước này."""
        if self.storage.exists(record):
            self.logger.info("Bỏ qua tài liệu đã có: %s", record.filename or record.record_id)
            return True
        if payload is None:  # dry-run: chưa tải nội dung
            self.logger.debug("Dry-run: không ghi %s", record.record_id)
            return False
        self.storage.save(record, payload)
        return True


__all__ = ["DataCollector", "Pipeline"]
