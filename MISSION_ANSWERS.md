# Day 14 Lab — Mission Answers

## Part 1 — Localhost vs Production

### Exercise 1.1 — Vấn đề trong bản develop

1. **Secret nằm trong mã nguồn.** `OPENAI_API_KEY` và thông tin đăng nhập trong `DATABASE_URL` được viết trực tiếp trong `app.py`. Đây là dữ liệu mẫu của lab. Với credential thật, người có quyền đọc repo hoặc lịch sử Git có thể lấy được chúng.
2. **Cấu hình gắn với mã nguồn.** `MAX_TOKENS` và `DEBUG` được khai báo dưới dạng hằng số và hiện chưa được dùng để điều khiển mock LLM hoặc server. Đổi biến môi trường cùng tên sẽ không thay đổi hành vi của app.
3. **Địa chỉ và cổng cố định khi chạy `python app.py`.** App bind vào `localhost:8000`. Bên trong container, bind vào loopback giới hạn kết nối trong container đó. Cổng cố định cũng gây vướng khi nền tảng cấp cổng qua `PORT`. Lệnh Docker trong bài đặt `--host 0.0.0.0` qua CLI của Uvicorn và publish cổng tại `127.0.0.1:8000` trên Windows.
4. **Tự động reload luôn bật khi chạy `python app.py`.** `reload=True` khởi động lại tiến trình khi file thay đổi, phù hợp lúc sửa mã nhưng có thể làm gián đoạn request khi server đang phục vụ.
5. **`print()` ghi cả dữ liệu nhạy cảm.** `POST /ask` in API key, toàn bộ câu hỏi và câu trả lời. Các dòng này thiếu trường log nhất quán để lọc theo sự kiện. Với dữ liệu thật, log có thể làm lộ credential hoặc nội dung của người dùng.
6. **Thiếu endpoint riêng cho health và readiness.** Kiểm tra container develop cho thấy `GET /` trả `200`, còn `GET /health` và `GET /ready` đều trả `404`. Nền tảng không có trạng thái sẵn sàng riêng để quyết định khi nào chuyển lưu lượng vào instance.
7. **Thiếu bước dọn dẹp ở cấp ứng dụng khi tắt.** Bản develop dựa vào Uvicorn để dừng server và chờ request đang xử lý. App thiếu hook `lifespan` để cập nhật trạng thái sẵn sàng và thu hồi tài nguyên nếu sau này mở kết nối hoặc khởi chạy tác vụ nền.

Mã đối chiếu [develop/app.py](01-localhost-vs-production/develop/app.py).

### Exercise 1.2 — Kết quả gọi `POST /ask`

Lệnh dưới đây được chạy từ PowerShell trên Windows, qua cổng `127.0.0.1:8000` do container develop của học viên publish. Bản develop nhận `question` qua query string.

```powershell
curl.exe --noproxy '*' -i -X POST 'http://127.0.0.1:8000/ask?question=Hello'
```

```http
HTTP/1.1 200 OK
date: Wed, 25 Nov 2026 07:49:19 GMT
server: uvicorn
content-length: 126
content-type: application/json

{"answer":"Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic."}
```

Mock LLM chọn ngẫu nhiên trong nhóm câu trả lời mặc định nên `answer` có thể thay đổi giữa các lần gọi.

### Exercise 1.3 — So sánh develop và production

