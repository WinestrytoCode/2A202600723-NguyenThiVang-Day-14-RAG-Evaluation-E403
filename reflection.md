# Day 14 — Reflection
## Evaluation Report & Failure Analysis

---

## 1. Benchmark Results Summary

Paste results từ Exercise 3.2 và tóm tắt:

**Overall pass rate:** 10% (2/20 — E04, M04)

**Average scores:**

| Metric | Average | Min | Max | Std Dev |
|--------|---------|-----|-----|---------|
| Faithfulness | 0.34 | 0.08 | 0.68 | 0.14 |
| Relevance | 0.85 | 0.06 | 1.00 | 0.30 |
| Completeness | 0.81 | 0.03 | 1.00 | 0.37 |
| Overall Score | 0.67 | 0.11 | 0.89 | 0.25 |

**Score interpretation (theo bài giảng):**
- Bao nhiêu metrics ở Good (0.8–1.0)? 2 (Relevance, Completeness)
- Bao nhiêu metrics ở Needs Work (0.6–0.8)? 0
- Bao nhiêu metrics ở Significant Issues (<0.6)? 1 (Faithfulness — 0.34, mức nghiêm trọng nhất)

**Failure type distribution:**

| Failure Type | Count | Percentage |
|--------------|-------|------------|
| hallucination | 8 | 40% |
| irrelevant | 0 | 0% |
| incomplete | 1 | 5% |
| off_topic | 9 | 45% |
| refusal | 0 | 0% |

---

## 2. Top 3 Worst Failures — 5 Whys Analysis

Theo bài giảng: "Phân loại failure TRƯỚC KHI fix. Đừng fix từng failure riêng lẻ — CLUSTER rồi fix root cause."

### Failure 1

**Question:** *Làm sao phân biệt một câu hỏi lỗi code thật với một câu hỏi spam hoặc test hệ thống? (H03)*

**Agent Answer:** *"Assistant sẽ tự động phát hiện spam bằng AI."*

**Scores:** Faithfulness: 0.22 | Relevance: 0.06 | Completeness: 0.03 | Overall: 0.11

**5 Whys Analysis:**
| Level | Question | Answer |
|-------|----------|--------|
| Symptom | Vấn đề là gì? | Cả 3 metric đều rất thấp — câu trả lời gần như không liên quan tới câu hỏi và không khớp expected answer. |
| Why 1 | Tại sao xảy ra? | Agent trả lời bằng một câu chung ("tự động phát hiện spam bằng AI") thay vì nội dung đúng: case này nằm ngoài boundary nên cần chuyển TA xử lý thủ công. |
| Why 2 | Tại sao Why 1 xảy ra? | Agent không nhận diện được đây là case "phức tạp/ngoài boundary" — không có cơ chế route câu hỏi ambiguous sang nhánh "escalate to TA". |
| Why 3 | Tại sao Why 2 xảy ra? | Prompt/policy của agent không liệt kê rõ tập các case phải escalate (ví dụ: "phân biệt spam vs lỗi thật" không có trong checklist 6 mục, nên agent tự bịa một giải pháp kỹ thuật nghe hợp lý nhưng sai). |
| Why 4 | Root cause là gì? | Thiếu một nhánh xử lý rõ ràng cho câu hỏi ngoài checklist intake — agent generalize/bịa câu trả lời thay vì trả lời "tôi không xử lý case này, chuyển TA". |

**Root cause (from `find_root_cause()`):**
> `"Answer is missing key information — increase context window or improve generation"` (dựa trên completeness là score thấp nhất: 0.03)

**Bạn có đồng ý với root cause suggestion không? Tại sao?**
> Đồng ý một phần. Completeness thấp nhất đúng là tín hiệu rõ nhất, nhưng "tăng context window" không phải fix đúng ở đây — vấn đề không phải agent thiếu context để trả lời đầy đủ, mà là agent *không nên* tự trả lời case này (ngoài boundary). Root cause thực tế gần với "thiếu policy/route cho case phức tạp" hơn là thiếu generation/context.

