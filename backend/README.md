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
Để tự tải file Excel sau khi OAuth thành công, thêm một trong hai biến sau:

```env
GOOGLE_DRIVE_FILE_ID=google-drive-file-id
# hoặc
GOOGLE_DRIVE_FILE_NAME=personal-finance.xlsx
```

Mặc định file tải về nằm trong `backend/storage/google_drive`. Có thể đổi bằng:

```env
GOOGLE_DRIVE_DOWNLOAD_DIR=backend/storage/google_drive
```

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

Callback OAuth xin quyền Google Drive readonly và Google Sheets write. Backend sẽ tự tải file Excel/Google Sheet đã cấu hình; FE cũng có thể dùng access token mới để overwrite nội dung Google Sheet. Có thể gọi lại thủ công bằng access token:

```bash
curl -X POST http://localhost:8000/auth/google/drive/excel \
  -H "Authorization: Bearer <google-access-token>"
```

Ghi dữ liệu lên Google Sheet qua backend:

```bash
curl -X PUT http://localhost:8000/auth/google/sheets/<spreadsheet-id>/values \
  -H "Authorization: Bearer <google-access-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "range": "Sheet1!A1",
    "clear_range": "Sheet1!A:Z",
    "values": [["Date", "Amount"], ["2026-05-01", 100000]]
  }'
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

Khi frontend chạy trên GitHub Pages, các URL production phải được cấu hình như sau:

```env
APP_ENV=production
GOOGLE_REDIRECT_URI=https://<render-service-url>/auth/google/callback
FRONTEND_URL=https://<github-username>.github.io/<repo-name>/
CORS_ORIGINS=https://<github-username>.github.io
GOOGLE_DRIVE_FILE_ID=<google-drive-file-id>
```

Trong Google Cloud Console, Authorized redirect URI phải trùng chính xác:

```text
https://<render-service-url>/auth/google/callback
```

OAuth consent screen cần khai báo các scope:

```text
https://www.googleapis.com/auth/drive.readonly
https://www.googleapis.com/auth/spreadsheets
https://www.googleapis.com/auth/drive.file
```

Google Cloud project cần bật Google Drive API và Google Sheets API. Sau khi thêm scope `spreadsheets`, người dùng phải reconnect Google để FE nhận access token mới; token cũ sẽ vẫn bị Google từ chối khi overwrite Sheet.

Frontend GitHub Pages nên mở login bằng backend Render:

```text
https://<render-service-url>/auth/google/login?return_to=https://<github-username>.github.io/<repo-name>/
```

Nếu OAuth thành công nhưng quay về `http://localhost:5173`, Render đang dùng image/config cũ hoặc `APP_ENV=production` chưa được deploy. Ở production, backend không đọc `backend/.env` và không fallback về localhost. Sau khi sửa env hoặc push image mới, vào Render chọn **Manual Deploy** -> **Deploy latest reference**.

Nếu tạo thủ công thay vì Blueprint:

1. Chọn **New +** -> **Web Service**.
2. Chọn **Deploy an existing image**.
3. Image URL: `docker.io/trietdang5599/mochi-finance-api:latest`.
4. Health Check Path: `/docs`.
5. Cấu hình environment variables theo `backend/.env.example`.
6. Deploy.

Render cấp biến môi trường `PORT`; Dockerfile hiện chạy Uvicorn với `${PORT:-8000}` và bind `0.0.0.0`, nên chạy được cả local lẫn Render.
