# Đưa ứng dụng lên mạng

Ứng dụng dùng Streamlit và MySQL. Máy chạy ứng dụng trên cloud cần kết nối
được tới một MySQL database chạy trên mạng; MySQL `127.0.0.1` trên máy cá nhân
không thể được app trên cloud sử dụng.

## Chuẩn bị database

1. Tạo một MySQL database trên máy chủ/dịch vụ có kết nối mạng.
2. Chạy `database/schema.sql` trên database đó để tạo bảng và danh mục ban đầu.
3. Ghi lại host, port, tên database, username và password. Cấp cho app một user
   database riêng với quyền cần thiết trên database của ứng dụng.

## Đưa mã nguồn lên GitHub

Đưa phiên bản cần triển khai của repository lên GitHub. Trong Streamlit Community
Cloud, chọn repository và nhánh, đặt entrypoint là
`AI_PROJECT/APP/frontend/app.py`, và chọn Python 3.12. File dependencies nằm tại
`AI_PROJECT/requirements.txt`.

## Khai báo Secrets trong Streamlit Community Cloud

Trong phần Advanced settings → Secrets, khai báo theo TOML, thay các giá trị mẫu
bằng thông tin database và Gemini của bạn:

```toml
DB_HOST = "your-mysql-host"
DB_PORT = 3306
DB_NAME = "chi_tieu_sinh_vien"
DB_USER = "your_mysql_user"
DB_PASSWORD = "your_mysql_password"
GEMINI_API_KEY = "your_gemini_api_key"
GEMINI_MODEL = "your_gemini_model"
```

Không commit file secrets hoặc `.env` lên GitHub. Sau khi deploy, mở đường dẫn
`*.streamlit.app` của app để sử dụng và chia sẻ cho người dùng.
