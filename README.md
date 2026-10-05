# mona-seo-check

A command-line tool that scores the on-page SEO of a single Vietnamese article against an automated checklist.

[![test](https://github.com/mona-software/mona-seo-check-vi/actions/workflows/test.yml/badge.svg)](https://github.com/mona-software/mona-seo-check-vi/actions/workflows/test.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

The tool targets Vietnamese content: keyword matching is Unicode-normalized (NFC) and the absolute-claim word list is Vietnamese. Input is an HTML file, a Markdown file, or a URL, plus the primary keyword. Each check reports `pass`, `fail`, `warn` or `manual`; checks that need human judgment are listed as `manual` rather than scored.

## Install

Requires Python 3.10+. The core has no third-party dependencies.

```bash
git clone https://github.com/mona-software/mona-seo-check-vi
cd mona-seo-check-vi
pip install -e .
# Optional: use BeautifulSoup for more lenient HTML parsing
pip install -e ".[html]"
```

## Usage

```bash
mona-seo-check <file-or-url> --keyword "<primary keyword>" [--secondary "kw1, kw2"] [--url] [--json] [--ascii]
```

| Option | Description |
| --- | --- |
| `source` | Path to an HTML or Markdown file, or a URL when `--url` is set |
| `--keyword` | Primary keyword (required) |
| `--secondary` | Comma-separated secondary keywords; each gets a check that it appears at least once (`warn` if absent) |
| `--url` | Treat `source` as a URL and download it |
| `--json` | Print JSON instead of a table |
| `--ascii` | Print `PASS`/`FAIL`/`WARN`/`MANUAL` instead of emoji (also used automatically when stdout is not UTF-8) |
| `--version` | Print the version |

Exit codes: `0` when no check fails (warnings and manual items allowed), `1` when at least one check fails, `2` when the source cannot be read.

### Example

```bash
mona-seo-check tests/fixtures/pass_mostly.html --keyword "thiết kế web"
```

Output (abridged; labels are in Vietnamese):

```
ID    Trạng tháiCheck                                                  Thực tế
------------------------------------------------------------------------------
1a    ✅         Độ dài title                                           56 ký tự
       └─ Thiết kế web chuẩn SEO cho doanh nghiệp nhỏ tại Việt Nam
1b    ✅         Title chứa từ khóa chính                               xuất hiện 1 lần
...
4     ⚠️        Mật độ từ khóa chính toàn bài                          0.90% (4 lần / 442 từ)
...
7     ✅         Độ so le độ dài câu (std số từ/câu)                    std=11.29, trung bình=26.0 từ/câu, 17 câu
...
M5    📝         Câu chuyện thật, trích dẫn có nguồn uy tín             cần người đánh giá
       └─ MANUAL — cần người đánh giá

Tổng: 27 check | Pass: 21 | Fail: 0 | Warn: 1 | Manual: 5
```

### JSON output

`--json` prints an object with `keyword`, `secondary_keywords`, `results` and `summary` (counts per status). Each result has these fields:

| Field | Meaning |
| --- | --- |
| `id` | Check ID (`1a`, `4`, `sec:<keyword>`, `M1`…) |
| `ten` | Check name |
| `trang_thai` | `pass`, `fail`, `warn` or `manual` |
| `thuc_te` | Measured value |
| `yeu_cau` | Threshold applied |
| `ghi_chu` | Note, such as the title text or the offending sentence |

## Checks

All thresholds are heuristics and can be adjusted in `src/mona_seo_check/checks.py`.

1. **Title**: 55–65 characters, contains the primary keyword, keyword within the first 20 characters, keyword repeated at most twice.
2. **Meta description**: 150–160 characters, contains the keyword (at most 3 times), no literal double quotes.
3. **Opening paragraph**: at most ~600 characters (about 6 lines); keyword appears within the first 100 words.
4. **Keyword density**: 1–3% across the article.
5. **Absolute claims**: flags each occurrence of "nhất", "số 1", "số một", "duy nhất", "tốt nhất" with the surrounding sentence.
6. **Headings**: at least one H2 contains the keyword, H2/H3 sections exist, no H3 before the first H2, no extra H1.
7. **Sentence length variance**: standard deviation of words per sentence; below 3 is a warning, since very uniform sentence lengths often indicate templated text.
8. **Paragraph length variance**: share of paragraphs with exactly 2 sentences (warn above 40%) and with 4+ sentences (warn below 15%).
9. **Image alt text**: every image has a non-empty `alt`.
10. **Keyword distribution**: with 3+ H2 sections, the keyword appears in at least 2 of them.
11. **Links**: warns if the article has no links.
12. **Length**: warns below 300 words.

Manual items (always reported as `manual`): content quality and brand voice, duplicate content on other sites, image quality and third-party logos, CTA strength, and whether stories and quotes are real and sourced.

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT, see [LICENSE](LICENSE).

**`mona-seo-check` is a product of MONA Software, a member of The MONA Group.**
