"""CLI: mona-seo-check — chấm on-page SEO 1 bài viết tiếng Việt."""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .checks import run_all_checks
from .parser import load_document

STATUS_ICON = {
    "pass": "✅",
    "fail": "❌",
    "warn": "⚠️",
    "manual": "📝",
}

STATUS_ASCII = {
    "pass": "PASS",
    "fail": "FAIL",
    "warn": "WARN",
    "manual": "MANUAL",
}


def _supports_unicode() -> bool:
    encoding = (sys.stdout.encoding or "").lower()
    return "utf" in encoding


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mona-seo-check",
        description="Chấm on-page SEO một bài viết tiếng Việt theo checklist tự động.",
    )
    p.add_argument("source", help="Đường dẫn file HTML/Markdown, hoặc URL (dùng cùng --url)")
    p.add_argument("--keyword", required=True, help="Từ khóa chính (bắt buộc)")
    p.add_argument("--secondary", default="", help="Từ khóa phụ, phân cách bằng dấu phẩy")
    p.add_argument("--url", action="store_true", help="Coi `source` là 1 URL thay vì đường dẫn file")
    p.add_argument("--json", action="store_true", help="Xuất kết quả dạng JSON thay vì bảng text")
    p.add_argument("--ascii", action="store_true", help="Ép dùng PASS/FAIL/WARN thay vì emoji")
    p.add_argument("--version", action="version", version=f"mona-seo-check {__version__}")
    return p


def format_table(results, use_ascii: bool) -> str:
    icons = STATUS_ASCII if use_ascii else STATUS_ICON
    lines = []
    header = f"{'ID':<6}{'Trạng thái':<10}{'Check':<55}{'Thực tế'}"
    lines.append(header)
    lines.append("-" * len(header))
    for r in results:
        icon = icons.get(r["trang_thai"], r["trang_thai"])
        ten = r["ten"]
        if len(ten) > 53:
            ten = ten[:50] + "..."
        lines.append(f"{r['id']:<6}{icon:<10}{ten:<55}{r['thuc_te']}")
        if r.get("ghi_chu"):
            lines.append(f"       └─ {r['ghi_chu']}")

    total = len(results)
    counts = {"pass": 0, "fail": 0, "warn": 0, "manual": 0}
    for r in results:
        counts[r["trang_thai"]] = counts.get(r["trang_thai"], 0) + 1

    lines.append("")
    lines.append(
        f"Tổng: {total} check | Pass: {counts['pass']} | Fail: {counts['fail']} | "
        f"Warn: {counts['warn']} | Manual: {counts['manual']}"
    )
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        doc = load_document(args.source, is_url=args.url)
    except Exception as exc:  # noqa: BLE001
        print(f"Lỗi đọc nguồn '{args.source}': {exc}", file=sys.stderr)
        return 2

    secondary_keywords = [s for s in args.secondary.split(",") if s.strip()] if args.secondary else []
    results = run_all_checks(doc, args.keyword, secondary_keywords)

    if args.json:
        payload = {
            "keyword": args.keyword,
            "secondary_keywords": secondary_keywords,
            "results": results,
            "summary": {
                status: sum(1 for r in results if r["trang_thai"] == status)
                for status in ("pass", "fail", "warn", "manual")
            },
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        use_ascii = args.ascii or not _supports_unicode()
        print(format_table(results, use_ascii))

    has_fail = any(r["trang_thai"] == "fail" for r in results)
    return 1 if has_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
