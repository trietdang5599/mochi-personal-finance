# mochi-personal-finance
Backend for Personal Finance

## Deploy Docker Hub

Docker Hub repository:

```text
trietdang5599/mochi-finance-api
```

Chạy các lệnh từ root repo.

### 1. Login Docker Hub

```bash
docker login
```

Nhập username/password hoặc access token của Docker Hub.

### 2. Build image

Thay `tagname` bằng version muốn deploy, ví dụ `latest`, `v1.0.0`, `2026-04-30`.

```bash
docker build -t trietdang5599/mochi-finance-api:tagname -f backend/Dockerfile .
```

Ví dụ:

```bash
docker build -t trietdang5599/mochi-finance-api:latest -f backend/Dockerfile .
```

### 3. Chạy thử local

```bash
docker run --rm -p 8000:8000 trietdang5599/mochi-finance-api:tagname
```

Mở API docs:

```text
http://localhost:8000/docs
```

Test nhanh API:

```bash
curl http://localhost:8000/transactions
```

### 4. Push image lên Docker Hub

```bash
docker push trietdang5599/mochi-finance-api:tagname
```

Ví dụ:

```bash
docker push trietdang5599/mochi-finance-api:latest
```

### 5. Pull và chạy image đã push

```bash
docker pull trietdang5599/mochi-finance-api:tagname
docker run --rm -p 8000:8000 trietdang5599/mochi-finance-api:tagname
```

## Deploy Render bằng Docker Hub image

Repo này dùng `render.yaml` theo kiểu image-backed service. Render sẽ pull image từ Docker Hub thay vì build Dockerfile từ GitHub:

```yaml
services:
  - type: web
    name: mochi-personal-finance-api
    runtime: image
    plan: free
    image:
      url: docker.io/trietdang5599/mochi-finance-api:latest
    healthCheckPath: /docs
```

Sau khi push image lên Docker Hub:

### Cách 1: Tạo service trực tiếp từ Docker Hub image

1. Vào Render Dashboard.
2. Chọn **New +** -> **Web Service**.
3. Chọn **Deploy an existing image**.
4. Nhập image URL:

```text
docker.io/trietdang5599/mochi-finance-api:latest
```

5. Deploy service.
6. Sau khi deploy xong, mở:

```text
https://<render-service-url>/docs
```

### Cách 2: Dùng Blueprint `render.yaml`

1. Push `render.yaml` lên GitHub.
2. Vào Render Dashboard.
3. Chọn **New +** -> **Blueprint**.
4. Connect repository này.
5. Render đọc `render.yaml` và tạo service dùng image:

```text
docker.io/trietdang5599/mochi-finance-api:latest
```

Lưu ý: với image-backed service, Render không tự deploy lại chỉ vì bạn push image mới lên tag `latest`. Sau mỗi lần `docker push`, vào Render chọn **Manual Deploy** -> **Deploy latest reference** để Render pull lại image mới.
