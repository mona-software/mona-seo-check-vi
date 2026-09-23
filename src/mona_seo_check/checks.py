"""Logic từng check on-page SEO.

Mỗi hàm `check_*` nhận vào `Document` (từ parser.py) + từ khóa, và trả về
MỘT hoặc NHIỀU dict kết quả theo khuôn:

    {
        "id": "1",                # số thứ tự / mã check
        "ten": "Title 55-65 ký tự",
        "trang_thai": "pass" | "fail" | "warn" | "manual",
        "thuc_te": "62 ký tự",     # số đo thực tế
        "yeu_cau": "55-65 ký tự",  # ngưỡng yêu cầu
        "ghi_chu": "...",          # giải thích thêm / trích dẫn câu vi phạm
    }

Toàn bộ ngưỡng số (55-65 ký tự title, 1-3% mật độ, std < 3...) là HEURISTIC
tổng quát hoá cho on-page SEO tiếng Việt — không phải công thức tuyệt đối,
chỉnh lại theo nhu cầu dùng thật.
"""

from __future__ import annotations

import re
import statistics
import unicodedata
from typing import Dict, List

from .parser import Document, normalize

FORBIDDEN_ABSOLUTE_WORDS = ["duy nhất", "tốt nhất", "số một", "số 1", "nhất"]

SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?…])\s+")


def _result(id_, ten, trang_thai, thuc_te, yeu_cau, ghi_chu="") -> Dict:
    return {
        "id": str(id_),
        "ten": ten,
        "trang_thai": trang_thai,
        "thuc_te": thuc_te,
        "yeu_cau": yeu_cau,
        "ghi_chu": ghi_chu,
    }


def _fold_lower(text: str) -> str:
    """Chuẩn hoá NFC + lowercase để so khớp từ khóa không phân biệt hoa/thường
    và không lệch nhau vì tổ hợp dấu Unicode khác nhau."""
    return unicodedata.normalize("NFC", text or "").lower()


def count_occurrences(haystack: str, needle: str) -> int:
    if not needle:
        return 0
    h = _fold_lower(haystack)
    n = _fold_lower(needle)
    if not n:
        return 0
    return h.count(n)


def split_words(text: str) -> List[str]:
    """Tách từ đơn giản — coi mỗi 'từ' là 1 chuỗi ký tự chữ/số liên tục
    (kể cả có dấu tiếng Việt). Đây là ước lượng đơn từ (không tách từ ghép
    tiếng Việt kiểu "thiết_kế" — đủ dùng để đo độ dài & mật độ)."""
    return re.findall(r"[^\W\d_]+|\d+", text, flags=re.UNICODE)


def split_sentences(text: str) -> List[str]:
    text = text.strip()
    if not text:
        return []
    parts = SENTENCE_SPLIT_RE.split(text)
    return [p.strip() for p in parts if p.strip()]


# ---------------------------------------------------------------------------
# 1. Title
# ---------------------------------------------------------------------------


def check_title(doc: Document, keyword: str) -> List[Dict]:
    results = []
    title = doc.title or ""
    length = len(title)

    if not doc.title:
        results.append(_result("1a", "Title tồn tại", "fail", "không có", "phải có <title>"))
        return results

    if 55 <= length <= 65:
        status = "pass"
    else:
        status = "fail"
    results.append(
        _result("1a", "Độ dài title", status, f"{length} ký tự", "55-65 ký tự", title)
    )

    kw_count = count_occurrences(title, keyword)
    results.append(
        _result(
            "1b",
            "Title chứa từ khóa chính",
            "pass" if kw_count >= 1 else "fail",
            f"xuất hiện {kw_count} lần",
            "≥1 lần",
        )
    )

    if kw_count >= 1:
        first_pos = _fold_lower(title).find(_fold_lower(keyword))
        in_first_20 = 0 <= first_pos < 20
        results.append(
            _result(
                "1c",
                "Từ khóa ở đầu title (trong 20 ký tự đầu)",
                "pass" if in_first_20 else "warn",
                f"vị trí ký tự {first_pos}" if first_pos >= 0 else "không tìm thấy",
                "nên nằm trong 20 ký tự đầu",
            )
        )

    results.append(
        _result(
            "1d",
            "Từ khóa không lặp quá 2 lần trong title",
            "pass" if kw_count <= 2 else "fail",
            f"{kw_count} lần",
            "≤2 lần",
        )
    )
    return results


