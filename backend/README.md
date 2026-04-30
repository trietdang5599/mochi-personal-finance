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

Chạy local:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
```

## Chạy bằng Docker

Chạy các lệnh từ root repo:

```bash
docker build -t mochi-finance-api -f backend/Dockerfile .
docker run --rm -p 8000:8000 --name mochi-finance-api mochi-finance-api
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
docker run --rm -p 8080:8000 --name mochi-finance-api mochi-finance-api
```

Khi đó mở `http://localhost:8080/docs`.

## Deploy lên Render

Repo đã có `render.yaml` để deploy bằng Render Blueprint.

1. Push code lên GitHub.
2. Vào Render Dashboard.
3. Chọn **New +** -> **Blueprint**.
4. Connect repository này.
5. Render sẽ đọc `render.yaml` và tạo web service `mochi-personal-finance-api`.
6. Sau khi deploy xong, mở:

```text
https://<render-service-url>/docs
```

Nếu tạo thủ công thay vì Blueprint:

1. Chọn **New +** -> **Web Service**.
2. Connect repository.
3. Runtime: **Docker**.
4. Dockerfile Path: `./backend/Dockerfile`.
5. Docker Build Context Directory: `.`.
6. Health Check Path: `/docs`.
7. Deploy.

Render cấp biến môi trường `PORT`; Dockerfile hiện chạy Uvicorn với `${PORT:-8000}` và bind `0.0.0.0`, nên chạy được cả local lẫn Render.
