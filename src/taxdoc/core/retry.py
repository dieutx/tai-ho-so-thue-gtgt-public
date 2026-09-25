"""Tiện ích thử lại có kiểm soát.

Mọi bước có thể hỏng tạm thời (tra cứu một trang, tải một tài liệu) đều đi qua
:func:`call_with_retries` để logic thử lại nằm một chỗ, dễ kiểm thử và dễ đổi
chiến lược chờ giữa các lần thử.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TypeVar

from .errors import CollectionError

T = TypeVar("T")
LOGGER_NAME = "taxdoc.retry"


def call_with_retries(
    operation: Callable[[], T],
    *,
    description: str,
    attempts: int = 3,
    backoff: float = 1.5,
    retry_on: tuple[type[Exception], ...] = (Exception,),
    logger: logging.Logger | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Chạy ``operation`` và thử lại khi gặp lỗi.

    Thời gian chờ giữa hai lần thử tăng dần theo ``backoff`` (``backoff ** n``).
    Hết số lần thử vẫn lỗi thì ném :class:`CollectionError`.
    """
    logger = logger or logging.getLogger(LOGGER_NAME)
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except retry_on as error:
            last_error = error
            if attempt >= attempts:
                break
            delay = backoff ** (attempt - 1)
            logger.warning(
                "%s thất bại (lần %s/%s): %s — thử lại sau %.1fs",
                description,
                attempt,
                attempts,
                error,
                delay,
            )
            sleep(delay)

    raise CollectionError(
        f"{description} thất bại sau {attempts} lần thử: {last_error}"
    ) from last_error


__all__ = ["call_with_retries"]
