# Benchmark & Observability Report — Day 14

**Họ tên** HoVanDung
**Ngày chạy** 25/11/2026
**Môi trường** Ubuntu/WSL2, Python 3.11.18 và Docker Desktop Linux. Compose giới hạn mỗi agent quan sát ở 0,5 CPU và 256 MB RAM. Các phép đo dùng mock LLM.

## 1. SLO của agent

| SLI | SLO | Lý do |
| --- | --- | --- |
| p95 latency `/ask` | ≤ 500 ms | Ngưỡng mặc định của `load_test.py` để kiểm soát nhóm request chậm. |
| Error rate `/ask` | ≤ 2% | Ngưỡng mặc định của `load_test.py` để giới hạn tỷ lệ request thất bại. |
| Accuracy trên golden dataset | ≥ 85% trong CI | Chặn chất lượng giảm trước merge. Lần xác nhận sau cập nhật knowledge base dùng ngưỡng 100%. |

### Exercise 7.1 — Prometheus metrics

Sau khi gửi một câu hỏi và đọc `/metrics`, output có:

```text
# TYPE http_requests_total counter
# TYPE agent_in_flight_requests gauge
# TYPE agent_question_length_chars histogram
agent_question_length_chars_count 1.0
```

Counter đếm tổng request. Gauge theo dõi số request đang xử lý. Histogram ghi độ dài ký tự cho mỗi câu hỏi qua validation. Middleware dùng mẫu route và gom URL không khớp vào label `unmatched`. Dùng đường dẫn thô có thể tạo một chuỗi thời gian cho mỗi URL lạ, làm tăng bộ nhớ, lưu trữ và chi phí truy vấn.

## 2. Benchmark hiệu năng bằng `load_test.py`

### 2.1 Concurrency và latency

Agent v2 dùng `MOCK_ERROR_RATE=0.01` và `MOCK_SLOW_RATE=0.03`. Mỗi lượt gửi 300 request. Script tính latency trên response `200` và tỷ lệ lỗi trên toàn bộ request.

| Concurrency | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Error rate | SLO | JSON |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 1 | 4.37 | 188.6 | 220.5 | 1706.9 | 0.67% | PASS | [load_v2_c1.json](reports/load_v2_c1.json) |
| 10 | 39.27 | 192.3 | 220.7 | 1694.1 | 0.67% | PASS | [load_v2_c10.json](reports/load_v2_c10.json) |
| 50 | 102.16 | 204.0 | 328.3 | 1728.1 | 1.00% | PASS | [load_v2_c50.json](reports/load_v2_c50.json) |
| 100 | 46.93 | 571.9 | 4341.8 | 4738.5 | 1.67% | FAIL | [load_v2_c100.json](reports/load_v2_c100.json) |

RPS tăng từ 4,37 lên 102,16 khi tăng concurrency từ 1 lên 50. Ở 100, RPS giảm còn 46,93 trong khi p95 tăng lên 4.341,8 ms. Lượt này vượt ngưỡng latency dù tỷ lệ lỗi còn dưới 2%. Số đo phù hợp với hiện tượng request phải chờ khi tăng tải. Cần thêm số đo hàng đợi hoặc profiling để định vị nguyên nhân.

### 2.2 Tail latency

Giữ 300 request và concurrency 20 cho cả ba lượt, rồi khởi động lại agent với tỷ lệ request chậm tương ứng.

| `MOCK_SLOW_RATE` | avg (ms) | p95 (ms) | p99 (ms) | JSON |
| ---: | ---: | ---: | ---: | --- |
| 0 | 191.7 | 219.9 | 228.0 | [load_v2_slow_0.json](reports/load_v2_slow_0.json) |
| 0.03 | 250.2 | 223.0 | 1694.9 | [load_v2_slow_0.03.json](reports/load_v2_slow_0.03.json) |
| 0.1 | 359.3 | 1693.9 | 1719.8 | [load_v2_slow_0.1.json](reports/load_v2_slow_0.1.json) |

Ở mức 3%, p99 tăng từ 228,0 lên 1.694,9 ms trong khi p95 chỉ từ 219,9 lên 223,0 ms. Khi tỷ lệ tăng đến 10%, nhóm chậm đã đủ lớn để đẩy cả p95 lên gần 1,7 giây. Trung bình làm loãng chênh lệch của nhóm chậm nên cần theo dõi percentile cùng tỷ lệ lỗi.

## 3. Benchmark chất lượng bằng `eval/run_eval.py`

