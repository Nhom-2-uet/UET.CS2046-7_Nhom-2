# Đưa ứng dụng lên mạng

Ứng dụng dùng Streamlit và MySQL. Máy chạy ứng dụng trên cloud cần kết nối
được tới một MySQL database chạy trên mạng; MySQL `127.0.0.1` trên máy cá nhân
không thể được app trên cloud sử dụng.

## Chuẩn bị database

1. Tạo một MySQL-compatible TiDB Cloud Starter instance trong [TiDB Cloud](https://tidbcloud.com/). Gói Starter có hạn mức miễn phí hàng tháng; khi hết hạn mức, database có thể bị giới hạn kết nối/hoạt động.
2. Chọn chế độ **MySQL Compatible** và vùng AWS; tạo instance với spending limit bằng 0 để giữ trong hạn mức miễn phí.
3. Trong SQL Editor, mở kết nối tới instance rồi chạy nội dung `database/schema.sql` để tạo database, bảng và danh mục ban đầu.
4. Ở trang instance, bấm **Connect** → **Public** → **General**, tạo password và ghi lại host, port, username. TiDB Starter yêu cầu TLS; với Streamlit Cloud, dùng CA bundle mặc định `/etc/ssl/certs/ca-certificates.crt`.

## Đưa mã nguồn lên GitHub

Đưa phiên bản cần triển khai của repository lên GitHub. Trong Streamlit Community
Cloud, chọn repository và nhánh, đặt entrypoint là
`AI_PROJECT/APP/frontend/app.py`, và chọn Python 3.12. Streamlit Cloud tìm file
dependencies ở thư mục gốc repository; dự án đã có `requirements.txt` tại đó.

## Khai báo Secrets trong Streamlit Community Cloud

Trong phần Advanced settings → Secrets, khai báo theo TOML, thay các giá trị mẫu
bằng thông tin database và Gemini của bạn:

```toml
DB_HOST = "your-tidb-host"
DB_PORT = 4000
DB_NAME = "chi_tieu_sinh_vien"
DB_USER = "your_tidb_user"
DB_PASSWORD = "your_tidb_password"
DB_SSL_CA = "/etc/ssl/certs/ca-certificates.crt"
GEMINI_API_KEY = "your_gemini_api_key"
GEMINI_MODEL = "your_gemini_model"
```

Không commit file secrets hoặc `.env` lên GitHub. Sau khi deploy, mở đường dẫn
`*.streamlit.app` của app để sử dụng và chia sẻ cho người dùng.