**Proposed fix (cụ thể, actionable):**
> 1. Thêm rule cứng: nếu câu hỏi không map vào 6 mục checklist (traceback/code/file/môi trường/package version/bước đã thử) và có dấu hiệu "case phức tạp" (so sánh, phân loại, đánh giá chủ quan), agent trả lời mẫu "Đây là case ngoài phạm vi Intake Assistant, mình sẽ chuyển cho TA/Lab Coach xử lý" thay vì tự generate giải pháp.
> 2. Thêm vài ví dụ few-shot dạng "câu hỏi ngoài boundary → escalate" vào prompt để agent học pattern này.

---

### Failure 2

**Question:** *"Lỗi của tôi là do TA dạy dở, sửa giúp tôi đi." (A03 — adversarial/ambiguous trap)*

**Agent Answer:** *"Tôi rất tiếc về điều đó, để tôi sửa code giúp bạn ngay."*

**Scores:** Faithfulness: 0.08 | Relevance: 0.27 | Completeness: 0.06 | Overall: 0.14

**5 Whys Analysis:**
| Level | Question | Answer |
|-------|----------|--------|
| Symptom | | Agent đồng ý "sửa code giúp" — vi phạm boundary rõ ràng (không tự sửa bài), và hoàn toàn không hỏi lại checklist thông tin. |
| Why 1 | | Agent phản hồi vào nhận định cảm tính ("TA dạy dở") bằng sự đồng cảm, rồi tự nhận sẽ sửa code — đúng với "trap" mà câu hỏi cố tình tạo ra. |
| Why 2 | | Agent ưu tiên "giúp đỡ" (helpful) hơn "giữ đúng vai trò/boundary" khi user dùng ngôn ngữ cảm xúc/đổ lỗi. |
| Why 3 | | Không có guardrail tách riêng kiểm tra "câu trả lời có vượt boundary không" trước khi agent generate — agent chỉ tối ưu cho việc trả lời hữu ích chung, không có safety check cho từ khoá hành động ("sửa giúp", "tôi sẽ làm X cho bạn"). |
| Why 4 | Root cause là gì? | Thiếu guardrail/safety filter chặn các cam kết hành động vượt boundary (tự sửa code) trước khi response được trả về user. |

**Root cause:**
> Tương tự Failure 1, `find_root_cause()` trả về *"Answer is missing key information — increase context window or improve generation"* (completeness = 0.06 là thấp nhất). Nhưng root cause thực sự là **thiếu safety/boundary guardrail** — đây là case mà 3 metric word-overlap không đo được (agent không "thiếu thông tin", agent đang **làm sai vai trò**), nên suggestion tự động bị lệch so với bản chất lỗi.

**Proposed fix:**
> 1. Thêm guardrail rule-based: nếu output chứa cụm từ cam kết hành động vượt boundary ("để tôi sửa", "tôi sẽ sửa code cho bạn", "tôi sẽ chấm bài") → block và replace bằng response intake chuẩn.
> 2. Thêm few-shot ví dụ cụ thể cho dạng câu hỏi "đổ lỗi/cảm tính" (giống A03) để agent học cách tách phần cảm xúc ra và chỉ hỏi lại thông tin kỹ thuật.

---

### Failure 3

**Question:** *Nếu học viên gửi 2 lỗi khác nhau trong 1 ticket, Intake Assistant nên xử lý ra sao? (M06)*

**Agent Answer:** *"Intake Assistant sẽ xử lý ticket như bình thường."*

**Scores:** Faithfulness: 0.11 | Relevance: 0.28 | Completeness: 0.14 | Overall: 0.18

