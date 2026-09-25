"""Cấu hình chạy: đọc từ file ``.env`` rồi tới biến môi trường.

Thứ tự ưu tiên (cao nhất trước):

1. Tham số dòng lệnh (``overrides`` truyền vào :meth:`Settings.from_env`)
2. Biến môi trường đang có trong tiến trình
3. File ``.env`` (dùng khi phát triển ở máy cá nhân)

Mọi biến đều có tiền tố ``TAXDOC_`` để không lẫn với biến khác.
"""

from __future__ import annotations

import os
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from .errors import ConfigError
from .models import CollectionPeriod

ENV_PREFIX = "TAXDOC_"
DEFAULT_ENV_FILE = ".env"
DATE_FORMAT = "%d/%m/%Y"
DEFAULT_WINDOW_DAYS = 31
MOCK_PROVIDER = "mock"
LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


def parse_date(value: str | date | datetime) -> date:
    """Đọc ngày dạng ``dd/mm/yyyy`` (hoặc giữ nguyên ``date``/``datetime``)."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value).strip(), DATE_FORMAT).date()
    except ValueError as error:
        raise ValueError(
            f"Ngày không hợp lệ: {value!r}. Định dạng đúng là dd/mm/yyyy"
        ) from error


def format_date(value: date) -> str:
    """Ghi ngày theo định dạng cấu hình chấp nhận."""
    return value.strftime(DATE_FORMAT)


def load_env_file(path: str | Path = DEFAULT_ENV_FILE) -> dict[str, str]:
    """Đọc file ``.env`` dạng ``KEY=VALUE``; bỏ qua dòng trống và dòng chú thích."""
    values: dict[str, str] = {}
    path = Path(path)
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if not key:
            continue
        values[key] = value.strip().strip('"').strip("'")
    return values


class _Env:
    """Đọc và kiểm tra kiểu dữ liệu cho một tập biến môi trường."""

    def __init__(self, values: Mapping[str, str]) -> None:
        self.values = values

    def _raw(self, name: str, default: str) -> str:
        return self.values.get(f"{ENV_PREFIX}{name}", default)

    def text(self, name: str, default: str = "") -> str:
        return self._raw(name, default).strip()

    def integer(self, name: str, default: int) -> int:
        raw = self._raw(name, str(default)).strip()
        try:
            return int(raw)
        except ValueError as error:
            raise ConfigError(f"{ENV_PREFIX}{name} phải là số nguyên, nhận được {raw!r}") from error

    def number(self, name: str, default: float) -> float:
        raw = self._raw(name, str(default)).strip()
        try:
            return float(raw)
        except ValueError as error:
            raise ConfigError(f"{ENV_PREFIX}{name} phải là số, nhận được {raw!r}") from error

    def boolean(self, name: str, default: bool = False) -> bool:
        raw = self._raw(name, str(default)).strip().lower()
        if raw in {"1", "true", "yes", "y", "co", "có"}:
            return True
        if raw in {"0", "false", "no", "n", "khong", "không", ""}:
            return False
        raise ConfigError(f"{ENV_PREFIX}{name} phải là true/false, nhận được {raw!r}")


def _split_windows(start: date, end: date, window_days: int) -> Iterator[tuple[date, date]]:
    """Cắt khoảng ngày thành các đoạn dài tối đa ``window_days`` ngày."""
    cursor = start
    while cursor <= end:
        chunk_end = min(end, cursor + timedelta(days=window_days - 1))
        yield cursor, chunk_end
        cursor = chunk_end + timedelta(days=1)


@dataclass(frozen=True)
class Settings:
    """Toàn bộ tham số của một lần chạy."""

    from_date: date
    to_date: date
    output_dir: Path = Path("output")
    #: Mã tài khoản dùng cho lớp xác thực. Với provider mock có thể để trống.
    account_id: str = ""
    #: Khoá tài khoản. Không bao giờ ghi thẳng ra log — xem ``redactions()``.
    account_key: str = ""
    provider: str = MOCK_PROVIDER
    #: Số ngày tối đa mỗi khoảng tra cứu.
    window_days: int = DEFAULT_WINDOW_DAYS
    page_size: int = 10
    #: Số bản ghi mà provider mock sinh ra (chỉ dùng cho demo/test).
    mock_records: int = 6
    #: Số lần thử cho mỗi bước tra cứu/tải.
    request_attempts: int = 3
    #: Hệ số chờ tăng dần giữa các lần thử lại.
    retry_backoff: float = 1.5
    pause_between_pages: float = 0.0
    dry_run: bool = False
    log_file: str = ""
    log_level: str = "INFO"

    # --- Dẫn xuất ---
    def windows(self) -> list[CollectionPeriod]:
        """Danh sách khoảng thời gian cần chạy, theo thứ tự thời gian."""
        return [
            CollectionPeriod(start=start, end=end)
            for start, end in _split_windows(self.from_date, self.to_date, self.window_days)
        ]

    def redactions(self) -> tuple[str, ...]:
        """Các giá trị phải che khi ghi log."""
        return tuple(value for value in (self.account_key,) if value)

    def validate(self) -> None:
        if self.from_date > self.to_date:
            raise ConfigError("TAXDOC_FROM_DATE phải nhỏ hơn hoặc bằng TAXDOC_TO_DATE")
        if self.window_days < 1:
            raise ConfigError("TAXDOC_WINDOW_DAYS phải lớn hơn 0")
        if self.page_size < 1:
            raise ConfigError("TAXDOC_PAGE_SIZE phải lớn hơn 0")
        if self.request_attempts < 1:
            raise ConfigError("TAXDOC_REQUEST_ATTEMPTS phải lớn hơn 0")
        if self.retry_backoff < 1:
            raise ConfigError("TAXDOC_RETRY_BACKOFF phải lớn hơn hoặc bằng 1")
        if self.pause_between_pages < 0:
            raise ConfigError("TAXDOC_PAUSE_BETWEEN_PAGES không được là số âm")
        if self.log_level.upper() not in LOG_LEVELS:
            raise ConfigError(f"TAXDOC_LOG_LEVEL phải là một trong {', '.join(LOG_LEVELS)}")
        if self.provider != MOCK_PROVIDER and not self.account_id:
            raise ConfigError(
                f"Provider {self.provider!r} cần TAXDOC_ACCOUNT_ID. "
                f"Provider mock ({MOCK_PROVIDER!r}) thì không."
            )

    @classmethod
    def from_env(
        cls,
        environ: Mapping[str, str] | None = None,
        *,
        env_file: str | Path | None = DEFAULT_ENV_FILE,
        **overrides: Any,
    ) -> Settings:
        """Tạo cấu hình từ môi trường; ``overrides`` là các giá trị từ dòng lệnh."""
        values: dict[str, str] = {}
        if env_file:
            values.update(load_env_file(env_file))
        values.update(dict(os.environ if environ is None else environ))
        env = _Env(values)

        def pick(key: str, fallback: Any) -> Any:
            value = overrides.get(key)
            return fallback if value is None else value

        today = date.today()
        try:
            from_raw = pick("from_date", env.text("FROM_DATE", format_date(today.replace(day=1))))
            to_raw = pick("to_date", env.text("TO_DATE", format_date(today)))
            settings = cls(
                from_date=parse_date(from_raw),
                to_date=parse_date(to_raw),
                output_dir=Path(pick("output_dir", env.text("OUTPUT_DIR", "output"))),
                account_id=pick("account_id", env.text("ACCOUNT_ID")),
                account_key=env.text("ACCOUNT_KEY"),
                provider=pick("provider", env.text("PROVIDER", MOCK_PROVIDER)),
                window_days=env.integer("WINDOW_DAYS", DEFAULT_WINDOW_DAYS),
                page_size=env.integer("PAGE_SIZE", 10),
                mock_records=env.integer("MOCK_RECORDS", 6),
                request_attempts=env.integer("REQUEST_ATTEMPTS", 3),
                retry_backoff=env.number("RETRY_BACKOFF", 1.5),
                pause_between_pages=env.number("PAUSE_BETWEEN_PAGES", 0.0),
                dry_run=bool(pick("dry_run", env.boolean("DRY_RUN", False))),
                log_file=pick("log_file", env.text("LOG_FILE")),
                log_level=pick("log_level", env.text("LOG_LEVEL", "INFO")),
            )
        except ValueError as error:  # parse_date
            raise ConfigError(str(error)) from error

        settings.validate()
        return settings

    def with_output_dir(self, directory: str | Path) -> Settings:
        return replace(self, output_dir=Path(directory))


__all__ = [
    "DEFAULT_ENV_FILE",
    "DEFAULT_WINDOW_DAYS",
    "ENV_PREFIX",
    "MOCK_PROVIDER",
    "Settings",
    "format_date",
    "load_env_file",
    "parse_date",
]