| Chỉ số | Agent v1 | Agent v2 | Agent v2 đã sửa KB |
| --- | ---: | ---: | ---: |
| Accuracy | 4.3% (1/23) | 91.3% (21/23) | 100.0% (23/23) |
| Avg tokens / câu | 57.4 | 108.8 | 114.0 |
| p95 (ms) | 189.6 | 216.6 | 206.5 |
| Tổng cost (USD) | 0.000409 | 0.000757 | 0.000793 |
| Cost / câu đúng (USD) | 0.00040875 | 0.00003607 | 0.00003449 |
| Quality gate | FAIL (ngưỡng 80%) | PASS (ngưỡng 80%) | PASS (ngưỡng 100%) |
| JSON | [eval_v1.json](reports/eval_v1.json) | [eval_v2.json](reports/eval_v2.json) | [eval_v2_fixed.json](reports/eval_v2_fixed.json) |

Eval chạy với `MOCK_ERROR_RATE=0`. V2 thêm retrieval, tăng token trung bình và tổng chi phí giả lập, đồng thời tăng số câu đạt từ 1 lên 21. Chi phí trên mỗi câu đúng giảm từ 0,00040875 USD xuống 0,00003607 USD. Bản đã sửa đạt 23/23, chi phí trên mỗi câu đúng còn 0,00003449 USD và quality gate ghi nhận **0 regression** so với v2 ban đầu.

| ID | Keyword bị thiếu trong v2 ban đầu | Nội dung bổ sung |
| --- | --- | --- |
| `security-02` | `token`, `hết hạn`, `chữ ký` | Tài liệu mô tả JWT có chữ ký số, thời hạn và cách server xác minh. |
| `scaling-03` | `cpu`, `memory`, `custom metrics` | Tài liệu mô tả Kubernetes HPA thay đổi số pod theo các metric đã cấu hình. |

Trong CI, chạy agent v2 rồi chạy `python eval/run_eval.py --min-accuracy 0.85`. Dùng exit code 1 để làm job fail và đặt job thành required check trên pull request. Có thể thêm `--baseline` với báo cáo trước đó để chặn hồi quy theo từng câu.

## 4. Observability stack

Docker image của agent observability cần `PYTHONUSERBASE=/home/agent/.local` để Python tìm các package mà stage builder cài. Sau khi bổ sung biến này, container qua health check và được dùng cho các lượt đo bên dưới.

### 4.1 Dashboard khi có tải

Tại thời điểm lấy mẫu Prometheus trong lượt 3 instance, `POST /ask` đạt **42.73 req/s**, tỷ lệ lỗi **0.46%**, p95 **587.25 ms**, trung bình **258.13 ms** và có **16** request đang xử lý. Ba target Prometheus đều `up`. [Grafana Dashboard](screenshots/grafana-dashboard.png)

| Target agent | Requests/s của `POST /ask` |
| --- | ---: |
| `172.20.0.3:8000` | 14.49 |
| `172.20.0.5:8000` | 14.11 |
| `172.20.0.6:8000` | 14.15 |

Tại mẫu này, Nginx chia tải tương đối đều giữa ba instance. P95 cao hơn trung bình vì một nhóm request chậm kéo dài phần đuôi phân phối. Tốc độ token input là **3303.57 token/s**, so với **1729.34 token/s** output. Prompt của v2 gồm cả câu hỏi, chỉ dẫn hệ thống và nội dung retrieval nên input có thể dài hơn phần trả lời.

Gọi `/metrics` qua Nginx trả **HTTP 404**. Prometheus scrape trực tiếp endpoint nội bộ của từng replica để lấy dữ liệu mà không công khai metric qua proxy.

### 4.2 Thí nghiệm gây lỗi có kiểm soát

Lượt A và B bật đồng thời trên ba replica và dùng Locust với 30 users, tăng 5 users/giây. Mốc đo là lúc bắt đầu áp dụng cấu hình bằng Docker Compose. Script đọc Prometheus mỗi 4 giây và ghi thời điểm đầu tiên thấy từng rule chuyển sang `firing`.

| Kịch bản | Thay đổi | Alert | Thời gian tới firing | Quan sát |
| --- | --- | --- | ---: | --- |
| A | `MOCK_ERROR_RATE=0.2` | `AgentHighErrorRate` | 99,6 giây | Error rate của rule là 20,35%, vượt 5%. |
| B | `MOCK_SLOW_RATE=0.3` | `AgentHighLatencyP95` | 155,6 giây | Latency p95 của rule là 1,895 giây, vượt 1 giây. |
| C | `LLM_MODEL=mock-llm-large` | `LLMCostBurnRateHigh` | 150,0 giây | Tốc độ chi phí ước tính là 16,31 USD/giờ, vượt ngưỡng 2 USD/giờ. |
| D | `docker pause` một replica | `AgentInstanceDown` | 45,2 giây | Prometheus thấy còn 2/3 target `up`. Locust ghi nhận 26 response HTTP `504` từ Nginx. |
| E | `AGENT_VERSION=v1` | Không phát sinh alert mới | — | Panel phiên bản ghi 3 replica v1. Truy vấn retrieval theo cửa sổ 1 phút không có mẫu. |

