# Backend Clean Architecture

GitHub Pages không chạy Python runtime. Thư mục này là backend API scaffold để deploy riêng khi cần đồng bộ dữ liệu thật.

```text
backend/
├── domain/                 # Enterprise business rules
├── application/            # Use cases
├── interface_adapters/     # Controllers/presenters/contracts
├── infrastructure/         # Frameworks, DB, external services
└── main.py                 # FastAPI composition root
```

## Chạy local

Chạy các lệnh từ root repo:

```bash
cp backend/.env.example backend/.env
```

Điền Google OAuth credentials trong `backend/.env` nếu cần login Google thật.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Mở:

```text
http://localhost:8000/docs
```

Google OAuth login:

```text
http://localhost:8000/auth/google/login
```

## Chạy bằng Docker

Chạy các lệnh từ root repo:

```bash
docker build -t trietdang5599/mochi-finance-api:latest -f backend/Dockerfile .
docker run --rm --env-file backend/.env -p 8000:8000 --name mochi-finance-api trietdang5599/mochi-finance-api:latest
```

Mở API docs:

```text
http://localhost:8000/docs
```

Test nhanh:

```bash
curl http://localhost:8000/transactions
```

Tạo transaction mẫu:

```bash
curl -X POST http://localhost:8000/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "type": "expense",
    "amount": 150000,
    "date": "2026-04-30",
    "category_id": "food",
    "description": "Lunch"
  }'
```

Nếu muốn đổi port local:

```bash
docker run --rm --env-file backend/.env -p 8080:8000 --name mochi-finance-api trietdang5599/mochi-finance-api:latest
```

Khi đó mở `http://localhost:8080/docs`.

## Deploy lên Render

Repo đã có `render.yaml` để deploy bằng Docker Hub image:

```text
docker.io/trietdang5599/mochi-finance-api:latest
```

1. Build image.
2. Push lên Docker Hub.
3. Vào Render Dashboard.
4. Chọn **New +** -> **Blueprint**.
5. Connect repository này.
6. Render sẽ đọc `render.yaml` và tạo web service `mochi-personal-finance-api`.
7. Cấu hình environment variables trên Render theo `backend/.env.example`.
8. Sau khi deploy xong, mở:

```text
https://<render-service-url>/docs
```

Nếu tạo thủ công thay vì Blueprint:

1. Chọn **New +** -> **Web Service**.
2. Chọn **Deploy an existing image**.
3. Image URL: `docker.io/trietdang5599/mochi-finance-api:latest`.
4. Health Check Path: `/docs`.
5. Cấu hình environment variables theo `backend/.env.example`.
6. Deploy.

Render cấp biến môi trường `PORT`; Dockerfile hiện chạy Uvicorn với `${PORT:-8000}` và bind `0.0.0.0`, nên chạy được cả local lẫn Render.
