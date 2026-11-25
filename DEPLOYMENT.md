# Deployment — Day 14

## URL public

Chờ điền URL `onrender.com` sau khi deploy agent Part 6.

## Nền tảng

Render. Blueprint khai báo Docker web service và dùng lại Key Value miễn phí trong cùng workspace. Trước khi sync, đặt `region` của web service khớp với Key Value hiện có. Trên Render Dashboard, chọn **New → Blueprint**, kết nối branch chứa mã Part 6 và nhập `06-lab-complete/render.yaml` vào **Blueprint Path**. [Blueprint](06-lab-complete/render.yaml) · [Hướng dẫn Render Blueprints](https://render.com/docs/infrastructure-as-code)

## Biến môi trường

| Biến | Nguồn cấu hình |
| --- | --- |
| `PORT` | Render cung cấp cho web service. Dockerfile dùng cổng này khi khởi động. |
| `ENVIRONMENT` | Blueprint đặt `production`. |
| `REDIS_URL` | Lấy **Internal URL** từ mục **Connect** của Key Value hiện có và nhập trên Render Dashboard. |
| `AGENT_API_KEY` | Người deploy nhập trên Render Dashboard. |

Với Blueprint đã tạo, nếu lần sync tiếp theo không hỏi các giá trị trên, thêm biến còn thiếu trong **day14-agent → Environment** sau khi web service được tạo. [Kết nối Key Value](https://render.com/docs/key-value#connect-to-your-key-value-instance) · [Biến `sync: false`](https://render.com/docs/blueprint-spec#prompting-for-secret-values)

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

| Kiểm tra | HTTP mong đợi | HTTP thực tế |
| --- | ---: | --- |
| `GET /health` | 200 | Chờ kiểm tra |
| `GET /ready` | 200 | Chờ kiểm tra |
| `POST /ask` thiếu key | 401 | Chờ kiểm tra |
| `POST /ask` có key | 200 | Chờ kiểm tra |

## Ảnh chụp

- `screenshots/dashboard.png` ghi lại Dashboard có web service và Key Value.
- `screenshots/running.png` ghi lại trạng thái deploy thành công của web service.
- `screenshots/test.png` ghi lại bốn mã HTTP trong PowerShell.
