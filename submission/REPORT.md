# Báo cáo cá nhân - K4-L3B Day 13 Monitoring & LLMOps

> Evidence dùng đường dẫn tương đối từ file này. Mục 8 là bản nháp dựa trên công việc thực tế; học viên cần đọc, chỉnh bằng lời của mình và xác nhận trước khi nộp.

## 1. Thông tin học viên

- **Họ và tên:** Hoàng Văn Sơn
- **MSSV:** 2A202602375
- **Lớp:** K4-L3B
- **Repository URL:** https://github.com/HoangVanSon252/K4-L3B-Day13-HoangVanSon-2A202602375-Monitoring-LLMOps
- **Commit SHA cuối:** Chưa chốt; điền sau commit cuối.
- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1`
- **Tên project Langfuse cá nhân:** `day13-k4-l3b-2A202602375`

## 2. Evidence index

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | [01-pytest.txt](evidence/01-pytest.txt) |
| Log validator | [02-log-validator.txt](evidence/02-log-validator.txt) |
| Dashboard validator | [03-dashboard-validator.txt](evidence/03-dashboard-validator.txt) |
| Structured log | [04-structured-log.txt](evidence/04-structured-log.txt) |
| PII redaction | [05-pii-redaction.txt](evidence/05-pii-redaction.txt) |
| Trace list | [06-trace-list.png](evidence/06-trace-list.png) |
| Trace waterfall | [07-trace-waterfall.png](evidence/07-trace-waterfall.png) |
| Trace metadata | [08-trace-metadata.png](evidence/08-trace-metadata.png) |
| Prompt versions | [09-prompt-versions.png](evidence/09-prompt-versions.png); [metadata](evidence/09-prompt-versions.txt) |
| Prompt rollback | [10-prompt-rollback.png](evidence/10-prompt-rollback.png); [metadata](evidence/10-prompt-rollback.txt) |
| Dashboard runtime | [11-dashboard-overview.png](evidence/11-dashboard-overview.png) |
| Incident metric | [12-incident-metric.txt](evidence/12-incident-metric.txt) |
| Incident log | [13-incident-log.txt](evidence/13-incident-log.txt) |
| Incident trace | [14-incident-trace.png](evidence/14-incident-trace.png) |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | Starter chưa hoàn thiện TODO | 100/100 | 229 records, 98 correlation IDs, không thiếu schema/context |
| `validate_dashboard.py` | Dashboard contract starter | 6/6 panel | Có query, unit và threshold cho mọi panel |
| `pytest` | 21 test starter | 22 passed | Thêm kiểm tra header correlation ID và response time |
| Số traces hợp lệ | 0 | 38 root traces | Vượt yêu cầu tối thiểu 10 trace |
| Số PII leak | Chưa kiểm chứng | 0 | Validator quét toàn bộ `data/logs.jsonl` |
| Latency P50/P95/P99; TTFT P95 | Chưa ghi | 153/2221/2221 ms; 50 ms | 10 request cuối; lần fetch prompt đầu làm tăng tail latency nhưng vẫn dưới 3000 ms |
| Retrieval success rate | Chưa ghi | 100% | 10 request cuối có `tool_success=true` |

## 4. Logging và PII

- **Correlation ID:** middleware xóa context cũ, nhận `x-request-id` hoặc sinh `req-<8-hex>`, bind bằng `structlog.contextvars`, rồi trả ID và `x-response-time-ms` trong response header.
- **Metadata structured log:** `ts`, `level`, `event`, `service`, `env`, `correlation_id`, `user_id_hash`, `session_id`, `feature`, `model`; response có thêm latency, TTFT, token, cost, quality và trạng thái retrieval.
- **PII scrubbing:** processor `scrub_event` chạy trước bước ghi JSONL, che email, số điện thoại Việt Nam, CCCD và thẻ thanh toán; user ID được SHA-256 rồi rút gọn 12 ký tự.
- **Kiểm chứng:** `validate_logs.py` báo 0 leak; evidence synthetic cho thấy bốn loại PII đều thành `[REDACTED_*]`.

## 5. Tracing và prompt versioning

- **Trace cá nhân:** 38 root observation `lab-agent-run` trong project cá nhân; input/output raw bị tắt để tránh lộ PII.
- **Cấu trúc:** `lab-agent-run` (AGENT) có child `retrieval` (RETRIEVER) và `generation` (GENERATION); generation ghi model, prompt object, input/output tokens và cost.
- **Nối trace với log:** metadata root có `correlation_id`, feature và model; user ID được hash, session ID và tags được truyền qua `propagate_attributes`.
- **Prompt:** `day13-chat`; v1 có nhãn `baseline` và `production`; v2 có nhãn `candidate`.
- **Trace candidate v2:** `e7149b41dfafb17fa8bbd3250603b73b` (session `prompt-v2-confirmed`).
- **Trace rollback v1:** `e694a70dec209a636297fde647d79147` (session `prompt-v1-rollback`).
- **Promote/rollback:** đã chuyển `production` sang v2, phát trace candidate, sau đó bỏ `production` khỏi v2 và gắn lại cho v1; trace rollback xác nhận ứng dụng dùng lại v1.

## 6. Dashboard, SLO và alerts

- **Dashboard:** `scripts/build_dashboard.py` đọc JSONL trong cửa sổ 60 phút gần nhất và dựng 6 panel: latency/TTFT, traffic, errors/retrieval, cost, tokens và quality. Runtime HTML và PNG nằm trong evidence.
- **SLO:** 99.5% request phải có `response_sent` với latency không quá 3000 ms trong cửa sổ 28 ngày. Ngưỡng bảo vệ gồm error rate <=2%, daily cost <=2.5 USD, quality trung bình >=0.75 và retrieval success >=90%.
- **Error budget:** 0.5%; với 10,000 request trong 28 ngày, tối đa 50 request được phép lỗi hoặc chậm hơn 3000 ms.
- **Alerts:** `HighLatencyP95` (warning, 5m), `LowRetrievalSuccess` (critical, 5m), `HighCostSpike` (warning, 1h); cùng gửi Slack `#k4-l3b-alerts`, có owner và runbook tại `docs/alerts.md`.

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1`.
- **Khoảng thời gian:** `2026-09-30T05:11:02Z` đến `2026-09-30T05:11:14Z` (UTC).
- **Metrics:** 5 response feature `monitoring` có latency 2803-4449 ms, trung bình 3210.6 ms, vượt ngưỡng 3000 ms; TTFT vẫn 50 ms.
- **Log:** `response_sent`, `correlation_id=req-f3130fb5`, `latency_ms=4449`, `tool_success=true`.
- **Trace:** `a2f7a1cd6b69f388b165ae0199a939de`; retrieval khoảng 2.505 s, generation khoảng 0.156 s.
- **Root cause:** incident `rag_slow` làm retrieval chậm; generation không phải nguồn trễ chính.
- **Fix:** tắt `rag_slow`; ở production cần kiểm tra retrieval/vector store, cache và timeout trước khi rollback prompt.
- **Phòng ngừa:** alert P95 >3000 ms, theo dõi retrieval success và dùng runbook Metrics -> Logs -> Traces.

## 8. Giải thích và tự đánh giá

> Học viên cần viết lại/xác nhận mục này bằng trải nghiệm của chính mình trước khi nộp.

- **Quyết định kỹ thuật:** không capture raw prompt/output trên Langfuse; chỉ ghi metadata an toàn và preview đã scrub để vẫn điều tra được mà không lộ PII.
- **Blocker:** trace ban đầu không xuất hiện dù script đã chạy.
- **Cách xử lý:** kiểm tra exporter và phát hiện `LANGFUSE_BASE_URL` có dấu `/` cuối làm endpoint OTLP thành `//api/...` và trả redirect 308; chuẩn hóa URL, tăng timeout và gọi `flush()`/`shutdown()` cho script ngắn.
- **Luồng điều tra:** metric xác định triệu chứng và thời gian; log chọn request qua `correlation_id`; trace so sánh span để tìm bước gây chậm.
- **Vai trò vận hành:** prompt version giúp gắn thay đổi với latency/token/cost/quality; label `production` cho phép rollback nhanh; SLO và error budget quyết định khi nào cần hành động.
- **Điều quan trọng nhất:** không kết luận nguyên nhân từ một metric; phải nối bằng chứng metric, log và trace của cùng request.
- **Hạn chế còn lại:** dashboard local dùng dữ liệu JSONL theo cửa sổ 60 phút; khi triển khai production cần backend lưu trữ metrics dài hạn.

## 9. Checklist trước khi nộp

- [x] Đổi tên project Langfuse thành `day13-k4-l3b-2A202602375`.
- [x] Thêm ảnh Langfuse `06`, `07`, `08`, `09`, `10`, `14`.
- [x] Incident evidence nối đúng metric -> log -> trace.
- [x] Repository chạy lại được; pytest và validators đều đạt.
- [x] Không commit `.env`, challenge file, secret hoặc PII thô.
- [ ] Đọc và viết lại/xác nhận mục tự đánh giá.
- [ ] Commit cuối, điền SHA vào mục 1 và nộp URL/SHA trên LMS/Codelabs.