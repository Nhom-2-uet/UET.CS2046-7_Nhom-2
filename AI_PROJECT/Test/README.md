# Bộ câu mẫu kiểm thử AI

`fixtures/ai_transaction_cases.jsonl` có 100 câu tiếng Việt, chia đều thành 5 nhóm:

- `money_shorthand`: cách viết số tiền như `45k`, `1tr2`, `2 triệu rưỡi`, `1 củ`.
- `multiple_transactions`: nhiều khoản thu/chi trong một câu.
- `relative_date`: ngày tương đối, với ngày tham chiếu cố định `2026-11-24`.
- `ambiguous`: hướng thu/chi hoặc nội dung mơ hồ; chỉ trích xuất khi có đủ căn cứ.
- `missing_information`: thiếu số tiền, chưa phải giao dịch đã xảy ra, hoặc là câu hỏi/dự định.

Mỗi dòng JSONL có câu nhập, ngày tham chiếu, các giao dịch mong đợi và ghi chú về cách xử lý. Các câu không đủ căn cứ được kỳ vọng trả danh sách `transactions` rỗng.

## Kiểm tra corpus ngoại tuyến

Từ thư mục gốc repo, chạy:

```powershell
python .\AI_PROJECT\Test\test_ai.py
```

Lệnh này kiểm tra số lượng, phân bố nhóm, tính duy nhất của mã ca và cấu trúc dữ liệu. Nó không gọi Gemini.

## Chạy benchmark Gemini trực tiếp

Trước tiên cấu hình `GEMINI_API_KEY` và `GEMINI_MODEL` trong `AI_PROJECT/.env`. Nên chạy thử một số lượng nhỏ trước:

```powershell
python .\AI_PROJECT\Test\test_ai.py --live --limit 5
```

Chạy toàn bộ 100 câu bằng:

```powershell
python .\AI_PROJECT\Test\test_ai.py --live
```

Benchmark live gửi từng câu tới Gemini, dùng quota API và có thể mất vài phút. Kết quả báo độ chính xác theo câu, theo nhóm và độ khớp các trường số tiền, danh mục, loại thu/chi, ngày và cờ ngày mặc định. Mục tiêu 95% được ghi theo kế hoạch của nhóm; kết quả phụ thuộc model và có thể dao động giữa các lần chạy.
