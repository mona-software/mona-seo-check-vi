"""Đọc HTML hoặc Markdown và trả về một cấu trúc dữ liệu chung (Document).

Mục tiêu: từ 1 file HTML, 1 file Markdown, hoặc 1 URL, trích ra:
- title: tiêu đề trang (thẻ <title> ở HTML, hoặc frontmatter/H1 đầu tiên ở Markdown)
- meta_description: mô tả meta (thẻ <meta name="description"> ở HTML,
  hoặc frontmatter `description:` ở Markdown)
- headings: danh sách (level, text) — level 1 = H1, 2 = H2, v.v.
- paragraphs: danh sách đoạn văn (plain text, đã bỏ heading/list/code)
- images: danh sách (src, alt)
- links: danh sách (text, href)
- full_text: toàn bộ text thân bài (không gồm title/meta) để đếm từ,
  đếm mật độ từ khóa, tách câu...

Ưu tiên dùng thư viện chuẩn (html.parser). Nếu môi trường có cài
`beautifulsoup4` thì parser HTML sẽ dùng BeautifulSoup vì khoan dung hơn với
HTML lỗi cú pháp — nhưng đây là optional, không bắt buộc cài.
"""

from __future__ import annotations

import re
import unicodedata
import urllib.request
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import List, Optional, Tuple

try:  # pragma: no cover - phụ thuộc optional
    from bs4 import BeautifulSoup  # type: ignore

    _HAS_BS4 = True
except Exception:  # pragma: no cover
    _HAS_BS4 = False


HEADING_TAGS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}


@dataclass
class Document:
    title: Optional[str] = None
    meta_description: Optional[str] = None
    headings: List[Tuple[int, str]] = field(default_factory=list)
    paragraphs: List[str] = field(default_factory=list)
    images: List[Tuple[str, str]] = field(default_factory=list)
    links: List[Tuple[str, str]] = field(default_factory=list)
    full_text: str = ""
    source_type: str = "html"  # "html" | "markdown"
    raw_h1_count: int = 0  # số thẻ <h1> tìm thấy trong phần thân (HTML)


def normalize(text: str) -> str:
    """Chuẩn hoá Unicode NFC — bắt buộc trước khi đo độ dài/so khớp
    chuỗi tiếng Việt có dấu, vì cùng 1 chữ có thể được lưu ở NFC hoặc
    NFD (dấu tổ hợp) và len()/so sánh chuỗi sẽ ra kết quả khác nhau."""
    return unicodedata.normalize("NFC", text or "")


