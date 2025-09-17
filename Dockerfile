# Sử dụng base image Python 3.11-slim, là một lựa chọn tốt và hiện đại.
FROM python:3.11-slim

# Thiết lập các biến môi trường để tối ưu hóa Python trong container.
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Thiết lập thư mục làm việc.
WORKDIR /app

# Sao chép file requirements.txt trước để tận dụng Docker layer caching.
# Nếu file này không đổi, Docker sẽ không cần cài lại các thư viện ở lần build sau.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép toàn bộ mã nguồn của dự án vào container.
# Cách này đảm bảo cả thư mục 'app' và file 'main.py' ở gốc đều được sao chép.
COPY . .

# Cloud Run sẽ chạy container với một user không phải root để tăng cường bảo mật.
# Do đó, chúng ta không cần tự tạo user 'appuser' nữa, có thể bỏ qua bước này để đơn giản hóa.

# Cloud Run yêu cầu ứng dụng lắng nghe trên cổng được cung cấp qua biến môi trường $PORT (thường là 8080).
# EXPOSE ở đây mang tính chất tài liệu, cho biết container sẽ lắng nghe trên cổng nào.
EXPOSE 8080

# Xóa HEALTHCHECK cũ đi. Cloud Run có cơ chế health check riêng, mạnh mẽ hơn và tự động
# kiểm tra trên cổng $PORT mà nó cung cấp. HEALTHCHECK trong Dockerfile có thể gây xung đột
# và không cần thiết trong môi trường Cloud Run.

# Đây là dòng lệnh quan trọng nhất.
# Nó khởi chạy uvicorn và yêu cầu nó lắng nghe trên cổng được cung cấp bởi Cloud Run ($PORT).
# Chúng ta dùng "shell form" (không có ngoặc vuông) để shell có thể nhận diện và thay thế biến $PORT.
CMD uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1