Thời gian đo A/B bao gồm khởi động lại agent, thu mẫu và thời gian chờ `for` của rule, lần lượt là 1 phút và 2 phút. Khi cả hai rule cùng firing, truy vấn `/ask` ghi nhận khoảng **15,47 req/s**, **20,09%** lỗi, p95 **1.894,68 ms** và trung bình **574,66 ms**. Trong cùng ảnh, rule chi phí đã firing từ giai đoạn tải trước đó và ghi **3,77 USD/giờ** theo bảng giá mock. `promtool test rules` trên bộ test alert của repo trả `SUCCESS`. [Grafana A/B](reports/observability/scenario-AB-grafana.png) · [Prometheus Alerts](screenshots/prometheus-alert-firing.png)

Ở C, đợi rule chi phí về inactive rồi áp dụng model lớn và tạo tải. Tại thời điểm rule firing, Prometheus ghi nhận cả ba instance chạy `mock-llm-large`, với chi phí ước tính **0,000599 USD/lần gọi thành công** cho riêng model này. Bảng giá mock đặt đơn giá input và output của model lớn gấp khoảng 16,67 lần model nhỏ. Tốc độ chi phí theo giờ còn phụ thuộc số lần gọi và số token qua cửa sổ 5 phút. [Prometheus C](reports/observability/scenario-C-alerts.png) · [Grafana C](reports/observability/scenario-C-grafana.png)

Ở D, container bị pause vẫn có trong DNS nhưng ngừng trả lời scrape, nên `up` của target về 0. Tại thời điểm rule firing, metric HTTP 5xx của agent khoảng **0,97%**. Các response `504` phát sinh ở Nginx khi chờ upstream, nên cần metric ở proxy để thấy các lỗi đó. Đã chạy `docker unpause` sau khi thu ảnh. [Prometheus D](reports/observability/scenario-D-alerts.png) · [Grafana D](reports/observability/scenario-D-grafana.png)

Ở E, Prometheus ghi khoảng **581,23 input token/s** và **313,73 output token/s**, với p95 **197,52 ms** và tỷ lệ lỗi **0,39%**. Panel retrieval dùng cửa sổ 5 phút nên khi chụp vẫn hiển thị dữ liệu v2 từ lượt trước. Cảnh báo duy nhất còn firing là rule chi phí từ C, với cùng thời điểm bắt đầu và cửa sổ tính chi phí 5 phút. Sau lượt E, cấu hình agent được trả về v2. [Grafana E](reports/observability/scenario-E-grafana.png)

Hạ tầng đo được thời gian phản hồi, lỗi HTTP và phiên bản đang chạy. Để phát hiện giảm chất lượng như ở kịch bản E, chạy định kỳ một tập câu hỏi có tiêu chí kiểm tra rõ ràng và cảnh báo khi tỷ lệ đạt giảm. Eval ở mục 3 ghi nhận v1 chỉ đạt **1/23** câu, so với **23/23** của v2 đã sửa. Trong CI, cùng tập câu hỏi có thể dùng làm quality gate trước khi triển khai.

Dữ liệu Prometheus đã thu khi chạy A–E được lưu cùng snapshot dashboard và dữ liệu trace. [Số liệu observability (JSON)](reports/observability/measurements.json)

### 4.3 Debug bằng Jaeger và log JSON

**Trace chậm** `f9e4fd1c11a50793a759efd70b2e0ddd`. `POST /ask` trả HTTP `200` trong **1.720,16 ms**. Span `agent.run` kéo dài **1.718,01 ms**. Bên trong, `chat mock-llm-small` chiếm **1.693,10 ms**, tương đương **98,43%** tổng thời gian, còn `agent.retrieve_context` mất **24,62 ms**. [Jaeger slow trace](screenshots/jaeger-slow-trace.png)

```json
{"ts":"2026-11-25T11:31:13.147327+00:00","level":"INFO","service":"observable-agent","instance":"3fd3173963d9","event":"llm_call","trace_id":"f9e4fd1c11a50793a759efd70b2e0ddd","span_id":"dac49423e2b1c63d","request_id":"06347a52ce04","model":"mock-llm-small","agent_version":"v2","input_tokens":70,"output_tokens":32,"cost_usd":0.00003,"llm_ms":1693.1}
```