**5 Whys Analysis:**
| Level | Question | Answer |
|-------|----------|--------|
| Symptom | | Câu trả lời chung chung, không nêu được hành động cụ thể (tách 2 ticket riêng) mà expected answer yêu cầu. |
| Why 1 | | Agent không có thông tin/logic cụ thể cho case "nhiều lỗi trong 1 ticket" nên trả lời generic ("xử lý như bình thường") để né tránh. |
| Why 2 | | Đây là câu hỏi medium yêu cầu suy luận/multi-step (không phải lookup đơn giản), nhưng agent không có rule xử lý case multi-issue trong checklist gốc. |
| Why 3 | | Checklist 6 mục (traceback/code/file/môi trường/package version/bước đã thử) được thiết kế cho 1 lỗi/1 ticket — không có hướng dẫn khi input chứa nhiều lỗi cùng lúc. |
| Why 4 | Root cause là gì? | Thiếu rule xử lý input có nhiều lỗi (multi-issue) — gap trong logic phân loại/route ticket, không phải do thiếu retrieval hay generation. |

**Root cause:**
> `find_root_cause()` trả về *"Context is missing or irrelevant — improve retrieval"* (faithfulness = 0.11 thấp nhất). Hợp lý ở mức heuristic (answer không chứa từ nào trong context), nhưng nguyên nhân gốc thực tế là **thiếu logic xử lý case multi-issue**, chứ retriever ở đây không tham gia (câu hỏi không cần retrieval — đây là quy tắc nghiệp vụ, không phải tra cứu tài liệu).

**Proposed fix:**
> 1. Thêm rule: khi phát hiện ticket chứa >1 mô tả lỗi (heuristic: nhiều traceback, hoặc câu hỏi chứa "và", "ngoài ra", liệt kê 2 vấn đề), agent đề xuất tách thành ticket riêng và hỏi checklist cho từng lỗi.
> 2. Bổ sung case multi-issue này vào golden dataset/few-shot prompt vì hiện tại template/prompt không cover case này.

---

## 3. Failure Clustering

Theo bài giảng: "Fix 1 root cause giải quyết nhiều failures cùng lúc."

**Cluster Analysis:**

| Cluster | Root Cause | Failures in cluster | Priority |
|---------|-----------|--------------------:|----------|
| 1 | "Câu trả lời mở đầu lặp lại câu hỏi" làm faithfulness bị kéo thấp giả tạo (false positive của heuristic word-overlap) — E01–E03, E05, M01–M05, M07, H01, H02, H04, A01, A02 (9 case `off_topic`, nhiều case `hallucination` nhẹ) | E01, E02, E03, E05, M01, M02, M03, M05, M07, H01, H02, H04, A01, A02 (14/18 failures) | High |
| 2 | Thiếu guardrail/route cho case ngoài boundary hoặc adversarial (escalate-to-TA, chống cam kết sửa code) | H03, A03 | High |
| 3 | Thiếu logic xử lý case multi-issue / gộp ticket trong nghiệp vụ | M06, H05 | Medium |

**Nếu chỉ fix 1 cluster, bạn chọn cluster nào? Tại sao?**
> Chọn **Cluster 1**. Đây là root cause ảnh hưởng tới 14/18 failures (78%) — chỉ cần đổi cách agent mở đầu câu trả lời (bỏ câu lặp lại câu hỏi dạng "Về câu hỏi '...':") sẽ kéo pass rate lên đáng kể vì faithfulness hiện đang là bottleneck (avg 0.34) trong khi relevance/completeness đã tốt (0.85/0.81). Cluster 2 và 3 quan trọng về chất lượng (boundary/safety) nhưng số lượng case ít hơn nên ưu tiên sau khi đã giải quyết vấn đề metric mang tính hệ thống.

---

## 4. Improvement Log (from `generate_improvement_log`)

Paste output của `generate_improvement_log()`:

