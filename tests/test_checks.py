import os

import pytest

from mona_seo_check import checks
from mona_seo_check.parser import load_document

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
KEYWORD = "thiết kế web"


def fixture(name):
    return os.path.join(FIXTURES, name)


# ---------------------------------------------------------------------------
# Toàn bài
# ---------------------------------------------------------------------------


def test_pass_mostly_html_no_fail_on_core_checks():
    doc = load_document(fixture("pass_mostly.html"))
    results = checks.run_all_checks(doc, KEYWORD)
    by_id = {r["id"]: r for r in results}

    assert by_id["1a"]["trang_thai"] == "pass"
    assert by_id["1b"]["trang_thai"] == "pass"
    assert by_id["2a"]["trang_thai"] == "pass"
    assert by_id["5"]["trang_thai"] == "pass"
    assert by_id["6d"]["trang_thai"] == "pass"
    assert by_id["9"]["trang_thai"] == "pass"


def test_fail_many_html_flags_many_issues():
    doc = load_document(fixture("fail_many.html"))
    results = checks.run_all_checks(doc, KEYWORD)
    statuses = [r["trang_thai"] for r in results]

    assert "fail" in statuses
    fail_count = statuses.count("fail")
    assert fail_count >= 5


def test_markdown_fixture_parses_title_and_description():
    doc = load_document(fixture("sample.md"))
    assert doc.title is not None
    assert "thiết kế web" in doc.title.lower()
    assert doc.meta_description is not None
    assert len(doc.headings) >= 2  # 2 H2, không tính H1 đã bị "ăn" làm title


# ---------------------------------------------------------------------------
# Test riêng từng hàm check
# ---------------------------------------------------------------------------


def test_title_length_pass():
    doc = load_document(fixture("pass_mostly.html"))
    results = checks.check_title(doc, KEYWORD)
    length_check = next(r for r in results if r["id"] == "1a")
    assert length_check["trang_thai"] == "pass"
    assert "56" in length_check["thuc_te"] or "ký tự" in length_check["thuc_te"]


def test_title_too_short_fails():
    doc = load_document(fixture("fail_many.html"))
    results = checks.check_title(doc, KEYWORD)
    length_check = next(r for r in results if r["id"] == "1a")
    assert length_check["trang_thai"] == "fail"


def test_keyword_density_within_range():
    doc = load_document(fixture("pass_mostly.html"))
    result = checks.check_keyword_density(doc, KEYWORD)[0]
    assert result["trang_thai"] in ("pass", "warn")


def test_keyword_density_stuffed_is_warn_or_fail():
    doc = load_document(fixture("fail_many.html"))
    result = checks.check_keyword_density(doc, KEYWORD)[0]
    assert result["trang_thai"] in ("warn", "fail")


def test_forbidden_words_detected():
    doc = load_document(fixture("fail_many.html"))
    results = checks.check_forbidden_absolute_words(doc)
    assert any(r["trang_thai"] == "fail" for r in results)
    # Phải bắt được ít nhất "tốt nhất" và "duy nhất"
    joined = " ".join(r["ten"] for r in results)
    assert "tốt nhất" in joined or "duy nhất" in joined


def test_forbidden_words_clean_passes():
    doc = load_document(fixture("pass_mostly.html"))
    results = checks.check_forbidden_absolute_words(doc)
    assert len(results) == 1
    assert results[0]["trang_thai"] == "pass"


def test_heading_hierarchy_jump_detected():
    doc = load_document(fixture("fail_many.html"))
    results = checks.check_heading_hierarchy(doc, KEYWORD)
    jump_check = next(r for r in results if r["id"] == "6c")
    assert jump_check["trang_thai"] == "fail"


def test_heading_hierarchy_ok_on_pass_fixture():
    doc = load_document(fixture("pass_mostly.html"))
    results = checks.check_heading_hierarchy(doc, KEYWORD)
    jump_check = next(r for r in results if r["id"] == "6c")
    assert jump_check["trang_thai"] == "pass"
    h2_kw_check = next(r for r in results if r["id"] == "6a")
    assert h2_kw_check["trang_thai"] == "pass"


def test_images_alt_missing_flagged():
    doc = load_document(fixture("fail_many.html"))
    result = checks.check_images_alt(doc)[0]
    assert result["trang_thai"] == "fail"


def test_images_alt_ok():
    doc = load_document(fixture("pass_mostly.html"))
    result = checks.check_images_alt(doc)[0]
    assert result["trang_thai"] == "pass"


def test_manual_checks_always_manual():
    results = checks.manual_checks()
    assert len(results) == 5
    assert all(r["trang_thai"] == "manual" for r in results)


def test_split_words_counts_vietnamese_correctly():
    words = checks.split_words("Thiết kế web chuẩn SEO 2026")
    assert len(words) == 6


def test_count_occurrences_case_and_accent_insensitive_case():
    text = "Thiết Kế Web là dịch vụ chủ lực."
    assert checks.count_occurrences(text, "thiết kế web") == 1
