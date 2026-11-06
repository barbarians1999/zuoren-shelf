"""Full-catalog browser acceptance for shelf and author-page reading routes.

Requires Playwright Python and /usr/bin/chromium. Starts only a local static server.
"""

import json
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

from playwright.sync_api import sync_playwright

from reader_routes import ROOT, static_server

REPORT_PATH = ROOT / "tests" / "reader_routes_full_results.json"
INTENTIONALLY_HIDDEN_AUTHOR_DUPLICATES = {
    "mx-marx-8b258427cf",
    "mx-marx-manifesto-1920",
    "mx-mao-2879fb351d",
    "mx-mao-293230863b",
    "mx-mao-7b164441c7",
    "mx-mao-6fdaa3c3b1",
    "mx-mao-dfb3f59735",
    "mx-mao-68029f79ad",
    "mx-mao-53b9a678c4",
    "mx-mao-193435e9d2",
    "mx-mao-c1ee5906d8",
    "mx-mao-ec47576830",
}


def route_params(url):
    parsed = urlsplit(url)
    values = parse_qs(parsed.query)
    return {key: items[-1] for key, items in values.items() if items}


def section_for_route(book, requested_id=None):
    sections = book.get("sections", [])
    visible = [(i, section) for i, section in enumerate(sections) if section.get("readerHidden") is not True]
    if book.get("type") == "scan":
        return None, "scan books are outside this text-section route test"
    if not visible:
        return None, "book has no readable sections"
    if requested_id:
        found = next((i for i, section in enumerate(sections) if section["id"] == requested_id), None)
        if found is not None:
            exact = next(((i, section) for i, section in visible if i == found), None)
            if exact:
                return exact[1], None
            following = next(((i, section) for i, section in visible if i > found), None)
            if following:
                return following[1], None
            preceding = next(((i, section) for i, section in reversed(visible) if i < found), None)
            if preceding:
                return preceding[1], None
    return visible[0][1], None


def make_query_url(origin, book_id, section_id, author_id=None):
    params = {"book": book_id, "section": section_id}
    if author_id:
        params["author"] = author_id
    return origin + "/?" + urlencode(params)


def identity_state(page, book, section, expected_resource, response_log, errors):
    page.wait_for_function("() => { const e = document.querySelector('#reader'); return e && !e.classList.contains('is-hidden'); }", timeout=15000)
    assert page.locator("#reader").is_visible(), "reader is not visible"
    assert page.locator("#book-title").inner_text() == book["title"], "wrong book title"
    assert page.locator("#section-title").text_content().strip() == section["title"], "wrong section title"
    page.wait_for_function(
        "() => { const e = document.querySelector('#desktop-content'); "
        "return e && e.firstElementChild && !e.firstElementChild.classList.contains('loading-copy'); }",
        timeout=15000,
    )
    assert expected_resource in response_log, f"section body not fetched: {expected_resource}"
    assert not errors, f"browser errors: {errors}"