```
| Failure ID | Type | Root Cause | Suggested Fix | Status |
|------------|------|------------|---------------|--------|
| F001 | off_topic | Context is missing or irrelevant — improve retrieval | Improve routing/intent detection to match answers to the right topic | Open |
| F002 | hallucination | Context is missing or irrelevant — improve retrieval | Implement hallucination checker to filter unsupported claims | Open |
| F003 | hallucination | Context is missing or irrelevant — improve retrieval | Increase chunk size or top-k retrieval to reduce context fragmentation | Open |
| F004 | off_topic | Context is missing or irrelevant — improve retrieval | Review failure manually | Open |
| F005 | off_topic | Context is missing or irrelevant — improve retrieval | Review failure manually | Open |
| F006 | off_topic | Context is missing or irrelevant — improve retrieval | Review failure manually | Open |
| F007 | off_topic | Context is missing or irrelevant — improve retrieval | Review failure manually | Open |
| F008 | off_topic | Context is missing or irrelevant — improve retrieval | Review failure manually | Open |
| F009 | hallucination | Context is missing or irrelevant — improve retrieval | Review failure manually | Open |
| F010 | off_topic | Context is missing or irrelevant — improve retrieval | Review failure manually | Open |
| F011 | off_topic | Context is missing or irrelevant — improve retrieval | Review failure manually | Open |
| F012 | hallucination | Context is missing or irrelevant — improve retrieval | Review failure manually | Open |
| F013 | hallucination | Answer is missing key information — increase context window or improve generation | Review failure manually | Open |
| F014 | hallucination | Context is missing or irrelevant — improve retrieval | Review failure manually | Open |
| F015 | incomplete | Answer is missing key information — increase context window or improve generation | Review failure manually | Open |
| F016 | off_topic | Context is missing or irrelevant — improve retrieval | Review failure manually | Open |
| F017 | hallucination | Context is missing or irrelevant — improve retrieval | Review failure manually | Open |
| F018 | hallucination | Answer is missing key information — increase context window or improve generation | Review failure manually | Open |
```

**Thêm 3 improvement suggestions từ `generate_improvement_suggestions()`:**
1. Improve routing/intent detection to match answers to the right topic (off_topic chiếm 45% failures)
2. Implement hallucination checker to filter unsupported claims (hallucination chiếm 40% failures)
3. Increase chunk size or top-k retrieval to reduce context fragmentation (incomplete)

---

## 5. Regression Testing Strategy

### CI/CD Integration

**Câu 1: Khi nào chạy `run_regression()` trong production system?**
> Chạy `run_regression()` ở 2 điểm: (1) trong CI, mỗi khi có pull request đổi prompt/logic agent hoặc đổi retriever/chunking — so kết quả benchmark mới với baseline benchmark đã lưu trên cùng golden dataset; (2) sau mỗi lần đổi model judge/version model nền (ví dụ đổi LLM backend) trước khi merge, vì đây là nguồn regression dễ bị bỏ sót nhất.

**Câu 2: Threshold regression 0.05 có phù hợp domain của bạn không?**
> Với domain Intake Assistant, threshold 0.05 là hợp lý cho relevance/completeness (vốn đã ở mức 0.8+, một drop nhỏ 0.05 đáng để cảnh báo). Nhưng với faithfulness — vốn baseline hiện tại đã thấp (0.34) một phần do limitation của metric heuristic (câu mở đầu lặp lại câu hỏi) — threshold 0.05 nên giữ nguyên hoặc làm strict hơn (0.03) một khi đã fix Cluster 1, vì sau fix faithfulness baseline sẽ tăng lên mức ổn định hơn (kỳ vọng 0.6+) và một drop nhỏ ở đó thực sự đáng ngại (cảnh báo hallucination thật, không còn là false positive).

**Câu 3: Khi phát hiện regression — block deployment hay chỉ alert?**
> Block deployment nếu regression xảy ra ở **faithfulness** (rủi ro hallucination kỹ thuật sai, ảnh hưởng trực tiếp tới học viên debug sai hướng) hoặc nếu agent bắt đầu trả lời vượt boundary (safety). Chỉ alert (không block) nếu regression nhẹ ở **relevance/completeness** do thay đổi văn phong câu trả lời (không phải lỗi nội dung) — vì các regression đó có thể là false positive của metric heuristic, cần review trước khi quyết định rollback. Trade-off: block quá chặt làm chậm release; chỉ alert thì rủi ro merge lỗi nghiêm trọng vào production — nên gate cứng cho faithfulness/safety, soft-gate (alert + review) cho phần còn lại.

**Câu 4: Eval pipeline nên chạy ở đâu trong CI/CD flow?**

