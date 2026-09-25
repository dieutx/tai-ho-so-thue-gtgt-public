# Kiến trúc

Tài liệu này dành cho người đọc mã nguồn hoặc muốn mở rộng framework. Mục tiêu là
mỗi module chỉ có **một trách nhiệm**, và mọi phần dễ thay (cách xác thực, nguồn
tài liệu, nơi lưu trữ) đều tách riêng để có thể thay mà không ảnh hưởng phần còn lại.

## Bản đồ module

| Module | Trách nhiệm | Không được làm |
|---|---|---|
| `core/models.py` | `DocumentRecord`, `CollectionPeriod`, `PageResult`, `RunSummary` | Gọi mạng, đọc/ghi file |
| `core/errors.py` | Cây ngoại lệ | — |
| `core/config.py` | `Settings` từ `.env` + biến môi trường, chia khoảng thời gian | Gọi mạng |
| `core/retry.py` | `call_with_retries`: thử lại với thời gian chờ tăng dần | Gọi mạng, hiểu nghiệp vụ |
| `core/logging_setup.py` | Cấu hình log, gắn `RedactionFilter` để che giá trị nhạy cảm | Ghi log nghiệp vụ |
| `core/pipeline.py` | `DataCollector` (duyệt trang) và `Pipeline` (điều phối) | Chi tiết giao thức |
| `providers/base.py` | `AuthenticationProvider`, `DocumentProvider` (interface) | Đọc/ghi file |
| `providers/mock_provider.py` | Bản mock offline, sinh dữ liệu tất định | Gọi mạng |
| `storage/exporter.py` | `StorageAdapter` + bản ghi xuống filesystem, xuất CSV/JSON | Gọi mạng |
| `cli.py` | Tham số dòng lệnh, mã thoát, khởi tạo thành phần | Nghiệp vụ |

Quan hệ phụ thuộc chỉ đi một chiều:

```text
cli ─► pipeline ─► providers/base ─► core/models
  │         │
  │         ├─► core/retry, core/errors
  │         └─► storage/exporter ─► core/models
  ├─► providers/__init__  (factory chọn provider)
  ├─► storage/__init__
  └─► core/config ─► core/models
```

`core/models.py` và `core/errors.py` là **lá**: chỉ dùng thư viện chuẩn và không
import module nào ở trên chúng. Nhờ vậy không có vòng import và rất dễ test.

## Năm giai đoạn của một lần chạy

```text
main()  (cli.py)
  │  Settings.from_env()      đọc .env rồi tới biến môi trường, tham số dòng lệnh thắng
  │  build_authentication()   lớp xác thực
  │  build_provider()         nguồn tài liệu
  ▼
Pipeline.run()  (core/pipeline.py)
  │
  ├─ Giai đoạn 1  authentication.authenticate()        → phiên làm việc
  ├─ Giai đoạn 2  Settings.windows()                    → nhiều khoảng ≤ window_days
  │
  ├─ Giai đoạn 3  DataCollector.collect()
  │                  provider.search(period, page) cho tới hết trang
  │
  ├─ Giai đoạn 4  với mỗi tài liệu: storage.exists() → storage.save()
  │                  (bỏ qua bước tải nếu tài liệu đã có sẵn)
  │
  └─ Giai đoạn 5  storage.export_index() → index.csv + index.json
```

`DataCollector` nhận một callback `is_stored` do `Pipeline` tiêm vào, nên nó
không biết gì về tầng lưu trữ mà vẫn bỏ qua được việc tải trùng — đây là ví dụ
cho nguyên tắc đảo ngược phụ thuộc.

## Ranh giới phụ thuộc (dependency injection)

`Pipeline` nhận `settings`, `authentication`, `provider`, `storage` qua tham số
khởi tạo, cùng hai thứ giúp test dễ hơn:

- `collector`: mặc định là `DataCollector`, có thể thay bằng bản tự viết;
- `sleep`: hàm ngủ, test truyền vào một hàm rỗng để chạy tức thì.

Nhờ vậy `tests/test_pipeline.py` chạy trọn luồng 5 giai đoạn mà không ra Internet
và không chờ đợi.

## Mở rộng

### Thêm nguồn tài liệu mới

1. Tạo lớp con của `DocumentProvider` trong `providers/`, cài `source`,
   `search()` và `fetch()`.
2. Đăng ký trong `build_provider()` ở `providers/__init__.py`.
3. Nếu cần cấu hình riêng, thêm trường vào `core/config.py` kèm kiểm tra hợp lệ.
4. Thêm test cho provider mới.

`Pipeline`, `DataCollector` và tầng lưu trữ **không cần sửa**.

### Đổi nơi lưu trữ

Tạo một lớp con của `StorageAdapter`. Chỉ cần cài `exists()`, `save()` và
`export_index()`. Ví dụ có thể hiện thực bản lưu lên kho đối tượng hoặc cơ sở dữ
liệu mà không đụng tới pipeline.

### Đổi cách thử lại

Mọi bước có thể hỏng tạm thời đều đi qua `call_with_retries`. Đổi số lần thử và
hệ số chờ bằng `TAXDOC_REQUEST_ATTEMPTS` và `TAXDOC_RETRY_BACKOFF`.

## Kiểm thử

Bộ test chạy hoàn toàn offline: provider mock sinh dữ liệu tất định nên không có
request nào ra Internet.

```bash
python -m unittest discover -s tests -t . -v
```

| File | Nội dung |
|---|---|
| `test_config.py` | Đọc `.env`, thứ tự ưu tiên, kiểm tra hợp lệ, chia khoảng thời gian |
| `test_storage.py` | Đặt tên file, ghi tài liệu, phát hiện trùng, xuất CSV/JSON |
| `test_pipeline.py` | Chạy hết luồng, phân trang, dry-run, thử lại, bỏ qua file đã có |

## Phạm vi của bản công khai

Repository này chỉ chứa **kiến trúc và cách tiếp cận kỹ thuật**. Những phần sau
cố tình không có mặt:

- tích hợp với bất kỳ hệ thống thật nào (chỉ có provider mock);
- thông tin xác thực, giá trị cấu hình của môi trường chạy thật;
- dữ liệu thật và bản ghi request/response.

Đây là bản tham chiếu công khai rút gọn, không phải công cụ vận hành đầy đủ.