**Trace lỗi** `0bc812a0938dd57ceb249cd3712a3552`. `POST /ask` trả HTTP `503` trong **873,38 ms**. Span `chat mock-llm-small` (`94d32c8d906acb14`, **847,31 ms**) có event `exception` với kiểu `utils.mock_llm.LLMError`. Lỗi được ghi lại ở `agent.run` và trả về client. [Jaeger error trace](screenshots/jaeger-error-trace.png)

```json
{"ts":"2026-11-25T11:31:19.666029+00:00","level":"INFO","service":"observable-agent","instance":"3fd3173963d9","event":"llm_error","trace_id":"0bc812a0938dd57ceb249cd3712a3552","span_id":"80d79dbe6f0e2cb3","request_id":"7898a342328b","error":"Upstream LLM error: 503 Service Unavailable (mock)"}
```

Log của ứng dụng ghi `span_id` của request HTTP. Khi mở trace bằng `trace_id` sẽ thấy cả span đó và hai span báo lỗi. [Mã ứng dụng ghi log](06-lab-complete/benchmark-observability/production/app/main.py)

## 5. Benchmark scaling bằng Locust

Chạy Locust headless với **100 users trong 2 phút** cho mỗi cấu hình, ramp-up 10 users/giây và cùng cấu hình mock mặc định. Kiểm tra số replica trước và sau mỗi lượt. Dùng `--no-deps` khi chạy Locust để Compose giữ đúng số replica đã đặt.

```bash
docker compose -p k5-day14-observability up -d --scale agent=N --wait
docker compose -p k5-day14-observability ps agent
docker compose -p k5-day14-observability run --rm -T --no-deps locust \
  -f /mnt/locust/locustfile.py --host http://nginx \
  --headless -u 100 -r 10 -t 2m --csv /mnt/results/scale_N
```

Thay `N` lần lượt bằng `1` và `3`, chờ Nginx và Prometheus cập nhật danh sách instance trước khi tạo tải. Bảng lấy từ dòng `POST /ask` trong CSV. Tỷ lệ lỗi tính bằng `Failure Count / Request Count`.

| Agent | Request | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Failures | Tỷ lệ lỗi | Nguồn |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 6344 | 53.35 | 200 | 1700 | 6400 | 91 | 1.43% | [CSV](benchmark-results/scale_1_stats.csv) |
| 3 | 7038 | 58.88 | 200 | 550 | 1700 | 66 | 0.94% | [CSV](benchmark-results/scale_3_stats.csv) |

Ở lượt 3 instance, p95 giảm từ **1700 xuống 550 ms**, còn RPS tăng từ **53.35 lên 58.88**. P50 vẫn là 200 ms. Phân tải qua nhiều replica giúp giảm phần đuôi trong hai lượt đo. Locust giữ số user cố định và mỗi user có thời gian chờ, nên throughput không tăng theo tỷ lệ replica. Trace chậm giúp tách thời gian gọi mock LLM khỏi phần chờ tại agent hoặc proxy.

Docker Desktop khởi động lại giữa lượt 1 và lượt 3 khi công việc được tạm dừng. Các số trên mô tả hai lần chạy thực tế. Để ước lượng mức cải thiện riêng do replica, cần lặp lại xen kẽ hai cấu hình trong cùng phiên.

Nếu p95 ít đổi sau scale, so sánh với p95 của lời gọi LLM theo model. LLM chiếm 98,43% ở trace chậm đã chọn. Thêm replica có thể giảm thời gian xếp hàng khi agent bận, còn thời lượng của từng lời gọi LLM phụ thuộc vào đường xử lý riêng của model.

## 6. Kết luận

1. Dùng p95 và p99 để phát hiện nhóm người dùng gặp phản hồi chậm. Tỷ lệ lỗi bổ sung góc nhìn về những request không tạo được latency thành công.
2. Khi scale, đối chiếu histogram latency với throughput và số request theo instance để biết tải được phân phối ra sao.
3. Theo dõi accuracy và chi phí trên mỗi câu đúng cùng metric vận hành để phát hiện thay đổi mà dashboard hạ tầng có thể bỏ qua.

Nếu triển khai thật, có thể theo dõi accuracy trên một tập truy vấn canary định kỳ, latency theo bước retrieval và LLM, tỷ lệ timeout ở proxy, và cảnh báo chi phí theo mức ngân sách.
