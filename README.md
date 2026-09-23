# mona-seo-check

Công cụ dòng lệnh (CLI) chấm điểm SEO on-page cho một bài viết tiếng Việt. Đưa vào 1 file HTML, 1 file Markdown, hoặc 1 đường link bài viết đã đăng, cộng với từ khóa chính đang nhắm tới — công cụ đọc toàn bộ nội dung, đếm số liệu thật (số ký tự title, số ký tự mô tả, mật độ từ khóa, độ dài câu, cấu trúc heading...) và trả về một bảng kết quả rõ ràng: mục nào đạt, mục nào chưa đạt, mục nào cần cảnh báo, và mục nào máy không tự chấm được nên phải nhờ người đọc lại.

## Vì sao cần công cụ này

Khi viết bài SEO tiếng Việt, rất nhiều lỗi nhỏ nhưng ảnh hưởng lớn đến thứ hạng lại rất dễ bị bỏ sót khi đọc lướt bằng mắt thường. Title quá ngắn hoặc quá dài so với khoảng hiển thị của Google, mô tả meta thiếu từ khóa, đoạn mở bài lan man không vào thẳng vấn đề, từ khóa nhồi nhét quá dày hoặc ngược lại gần như không xuất hiện, heading H3 bị đặt trước H2 làm rối cấu trúc trang, ảnh quên gắn thuộc tính alt khiến Google Images không hiểu ảnh nói về gì — tất cả những lỗi này đều có thể đo được bằng số liệu cụ thể, không cần đoán mò. Ngoài ra công cụ còn bắt luôn hai lỗi hay gặp khi viết vội: dùng từ khẳng định tuyệt đối kiểu "tốt nhất", "số 1", "duy nhất" (dễ khiến nội dung nghe như quảng cáo sáo rỗng và có rủi ro pháp lý ở một số ngành), và văn phong quá đều đặn — câu nào cũng dài bằng nhau, đoạn nào cũng có đúng hai câu — một dấu hiệu thường gặp ở nội dung viết hàng loạt thiếu tự nhiên.

Công cụ chỉ chấm được phần đo lường được bằng máy. Những phần cần con mắt và sự phán đoán của con người — nội dung có thật sự hay không, có đúng giọng thương hiệu không, có trùng lặp với bài của nơi khác không, ảnh có bị dính logo hãng khác không, câu chuyện kể trong bài có đáng tin không — công cụ liệt kê thẳng ra là "MANUAL — cần người đánh giá" thay vì giả vờ chấm được.

## Cài đặt

```bash
pip install -e .
```

(Repo chưa đăng ký lên PyPI; khi cài từ PyPI sẽ chỉ cần `pip install mona-seo-check`.)

Yêu cầu Python 3.10 trở lên. Công cụ chỉ dùng thư viện chuẩn của Python — không bắt buộc cài thêm gì. Nếu muốn parser HTML khoan dung hơn với các trang có mã HTML lỗi cú pháp, có thể cài thêm:

```bash
pip install -e ".[html]"   # thêm beautifulsoup4, không bắt buộc
```

## Cách dùng

```bash
mona-seo-check <đường-dẫn-file-hoặc-URL> --keyword "<từ khóa chính>" [--secondary "kw phụ 1, kw phụ 2"] [--url] [--json] [--ascii]
```

- `--keyword` (bắt buộc): từ khóa chính đang nhắm tới cho bài viết.
- `--secondary` (tùy chọn): các từ khóa phụ, phân cách bằng dấu phẩy.
- `--url`: coi tham số đầu tiên là một URL và tự tải nội dung về, thay vì đọc từ file trên máy.
- `--json`: xuất kết quả dạng JSON có cấu trúc, tiện để ghép vào pipeline khác.
- `--ascii`: ép hiển thị PASS/FAIL/WARN/MANUAL bằng chữ thay vì icon, dùng khi terminal không hiển thị được emoji.

Công cụ thoát với mã 1 nếu có bất kỳ mục nào FAIL (tiện để gắn vào CI), và mã 0 nếu không có mục FAIL nào (kể cả khi vẫn còn WARN/MANUAL).

### Ví dụ chạy thật + output thật

Lệnh:

