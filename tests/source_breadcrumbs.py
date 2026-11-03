"""Inspect and remove source-site breadcrumb bars from imported section HTML."""

import argparse
import html
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
BOOK_INDEX = ROOT / "book-index.json"
ALLOWED_TAGS = {"a", "table", "tbody", "tr", "td"}
SEPARATOR_ONLY = re.compile(r"^[\s\u3000\u00a0\-–—>→➜]*$")


def find_breadcrumb(html_text):
    """Return (start, end, hrefs) for a pure top-of-section source breadcrumb."""
    divider = re.search(r"<hr\b[^>]*>", html_text, re.IGNORECASE)
    if not divider:
        return None

    prefix = html_text[: divider.start()]
    anchors = list(re.finditer(r"<a\b([^>]*)>(.*?)</a\s*>", prefix, re.IGNORECASE | re.DOTALL))
    if not anchors:
        return None

    hrefs = []
    for anchor in anchors:
        href_match = re.search(r"\bhref\s*=\s*([\"'])(.*?)\1", anchor.group(1), re.IGNORECASE | re.DOTALL)
        if not href_match:
            return None
        hrefs.append(html_unescape(href_match.group(2)))
    for href in hrefs:
        parsed = urlsplit(href)
        host = (parsed.hostname or "").lower()
        if not (
            parsed.scheme in {"http", "https"}
            and (host == "marxists.org" or host.endswith(".marxists.org"))
            and parsed.path.lower().endswith("/index.htm")
        ):
            return None

    tags = {tag.lower() for tag in re.findall(r"<\s*/?\s*([a-z0-9]+)", prefix, re.IGNORECASE)}
    if not tags <= ALLOWED_TAGS:
        return None

    without_links = re.sub(r"<a\b[^>]*>.*?</a\s*>", " ", prefix, flags=re.IGNORECASE | re.DOTALL)
    visible_separators = html_unescape(re.sub(r"<[^>]*>", " ", without_links))
    if not SEPARATOR_ONLY.fullmatch(visible_separators):
        return None

    # Remove only the leading breadcrumb and its divider; retain the entire body tail.
    leading_space = len(html_text) - len(html_text.lstrip())
    return leading_space, divider.end(), hrefs


def html_unescape(value):
    return html.unescape(value)


def iter_sections():
    catalog = json.loads(BOOK_INDEX.read_text(encoding="utf-8"))
    for book in catalog["books"]:
        section_dir = ROOT / book.get("sectionPath", "sections")
        for section in book.get("sections", []):
            path = section_dir / f"{section['id']}.json"
            record = json.loads(path.read_text(encoding="utf-8"))
            yield book, section, path, record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="write the cleanup to section JSON files")
    parser.add_argument("--report", type=Path, help="write a JSON list of affected section identities")
    args = parser.parse_args()

    found = []
    for book, section, path, record in iter_sections():
        source_html = record.get("html", "")
        match = find_breadcrumb(source_html)
        if not match:
            continue
        start, end, hrefs = match
        found.append({
            "bookId": book["id"],
            "bookTitle": book["title"],
            "sectionId": section["id"],
            "sectionTitle": section["title"],
            "path": str(path.relative_to(ROOT)),
            "hrefs": hrefs,
        })
        if args.apply:
            record["html"] = source_html[:start] + source_html[end:]
            path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.report:
        args.report.write_text(json.dumps(found, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    mode = "removed" if args.apply else "found"
    print(f"{mode}: {len(found)} source breadcrumb blocks across {len({item['bookId'] for item in found})} books")
    if found and not args.apply:
        print("Run with --apply to remove only these top-of-section breadcrumb blocks.")


if __name__ == "__main__":
    main()
