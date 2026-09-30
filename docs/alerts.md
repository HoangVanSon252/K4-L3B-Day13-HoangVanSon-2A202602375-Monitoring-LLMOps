# Alerts và runbook

Các alert dưới đây dựa trên triệu chứng người dùng/SLO. Tất cả gửi tới Slack `#k4-l3b-alerts`, owner `student-2A202602375`.

## Alert 1: HighLatencyP95

- Severity: `warning`; duration: `5m`.
- Điều kiện: `p95(latency_ms) > 3000` trong 5 phút.
- Ảnh hưởng: người dùng chờ phản hồi lâu hơn mục tiêu SLO.
- Kiểm tra: mở panel Latency để khoanh vùng thời gian; lọc `response_sent` có latency cao và lấy `correlation_id`; mở trace cùng ID để so sánh retrieval và generation.
- Mitigation: tắt incident/practice scenario; giảm tải hoặc đặt timeout cho retrieval; chỉ rollback prompt nếu trace chứng minh prompt/generation là nguyên nhân.

## Alert 2: LowRetrievalSuccess

- Severity: `critical`; duration: `5m`.
- Điều kiện: `retrieval_success_rate < 90` trong 5 phút.
- Ảnh hưởng: câu trả lời có thể thiếu context hoặc giảm chất lượng.
- Kiểm tra: mở panel Errors & retrieval; lọc log có `tool_success=false`; mở trace theo `correlation_id` và kiểm tra observation `retrieval`.
- Mitigation: kiểm tra nguồn tài liệu/vector store, kết nối và timeout; bật phản hồi an toàn khi không có context; khôi phục cấu hình retrieval gần nhất nếu có regression.

## Alert 3: HighCostSpike

- Severity: `warning`; duration: `1h`.
- Điều kiện: `daily_cost_usd > 2.5` trong một giờ.
- Ảnh hưởng: vượt ngân sách vận hành, thường đi kèm traffic hoặc token tăng bất thường.
- Kiểm tra: so sánh panel Cost, Tokens và Traffic; lọc log theo model/feature; mở generation observation để kiểm tra token và prompt version.
- Mitigation: áp dụng rate limit, giới hạn output token và rollback prompt nếu version mới làm token/cost tăng rõ rệt.