# Deployment — Day 14

## URL public

Bản đầu tiên [day14-agent ở Singapore](https://day14-agent-4xaq.onrender.com) chạy commit `1148a22`. Chờ URL public của `day14-agent-oregon` sau khi sync Blueprint mới.

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

Chạy đoạn sau trong PowerShell khi web service đã deploy. Nhập URL và API key đã đặt trên Render khi được hỏi. Mỗi phép kiểm tra chỉ in mã HTTP.

```powershell
$base = (Read-Host 'Public URL').TrimEnd('/')
$secureKey = Read-Host 'AGENT_API_KEY' -AsSecureString
$agentKey = [System.Net.NetworkCredential]::new('', $secureKey).Password

function Get-Day14HttpStatus {
    param([string]$Method, [string]$Path, [hashtable]$Headers = @{})

    $request = @{
        Uri = "$base$Path"
        Method = $Method
        Headers = $Headers
        UseBasicParsing = $true
        ErrorAction = 'Stop'
        TimeoutSec = 120
    }
    if ($Method -eq 'POST') {
        $request.ContentType = 'application/json'
        $request.Body = '{"question":"Hello"}'
    }

    try {
        [int](Invoke-WebRequest @request).StatusCode
    } catch {
        if (-not $_.Exception.Response) { throw }
        [int]$_.Exception.Response.StatusCode
    }
}

try {
    "GET /health                   $(Get-Day14HttpStatus GET /health)"
    "GET /ready                    $(Get-Day14HttpStatus GET /ready)"
    "POST /ask (thieu key)         $(Get-Day14HttpStatus POST /ask)"
    "POST /ask (co key)            $(Get-Day14HttpStatus POST /ask @{ 'X-API-Key' = $agentKey })"
} finally {
    Remove-Variable agentKey, secureKey
}
```

| Kiểm tra | HTTP mong đợi | HTTP thực tế của bản Singapore |
| --- | ---: | --- |
| `GET /health` | 200 | `200` · `{"status":"ok"}` |
| `GET /ready` | 200 | `503` · `{"ready":false}` |
| `POST /ask` thiếu key | 401 | `401` · `{"detail":"Missing or invalid API key"}` |
| `POST /ask` có key | 200 | Chờ Redis sẵn sàng để kiểm tra từ máy học viên. |

Lần kiểm tra ngày 25/11/2026 xác nhận `/ready` trả `503`. Key Value `day14-deployment` hiển thị **Available** ở Oregon, còn web service ở Singapore. URL nội bộ yêu cầu cả hai cùng workspace và cùng region. Bốn bài kiểm tra sẽ được chạy lại trên URL của `day14-agent-oregon`. [Kết nối nội bộ trên Render](https://render.com/docs/key-value#connect-to-your-key-value-instance)

## Ảnh chụp

- `screenshots/dashboard.png` ghi lại Dashboard có web service và Key Value.
- `screenshots/running.png` ghi lại trạng thái deploy thành công của web service.
- `screenshots/test.png` ghi lại bốn mã HTTP trong PowerShell.