```bash
mona-seo-check tests/fixtures/pass_mostly.html --keyword "thiết kế web"
```

Output (chạy trực tiếp trên fixture mẫu trong repo, dán nguyên văn):

```
ID    Trạng tháiCheck                                                  Thực tế
------------------------------------------------------------------------------
1a    ✅         Độ dài title                                           56 ký tự
       └─ Thiết kế web chuẩn SEO cho doanh nghiệp nhỏ tại Việt Nam
1b    ✅         Title chứa từ khóa chính                               xuất hiện 1 lần
1c    ✅         Từ khóa ở đầu title (trong 20 ký tự đầu)               vị trí ký tự 0
1d    ✅         Từ khóa không lặp quá 2 lần trong title                1 lần
2a    ✅         Độ dài meta description                                150 ký tự
       └─ Thiết kế web chuẩn SEO giúp doanh nghiệp tăng khách hàng, tối ưu tốc độ tải trang và trải nghiệm người dùng ngay từ những ngày đầu ra mắt website mới.
2b    ✅         Meta description chứa từ khóa chính (≤3 lần)           1 lần
2c    ✅         Không chứa dấu ngoặc kép literal                       không có
3a    ✅         Sapo ngắn gọn (ước lượng ~6 dòng)                      316 ký tự
3b    ✅         Từ khóa chính xuất hiện trong 100 từ đầu bài           có
4     ⚠️        Mật độ từ khóa chính toàn bài                          0.90% (4 lần / 442 từ)
5     ✅         Không dùng từ so sánh tuyệt đối ("nhất", "số 1", "...  0 lần
6a    ✅         Có ít nhất 1 H2 chứa từ khóa chính                     2/3 H2 chứa từ khóa
6b    ✅         Có heading H2/H3 chia mục                              5 heading
6c    ✅         Không nhảy cấp heading (H3 xuất hiện trước H2 đầu ...  thứ tự hợp lệ
6d    ✅         Không có H1 nào ngoài title/H1 chính                   0 H1 thừa
7     ✅         Độ so le độ dài câu (std số từ/câu)                    std=11.29, trung bình=26.0 từ/câu, 17 câu
8a    ✅         Tỷ lệ đoạn đúng 2 câu                                  22.2%
8b    ✅         Tỷ lệ đoạn ≥4 câu                                      22.2%
9     ✅         Ảnh có thuộc tính alt non-empty                        2/2 ảnh có alt
10    ✅         Từ khóa xuất hiện ở ≥2 mục H2 khác nhau (không dồn...  xuất hiện trong 2/3 mục H2
11    ✅         Có liên kết trong bài                                  1 link
12    ✅         Độ dài bài viết                                        442 từ
M1    📝         Chất lượng nội dung / giọng văn thương hiệu, có nê...  cần người đánh giá
       └─ MANUAL — cần người đánh giá
M2    📝         Trùng lặp nội dung so với website khác (cần crawl ...  cần người đánh giá
       └─ MANUAL — cần người đánh giá
M3    📝         Ảnh có dính logo đối thủ / chất lượng hình ảnh         cần người đánh giá
       └─ MANUAL — cần người đánh giá
M4    📝         CTA có đủ thuyết phục / mạnh mẽ                        cần người đánh giá
       └─ MANUAL — cần người đánh giá
M5    📝         Câu chuyện thật, trích dẫn có nguồn uy tín             cần người đánh giá
       └─ MANUAL — cần người đánh giá

Tổng: 27 check | Pass: 21 | Fail: 0 | Warn: 1 | Manual: 5
```

Chạy trên terminal không hỗ trợ emoji hoặc muốn ép hiển thị chữ:

```bash
mona-seo-check tests/fixtures/fail_many.html --keyword "thiết kế web" --ascii
```

sẽ in `PASS` / `FAIL` / `WARN` / `MANUAL` thay vì icon, và với bài có nhiều lỗi thì lệnh thoát với mã 1.

Xuất JSON để ghép vào script/CI khác:

```bash
mona-seo-check bai-viet.html --keyword "từ khóa chính" --json
```

## Danh sách check tự động hóa được