| Tiêu chí | Develop | Production | Vì sao quan trọng |
| --- | --- | --- | --- |
| Cấu hình | Khai báo trực tiếp trong `app.py`. | `Settings` trong `config.py` đọc biến môi trường như `HOST`, `PORT`, `DEBUG` và `LLM_MODEL`. | Có thể dùng cùng mã nguồn cho local, staging và production rồi cấp cấu hình theo môi trường. |
| Secret | API key và URL có thông tin đăng nhập nằm trong mã nguồn. API key mẫu còn được in ra log. | Đọc `OPENAI_API_KEY` và `AGENT_API_KEY` từ biến môi trường. `.env.example` để trống giá trị secret. | Có thể xoay vòng credential độc lập với bản deploy và giảm rủi ro lộ qua lịch sử Git hoặc log. |
| Host, port và reload | Khi chạy trực tiếp, dùng `localhost:8000` và `reload=True`. | Dùng `HOST` và `PORT`, mặc định `0.0.0.0:8000`. Reload mặc định tắt và bật khi `DEBUG=true`. | Container có thể nhận kết nối qua cổng publish, nền tảng có thể chọn cổng và server tránh restart do watcher trong chế độ chạy mặc định. |
| Logging | `print()` in nội dung request, response và API key mẫu. | Dùng `logging` và ghi sự kiện có trường như `event`, `question_length` hoặc `response_length`. | Có thể tìm sự kiện theo tên và xem độ dài dữ liệu mà không đưa nội dung câu hỏi hoặc câu trả lời vào log của handler. |
| Health và readiness | `GET /` trả lời chào. Thiếu `/health` và `/ready`. | `GET /health` báo trạng thái và uptime. `GET /ready` kiểm tra `is_ready` và trả `503` khi cờ này tắt. | Bộ điều phối có thể dùng liveness để kiểm tra tiến trình và readiness để quyết định có chuyển request đến instance hay không. |
| Shutdown | Uvicorn thực hiện shutdown mặc định. App thiếu hook shutdown riêng. | Uvicorn xử lý việc chờ request đang chạy. Hook `lifespan` đặt `is_ready=False` và ghi log ở giai đoạn shutdown. | Request đang xử lý có cơ hội hoàn thành. App có sẵn chỗ để đóng kết nối hoặc thu hồi tài nguyên khi tích hợp dịch vụ thật. |
| Giao diện `POST /ask` | Nhận query string `?question=Hello` và trả `answer`. | Nhận JSON `{"question":"Hello"}`, trả `422` khi thiếu câu hỏi và trả `question`, `answer`, `model` khi thành công. | Client cần gửi đúng định dạng cho từng bản và có thêm thông tin để kiểm tra phản hồi của bản production. |

Khi chạy mã bản production trong container riêng với `PORT=8001` và mock LLM, `GET /health` trả `200` với `status: "ok"`, `GET /ready` trả `200` với `ready: true`, và `POST /ask` với JSON `{"question":"Hello"}` trả `200`. Sau khi gửi `SIGTERM`, log Uvicorn ghi `Application shutdown complete`.

Trong lượt chạy đó, cảnh báo thiếu `OPENAI_API_KEY` từ `config.py` khởi tạo root logger trước `logging.basicConfig()` trong `app.py`. Các sự kiện `INFO` của ứng dụng vì thế không xuất hiện trong log thực tế, dù mã đã khai báo các trường sự kiện.

Mã đối chiếu [production/app.py](01-localhost-vs-production/production/app.py), [production/config.py](01-localhost-vs-production/production/config.py), [production/.env.example](01-localhost-vs-production/production/.env.example).

## Part 2 — Docker Containerization

### Exercise 2.1 — Dockerfile của bản develop

1. **Base image.** `FROM python:3.11` lấy image nền đã có Python 3.11 và các thành phần hệ thống đi kèm.
2. **Thư mục làm việc.** `WORKDIR /app` đặt thư mục mặc định cho các lệnh theo sau. Các đường dẫn tương đối như đích `.` của `COPY` và `app.py` trong `CMD` được tính từ `/app`.
3. **Thứ tự `COPY`.** Dockerfile copy `requirements.txt` và chạy `pip install` trước khi copy mã nguồn. Khi chỉ sửa `app.py`, các layer cài dependencies có thể dùng lại từ cache. Khi `requirements.txt` đổi, Docker thực hiện lại bước cài đặt.
4. **`CMD` và `ENTRYPOINT`.** `ENTRYPOINT` cấu hình tiến trình chính. Khi có cả hai ở dạng exec, `CMD` cung cấp tham số mặc định cho `ENTRYPOINT`. Dockerfile develop chỉ có `CMD ["python", "app.py"]`, nên chạy `python app.py` theo mặc định và có thể thay lệnh này bằng đối số sau tên image trong `docker run`.