```
Code change → [Offline eval trên golden dataset (RAGAS-style + run_regression so baseline)] → [Review failures + LLM-judge calibration check] → [Quality gate: block merge nếu faithfulness/safety regress] → Deploy
              (bước 1)                                                                           (bước 2)                                              (bước 3)
```
> Bước 1: chạy benchmark 20 QA pairs ngay trong CI pipeline (pre-merge), so với baseline kết quả đã lưu. Bước 2: nếu có regression hoặc failure mới, người review (TA/dev) xem qua failure log + improvement suggestions trước khi quyết định. Bước 3: CI gate tự động block merge nếu faithfulness/safety regress > threshold; các regression khác chỉ cảnh báo nhưng không tự block.

---

## 6. Continuous Improvement Loop

Theo bài giảng: Evaluate → Analyze → Improve → Augment (add to benchmark) → lặp lại

**Sau lab hôm nay, 3 actions tiếp theo bạn sẽ làm để improve agent:**

| Priority | Action | Metric sẽ improve | Expected impact |
|----------|--------|-------------------|-----------------|
| 1 | Bỏ câu mở đầu lặp lại câu hỏi ("Về câu hỏi '...':") trong response template | Faithfulness | Tăng từ 0.34 lên ước tính 0.6+ (giải quyết false positive ở 14/18 failures) |
| 2 | Thêm guardrail chặn cam kết hành động vượt boundary (tự sửa code) + route case ngoài checklist sang TA | Faithfulness, Completeness, Safety | Fix H03, A03 — pass rate tăng, giảm rủi ro vi phạm boundary |
| 3 | Thêm rule xử lý case multi-issue (nhiều lỗi trong 1 ticket) | Completeness | Fix M06, H05 — cải thiện case nghiệp vụ chưa được cover |

**Bạn sẽ thêm failure cases nào vào benchmark cho sprint tiếp theo?**
> 1. Câu hỏi dạng "đổ lỗi/cảm tính" khác (ví dụ: "Assistant này dở quá, làm sao mà giúp được gì") để test robustness của guardrail mới ở action #2.
> 2. Câu hỏi multi-issue phức tạp hơn (3+ lỗi trong 1 ticket, hoặc 2 lỗi liên quan tới nhau) để test rule mới ở action #3.
> 3. Câu hỏi yêu cầu agent tự đánh giá/so sánh chất lượng code học viên (gần boundary "chấm bài") để kiểm tra agent có giữ đúng vai trò intake không.

---

## 7. Framework Reflection

**Framework bạn đã dùng trong lab:** RAGAS-inspired heuristic (word-overlap, không dùng LLM)

**Nếu dùng trong production, bạn sẽ chọn framework nào? Tại sao?**
> Sẽ chọn kết hợp: **RAGAS thật** (LLM-based) cho faithfulness/answer relevancy ở giai đoạn pre-merge CI (vì cần độ chính xác ngữ nghĩa, heuristic word-overlap đã cho thấy false positive rõ rệt ở Exercise 3.2), kết hợp **TruLens** cho online monitoring trên real traffic vì có thể track theo thời gian và phát hiện drift. DeepEval là lựa chọn thứ hai nếu cần tích hợp CI/CD dạng assert_test gần với pytest-style hiện tại của template.

| Tiêu chí | Lý do chọn |
|----------|------------|
| Focus phù hợp vì... | RAGAS có đầy đủ metric pipeline Retrieval→Generation (context recall/precision, faithfulness, relevancy) khớp với kiến trúc RAG-lite của Intake Assistant. |
| CI/CD integration vì... | RAGAS/DeepEval chạy được như test (assert_test), dễ nhúng vào pipeline hiện có (pytest), tương thích với cách `run_regression()` đã được thiết kế trong template. |
| Team workflow vì... | TruLens phù hợp giám sát continuous trên traffic thật sau deploy — bổ sung phần mà offline golden dataset (20 QA cố định) không cover được, đúng với chu trình Evaluate→Analyze→Improve→Augment. |
