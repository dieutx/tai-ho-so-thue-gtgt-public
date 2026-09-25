"""Cho phép chạy ``python -m taxdoc``."""

from __future__ import annotations

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
