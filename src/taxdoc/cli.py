"""Giao diện dòng lệnh.

Chạy được trên cả Windows và Linux::

    taxdoc --from-date 01/01/2026 --to-date 31/01/2026 --output-dir output/demo

Mã thoát: ``0`` thành công, ``1`` chạy xong nhưng thiếu tài liệu, ``2`` lỗi cấu hình.
Mặc định dùng provider ``mock`` nên chạy được hoàn toàn offline, không cần tài khoản.
"""

from __future__ import annotations

import argparse
import logging
import platform
import sys

from . import __version__
from .core.config import DEFAULT_ENV_FILE, MOCK_PROVIDER, Settings
from .core.errors import ConfigError, TaxdocError
from .core.logging_setup import configure_logging
from .core.pipeline import Pipeline
from .providers import build_authentication, build_provider
from .storage import FileSystemStorageAdapter

LOGGER_NAME = "taxdoc"

EXIT_OK = 0
EXIT_INCOMPLETE = 1
EXIT_CONFIG_ERROR = 2

EXAMPLES = """\
Ví dụ:
  taxdoc --from-date 01/01/2026 --to-date 31/01/2026
  taxdoc --from-date 01/01/2026 --to-date 31/12/2026 --window-days 31
  taxdoc --dry-run                     # chỉ liệt kê, không ghi tài liệu
  taxdoc -v --log-file logs/run.log

Mặc định dùng provider mock nên chạy hoàn toàn offline, không cần tài khoản thật.
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="taxdoc",
        description="Khung automation thu thập và xử lý tài liệu (bản tham chiếu công khai).",
        epilog=EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--from-date", metavar="dd/mm/yyyy", help="Ngày bắt đầu thu thập")
    parser.add_argument("--to-date", metavar="dd/mm/yyyy", help="Ngày kết thúc thu thập")
    parser.add_argument("--output-dir", help="Thư mục lưu tài liệu và danh sách")
    parser.add_argument(
        "--provider",
        help=f"Nguồn tài liệu; bản public chỉ hỗ trợ {MOCK_PROVIDER!r}",
    )
    parser.add_argument("--window-days", type=int, metavar="N", help="Số ngày tối đa mỗi khoảng")
    parser.add_argument("--page-size", type=int, metavar="N", help="Số tài liệu mỗi trang")
    parser.add_argument("--env-file", default=DEFAULT_ENV_FILE, help="File cấu hình dạng .env")
    parser.add_argument("--dry-run", action="store_true", help="Chỉ liệt kê, không ghi tài liệu")
    parser.add_argument("--log-file", metavar="FILE", help="Ghi thêm log chi tiết (DEBUG) ra file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Log chi tiết ra màn hình")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        settings = Settings.from_env(
            env_file=args.env_file,
            from_date=args.from_date,
            to_date=args.to_date,
            output_dir=args.output_dir,
            provider=args.provider,
            window_days=args.window_days,
            page_size=args.page_size,
            dry_run=True if args.dry_run else None,
            log_file=args.log_file,
        )
    except (ConfigError, ValueError) as error:
        print(f"LỖI CẤU HÌNH: {error}", file=sys.stderr)
        return EXIT_CONFIG_ERROR

    try:
        configure_logging(
            verbose=args.verbose,
            log_file=settings.log_file or None,
            redactions=settings.redactions(),
            level=settings.log_level,
        )
    except OSError as error:
        print(f"LỖI CẤU HÌNH: không mở được file log: {error}", file=sys.stderr)
        return EXIT_CONFIG_ERROR

    logger = logging.getLogger(LOGGER_NAME)
    logger.debug(
        "taxdoc %s | Python %s | %s",
        __version__,
        platform.python_version(),
        platform.platform(),
    )

    authentication = build_authentication(settings)
    provider = build_provider(settings)
    storage = FileSystemStorageAdapter(settings.output_dir, logger=logger)

    try:
        summary = Pipeline(
            settings,
            authentication=authentication,
            provider=provider,
            storage=storage,
            logger=logger,
        ).run()
    except TaxdocError as error:
        logger.error("%s", error)
        return EXIT_INCOMPLETE
    finally:
        authentication.close()
        provider.close()
        storage.close()

    logger.info("HOÀN TẤT: %s/%s tài liệu", summary.collected, summary.expected)
    if settings.dry_run:
        logger.info("Dry-run: tìm thấy %s tài liệu, không ghi file nào.", summary.expected)
        return EXIT_OK
    return EXIT_OK if summary.complete else EXIT_INCOMPLETE


__all__ = ["build_parser", "main"]
