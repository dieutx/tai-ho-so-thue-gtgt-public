"""Test cho tầng cấu hình: đọc .env, ưu tiên, kiểm tra hợp lệ và chia khoảng thời gian."""

from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

from taxdoc.core.config import Settings, format_date, load_env_file, parse_date
from taxdoc.core.errors import ConfigError


class ParseDateTests(unittest.TestCase):
    def test_doc_dung_dinh_dang(self):
        self.assertEqual(parse_date("31/01/2026"), date(2026, 1, 31))

    def test_sai_dinh_dang_bao_loi(self):
        with self.assertRaises(ValueError):
            parse_date("2026-01-31")

    def test_format_nguoc_lai(self):
        self.assertEqual(format_date(date(2026, 1, 31)), "31/01/2026")


class LoadEnvFileTests(unittest.TestCase):
    def test_bo_qua_dong_trong_va_chu_thich(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text(
                "# chú thích\n\nTAXDOC_PROVIDER=mock\nTAXDOC_PAGE_SIZE=5\n",
                encoding="utf-8",
            )
            values = load_env_file(path)
        self.assertEqual(values, {"TAXDOC_PROVIDER": "mock", "TAXDOC_PAGE_SIZE": "5"})

    def test_file_khong_ton_tai_tra_dict_rong(self):
        self.assertEqual(load_env_file("khong-ton-tai.env"), {})


class WindowsTests(unittest.TestCase):
    def test_chia_theo_so_ngay_toi_da(self):
        settings = Settings(from_date=date(2026, 1, 1), to_date=date(2026, 3, 5), window_days=31)
        windows = settings.windows()
        self.assertEqual(len(windows), 3)
        self.assertEqual((windows[0].start, windows[0].end), (date(2026, 1, 1), date(2026, 1, 31)))
        self.assertEqual((windows[-1].start, windows[-1].end), (date(2026, 3, 4), date(2026, 3, 5)))

    def test_mot_khoang_duy_nhat(self):
        settings = Settings(from_date=date(2026, 1, 1), to_date=date(2026, 1, 10), window_days=31)
        self.assertEqual(len(settings.windows()), 1)


class ValidationTests(unittest.TestCase):
    def test_ngay_dao_nguoc_bao_loi(self):
        settings = Settings(from_date=date(2026, 3, 1), to_date=date(2026, 1, 1))
        with self.assertRaises(ConfigError):
            settings.validate()

    def test_so_ngay_moi_khoang_phai_duong(self):
        settings = Settings(from_date=date(2026, 1, 1), to_date=date(2026, 1, 2), window_days=0)
        with self.assertRaises(ConfigError):
            settings.validate()

    def test_redactions_chi_gom_gia_tri_khong_rong(self):
        settings = Settings(
            from_date=date(2026, 1, 1), to_date=date(2026, 1, 2), account_key=""
        )
        self.assertEqual(settings.redactions(), ())
        settings = Settings(
            from_date=date(2026, 1, 1), to_date=date(2026, 1, 2), account_key="abc"
        )
        self.assertEqual(settings.redactions(), ("abc",))


class FromEnvTests(unittest.TestCase):
    def test_tham_so_dong_lenh_thang_bien_moi_truong(self):
        environ = {"TAXDOC_FROM_DATE": "01/02/2026", "TAXDOC_TO_DATE": "28/02/2026"}
        settings = Settings.from_env(environ, env_file=None, from_date="01/01/2026")
        self.assertEqual(settings.from_date, date(2026, 1, 1))
        self.assertEqual(settings.to_date, date(2026, 2, 28))

    def test_doc_bien_moi_truong(self):
        settings = Settings.from_env(
            {"TAXDOC_PROVIDER": "mock", "TAXDOC_PAGE_SIZE": "4"}, env_file=None
        )
        self.assertEqual(settings.provider, "mock")
        self.assertEqual(settings.page_size, 4)

    def test_provider_that_thieu_tai_khoan_bao_loi(self):
        with self.assertRaises(ConfigError):
            Settings.from_env({}, env_file=None, provider="production")

    def test_provider_that_co_tai_khoan_thi_hop_le(self):
        settings = Settings.from_env({}, env_file=None, provider="production", account_id="acct-1")
        self.assertEqual(settings.provider, "production")

    def test_ngay_khong_hop_le_bao_config_error(self):
        with self.assertRaises(ConfigError):
            Settings.from_env({"TAXDOC_FROM_DATE": "31-01-2026"}, env_file=None)

    def test_so_khong_hop_le_bao_config_error(self):
        with self.assertRaises(ConfigError):
            Settings.from_env({"TAXDOC_PAGE_SIZE": "nhieu"}, env_file=None)

    def test_bat_co_bang_true(self):
        settings = Settings.from_env({"TAXDOC_DRY_RUN": "true"}, env_file=None)
        self.assertTrue(settings.dry_run)


if __name__ == "__main__":
    unittest.main()
