# Tax Document Automation Framework

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

A Python automation framework designed to demonstrate scalable document
collection and processing workflows.

> **This repository is a simplified public reference implementation.**
> Đây là bản tham chiếu công khai, rút gọn — không phải công cụ vận hành đầy đủ.

---

## Giới thiệu (About)

**taxdoc-framework** — framework Python để **tải và xử lý tờ khai thuế** từ Cổng
Dịch vụ công (dichvucong).

Đây là bản tham chiếu công khai, rút gọn: kho chứa chỉ minh hoạ kiến trúc
pipeline (xác thực → thu thập → lưu trữ → xuất danh sách) cùng provider `mock`
chạy offline để demo và kiểm thử. Bản này **không** kèm tích hợp với hệ thống
thật, không có endpoint, không có thông tin đăng nhập và không có dữ liệu thật.

---

## Tổng quan

Framework này minh hoạ cách thiết kế một pipeline automation cho việc thu thập và
xử lý tài liệu, tách bạch từng tầng để dễ thay thế và dễ kiểm thử:

- quy trình xác thực (authentication workflows)
- tìm và phân trang tài liệu (document discovery)
- trích xuất metadata (metadata extraction)
- tổ chức file trên đĩa (file organization)
- xuất danh sách có cấu trúc (structured export)

Chạy trên **Windows, Linux và macOS**, Python **3.10+**. Bản này **không có
dependency bắt buộc** và chạy hoàn toàn offline nhờ provider `mock`.

---

## Kiến trúc

```text
Input
  |
Authentication Layer   AuthenticationProvider
  |
Document Provider      DocumentProvider (search theo trang, fetch từng tài liệu)
  |
Processing Pipeline    DataCollector + Pipeline
  |
Storage Layer          StorageAdapter
  |
Export                 index.csv + index.json
```

Chi tiết bản đồ module, ranh giới phụ thuộc và cách mở rộng:
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Điểm nhấn kỹ thuật

- **Modular provider architecture** — xác thực và nguồn tài liệu là hai interface
  riêng, thay cái này không ảnh hưởng cái kia.
- **Config-driven execution** — mọi tham số đến từ `.env`/biến môi trường/dòng lệnh.
- **Retry and error handling** — mọi bước dễ hỏng đi qua một hàm thử lại duy nhất,
  với thời gian chờ tăng dần.
- **Structured logging** — log có mức rõ ràng, kèm `RedactionFilter` che giá trị
  nhạy cảm trước khi ghi ra màn hình hoặc file.
- **Testable components** — dependency injection đầy đủ; test chạy offline, không
  cần mạng cũng không cần chờ đợi.
- **Extensible storage adapters** — đổi nơi lưu trữ chỉ cần cài `exists()`,
  `save()` và `export_index()`.

## Bắt đầu nhanh

```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate          # Windows: .\.venv\Scripts\Activate.ps1
python -m pip install -e .

# Chạy thử: liệt kê tài liệu, không ghi file
taxdoc --from-date 01/01/2026 --to-date 31/01/2026 --dry-run

# Chạy thật rồi xem kết quả
taxdoc --from-date 01/01/2026 --to-date 31/03/2026 --output-dir output/demo
```

Không cần cài đặt cũng chạy được:

```bash
PYTHONPATH=src python -m taxdoc --dry-run
```

## Cấu hình

Sao chép [`examples/sample_config.env`](examples/sample_config.env) thành `.env`
rồi chỉnh. Thứ tự ưu tiên (cao nhất trước): tham số dòng lệnh → biến môi trường →
file `.env`. File `.env` nằm trong `.gitignore`.

