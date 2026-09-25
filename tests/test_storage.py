"""Test cho tầng lưu trữ: đặt tên file, ghi tài liệu, phát hiện trùng, xuất danh sách."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from taxdoc.core.errors import StorageError
from taxdoc.storage import FileSystemStorageAdapter, slugify
from tests.support import make_record, payload_for


class SlugifyTests(unittest.TestCase):
    def test_bo_ky_tu_khong_an_toan(self):
        self.assertEqual(slugify("G 12/18-abc"), "G-12-18-abc")

    def test_gia_tri_rong_tra_unknown(self):
        self.assertEqual(slugify(""), "unknown")

    def test_gioi_han_do_dai(self):
        self.assertEqual(len(slugify("a" * 200, maximum=10)), 10)


class StorageAdapterTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.directory = Path(self._tmp.name)
        self.adapter = FileSystemStorageAdapter(self.directory)

    def tearDown(self):
        self._tmp.cleanup()

    # --- exists / save ---
    def test_chua_co_tai_lieu_thi_exists_false(self):
        self.assertFalse(self.adapter.exists(make_record()))

    def test_luu_tai_lieu_va_dat_ten(self):
        record = make_record()
        path = self.adapter.save(record, payload_for(record))
        self.assertTrue(path.is_file())
        self.assertEqual(path.name, self.adapter.filename_for(record))
        self.assertEqual(record.filename, path.name)

    def test_sau_khi_luu_thi_exists_true(self):
        record = make_record()
        self.adapter.save(record, payload_for(record))
        self.assertTrue(self.adapter.exists(make_record()))

    def test_tu_choi_noi_dung_rong(self):
        with self.assertRaises(StorageError):
            self.adapter.save(make_record(), b"")

    def test_file_rong_khong_tinh_la_da_co(self):
        record = make_record()
        (self.directory / self.adapter.filename_for(record)).write_bytes(b"")
        self.assertFalse(self.adapter.exists(record))

    def test_ten_file_chi_gom_ma_khi_thieu_ky_va_loai(self):
        record = make_record(period="", category="")
        self.assertEqual(self.adapter.filename_for(record), "DOC-0001.json")


class ExportIndexTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.directory = Path(self._tmp.name)
        self.adapter = FileSystemStorageAdapter(self.directory)

    def tearDown(self):
        self._tmp.cleanup()

    def test_ghi_ca_csv_va_json_theo_thu_tu_ma(self):
        records = [make_record("DOC-0002"), make_record("DOC-0001")]
        exported = self.adapter.export_index(records)
        self.assertIsNotNone(exported)
        csv_path, json_path = exported

        with csv_path.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual([row["record_id"] for row in rows], ["DOC-0001", "DOC-0002"])
        self.assertEqual(rows[0]["category"], "Declaration")

        payload = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertEqual([item["record_id"] for item in payload], ["DOC-0001", "DOC-0002"])
        self.assertIn("submitted_on", payload[0])

    def test_khong_co_tai_lieu_thi_khong_ghi_gi(self):
        self.assertIsNone(self.adapter.export_index([]))
        self.assertEqual(list(self.directory.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
