# Deployment — Day 14

## URL public

[day14-agent-oregon trên Render](https://day14-agent-oregon.onrender.com) — commit `29d43dd` báo **Live** trên Dashboard.

## Nền tảng

Render. Blueprint khai báo Docker web service `day14-agent-oregon` ở Oregon để dùng lại Key Value `day14-deployment` trong cùng workspace. Sau khi push lên `main`, kiểm tra **Syncs** trong Blueprint hiện có. Dùng **Manual sync** nếu Render chưa tự sync. [Blueprint](06-lab-complete/render.yaml) · [Hướng dẫn Render Blueprints](https://render.com/docs/infrastructure-as-code)

## Biến môi trường

| Biến | Nguồn cấu hình |
| --- | --- |
| `PORT` | Render cung cấp cho web service. Dockerfile dùng cổng này khi khởi động. |
| `ENVIRONMENT` | Blueprint đặt `production`. |
| `REDIS_URL` | Blueprint dùng `fromService` để lấy URL nội bộ của Key Value `day14-deployment`. |
| `AGENT_API_KEY` | Người deploy nhập trên Render Dashboard. |

Sau khi web service mới được tạo, đặt `AGENT_API_KEY` trong **day14-agent-oregon → Environment** rồi chọn **Save and deploy**. [Kết nối Key Value](https://render.com/docs/key-value#connect-to-your-key-value-instance) · [Biến `sync: false`](https://render.com/docs/blueprint-spec#prompting-for-secret-values)

## Kiểm tra URL public

Chạy đoạn sau trong PowerShell khi web service đã deploy. Nhập API key đã đặt trên Render tại dấu nhắc ẩn. Ba lượt đầu in mã HTTP. Lượt có key in cả mã và nội dung phản hồi.

```powershell
$base = 'https://day14-agent-oregon.onrender.com'

curl.exe -q -sS --max-time 120 -o NUL -w 'GET /health          %{http_code}\n' "$base/health"
curl.exe -q -sS --max-time 120 -o NUL -w 'GET /ready           %{http_code}\n' "$base/ready"

'{"question":"Hello"}' | curl.exe -q -sS --max-time 120 -o NUL `
  -w 'POST /ask thieu key  %{http_code}\n' `
  -H 'Content-Type: application/json' --data-binary '@-' "$base/ask"

$secureKey = Read-Host 'Nhap key cua service Oregon' -AsSecureString
$agentKey = [System.Net.NetworkCredential]::new('', $secureKey).Password

try {
    $response = Invoke-WebRequest -UseBasicParsing -ErrorAction Stop `
        -Uri "$base/ask" -Method Post -TimeoutSec 120 `
        -Headers @{ 'X-API-Key' = $agentKey } `
        -ContentType 'application/json' -Body '{"question":"Hello"}'
    "POST /ask co key     $($response.StatusCode)"
    $response.Content
} finally {
    Remove-Variable agentKey, secureKey
}
```

| Kiểm tra | HTTP mong đợi | HTTP thực tế của bản Oregon |
| --- | ---: | --- |
| `GET /health` | 200 | `200` · `{"status":"ok"}` |
| `GET /ready` | 200 | `200` · `{"ready":true}` |
| `POST /ask` thiếu key | 401 | `401` · `{"detail":"Missing or invalid API key"}` |
| `POST /ask` có key | 200 | `200` · JSON có `question` và `answer`. |

Phản hồi thực tế cho `POST /ask` có key lúc 10:18:06 GMT ngày 25/11/2026:

```http
HTTP/1.1 200 OK
Date: Wed, 25 Nov 2026 10:18:06 GMT
Content-Type: application/json

{"question":"Hello","answer":"Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic."}
```

Ngày 25/11/2026, bản Singapore trả `503` cho `/ready` vì Key Value `day14-deployment` ở Oregon. Sau khi deploy web service cùng vùng với Key Value, `/ready` trên URL Oregon trả `200` với `{"ready":true}`. [Kết nối nội bộ trên Render](https://render.com/docs/key-value#connect-to-your-key-value-instance)

## Ảnh chụp

- [Dashboard Render](screenshots/dashboard.png) hiển thị web service `day14-agent-oregon` ở trạng thái **Deployed**.
- [Lần deploy đang chạy](screenshots/running.png) xác nhận commit `29d43dd` ở trạng thái **Live**.
- [Kết quả kiểm tra API](screenshots/test.png) ghi lại bốn mã HTTP `200 / 200 / 401 / 200` trong PowerShell.