def fetch_url(url: str) -> str:
    """Tải nội dung 1 URL bằng urllib (stdlib), không bắt buộc `requests`."""
    req = urllib.request.Request(url, headers={"User-Agent": "mona-seo-check/0.1"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        raw = resp.read()
    return raw.decode(charset, errors="replace")


# ---------------------------------------------------------------------------
# HTML parsing
# ---------------------------------------------------------------------------


class _SimpleHTMLParser(HTMLParser):
    """Parser HTML tự viết bằng html.parser, dùng khi không có bs4.

    Không phải parser HTML hoàn chỉnh (không xử lý mọi trường hợp lỗi
    cú pháp) — đủ dùng cho bài viết CMS/blog thông thường.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: List[str] = []
        self.meta_description: Optional[str] = None
        self.headings: List[Tuple[int, str]] = []
        self.paragraphs: List[str] = []
        self.images: List[Tuple[str, str]] = []
        self.links: List[Tuple[str, str]] = []
        self.body_text_parts: List[str] = []

        self._in_title = False
        self._heading_level: Optional[int] = None
        self._heading_buf: List[str] = []
        self._in_p = False
        self._p_buf: List[str] = []
        self._in_a = False
        self._a_href: str = ""
        self._a_buf: List[str] = []
        self._skip_stack: List[str] = []  # script/style: bỏ qua text bên trong

    def handle_starttag(self, tag: str, attrs) -> None:
        attrs_d = dict(attrs)
        if tag in ("script", "style"):
            self._skip_stack.append(tag)
            return
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            name = (attrs_d.get("name") or "").lower()
            if name == "description" and attrs_d.get("content"):
                self.meta_description = attrs_d["content"]
        elif tag in HEADING_TAGS:
            self._heading_level = HEADING_TAGS[tag]
            self._heading_buf = []
        elif tag == "p":
            self._in_p = True
            self._p_buf = []
        elif tag == "img":
            src = attrs_d.get("src", "")
            alt = attrs_d.get("alt", "")
            self.images.append((src, alt))
        elif tag == "a":
            self._in_a = True
            self._a_href = attrs_d.get("href", "")
            self._a_buf = []
        elif tag == "br":
            if self._in_p:
                self._p_buf.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style"):
            if self._skip_stack:
                self._skip_stack.pop()
            return
        if tag == "title":
            self._in_title = False
        elif tag in HEADING_TAGS and self._heading_level is not None:
            text = "".join(self._heading_buf).strip()
            if text:
                self.headings.append((self._heading_level, text))
                self.body_text_parts.append(text)
            self._heading_level = None
        elif tag == "p":
            text = "".join(self._p_buf).strip()
            text = re.sub(r"\s+", " ", text)
            if text:
                self.paragraphs.append(text)
                self.body_text_parts.append(text)
            self._in_p = False
        elif tag == "a":
            text = "".join(self._a_buf).strip()
            self.links.append((text, self._a_href))
            self._in_a = False

    def handle_data(self, data: str) -> None:
        if self._skip_stack:
            return
        if self._in_title:
            self.title_parts.append(data)
        if self._heading_level is not None:
            self._heading_buf.append(data)
        if self._in_p:
            self._p_buf.append(data)
        if self._in_a:
            self._a_buf.append(data)


def parse_html(html: str) -> Document:
    doc = Document(source_type="html")

    if _HAS_BS4:  # pragma: no cover - nhánh optional, khó ép chạy trong CI mặc định
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        title_tag = soup.find("title")
        doc.title = title_tag.get_text(strip=True) if title_tag else None
        meta_tag = soup.find("meta", attrs={"name": "description"})
        doc.meta_description = meta_tag.get("content") if meta_tag else None
        for level, tagname in ((1, "h1"), (2, "h2"), (3, "h3"), (4, "h4"), (5, "h5"), (6, "h6")):
            pass
        for h in soup.find_all([f"h{i}" for i in range(1, 7)]):
            text = h.get_text(strip=True)
            if text:
                doc.headings.append((HEADING_TAGS[h.name], text))
        for p in soup.find_all("p"):
            text = re.sub(r"\s+", " ", p.get_text(" ", strip=True))
            if text:
                doc.paragraphs.append(text)
        for img in soup.find_all("img"):
            doc.images.append((img.get("src", ""), img.get("alt", "")))
        for a in soup.find_all("a"):
            doc.links.append((a.get_text(strip=True), a.get("href", "")))
        body_parts = [t for _, t in doc.headings] + doc.paragraphs
        doc.full_text = normalize(" ".join(body_parts))
        doc.raw_h1_count = max(0, sum(1 for lvl, _ in doc.headings if lvl == 1) - 1)
        doc.title = normalize(doc.title) if doc.title else None
        doc.meta_description = normalize(doc.meta_description) if doc.meta_description else None
        return doc

    parser = _SimpleHTMLParser()
    parser.feed(html)
    doc.title = normalize("".join(parser.title_parts).strip()) or None
    doc.meta_description = (
        normalize(parser.meta_description.strip()) if parser.meta_description else None
    )
    doc.headings = [(lvl, normalize(t)) for lvl, t in parser.headings]
    doc.paragraphs = [normalize(p) for p in parser.paragraphs]
    doc.images = parser.images
    doc.links = parser.links
    doc.full_text = normalize(" ".join(parser.body_text_parts))
    doc.raw_h1_count = max(0, sum(1 for lvl, _ in doc.headings if lvl == 1) - 1)
    return doc


# ---------------------------------------------------------------------------
# Markdown parsing
# ---------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]*)\)")
_LINK_RE = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)]*)\)")
_CODE_FENCE_RE = re.compile(r"^```")


def _parse_frontmatter(text: str) -> Tuple[dict, str]:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    raw = m.group(1)
    meta = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip().lower()] = value.strip().strip("'\"")
    rest = text[m.end():]
    return meta, rest


def parse_markdown(md_text: str) -> Document:
    doc = Document(source_type="markdown")
    meta, body = _parse_frontmatter(md_text)

    doc.title = normalize(meta.get("title")) if meta.get("title") else None
    doc.meta_description = (
        normalize(meta.get("description") or meta.get("meta_description"))
        if (meta.get("description") or meta.get("meta_description"))
        else None
    )

    lines = body.splitlines()
    in_code = False
    current_para: List[str] = []
    first_h1_used_as_title = doc.title is None
    body_text_parts: List[str] = []

    def flush_paragraph() -> None:
        if current_para:
            text = normalize(re.sub(r"\s+", " ", " ".join(current_para)).strip())
            if text:
                doc.paragraphs.append(text)
                body_text_parts.append(text)
            current_para.clear()

    for line in lines:
        stripped = line.strip()

        if _CODE_FENCE_RE.match(stripped):
            in_code = not in_code
            continue
        if in_code:
            continue

        if not stripped:
            flush_paragraph()
            continue

        heading_match = _HEADING_RE.match(stripped)
        if heading_match:
            flush_paragraph()
            level = len(heading_match.group(1))
            text = normalize(heading_match.group(2).strip())
            if level == 1 and first_h1_used_as_title:
                doc.title = text
                first_h1_used_as_title = False
                continue
            doc.headings.append((level, text))
            body_text_parts.append(text)
            continue

        # Ảnh/link dạng markdown — vẫn tính vào đoạn văn hiện tại (text)
        for alt, src in _IMAGE_RE.findall(stripped):
            doc.images.append((src, alt))
        for text_, href in _LINK_RE.findall(stripped):
            doc.links.append((text_, href))

        # Bỏ list marker đơn giản (-, *, 1.) khi gom vào đoạn văn
        clean_line = re.sub(r"^\s*([-*]|\d+\.)\s+", "", stripped)
        current_para.append(clean_line)

    flush_paragraph()

    # raw_h1_count: số heading level==1 CÒN LẠI trong thân bài sau khi H1 đầu
    # tiên đã bị "ăn" làm title. >0 nghĩa là bài có nhiều hơn 1 H1 (lỗi cấu trúc).
    doc.raw_h1_count = sum(1 for lvl, _ in doc.headings if lvl == 1)
    doc.full_text = normalize(" ".join(body_text_parts))
    return doc


# ---------------------------------------------------------------------------
# Entry point chung
# ---------------------------------------------------------------------------


def load_document(source: str, is_url: bool = False) -> Document:
    """source: đường dẫn file HOẶC url (nếu is_url=True) HOẶC nội dung đã có sẵn.

    Tự đoán HTML vs Markdown theo phần mở rộng file, hoặc theo nội dung
    (có thẻ <html>/<body> → HTML) khi tải từ URL.
    """
    if is_url:
        content = fetch_url(source)
        looks_like_html = bool(re.search(r"<html[\s>]|<body[\s>]|<!doctype html", content, re.I))
        return parse_html(content) if looks_like_html else parse_markdown(content)

    lower = source.lower()
    with open(source, "r", encoding="utf-8") as f:
        content = f.read()

    if lower.endswith((".md", ".markdown")):
        return parse_markdown(content)
    if lower.endswith((".html", ".htm")):
        return parse_html(content)

    # Không rõ đuôi file — đoán theo nội dung
    if re.search(r"<html[\s>]|<body[\s>]|<!doctype html", content, re.I):
        return parse_html(content)
    return parse_markdown(content)
