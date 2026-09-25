# Tax Document Automation Framework

[![CI](https://github.com/dieutx/tai-ho-so-thue-gtgt-public/actions/workflows/ci.yml/badge.svg)](https://github.com/dieutx/tai-ho-so-thue-gtgt-public/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Khung automation Python dùng để thu thập và xử lý **tờ khai thuế** từ Cổng Dịch
vụ công (dichvucong). Dự án được thiết kế theo hướng tách tầng rõ ràng, để có
thể thay một thành phần mà không ảnh hưởng phần còn lại, và để mọi thành phần
đều kiểm thử được.

> **Đây là bản tham chiếu công khai, rút gọn.**
> Repo chỉ minh hoạ kiến trúc và cách tiếp cận kỹ thuật. Bản này không chứa tích
> hợp với hệ thống thật, không có địa chỉ API, không có thông tin đăng nhập và
> không có dữ liệu thật.

---

## Mục lục

1. [Giới thiệu](#1-giới-thiệu)
2. [Đặc điểm nổi bật](#2-đặc-điểm-nổi-bật)
3. [Kiến trúc](#3-kiến-trúc)
4. [Cài đặt và chạy thử](#4-cài-đặt-và-chạy-thử)
5. [Cấu hình](#5-cấu-hình)
6. [Sử dụng](#6-sử-dụng)
7. [Kết quả đầu ra](#7-kết-quả-đầu-ra)
8. [Bối cảnh](#8-bối-cảnh)
9. [Kiểm thử](#9-kiểm-thử)
10. [Phạm vi và bảo mật](#10-phạm-vi-và-bảo-mật)
11. [Giấy phép](#11-giấy-phép)

---

## 1. Giới thiệu

Chương trình nhận một khoảng ngày, tự chia khoảng đó thành nhiều phần nhỏ, thu
thập tờ khai theo từng trang, lưu tài liệu xuống đĩa và xuất một danh sách có
cấu trúc để tra cứu lại.

```text
Khoảng ngày bất kỳ
  └─► tự chia thành các khoảng nhỏ (mặc định tối đa 31 ngày)
        └─► duyệt từng trang, thu thập từng tờ khai
              └─► lưu file + xuất danh sách (CSV/JSON), bỏ qua file đã có
```

Repo này chạy **hoàn toàn offline** bằng một provider `mock` sinh dữ liệu mẫu,
nên có thể chạy thử và kiểm thử mà không cần mạng và không cần tài khoản.

## 2. Đặc điểm nổi bật

- **Kiến trúc hướng provider.** Xác thực và nguồn tài liệu là hai lớp trừu tượng
  riêng biệt; thay cái này không ảnh hưởng cái kia.
- **Cấu hình tập trung.** Mọi tham số đến từ file `.env`, biến môi trường hoặc
  tham số dòng lệnh, theo thứ tự ưu tiên rõ ràng.
- **Thử lại và xử lý lỗi.** Mọi bước dễ hỏng đi qua một hàm thử lại duy nhất,
  với thời gian chờ tăng dần; hết số lần thử thì báo lỗi rõ ràng.
- **Ghi log có cấu trúc.** Log theo mức, có bộ lọc che các giá trị nhạy cảm trước
  khi ghi ra màn hình hoặc ra file.
- **Thành phần dễ kiểm thử.** Phụ thuộc được tiêm từ ngoài vào, nên test chạy
  tức thì, không cần mạng và không cần chờ đợi.
- **Kho lưu trữ mở rộng được.** Đổi nơi lưu chỉ cần cài ba phương thức
  `exists()`, `save()` và `export_index()`.
- **Không có dependency bắt buộc.** Chỉ dùng thư viện chuẩn của Python.

## 3. Kiến trúc

Một lần chạy đi qua năm lớp, mỗi lớp do một thành phần phụ trách:

```text
Đầu vào (khoảng ngày)
  │
  ├─ Lớp xác thực        AuthenticationProvider
  ├─ Nguồn tài liệu      DocumentProvider
  ├─ Điều phối pipeline  DataCollector + Pipeline
  ├─ Lưu trữ             StorageAdapter
  └─ Xuất danh sách      index.csv + index.json
```

Luồng chạy chi tiết theo năm giai đoạn:

| Giai đoạn | Việc | Thành phần |
|---|---|---|
| 1 | Thiết lập phiên làm việc | `AuthenticationProvider` |
| 2 | Chia khoảng ngày | `Settings.windows()` |
| 3 | Duyệt trang, thu thập tài liệu | `DataCollector` + `DocumentProvider` |
| 4 | Lưu từng tài liệu | `StorageAdapter` |
| 5 | Xuất danh sách CSV/JSON | `StorageAdapter` |

Bản đồ module, ranh giới phụ thuộc và cách mở rộng:
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## 4. Cài đặt và chạy thử

Yêu cầu: Python **3.10+**. Chạy được trên Windows, Linux và macOS.

```bash
git clone https://github.com/dieutx/tai-ho-so-thue-gtgt-public.git
cd tai-ho-so-thue-gtgt-public
python -m venv .venv
source .venv/bin/activate          # Windows: .\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

Chạy thử ngay, không cần cấu hình gì thêm:

```bash
# Chỉ liệt kê, không ghi file
taxdoc --from-date 01/01/2026 --to-date 31/01/2026 --dry-run

# Chạy thật rồi xem kết quả trong output/demo/
taxdoc --from-date 01/01/2026 --to-date 31/03/2026 --output-dir output/demo
```

Nếu không muốn cài đặt, chạy trực tiếp từ mã nguồn:

```bash
PYTHONPATH=src python -m taxdoc --dry-run
```

## 5. Cấu hình

Sao chép file mẫu thành `.env` rồi chỉnh theo nhu cầu:

```bash
cp examples/sample_config.env .env
```

Thứ tự ưu tiên (cao nhất trước): **tham số dòng lệnh → biến môi trường → file
`.env`**. File `.env` đã nằm trong `.gitignore`.

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

## 6. Sử dụng

```bash
# Thu thập hồ sơ một tháng
taxdoc --from-date 01/01/2026 --to-date 31/01/2026 --output-dir output/2026-01

# Khoảng dài tùy ý: tự chia thành nhiều khoảng nhỏ
taxdoc --from-date 01/01/2026 --to-date 31/12/2026

# Đổi số ngày mỗi khoảng và số tài liệu mỗi trang
taxdoc --window-days 15 --page-size 20

# Chỉ liệt kê, không ghi file
taxdoc --dry-run

# Ghi log chi tiết ra file để chẩn đoán
taxdoc -v --log-file logs/run.log

# Đổi file cấu hình
taxdoc --env-file cau-hinh-khac.env
```

Mã thoát: `0` thành công, `1` chạy xong nhưng thiếu tài liệu, `2` lỗi cấu hình.

## 7. Kết quả đầu ra

```text
output/demo/
├── DOC-20260101-0001-01-2026-Declaration.json
├── DOC-20260101-0002-01-2026-Acknowledgement.json
├── ...
├── index.csv
└── index.json
```

- Tên file **tất định** theo mã tài liệu (kèm kỳ và loại nếu có), nên lần chạy
  sau sẽ **bỏ qua** tài liệu đã có và có thể chạy tiếp khi bị gián đoạn.
- `index.csv` ghi bằng UTF-8 kèm BOM để mở đúng trong Excel.
- `index.json` dùng cho xử lý tự động.
- Nếu tài liệu đã có sẵn, chương trình không tải lại mà vẫn tính là đã thu thập.

## 8. Bối cảnh

Dự án được xây dựng từ một yêu cầu automation thực tế.

Hệ thống vận hành đã xử lý được:

- **workflow phức tạp** — nhiều nguồn dữ liệu, phân trang, quy tắc ngày tháng;
- **khối lượng tài liệu lớn** — thu thập số lượng lớn và chạy tiếp khi gián đoạn;
- **thách thức về độ tin cậy** — lỗi tạm thời, giới hạn tần suất, hệ thống đích
  thay đổi giao diện;
- **nhu cầu vận hành** — cấu hình linh hoạt, ghi log đầy đủ, cập nhật không cần
  sửa mã nguồn.

Do cân nhắc về bảo mật và vận hành, repo này chỉ cung cấp phần kiến trúc và cách
tiếp cận kỹ thuật đã được khái quát hoá.

## 9. Kiểm thử

```bash
python -m unittest discover -s tests -t . -v
```

Bộ test chạy **offline**, không cần Internet và không cần tài khoản: provider
`mock` sinh dữ liệu tất định, và pipeline nhận sẵn hàm `sleep` rỗng nên chạy
tức thì.

| File | Nội dung |
|---|---|
| `tests/test_config.py` | Đọc `.env`, thứ tự ưu tiên, kiểm tra hợp lệ, chia khoảng thời gian |
| `tests/test_storage.py` | Đặt tên file, ghi tài liệu, phát hiện trùng, xuất CSV/JSON |
| `tests/test_pipeline.py` | Chạy hết luồng, phân trang, dry-run, thử lại, bỏ qua file đã có |

## 10. Phạm vi và bảo mật

Repo này **cố tình không chứa**:

- thông tin đăng nhập của môi trường vận hành;
- địa chỉ API và tham số của hệ thống thật;
- dữ liệu thật của người dùng;
- các chi tiết riêng của tổ chức.

Bản vận hành thật có thêm một số tích hợp không nằm trong repo này.

## 11. Giấy phép

Phát hành theo [giấy phép MIT](LICENSE).

Đây là bản tham chiếu công khai, rút gọn. Dự án không liên kết, không được bảo
trợ và không có quan hệ với bất kỳ tổ chức hay dịch vụ nào.