# ---------------------------------------------------------------------------
# 2. Meta description
# ---------------------------------------------------------------------------


def check_meta_description(doc: Document, keyword: str) -> List[Dict]:
    results = []
    meta = doc.meta_description or ""

    if not doc.meta_description:
        results.append(
            _result("2a", "Meta description tồn tại", "fail", "không có", "phải có meta description")
        )
        return results

    length = len(meta)
    results.append(
        _result(
            "2a",
            "Độ dài meta description",
            "pass" if 150 <= length <= 160 else "fail",
            f"{length} ký tự",
            "150-160 ký tự",
            meta,
        )
    )

    kw_count = count_occurrences(meta, keyword)
    results.append(
        _result(
            "2b",
            "Meta description chứa từ khóa chính (≤3 lần)",
            "pass" if 1 <= kw_count <= 3 else ("fail" if kw_count == 0 else "warn"),
            f"{kw_count} lần",
            "1-3 lần",
        )
    )

    has_quote = '"' in meta
    results.append(
        _result(
            "2c",
            "Không chứa dấu ngoặc kép literal",
            "fail" if has_quote else "pass",
            "có dấu \"" if has_quote else "không có",
            'không chứa ký tự "',
        )
    )
    return results


# ---------------------------------------------------------------------------
# 3. Sapo / đoạn mở bài
# ---------------------------------------------------------------------------


def check_sapo(doc: Document, keyword: str) -> List[Dict]:
    results = []
    if not doc.paragraphs:
        results.append(
            _result("3a", "Có đoạn mở bài (sapo)", "fail", "không có đoạn văn nào", "phải có ≥1 đoạn")
        )
        return results

    sapo = doc.paragraphs[0]
    length = len(sapo)
    results.append(
        _result(
            "3a",
            "Sapo ngắn gọn (ước lượng ~6 dòng)",
            "pass" if length <= 600 else "warn",
            f"{length} ký tự",
            "≤600 ký tự (~6 dòng)",
        )
    )

    words_100 = " ".join(split_words(doc.full_text)[:100])
    kw_in_100 = count_occurrences(words_100, keyword) >= 1
    results.append(
        _result(
            "3b",
            "Từ khóa chính xuất hiện trong 100 từ đầu bài",
            "pass" if kw_in_100 else "fail",
            "có" if kw_in_100 else "không có",
            "phải có trong 100 từ đầu",
        )
    )
    return results


# ---------------------------------------------------------------------------
# 4. Mật độ từ khóa toàn bài
# ---------------------------------------------------------------------------


def check_keyword_density(doc: Document, keyword: str) -> List[Dict]:
    total_words = len(split_words(doc.full_text))
    if total_words == 0:
        return [
            _result("4", "Mật độ từ khóa chính", "fail", "bài trống", "1-3%")
        ]
    kw_count = count_occurrences(doc.full_text, keyword)
    density = (kw_count / total_words) * 100
    status = "pass" if 1.0 <= density <= 3.0 else ("warn" if density > 0 else "fail")
    return [
        _result(
            "4",
            "Mật độ từ khóa chính toàn bài",
            status,
            f"{density:.2f}% ({kw_count} lần / {total_words} từ)",
            "1-3%",
        )
    ]


# ---------------------------------------------------------------------------
# 5. Từ so sánh tuyệt đối bị cấm
# ---------------------------------------------------------------------------