| Biến | Bắt buộc | Mặc định | Ý nghĩa |
|---|---:|---|---|
| `TAXDOC_FROM_DATE` | Không | Đầu tháng hiện tại | Ngày bắt đầu, `dd/mm/yyyy` |
| `TAXDOC_TO_DATE` | Không | Hôm nay | Ngày kết thúc |
| `TAXDOC_OUTPUT_DIR` | Không | `output` | Thư mục lưu tài liệu và danh sách |
| `TAXDOC_PROVIDER` | Không | `mock` | Nguồn tài liệu; bản public chỉ có `mock` |
| `TAXDOC_ACCOUNT_ID` | Không | trống | Mã tài khoản (bắt buộc nếu dùng nguồn thật) |
| `TAXDOC_ACCOUNT_KEY` | Không | trống | Khoá tài khoản — luôn được che trong log |
| `TAXDOC_WINDOW_DAYS` | Không | `31` | Số ngày tối đa mỗi khoảng tra cứu |
| `TAXDOC_PAGE_SIZE` | Không | `10` | Số tài liệu mỗi trang |
| `TAXDOC_MOCK_RECORDS` | Không | `6` | Số tài liệu provider mock sinh ra |
| `TAXDOC_REQUEST_ATTEMPTS` | Không | `3` | Số lần thử cho mỗi bước tra cứu/tải |
| `TAXDOC_RETRY_BACKOFF` | Không | `1.5` | Hệ số chờ tăng dần giữa các lần thử |
| `TAXDOC_PAUSE_BETWEEN_PAGES` | Không | `0` | Nghỉ giữa hai trang (giây) |
| `TAXDOC_DRY_RUN` | Không | `false` | Chỉ liệt kê, không ghi tài liệu |
| `TAXDOC_LOG_FILE` | Không | trống | Ghi thêm toàn bộ log (DEBUG) ra file |
| `TAXDOC_LOG_LEVEL` | Không | `INFO` | Mức log ra màn hình |

## Kết quả đầu ra

```text
output/demo/
├── DOC-20260101-0001-01-2026-Declaration.json
├── DOC-20260101-0002-01-2026-Acknowledgement.json
├── ...
├── index.csv
└── index.json
```

Tên file tất định theo mã tài liệu (kèm kỳ và loại nếu có), nên lần chạy sau sẽ
**bỏ qua** tài liệu đã có và có thể chạy tiếp khi bị gián đoạn. `index.csv` ghi
bằng UTF-8 kèm BOM để mở đúng trong Excel; `index.json` để xử lý tự động.

## Background

This project was developed from a real-world automation requirement.

The production system successfully handled:

- complex workflows (nhiều nguồn dữ liệu, phân trang, quy tắc ngày tháng);
- large document collections (tải khối lượng lớn, chạy tiếp khi gián đoạn);
- reliability challenges (lỗi tạm thời, giới hạn tần suất, thay đổi giao diện);
- operational automation needs (cấu hình, log, cập nhật không cần sửa mã).

Due to security and operational considerations, this repository provides only the
generalized architecture and engineering approach.

## Cân nhắc bảo mật (Security Considerations)

This repository intentionally excludes:

- production credentials
- private endpoints
- real user data
- organization-specific implementation details

The original production implementation contains additional integrations that are
not included in this public version.

## Kiểm thử

```bash
python -m unittest discover -s tests -t . -v   # chạy offline
```

Bộ test **không cần Internet, không cần tài khoản**: provider mock sinh dữ liệu
tất định, và `Pipeline` nhận sẵn hàm `sleep` rỗng nên chạy tức thì.

| File | Nội dung |
|---|---|
| `tests/test_config.py` | Đọc `.env`, thứ tự ưu tiên, kiểm tra hợp lệ, chia khoảng thời gian |
| `tests/test_storage.py` | Đặt tên file, ghi tài liệu, phát hiện trùng, xuất CSV/JSON |
| `tests/test_pipeline.py` | Chạy hết luồng, phân trang, dry-run, thử lại, bỏ qua file đã có |

## Giấy phép và miễn trừ

Phát hành theo [giấy phép MIT](LICENSE).

This repository is a simplified public reference implementation. It is not
affiliated with, endorsed by, or connected to any organization or service.
