"""Cấu hình log cho CLI và thư viện.

Mọi giá trị nhạy cảm (ví dụ khoá tài khoản) được lọc bằng :class:`RedactionFilter`
trước khi ghi ra màn hình hoặc ra file, kể cả khi log đến từ thư viện bên ngoài.
"""

from __future__ import annotations

import logging
import sys

LOGGER_NAME = "taxdoc"
CONSOLE_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


class RedactionFilter(logging.Filter):
    """Thay các giá trị cần che bằng ``***`` trước khi bản ghi được ghi ra."""

    def __init__(self, values: tuple[str, ...] = ()) -> None:
        super().__init__()
        self._values = tuple(value for value in values if value)

    def filter(self, record: logging.LogRecord) -> bool:
        if not self._values:
            return True
        message = record.getMessage()
        masked = message
        for value in self._values:
            masked = masked.replace(value, "***")
        if masked != message:
            record.msg = masked
            record.args = ()
        return True


def configure_logging(
    verbose: bool = False,
    *,
    log_file: str | None = None,
    redactions: tuple[str, ...] = (),
    level: str = "INFO",
) -> None:
    """Cấu hình log ra màn hình (và tùy chọn ra file).

    Màn hình hiện mức ``level`` (mặc định ``INFO``), hoặc ``DEBUG`` khi bật
    ``verbose``; file log luôn ghi ở mức ``DEBUG`` để đủ dữ liệu khi cần chẩn đoán.
    """
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
    root.setLevel(logging.DEBUG)

    console_level = logging.DEBUG if verbose else logging.getLevelName(level.upper())
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(console_level if isinstance(console_level, int) else logging.INFO)
    console.setFormatter(logging.Formatter(CONSOLE_FORMAT, datefmt="%H:%M:%S"))
    console.addFilter(RedactionFilter(redactions))
    root.addHandler(console)

    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(CONSOLE_FORMAT, datefmt="%Y-%m-%d %H:%M:%S"))
        file_handler.addFilter(RedactionFilter(redactions))
        root.addHandler(file_handler)


__all__ = ["RedactionFilter", "configure_logging"]