def check_forbidden_absolute_words(doc: Document) -> List[Dict]:
    full_text = doc.full_text
    sentences = split_sentences(full_text)
    findings = []

    for word in FORBIDDEN_ABSOLUTE_WORDS:
        pattern = re.compile(r"(?<!\w)" + re.escape(word) + r"(?!\w)", re.IGNORECASE)
        for m in pattern.finditer(full_text):
            # tìm câu chứa vị trí match để trích dẫn
            quote = None
            for s in sentences:
                if word.lower() in s.lower():
                    quote = s
                    break
            findings.append((word, quote or full_text[max(0, m.start() - 30): m.end() + 30]))

    if not findings:
        return [
            _result(
                "5",
                'Không dùng từ so sánh tuyệt đối ("nhất", "số 1", "duy nhất", "tốt nhất")',
                "pass",
                "0 lần",
                "0 lần",
            )
        ]

    results = []
    for word, quote in findings:
        results.append(
            _result(
                "5",
                f'Dùng từ so sánh tuyệt đối "{word}"',
                "fail",
                quote,
                'không dùng "nhất/số 1/duy nhất/tốt nhất"',
            )
        )
    return results


# ---------------------------------------------------------------------------
# 6. Heading hierarchy
# ---------------------------------------------------------------------------


def check_heading_hierarchy(doc: Document, keyword: str) -> List[Dict]:
    results = []
    headings = doc.headings

    h2_list = [t for lvl, t in headings if lvl == 2]
    h2_with_kw = [t for t in h2_list if count_occurrences(t, keyword) >= 1]
    results.append(
        _result(
            "6a",
            "Có ít nhất 1 H2 chứa từ khóa chính",
            "pass" if h2_with_kw else "fail",
            f"{len(h2_with_kw)}/{len(h2_list)} H2 chứa từ khóa",
            "≥1 H2 chứa từ khóa",
        )
    )

    has_h2_or_h3 = any(lvl in (2, 3) for lvl, _ in headings)
    results.append(
        _result(
            "6b",
            "Có heading H2/H3 chia mục",
            "pass" if has_h2_or_h3 else "fail",
            f"{len(headings)} heading" if headings else "không có heading",
            "phải có H2/H3",
        )
    )

    # H3 xuất hiện trước H2 đầu tiên = nhảy cấp
    first_h2_idx = next((i for i, (lvl, _) in enumerate(headings) if lvl == 2), None)
    first_h3_idx = next((i for i, (lvl, _) in enumerate(headings) if lvl == 3), None)
    jump_error = (
        first_h3_idx is not None
        and (first_h2_idx is None or first_h3_idx < first_h2_idx)
    )
    results.append(
        _result(
            "6c",
            "Không nhảy cấp heading (H3 xuất hiện trước H2 đầu tiên)",
            "fail" if jump_error else "pass",
            "H3 đứng trước H2" if jump_error else "thứ tự hợp lệ",
            "H2 phải xuất hiện trước H3",
        )
    )

    extra_h1 = doc.raw_h1_count
    results.append(
        _result(
            "6d",
            "Không có H1 nào ngoài title/H1 chính",
            "pass" if extra_h1 == 0 else "fail",
            f"{extra_h1} H1 thừa trong thân bài" if extra_h1 else "0 H1 thừa",
            "chỉ 1 H1 duy nhất (H1 chính/title)",
        )
    )
    return results


# ---------------------------------------------------------------------------
# 7. Câu so le (độ dài câu không đều)
# ---------------------------------------------------------------------------


def check_sentence_variance(doc: Document) -> List[Dict]:
    """Đếm số từ mỗi câu rồi tính độ lệch chuẩn (std).

    Văn người viết tự nhiên thường có câu ngắn câu dài xen kẽ → std cao.
    Văn máy sinh hàng loạt có xu hướng câu đều nhau (gần cùng độ dài) → std
    thấp bất thường. Ngưỡng std < 3 chỉ là GỢI Ý CẢNH BÁO (warn), không phải
    bằng chứng chắc chắn — bài ngắn/ít câu cũng có thể std thấp một cách
    tình cờ, nên không set FAIL cứng ở đây.
    """
    sentences = split_sentences(doc.full_text)
    lengths = [len(split_words(s)) for s in sentences if split_words(s)]

    if len(lengths) < 3:
        return [
            _result(
                "7",
                "Độ so le độ dài câu (std số từ/câu)",
                "manual",
                f"chỉ {len(lengths)} câu — không đủ dữ liệu",
                "std ≥3 (câu ngắn/dài xen kẽ)",
            )
        ]

    std = statistics.pstdev(lengths)
    status = "warn" if std < 3 else "pass"
    return [
        _result(
            "7",
            "Độ so le độ dài câu (std số từ/câu)",
            status,
            f"std={std:.2f}, trung bình={statistics.mean(lengths):.1f} từ/câu, {len(lengths)} câu",
            "std ≥3 — câu quá đều là dấu hiệu văn máy",
        )
    ]