1. **Title**: độ dài 55-65 ký tự, chứa từ khóa chính, khuyến khích từ khóa nằm trong 20 ký tự đầu, không lặp từ khóa quá 2 lần.
2. **Meta description**: độ dài 150-160 ký tự, chứa từ khóa chính (tối đa 3 lần), không chứa dấu ngoặc kép literal.
3. **Sapo / đoạn mở bài**: ước lượng độ dài (ngưỡng ~600 ký tự cho ~6 dòng), từ khóa chính phải xuất hiện trong 100 từ đầu bài.
4. **Mật độ từ khóa chính** trên toàn bài: 1-3%.
5. **Cấm từ so sánh tuyệt đối**: "nhất", "số 1", "duy nhất", "tốt nhất" — báo từng lần xuất hiện kèm trích câu.
6. **Cấu trúc heading**: có ít nhất 1 H2 chứa từ khóa, có H2/H3 chia mục, không nhảy cấp (H3 xuất hiện trước H2 đầu tiên), không có H1 thừa ngoài H1 chính.
7. **Độ so le độ dài câu**: tính độ lệch chuẩn số từ/câu — câu quá đều nhau là dấu hiệu văn viết máy móc (ngưỡng cảnh báo là gợi ý, không phải luật cứng).
8. **Độ so le độ dài đoạn văn**: tỷ lệ đoạn đúng 2 câu, tỷ lệ đoạn từ 4 câu trở lên — cũng là heuristic phát hiện cấu trúc quá khuôn mẫu.
9. **Ảnh có thuộc tính alt**: mọi ảnh trong bài phải có mô tả alt không rỗng.
10. **Từ khóa phân bổ đều**: nếu bài có từ 3 mục H2 trở lên, từ khóa chính phải xuất hiện ở ít nhất 2 mục khác nhau, tránh dồn hết vào một chỗ.
11. **Liên kết trong bài**: cảnh báo (không chấm rớt) nếu bài không có liên kết nào — công cụ không tự biết trang nào phù hợp để liên kết tới nên đây luôn là gợi ý, cần người quyết định.
12. **Độ dài bài viết**: cảnh báo nếu dưới 300 từ, vì bài quá ngắn không đủ để đánh giá các mục khác một cách tin cậy.

## Các mục MANUAL — máy không tự chấm được

- Chất lượng nội dung và giọng văn thương hiệu, có nêu được điểm mạnh của thương hiệu hay không.
- Nội dung có trùng lặp với website khác không (cần công cụ crawl đối chiếu riêng, ngoài phạm vi của tool này).
- Ảnh có dính logo của đối thủ, hoặc chất lượng hình ảnh có đẹp hay không.
- Lời kêu gọi hành động (CTA) có đủ thuyết phục hay không.
- Câu chuyện kể trong bài có thật, trích dẫn có dẫn nguồn uy tín hay không.

## Chạy test

```bash
pip install -e ".[dev]"
pytest
```

## Giấy phép

MIT License — xem file `LICENSE`.

---

## English

`mona-seo-check` is a CLI tool that scores on-page SEO for a Vietnamese article. Give it an HTML file, a Markdown file, or a URL, plus your target primary keyword, and it parses the real content to measure things a human reviewer often misses when skimming: title/meta length, keyword density, opening-paragraph keyword placement, heading hierarchy (no H3 before the first H2, no stray extra H1), sentence and paragraph length variance (a heuristic signal for overly uniform, machine-written prose), missing image alt text, absolute-comparison words banned in many markets ("best", "number one", "only"), and internal links. Checks that genuinely require human judgment — content quality, brand voice, duplicate-content detection, image/CTA quality, sourcing of claims — are explicitly reported as `MANUAL`, not guessed at.

Install: `pip install -e .` (Python 3.10+, standard library only; `pip install -e ".[html]"` for an optional BeautifulSoup-based HTML parser).

Usage: `mona-seo-check <file-or-url> --keyword "<primary keyword>" [--secondary "kw1, kw2"] [--url] [--json] [--ascii]`. Exits with code 1 if any check fails, 0 otherwise. Run tests with `pip install -e ".[dev]" && pytest`.

---
Từ MONA — https://mona.media · Các repo khác: https://github.com/themonagroup · Hub mã nguồn mở: https://mona.media/mona-open/
