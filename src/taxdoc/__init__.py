"""Tax Document Automation Framework — bản tham chiếu công khai, rút gọn.

Gói được chia theo kiến trúc sạch, mỗi tầng một trách nhiệm:

``taxdoc.core``
    Mô hình dữ liệu, cấu hình, log, tiện ích thử lại và pipeline ghép các giai
    đoạn lại với nhau.
``taxdoc.providers``
    Lớp trừu tượng cho xác thực và thu thập tài liệu, kèm một bản mock chạy
    hoàn toàn offline để demo và kiểm thử.
``taxdoc.storage``
    Các storage adapter ghi tài liệu đã thu thập và xuất danh sách có cấu trúc.

Mặc định mọi thứ chạy offline. Repository này **không** chứa tích hợp với hệ
thống thật; xem ``README.md`` và ``docs/ARCHITECTURE.md`` để hiểu lý do thiết kế.
"""

from __future__ import annotations

__version__ = "1.0.0"

__all__ = ["__version__"]