# ---------------------------------------------------------------------------
# 8. Đoạn văn so le
# ---------------------------------------------------------------------------


def check_paragraph_variance(doc: Document) -> List[Dict]:
    """Tỷ lệ đoạn đúng 2 câu và tỷ lệ đoạn ≥4 câu — heuristic tổng quát hoá
    để phát hiện bài viết có cấu trúc đoạn quá khuôn mẫu (mọi đoạn dài như
    nhau). Ngưỡng 40%/15% là gợi ý, chỉnh theo nhu cầu thực tế."""
    paragraphs = doc.paragraphs
    if not paragraphs:
        return [
            _result("8", "Độ so le độ dài đoạn văn", "manual", "không có đoạn văn", "—")
        ]

    sentence_counts = [len(split_sentences(p)) for p in paragraphs]
    total = len(sentence_counts)
    two_sentence_ratio = sum(1 for c in sentence_counts if c == 2) / total * 100
    long_ratio = sum(1 for c in sentence_counts if c >= 4) / total * 100

    results = []
    results.append(
        _result(
            "8a",
            "Tỷ lệ đoạn đúng 2 câu",
            "pass" if two_sentence_ratio <= 40 else "warn",
            f"{two_sentence_ratio:.1f}%",
            "≤40%",
        )
    )
    results.append(
        _result(
            "8b",
            "Tỷ lệ đoạn ≥4 câu",
            "pass" if long_ratio >= 15 else "warn",
            f"{long_ratio:.1f}%",
            "≥15%",
        )
    )
    return results


# ---------------------------------------------------------------------------
# 9. Ảnh có alt
# ---------------------------------------------------------------------------


def check_images_alt(doc: Document) -> List[Dict]:
    if not doc.images:
        return [
            _result("9", "Ảnh có thuộc tính alt", "warn", "bài không có ảnh nào", "mọi ảnh phải có alt")
        ]

    missing = [src for src, alt in doc.images if not alt.strip()]
    status = "pass" if not missing else "fail"
    detail = f"{len(doc.images) - len(missing)}/{len(doc.images)} ảnh có alt"
    ghi_chu = "; ".join(missing[:5]) if missing else ""
    return [_result("9", "Ảnh có thuộc tính alt non-empty", status, detail, "100% ảnh có alt", ghi_chu)]


# ---------------------------------------------------------------------------
# 10. Từ khóa phân bổ đều theo H2
# ---------------------------------------------------------------------------


def check_keyword_distribution(doc: Document, keyword: str) -> List[Dict]:
    h2_list = [t for lvl, t in doc.headings if lvl == 2]
    if len(h2_list) < 3:
        return [
            _result(
                "10",
                "Từ khóa phân bổ đều giữa các mục H2",
                "manual",
                f"chỉ có {len(h2_list)} H2 — chưa đủ để đánh giá phân bổ",
                "cần ≥3 H2 để áp dụng check này",
            )
        ]

    # Xấp xỉ: chia full_text thành các đoạn theo từng H2 bằng cách đếm
    # đoạn văn nằm giữa các heading — ở đây dùng cách đơn giản: đếm số H2
    # có từ khóa xuất hiện trong CHÍNH tiêu đề H2 đó không đủ, nên duyệt
    # qua paragraphs theo thứ tự và gán cho H2 gần nhất phía trước.
    sections: List[str] = []
    current: List[str] = []
    # Ghép lại thứ tự thật (headings + paragraphs không giữ thứ tự chung
    # trong Document hiện tại) — dùng full_text chia theo heading text làm
    # điểm mốc thô.
    text = doc.full_text
    positions = []
    for _, h2_text in [(lvl, t) for lvl, t in doc.headings if lvl == 2]:
        idx = text.find(h2_text)
        if idx >= 0:
            positions.append(idx)
    positions.append(len(text))
    positions = sorted(set(positions))

    kw_in_sections = 0
    for i in range(len(positions) - 1):
        chunk = text[positions[i]: positions[i + 1]]
        if count_occurrences(chunk, keyword) >= 1:
            kw_in_sections += 1

    status = "pass" if kw_in_sections >= 2 else "warn"
    return [
        _result(
            "10",
            "Từ khóa xuất hiện ở ≥2 mục H2 khác nhau (không dồn 1 chỗ)",
            status,
            f"xuất hiện trong {kw_in_sections}/{len(h2_list)} mục H2",
            "≥2 mục H2",
        )
    ]