def main():
    data = json.loads((ROOT / "book-index.json").read_text(encoding="utf-8"))
    books = data["books"]
    book_by_id = {book["id"]: book for book in books}
    assert len(book_by_id) == len(books), "duplicate book IDs"
    section_files_checked = 0
    for book in books:
        section_ids = [section.get("id") for section in book.get("sections", [])]
        assert all(section_ids), f"missing section ID in {book['id']}"
        assert len(section_ids) == len(set(section_ids)), f"duplicate section ID in {book['id']}"
        section_dir = ROOT / book.get("sectionPath", "sections")
        for section_id in section_ids:
            assert (section_dir / f"{section_id}.json").is_file(), f"missing body file: {book['id']}/{section_id}"
            section_files_checked += 1

    home_books = [(i, book) for i, book in enumerate(books) if not book.get("authorOnly")]
    author_only = {book["id"] for book in books if book.get("authorOnly")}
    assert len(home_books) + len(author_only) == len(books)
    report = {
        "summary": {},
        "books": [],
        "failures": [],
        "skips": [],
        "intentional_source_exclusions": [],
    }

    with static_server() as origin:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                executable_path="/usr/bin/chromium",
                args=["--no-sandbox", "--disable-cache"],
            )

            # Exercise every ordinary shelf-card link and capture the actual copied URL.
            context = browser.new_context(viewport={"width": 1365, "height": 900})
            context.grant_permissions(["clipboard-read", "clipboard-write"], origin=origin)
            page = context.new_page()
            page.set_default_timeout(7000)
            page.goto(origin + "/", wait_until="domcontentloaded")
            page.wait_for_selector("#book-list .open-button")
            copied_from_home = {}
            for count, (book_index, book) in enumerate(home_books, 1):
                try:
                    section, reason = section_for_route(book)
                    if reason:
                        report["skips"].append({"bookId": book["id"], "reason": reason})
                        continue
                    page.locator(f'#book-list .open-button[data-book="{book_index}"]').click()
                    assert page.locator("#book-title").inner_text() == book["title"]
                    params = route_params(page.url)
                    assert params.get("book") == book["id"], page.url
                    assert params.get("section") == section["id"], page.url
                    page.locator("#desktop-share-button").click()
                    copied = page.evaluate("navigator.clipboard.readText()")
                    assert copied == page.url, (copied, page.url)
                    copied_from_home[book["id"]] = copied
                    page.locator("#back-button").click()
                    assert page.locator("#shelf").is_visible()
                except Exception as error:
                    report["failures"].append({
                        "stage": "home-card-click-copy",
                        "bookId": book["id"],
                        "title": book["title"],
                        "error": str(error),
                    })
                    try:
                        if page.locator("#reader").is_visible():
                            page.locator("#back-button").click(timeout=1000)
                    except Exception:
                        pass
                if count % 25 == 0:
                    print(f"home cards: {count}/{len(home_books)}", flush=True)
            context.close()

            # Gather rendered author-page links, after the app's intentional deduplication.
            author_routes = {}
            context = browser.new_context(viewport={"width": 1365, "height": 900})
            page = context.new_page()
            page.set_default_timeout(7000)
            for author in data.get("authorIndex", []):
                page.goto(origin + "/?author=" + author["id"], wait_until="domcontentloaded")
                page.wait_for_selector("#author-featured-list")
                hrefs = page.locator("#author-featured-list a[href]").evaluate_all(
                    "nodes => nodes.map(a => a.getAttribute('href'))"
                )
                for href in hrefs:
                    params = route_params(href)
                    book_id = params.get("book")
                    section_id = params.get("section")
                    if book_id in author_only and section_id:
                        author_routes.setdefault(book_id, {"href": href, "authorId": author["id"]})
            context.close()

            missing_author_links = author_only - set(author_routes)
            expected_missing = author_only & INTENTIONALLY_HIDDEN_AUTHOR_DUPLICATES
            unexpected_missing = missing_author_links - expected_missing
            for book_id in sorted(expected_missing):
                book = book_by_id[book_id]
                report["intentional_source_exclusions"].append({
                    "bookId": book_id,
                    "title": book["title"],
                    "reason": "Author page intentionally hides this duplicate edition/article link; direct route is still tested below.",
                })
            for book_id in sorted(unexpected_missing):
                book = book_by_id[book_id]
                report["failures"].append({
                    "stage": "author-link-discovery",
                    "bookId": book_id,
                    "title": book["title"],
                    "error": "author-only book has no rendered author-page link",
                })

            if set(author_routes) != author_only - expected_missing:
                report["failures"].append({
                    "stage": "author-link-coverage",
                    "error": f"rendered author links cover {len(author_routes)} of {len(author_only)} author-only books; expected {len(author_only - expected_missing)} plus {len(expected_missing)} intentional Mao exclusions",
                })

            # For every book ID, use its actual home-card URL, actual rendered author href,
            # or an explicit direct route for the intentionally hidden author-page duplicates.
            verified = []
            for index, book in enumerate(books, 1):
                section, reason = section_for_route(book)
                if reason:
                    report["skips"].append({"bookId": book["id"], "title": book["title"], "reason": reason})
                    continue
                route_info = None
                if book["id"] in copied_from_home:
                    source_url = copied_from_home[book["id"]]
                    source_kind = "home-card-click"
                elif book["id"] in author_routes:
                    route_info = author_routes[book["id"]]
                    source_url = route_info["href"]
                    source_kind = "rendered-author-page-link"
                else:
                    source_url = make_query_url(origin, book["id"], section["id"])
                    source_kind = "intentionally-hidden-author-duplicate"

                params = route_params(source_url)
                requested_section = params.get("section")
                canonical_section, section_reason = section_for_route(book, requested_section)
                if section_reason:
                    report["skips"].append({"bookId": book["id"], "title": book["title"], "reason": section_reason})
                    continue
                relative_resource = (book.get("sectionPath") or "sections").strip("/")
                expected_resource = "/" + relative_resource + "/" + canonical_section["id"] + ".json"
                page_errors = []
                response_log = []
                context = None
                try:
                    # Each book begins in its own empty browser context, as a recipient would open a share.
                    context = browser.new_context(viewport={"width": 1365, "height": 900})
                    context.grant_permissions(["clipboard-read", "clipboard-write"], origin=origin)
                    page = context.new_page()
                    page.set_default_timeout(15000)
                    page.on("pageerror", lambda error, bucket=page_errors: bucket.append(str(error)))
                    page.on(
                        "response",
                        lambda response, path=expected_resource, bucket=response_log:
                            bucket.append(urlsplit(response.url).path)
                            if urlsplit(response.url).path == path and response.status == 200
                            else None,
                    )
                    page.goto(source_url if source_url.startswith("http") else origin + source_url,
                              wait_until="domcontentloaded", timeout=20000)
                    identity_state(page, book, canonical_section, expected_resource, response_log, page_errors)
                    loaded_params = route_params(page.url)
                    assert loaded_params.get("book") == book["id"], page.url
                    assert loaded_params.get("section") == canonical_section["id"], page.url
                    page.locator("#desktop-share-button").click()
                    copied_url = page.evaluate("navigator.clipboard.readText()")
                    assert copied_url == page.url, (copied_url, page.url)
                    page_errors.clear()
                    response_log.clear()
                    page.goto(copied_url, wait_until="domcontentloaded", timeout=20000)
                    identity_state(page, book, canonical_section, expected_resource, response_log, page_errors)
                    page_errors.clear()
                    response_log.clear()
                    page.reload(wait_until="domcontentloaded", timeout=20000)
                    identity_state(page, book, canonical_section, expected_resource, response_log, page_errors)
                    verified.append({
                        "bookId": book["id"],
                        "title": book["title"],
                        "source": source_kind,
                        "sourceUrl": urlsplit(source_url).path + ("?" + urlsplit(source_url).query if urlsplit(source_url).query else ""),
                        "canonicalUrl": urlsplit(copied_url).path + "?" + urlsplit(copied_url).query,
                        "sectionId": canonical_section["id"],
                        "sectionTitle": canonical_section["title"],
                        "bodyResource": expected_resource,
                        "copy": "pass",
                        "newContextDirect": "pass",
                        "refresh": "pass",
                    })
                except Exception as error:
                    report["failures"].append({
                        "stage": "full-route-copy-direct-refresh",
                        "bookId": book["id"],
                        "title": book["title"],
                        "source": source_kind,
                        "sourceUrl": source_url,
                        "expectedSectionId": canonical_section["id"],
                        "error": str(error),
                        "pageErrors": page_errors,
                    })
                finally:
                    if context:
                        context.close()
                if index % 25 == 0:
                    print(f"full routes: {index}/{len(books)}; passed={len(verified)} failed={len(report['failures'])}", flush=True)

            report["books"] = verified
            report["summary"] = {
                "catalogBooks": len(books),
                "sectionIdsAndBodyFilesChecked": section_files_checked,
                "homeCardsClicked": len(copied_from_home),
                "renderedAuthorOnlyLinks": len(author_routes),
                "intentionallyHiddenAuthorOnlyDuplicates": len(expected_missing),
                "directRouteCopyNewContextRefreshPassed": len(verified),
                "failed": len(report["failures"]),
                "skipped": len(report["skips"]),
            }
            browser.close()

    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("FULL CATALOG SUMMARY", json.dumps(report["summary"], ensure_ascii=False), flush=True)
    print("INTENTIONAL SOURCE EXCLUSIONS", json.dumps(report["intentional_source_exclusions"], ensure_ascii=False), flush=True)
    print("FAILURES", json.dumps(report["failures"], ensure_ascii=False), flush=True)
    print("SKIPS", json.dumps(report["skips"], ensure_ascii=False), flush=True)
    print("REPORT", str(REPORT_PATH), flush=True)
    if report["failures"] or report["skips"] or len(verified) != len(books):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