Mã đối chiếu [Dockerfile develop](02-docker/develop/Dockerfile).

### Exercise 2.2 — Build và chạy image develop

Chạy từ PowerShell ở gốc repo:

```powershell
docker build -f 02-docker/develop/Dockerfile -t my-agent:develop .
docker run --rm -d --name day14-part2-develop -p 127.0.0.1:8000:8000 my-agent:develop
curl.exe --noproxy "*" -i -X POST "http://127.0.0.1:8000/ask?question=What%20is%20Docker%3F"
```

Lần gọi ngay sau `docker run -d` gặp `curl: (52) Empty reply from server`. Sau khi khởi động lại container và đợi `/health` phản hồi, `/ask` trả kết quả sau:

```http
HTTP/1.1 200 OK
date: Wed, 25 Nov 2026 08:03:44 GMT
server: uvicorn
content-length: 103
content-type: application/json

{"answer":"Container là cách đóng gói app để chạy ở mọi nơi. Build once, run anywhere!"}
```

### Exercise 2.3 — So sánh dung lượng image

```powershell
docker build -f 02-docker/production/Dockerfile -t my-agent:advanced .
docker images my-agent
docker image inspect --format '{{.Size}}' my-agent:develop my-agent:advanced
```

| Image | Image ID | Dung lượng hiển thị | Dung lượng từ `image inspect` |
| --- | --- | ---: | ---: |
| `my-agent:develop` | `d19a6f332612` | 1,67 GB | 1.667.788.020 byte |
| `my-agent:advanced` | `44a94ede122d` | 240 MB | 239.815.351 byte |

Mức giảm tính từ số byte là `(1.667.788.020 − 239.815.351) / 1.667.788.020 × 100 ≈ 85,62%`.

Stage `builder` dùng `python:3.11-slim`, cài `gcc` và `libpq-dev`, rồi cài Python dependencies vào `/root/.local`. Stage `runtime` bắt đầu từ một image `python:3.11-slim` mới, copy các package đã cài cùng mã ứng dụng và mock LLM. Image cuối dùng base slim và không mang theo các lớp cài công cụ build của stage `builder`. Tiến trình chạy dưới `appuser`.

Mã đối chiếu [Dockerfile production](02-docker/production/Dockerfile).

### Exercise 2.4 — Docker Compose và kiểm tra qua Nginx

```text
Client → Nginx (:80 trên host) → Agent (:8000, mạng internal)
                                    ├─ cấu hình Redis tại redis:6379
                                    └─ cấu hình Qdrant tại qdrant:6333
```

Nginx chuyển request tới `agent:8000` qua mạng nội bộ. Compose cấu hình `REDIS_URL` và `QDRANT_URL` cho agent, đồng thời đợi Redis và Qdrant báo `healthy` trước khi khởi động agent. Hai lần gọi HTTP dưới đây xác nhận đường đi qua Nginx tới agent và phản hồi của mock LLM.

```powershell
docker compose -p k5-day14-docker -f 02-docker/production/docker-compose.yml up -d --build --wait
docker compose -p k5-day14-docker -f 02-docker/production/docker-compose.yml ps
```

Kết quả `compose ps`:

| Service | Image | Trạng thái | Cổng hiển thị |
| --- | --- | --- | --- |
| `agent` | `k5-day14-docker-agent` | `Up (healthy)` | `8000/tcp` |
| `nginx` | `nginx:alpine` | `Up` | host `80` → `80/tcp`, host `443` → `443/tcp` |
| `qdrant` | `qdrant/qdrant:v1.9.0` | `Up (healthy)` | `6333-6334/tcp` |
| `redis` | `redis:7-alpine` | `Up (healthy)` | `6379/tcp` |

```powershell
curl.exe --noproxy "*" -i "http://127.0.0.1/health"
'{"question":"Explain microservices"}' | curl.exe --noproxy "*" -i -H "Content-Type: application/json" --data-binary '@-' "http://127.0.0.1/ask"
```

**`GET /health`**

