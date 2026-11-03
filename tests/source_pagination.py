"""Find and remove imported Marxists.org previous/next-page footer bars."""

import argparse
import html
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
BOOK_INDEX = ROOT / "book-index.json"
PREVIOUS_NEXT = {"上一篇", "下一篇", "上一页", "下一页"}
NAV_LABELS = PREVIOUS_NEXT | {"回目录", "目录"}
SEPARATOR_TAGS = re.compile(r"(?:<br\b[^>]*>|&nbsp;|&#160;|&#x0*a0;|&ensp;|&emsp;)", re.IGNORECASE)


def normalized_label(anchor):
    text = re.sub(r"<[^>]+>", " ", anchor.group(2))
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def is_source_link(anchor):
    href_match = re.search(r"\bhref\s*=\s*([\"'])(.*?)\1", anchor.group(1), re.IGNORECASE | re.DOTALL)
    if not href_match:
        return False
    parsed = urlsplit(html.unescape(href_match.group(2)))
    host = (parsed.hostname or "").lower()
    return parsed.scheme in {"http", "https"} and (host == "marxists.org" or host.endswith(".marxists.org"))


def only_separators(fragment):
    fragment = SEPARATOR_TAGS.sub("", fragment)
    fragment = html.unescape(re.sub(r"<[^>]*>", "", fragment))
    return not re.sub(r"[\s\u3000\u00a0\-–—>→➜]*", "", fragment)


def nav_groups(html_text):
    anchors = list(re.finditer(r"<a\b([^>]*)>(.*?)</a\s*>", html_text, re.IGNORECASE | re.DOTALL))
    groups = []
    current = []
    for anchor in anchors:
        label = normalized_label(anchor)
        if label not in NAV_LABELS or not is_source_link(anchor):
            if current:
                groups.append(current)
                current = []
            continue
        if current and not only_separators(html_text[current[-1].end():anchor.start()]):
            groups.append(current)
            current = []
        current.append(anchor)
    if current:
        groups.append(current)
    return [group for group in groups if len(group) >= 2 and any(normalized_label(item) in PREVIOUS_NEXT for item in group)]


def paragraph_span_for_group(html_text, group):
    start, end = group[0].start(), group[-1].end()
    for paragraph in re.finditer(r"<p\b[^>]*>(.*?)</p\s*>", html_text, re.IGNORECASE | re.DOTALL):
        if paragraph.start() <= start and end <= paragraph.end():
            inner = paragraph.group(1)
            links = list(re.finditer(r"<a\b([^>]*)>(.*?)</a\s*>", inner, re.IGNORECASE | re.DOTALL))
            if len(links) != len(group):
                return None
            if any(normalized_label(item) not in NAV_LABELS or not is_source_link(item) for item in links):
                return None
            if not only_separators(re.sub(r"<a\b[^>]*>.*?</a\s*>", " ", inner, flags=re.IGNORECASE | re.DOTALL)):
                return None
            return paragraph.start(), paragraph.end()
    return None


def removal_spans(html_text):
    spans = []
    groups = nav_groups(html_text)
    for group in groups:
        paragraph_span = paragraph_span_for_group(html_text, group)
        if paragraph_span:
            start, end = paragraph_span
            # Remove only the divider immediately attached to an otherwise-empty nav bar.
            dividers = list(re.finditer(r"<hr\b[^>]*>", html_text[:start], re.IGNORECASE))
            if dividers:
                divider = dividers[-1]
                between = html_text[divider.end():start]
                if only_separators(between) and start - divider.start() < 200:
                    start = divider.start()
            spans.append((start, end, group))
        else:
            spans.append((group[0].start(), group[-1].end(), group))
    return spans


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
    parser.add_argument("--apply", action="store_true", help="remove matching source pagination bars")
    parser.add_argument("--report", type=Path, help="write the pre-cleanup inventory as JSON")
    args = parser.parse_args()

    found = []
    for book, section, path, record in iter_sections():
        body = record.get("html", "")
        spans = removal_spans(body)
        if not spans:
            continue
        output = body
        for start, end, group in reversed(spans):
            labels = [normalized_label(item) for item in group]
            hrefs = []
            for item in group:
                href = re.search(r"\bhref\s*=\s*([\"'])(.*?)\1", item.group(1), re.IGNORECASE | re.DOTALL)
                hrefs.append(html.unescape(href.group(2)) if href else "")
            found.append({
                "bookId": book["id"],
                "bookTitle": book["title"],
                "sectionId": section["id"],
                "sectionTitle": section["title"],
                "path": str(path.relative_to(ROOT)),
                "labels": labels,
                "hrefs": hrefs,
            })
            output = output[:start] + output[end:]
        if args.apply:
            record["html"] = output
            path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.report:
        args.report.write_text(json.dumps(found, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{'removed' if args.apply else 'found'}: {len(found)} source pagination bars across {len({item['bookId'] for item in found})} books")
    if found and not args.apply:
        print("Run with --apply to remove these source pagination bars.")


if __name__ == "__main__":
    main()
