"""Test cho pipeline: chạy hết luồng, phân trang, dry-run, thử lại và bỏ qua file đã có."""

from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from taxdoc.core.errors import AuthenticationError, CollectionError
from taxdoc.core.pipeline import Pipeline
from taxdoc.providers.mock_provider import MockAuthenticationProvider, MockDocumentProvider
from taxdoc.storage import FileSystemStorageAdapter
from tests.support import make_settings

INDEX_FILES = {"index.csv", "index.json"}


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.directory = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def build(self, *, settings=None, provider=None, auth=None):
        """Dựng một pipeline đã tiêm sẵn provider, xác thực và storage."""
        settings = settings or make_settings(self.directory, mock_records=5, page_size=2)
        provider = provider or MockDocumentProvider(
            total_records=settings.mock_records, page_size=settings.page_size
        )
        auth = auth or MockAuthenticationProvider()
        storage = FileSystemStorageAdapter(self.directory)
        pipeline = Pipeline(
            settings,
            authentication=auth,
            provider=provider,
            storage=storage,
            sleep=lambda _seconds: None,
        )
        return pipeline, provider, storage

    def document_files(self) -> list[str]:
        return sorted(p.name for p in self.directory.iterdir() if p.name not in INDEX_FILES)

    # --- Luồng chính ---
    def test_chay_het_luong_va_luu_tai_lieu(self):
        pipeline, _provider, _storage = self.build()
        summary = pipeline.run()

        self.assertEqual(summary.expected, 5)
        self.assertEqual(summary.collected, 5)
        self.assertTrue(summary.complete)
        self.assertEqual(len(self.document_files()), 5)
        self.assertTrue((self.directory / "index.json").is_file())
        self.assertTrue((self.directory / "index.csv").is_file())

    def test_phan_trang_tra_ve_du_tai_lieu(self):
        settings = make_settings(self.directory, mock_records=7, page_size=3)
        pipeline, _provider, _storage = self.build(settings=settings)
        summary = pipeline.run()
        self.assertEqual(summary.expected, 7)
        self.assertTrue(summary.complete)

    # --- Dry-run ---
    def test_dry_run_khong_ghi_file_va_khong_tai(self):
        settings = make_settings(self.directory, mock_records=4, page_size=2, dry_run=True)
        pipeline, provider, _storage = self.build(settings=settings)
        summary = pipeline.run()

        self.assertTrue(summary.dry_run)
        self.assertEqual(summary.expected, 4)
        self.assertEqual(summary.collected, 0)
        self.assertFalse(summary.complete)
        self.assertEqual(provider.fetched, 0)
        self.assertEqual(list(self.directory.iterdir()), [])

    # --- Thử lại ---
    def test_thu_lai_khi_nguon_loi_tam_thoi(self):
        settings = make_settings(self.directory, mock_records=2, page_size=2, request_attempts=3)
        provider = MockDocumentProvider(total_records=2, page_size=2, transient_failures=1)
        pipeline, _provider, _storage = self.build(settings=settings, provider=provider)
        summary = pipeline.run()
        self.assertEqual(summary.collected, 2)

    def test_het_luot_thu_thi_bao_loi(self):
        settings = make_settings(self.directory, mock_records=2, page_size=2, request_attempts=2)
        provider = MockDocumentProvider(total_records=2, page_size=2, transient_failures=5)
        pipeline, _provider, _storage = self.build(settings=settings, provider=provider)
        with self.assertRaises(CollectionError):
            pipeline.run()

    # --- Xác thực và bỏ qua file đã có ---
    def test_xac_thuc_that_bai_thi_dung_luong(self):
        pipeline, _provider, _storage = self.build(auth=MockAuthenticationProvider(succeed=False))
        with self.assertRaises(AuthenticationError):
            pipeline.run()

    def test_bo_qua_tai_lieu_da_co(self):
        settings = make_settings(self.directory, mock_records=2, page_size=2)
        first, _provider, storage = self.build(settings=settings)
        first.run()

        second_provider = MockDocumentProvider(total_records=2, page_size=2)
        second = Pipeline(
            settings,
            authentication=MockAuthenticationProvider(),
            provider=second_provider,
            storage=storage,
            sleep=lambda _seconds: None,
        )
        summary = second.run()

        self.assertEqual(summary.collected, 2)
        self.assertEqual(second_provider.fetched, 0)

    # --- Chia khoảng thời gian ---
    def test_nhieu_khoang_thoi_gian_khong_trung_ma(self):
        settings = make_settings(
            self.directory,
            from_date=date(2026, 1, 1),
            to_date=date(2026, 3, 5),
            window_days=31,
            mock_records=2,
            page_size=5,
        )
        pipeline, _provider, _storage = self.build(settings=settings)
        summary = pipeline.run()

        self.assertEqual(summary.periods, 3)
        self.assertEqual(summary.expected, 6)


if __name__ == "__main__":
    unittest.main()