```http
HTTP/1.1 200 OK
Server: nginx
Date: Wed, 25 Nov 2026 08:06:01 GMT
Content-Type: application/json
Content-Length: 96
Connection: keep-alive
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block

{"status":"ok","uptime_seconds":43.9,"version":"2.0.0","timestamp":"2026-11-25T08:06:01.066175"}
```

**`POST /ask`**

```http
HTTP/1.1 200 OK
Server: nginx
Date: Wed, 25 Nov 2026 08:06:01 GMT
Content-Type: application/json
Content-Length: 126
Connection: keep-alive
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block

{"answer":"Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic."}
```

Mã đối chiếu [Docker Compose](02-docker/production/docker-compose.yml) và [cấu hình Nginx](02-docker/production/nginx/nginx.conf).

## Part 3 — Cloud Deployment

### Exercise 3.2 — Render

Blueprint khai báo `day14-agent-oregon`, một web service dùng `Dockerfile` trong `06-lab-complete/`. `REDIS_URL` lấy URL nội bộ của Key Value `day14-deployment` qua `fromService`. Người deploy đặt `AGENT_API_KEY` trong Environment của web service. [render.yaml](06-lab-complete/render.yaml)

Bản `day14-agent-oregon` báo **Live** ở commit `29d43dd`. Các lượt kiểm tra public xác nhận `/health` trả `200`, `/ready` trả `200` với `{"ready":true}`, `POST /ask` thiếu key trả `401` và `POST /ask` có key trả `200` cùng câu trả lời mock. [URL public](https://day14-agent-oregon.onrender.com) · [DEPLOYMENT.md](DEPLOYMENT.md)

### Exercise 3.1 — So sánh cấu hình Railway và Render

| Tiêu chí | Railway | Render |
| --- | --- | --- |
| Phạm vi | `railway.toml` mẫu mô tả cách build và chạy một service. Redis được tạo ở cấp project và liên kết qua biến môi trường. | `render.yaml` khai báo web service và nhận URL của Key Value hiện có từ biến môi trường. |
| Build và chạy | Ví dụ trong repo dùng Nixpacks và đặt `startCommand` chạy Uvicorn theo `$PORT`. | Blueprint của bài dùng `runtime: docker`, chỉ định Dockerfile và build context của Part 6, rồi dùng `CMD` từ Dockerfile. |
| Health check | `healthcheckPath` trong `[deploy]` trỏ tới `/health`. | `healthCheckPath` đặt trên web service, cũng trỏ tới `/health`. |
| Cấu hình và secret | Credential được cấp qua biến của service trên Railway. | `AGENT_API_KEY` dùng `sync: false` để nhập trên Dashboard, còn `REDIS_URL` dùng `fromService` để lấy URL nội bộ của Key Value. |

Blueprint của bài khai báo web service ở Oregon và dùng `fromService` để kết nối tới Key Value `day14-deployment` đã có sẵn trong cùng vùng. [Ví dụ Railway của đề](03-cloud-deployment/railway/railway.toml) · [Đặc tả Render Blueprint](https://render.com/docs/blueprint-spec)

### Exercise 3.3 — Pipeline Cloud Run

1. Cloud Build dùng Python 3.11 để cài dependencies và chạy `pytest`.
2. Khi test đạt, pipeline build Docker image, gắn tag theo `$COMMIT_SHA` và `latest`, rồi push cả hai tag lên registry.
3. Bước deploy đưa image tag `$COMMIT_SHA` lên Cloud Run tại `asia-southeast1`, đặt biến môi trường và tham chiếu secret từ Secret Manager.
4. Manifest `service.yaml` mô tả riêng cấu hình service, gồm số instance, concurrency, cổng và các probe `/health` và `/ready`.

Mã đối chiếu [cloudbuild.yaml](03-cloud-deployment/production-cloud-run/cloudbuild.yaml) và [service.yaml](03-cloud-deployment/production-cloud-run/service.yaml).

## Part 4 — API Security

### Exercise 4.1 — API key

Bản develop đọc `AGENT_API_KEY` lúc khởi động. `POST /ask` dùng dependency `verify_api_key` để đọc `X-API-Key`. Thiếu header trả `401`, header sai trả `403`, key đúng trả `200`. Muốn đổi key, cập nhật biến môi trường, khởi động lại service và cập nhật key ở client. Bản Final Project áp dụng hợp đồng riêng, theo đó cả key sai và thiếu key đều trả `401`. [app.py bản develop](04-api-gateway/develop/app.py)

Kết quả `curl -i` chạy trên Ubuntu/WSL2, trích các dòng liên quan:

```http
HTTP/1.1 401 Unauthorized
Content-Type: application/json

{"detail":"Missing API key. Include header: X-API-Key: <your-key>"}
```

```http
HTTP/1.1 403 Forbidden
Content-Type: application/json

{"detail":"Invalid API key."}
```

```http
HTTP/1.1 200 OK
Content-Type: application/json

{"question":"What is Docker?","answer":"Container là cách đóng gói app để chạy ở mọi nơi. Build once, run anywhere!"}
```

### Exercise 4.2–4.3 — JWT và rate limiting

Gọi `POST /auth/token` bằng tài khoản demo `student`, lấy `access_token` và gửi `Authorization: Bearer <token>` cho `POST /ask`. Server ký JWT bằng HS256, kiểm tra chữ ký và thời hạn, rồi lấy `sub` và `role` để xác định người gọi. Token dùng trong phép đo được giữ riêng.

Bản mẫu dùng **sliding window** trong bộ nhớ. Nó bỏ các timestamp quá 60 giây trước khi đếm request còn lại theo từng người dùng. Vai trò `user` có giới hạn **10 request/phút**. Vai trò `admin` được cấp giới hạn **100 request/phút** theo role trong token đã xác thực. [auth.py](04-api-gateway/production/auth.py) · [rate_limiter.py](04-api-gateway/production/rate_limiter.py)

Lượt gọi đầu tiên có JWT hợp lệ trả `200`. Gọi thêm 20 lần liên tiếp với cùng token cho kết quả **9 lượt `200` và 11 lượt `429`**. Tính cả lượt đầu, request thứ 11 là request đầu tiên bị giới hạn.

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 0
Retry-After: 59
Content-Type: application/json

{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":59}}
```

### Exercise 4.4 — Cost guard

Với ngân sách giả lập 10 USD mỗi người mỗi tháng, dùng khóa Redis gồm mã người dùng và tháng UTC. Trước khi gọi LLM, dùng một thao tác nguyên tử để đọc tổng đã dùng và giữ trước phần chi phí ước tính. Nếu tổng vượt 10 USD, trả `402`. Sau khi gọi xong, ghi chi phí theo số token thực tế và hoàn phần giữ dư. Khóa hết hạn khi sang tháng mới. Cách này giúp các worker dùng chung ngân sách và tránh duyệt nhiều request đồng thời vượt ngưỡng.

Một request có thể tốn nhiều token dù người dùng gọi chậm. Rate limit kiểm soát số request trong một khoảng thời gian và cost guard kiểm soát tổng ngân sách. Bản mẫu Part 4 minh hoạ cách kiểm tra trước và ghi usage sau khi gọi LLM bằng ngân sách ngày trong RAM. Agent Part 6 lưu trạng thái ngân sách trong Redis. [cost_guard.py Part 4](04-api-gateway/production/cost_guard.py) · [cost_guard.py Part 6](06-lab-complete/app/cost_guard.py)

## Part 5 — Scaling & Reliability

### Exercise 5.1–5.2 — Liveness, readiness và shutdown

`GET /health` cho biết app đang chạy. `GET /ready` cho biết instance đã sẵn sàng nhận request. Load balancer có thể ngừng chuyển request đến một instance chưa sẵn sàng trong khi tiến trình tiếp tục chạy. Trong lượt chạy local bản develop, `/health` trả `200` với `status: "ok"` và `/ready` trả `200` với `ready: true`.

Gửi `SIGTERM` sau 0,5 giây kể từ lúc bắt đầu request. Lượt thử với một request trả `200` và tiến trình thoát với mã `0`. Trong lượt xác nhận với hai request song song, cả hai trả `200`, log có `Graceful shutdown initiated` và `Shutdown complete`, và tiến trình cũng thoát với mã `0`. Lượt đầu với hai request gặp một lỗi `Connection reset by peer`. Bản mẫu gọi mock LLM đồng bộ trong handler `async`, vì vậy thời điểm một kết nối bắt đầu được xử lý có thể khác thời điểm client gửi request. [app.py bản develop](05-scaling-reliability/develop/app.py)

### Exercise 5.3–5.5 — Stateless, Nginx và Redis

Bản production lưu history theo `session_id` trong Redis. Nếu chỉ lưu trong RAM của từng worker, request sau có thể vào một instance khác và không thấy các lượt trước. Nginx chuyển request tới các agent, còn các agent đọc và ghi cùng một Redis.

```bash
docker compose -p k5-day14-scaling up -d --build --scale agent=3 --wait
docker compose -p k5-day14-scaling ps
python test_stateless.py
docker compose -p k5-day14-scaling down
```

`compose ps` báo **3 agent healthy**, Redis healthy và Nginx mở cổng `8080`. Script gọi `POST /chat` **5 lần** với cùng session và ghi được các instance theo thứ tự sau:

```text
Request 1: instance-53b281
Request 2: instance-1c812d
Request 3: instance-875763
Request 4: instance-53b281
Request 5: instance-1c812d
Total requests: 5
Total messages: 10
Session history preserved across all instances via Redis!
```

Lịch sử đủ 5 cặp hỏi đáp dù request được phân qua 3 instance. Script xác nhận việc dùng chung session qua Redis khi cân bằng tải. [test_stateless.py](05-scaling-reliability/production/test_stateless.py)


## Part 6 — Final Project

Agent dùng Redis để chia sẻ cửa sổ rate limit và ngân sách theo ngày giữa các worker. `/health` kiểm tra tiến trình và `/ready` chỉ trả `200` khi Redis phản hồi. Uvicorn chạy với hai worker trong image và hoàn thành request đang xử lý trước khi FastAPI đóng kết nối Redis khi tắt.

Học viên chạy `python check_production_ready.py` ở chế độ đầy đủ trong Ubuntu/WSL2 với Docker Desktop và Python 3.11. Kết quả:

```text
Checklist Deliverable
  ✅ Dockerfile (multi-stage, < 500 MB)
  ✅ docker-compose.yml (agent + redis)
  ✅ .dockerignore
  ✅ Health check endpoint (GET /health)
  ✅ Readiness endpoint (GET /ready)
  ✅ API Key authentication
  ✅ Rate limiting
  ✅ Cost guard
  ✅ Config từ environment variables
  ✅ Structured logging
  ✅ Graceful shutdown
  ✅ Public URL ready (Railway / Render config)
----------------------------------------------------------------
Result: 12/12 tiêu chí đạt · 42/42 checks passed
PASS 12/12 — PRODUCTION READY! Deploy nào!
```

- Image build trong **45 giây** và script báo dung lượng **273 MB**. Container trả `/health` HTTP `200`.
- `/ready` trả `200` khi Redis hoạt động và `503` khi mất Redis. `/health` vẫn trả `200` trong cả hai trường hợp.
- `/ask` trả `401` khi thiếu hoặc sai key và `200` với key hợp lệ. Với giới hạn thử nghiệm 5 request/phút, request tiếp theo trả `429`. Sau khi restart agent, cửa sổ giới hạn vẫn còn trong Redis.
- Với ngân sách thử nghiệm `0.000001 USD`, lượt gọi đầu tiên trả `402`. Script đọc được **17 dòng log JSON hợp lệ**.
- Request đang xử lý vẫn trả `200` khi agent nhận `SIGTERM`, tiến trình thoát với mã `0`. `docker stop` hoàn thành sau **1,0 giây**, cũng với mã thoát `0`.

Codex chạy lại script đầy đủ trên Docker sau khi hoàn thành Part 7. Kết quả vẫn là **PASS 12/12 · 42/42 checks passed**. Image giữ kích thước **273 MB**. Lượt build có cache hoàn thành sau **4 giây**, còn `docker stop` hoàn thành sau **0,9 giây** với mã thoát `0`.

## AI log

- **Yêu cầu** — Giải thích lỗi mở `0.0.0.0:8000` trên Windows, soạn câu trả lời Part 1 và kiểm tra lại sau khi học viên chạy Docker.
- **Kết quả từ Codex** — Đối chiếu mã hai bản, cập nhật Exercise 1.2 bằng phản hồi thực tế từ container do học viên chạy và kiểm tra các endpoint của bản production trong container riêng.
- **Thao tác của học viên** — Khởi động container develop và yêu cầu kiểm tra lại qua cổng đã publish trên Windows.

- **Yêu cầu Part 2** — Cung cấp lệnh PowerShell để học viên chạy Docker, hỗ trợ xử lý lỗi khi gọi `/ask`, rồi ghi kết quả vào bài.
- **Kết quả từ Codex** — Đối chiếu Dockerfile và cấu hình Compose, hướng dẫn đợi `/health` sau khi gặp lỗi kết nối, tính phần trăm giảm dung lượng và trình bày output học viên cung cấp.
- **Thao tác của học viên** — Tự build hai image, đo dung lượng, kiểm tra `/ask` trên bản develop, chạy Compose và gửi trạng thái service cùng hai phản hồi HTTP qua Nginx.

- **Yêu cầu Part 3** — Chuẩn bị cấu hình cloud, mẫu lưu kết quả và lệnh để học viên tự deploy và kiểm tra.
- **Kết quả từ Codex** — Đối chiếu đặc tả Render, sửa Blueprint sau khi xác định lệch region và kiểm tra ba mã HTTP trên URL Oregon. So sánh cấu hình Railway với Render và diễn giải pipeline Cloud Run từ các manifest của đề.
- **Thao tác của học viên** — Xác nhận Key Value ở Oregon, push Blueprint, đồng bộ trên Render và gửi ảnh service Oregon báo Live. Sau khi cập nhật key trên Render, học viên tự chạy kiểm tra và gửi phản hồi HTTP `200` có nội dung `answer`.

- **Yêu cầu Part 4–5** — Chạy các bài thử còn thiếu, lấy HTTP và log thực tế để điền Mission Answers.
- **Kết quả từ Codex** — Chạy các container và app mẫu trong WSL2. Kiểm tra API key, JWT, rate limit, `SIGTERM` và session Redis qua ba instance. Ghi kết quả thực tế và lý giải các bài tập dựa trên mã ví dụ.
- **Thao tác của học viên** — Cho phép Codex trực tiếp chạy Docker và thu bằng chứng local.

- **Yêu cầu Part 6** — Hoàn thiện bản khung của agent để deploy trong Part 3.
- **Kết quả từ Codex** — Cài đặt xác thực API key, kiểm tra sức khỏe, rate limit và ngân sách dùng Redis, log JSON và shutdown theo vòng đời ứng dụng. Chuẩn bị Dockerfile và Compose, rồi chạy kiểm tra cú pháp, chế độ `--static-only` và lần xác nhận đầy đủ có Docker.
- **Thao tác của học viên** — Cài Python 3.11 cho lab trong Ubuntu, bật tích hợp Docker Desktop cho WSL2, xác nhận Docker Client Linux và Compose đọc được hai service, rồi chạy script đầy đủ. Học viên gửi output `PASS 12/12` cùng các kiểm tra chi tiết.

- **Yêu cầu Part 7** — Hoàn thiện benchmark và observability bằng số đo từ các lượt chạy thật trong workspace của học viên.
- **Kết quả từ Codex** — Thêm histogram độ dài câu hỏi, bổ sung knowledge base cho JWT và Kubernetes HPA, và sửa đường dẫn package Python của image observability. Chạy load test, eval, Locust, các kịch bản alert và `promtool` trong Ubuntu/WSL2. Đối chiếu JSON, CSV, ảnh và hai trace với log gốc trước khi ghi báo cáo. [Benchmark & Observability Report](BENCHMARK_REPORT.md)
- **Thao tác của học viên** — Cho phép Codex trực tiếp chạy Docker và ghi kết quả của các lượt benchmark local vào bài.