# ---------------------------------------------------------------------------
# 11. Liên kết nội bộ (luôn WARN/manual, không FAIL cứng)
# ---------------------------------------------------------------------------


def check_internal_links(doc: Document) -> List[Dict]:
    if doc.links:
        return [
            _result(
                "11",
                "Có liên kết trong bài",
                "pass",
                f"{len(doc.links)} link",
                "nên có liên kết nội bộ tới trang liên quan (đánh giá thủ công trang nào phù hợp)",
            )
        ]
    return [
        _result(
            "11",
            "Có liên kết trong bài",
            "warn",
            "0 link",
            "nên có liên kết nội bộ — công cụ không tự biết trang cha nào phù hợp, cần người chọn",
        )
    ]


# ---------------------------------------------------------------------------
# 12. Độ dài bài
# ---------------------------------------------------------------------------


def check_length(doc: Document) -> List[Dict]:
    total_words = len(split_words(doc.full_text))
    status = "warn" if total_words < 300 else "pass"
    return [
        _result(
            "12",
            "Độ dài bài viết",
            status,
            f"{total_words} từ",
            "≥300 từ để đủ audit/SEO",
        )
    ]


# ---------------------------------------------------------------------------
# Check MANUAL — không tự chấm được, luôn trả về "manual"
# ---------------------------------------------------------------------------

MANUAL_CHECKS = [
    ("M1", "Chất lượng nội dung / giọng văn thương hiệu, có nêu điểm mạnh thương hiệu"),
    ("M2", "Trùng lặp nội dung so với website khác (cần crawl đối chiếu)"),
    ("M3", "Ảnh có dính logo đối thủ / chất lượng hình ảnh"),
    ("M4", "CTA có đủ thuyết phục / mạnh mẽ"),
    ("M5", "Câu chuyện thật, trích dẫn có nguồn uy tín"),
]


def manual_checks() -> List[Dict]:
    return [
        _result(cid, ten, "manual", "cần người đánh giá", "—", "MANUAL — cần người đánh giá")
        for cid, ten in MANUAL_CHECKS
    ]


# ---------------------------------------------------------------------------
# Chạy toàn bộ
# ---------------------------------------------------------------------------


def run_all_checks(doc: Document, keyword: str, secondary_keywords: List[str] | None = None) -> List[Dict]:
    secondary_keywords = secondary_keywords or []
    results: List[Dict] = []
    results += check_title(doc, keyword)
    results += check_meta_description(doc, keyword)
    results += check_sapo(doc, keyword)
    results += check_keyword_density(doc, keyword)
    results += check_forbidden_absolute_words(doc)
    results += check_heading_hierarchy(doc, keyword)
    results += check_sentence_variance(doc)
    results += check_paragraph_variance(doc)
    results += check_images_alt(doc)
    results += check_keyword_distribution(doc, keyword)
    results += check_internal_links(doc)
    results += check_length(doc)

    for kw in secondary_keywords:
        kw = kw.strip()
        if not kw:
            continue
        count = count_occurrences(doc.full_text, kw)
        results.append(
            _result(
                f"sec:{kw}",
                f'Từ khóa phụ "{kw}" xuất hiện trong bài',
                "pass" if count >= 1 else "warn",
                f"{count} lần",
                "≥1 lần (khuyến nghị)",
            )
        )

    results += manual_checks()
    return results
