"""Check the consolidated Lenin work entry and retained edition routes."""

import re
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import sync_playwright

from reader_routes import static_server


def route_params(url):
    return {key: values[-1] for key, values in parse_qs(urlsplit(url).query).items()}


def author_links(page):
    return page.locator("#author-featured-list a[href]").evaluate_all(
        "nodes => nodes.map(a => ({text: a.innerText.trim(), href: a.getAttribute('href'), "
        "priority: Boolean(a.closest('li.is-priority'))}))"
    )


def wait_for_reader(page):
    page.wait_for_function(
        "() => { const e = document.querySelector('#reader'); "
        "return e && !e.classList.contains('is-hidden') && "
        "!document.querySelector('#section-title').textContent.includes('正在加载'); }",
        timeout=15000,
    )


def main():
    with static_server() as origin:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                executable_path="/usr/bin/chromium",
                args=["--no-sandbox", "--disable-cache"],
            )
            page = browser.new_page(viewport={"width": 1365, "height": 900})

            page.goto(f"{origin}/?author=lenin", wait_until="domcontentloaded")
            page.wait_for_selector("#author-featured-list a")
            links = author_links(page)
            count = int(re.search(r"\d+", page.locator("#author-featured-count").inner_text()).group())
            assert len(links) == count, (len(links), count)
            howto_links = [link for link in links if route_params(link["href"]).get("book") == "howto"]
            mia_links = [
                link for link in links
                if route_params(link["href"]).get("book") == "mx-lenin-eda649f794"
            ]
            assert len(howto_links) == 1 and not mia_links, links
            assert route_params(howto_links[0]["href"]) == {"author": "lenin", "book": "howto", "section": "part-03"}
            assert howto_links[0]["priority"] and howto_links[0]["text"] == "怎么办？"
            assert page.locator("#author-summary").inner_text().endswith(f"本地收录 {count} 项作品与文章，按写作或发表时间排列。")
            print("dynamic Lenin author page: one recommended howto/part-03 entry and consistent count: PASS")

            for query in ("怎么办", "怎么办？", "《怎么办？》"):
                page.locator("#book-search").fill(query)
                page.wait_for_function(
                    "() => document.querySelector('#author-featured-count').textContent.trim() === '（1）'"
                )
                filtered = author_links(page)
                assert len(filtered) == 1 and route_params(filtered[0]["href"]).get("book") == "howto", (query, filtered)
                assert filtered[0]["priority"] and filtered[0]["text"] == "怎么办？", (query, filtered)
            page.locator("#book-search").fill("没有这个作品")
            page.wait_for_function(
                "() => document.querySelector('#author-featured-count').textContent.trim() === '（0）'"
            )
            assert page.locator("#author-featured-list li").count() == 0
            page.locator("#book-search").fill("我们纲领中的民族问题")
            page.wait_for_function(
                "() => document.querySelector('#author-featured-count').textContent.trim() === '（1）'"
            )
            other_work = author_links(page)
            assert len(other_work) == 1
            assert route_params(other_work[0]["href"]).get("book") == "lenin-selected"
            assert route_params(other_work[0]["href"]).get("section") == "section-026"
            print("dynamic author search resolves all group aliases and preserves unrelated/no-result search: PASS")

            # Distinct letters and editorial versions remain visible as separate works.
            for author_id, retained_ids in [
                ("marx", {"mx-marx-72fc4a449f", "mx-marx-6ada1c8b56", "mx-marx-f11d3f0ca7", "mx-marx-42c236acf6"}),
                ("engels", {"mx-engels-1e0fdedec5", "mx-engels-7a4e965cae"}),
            ]:
                page.goto(f"{origin}/?author={author_id}", wait_until="domcontentloaded")
                page.wait_for_selector("#author-featured-list a")
                ids = {route_params(link["href"]).get("book") for link in author_links(page)}
                assert retained_ids <= ids, (author_id, retained_ids - ids)
            print("same-title letters and distinct Wage Labour editions remain separate: PASS")

            # Both original reader URLs remain independently usable.
            for book_id, section_id, section_text, title in [
                ("howto", "part-03", "（一）什么是“批评自由”？", "怎么办"),
                ("mx-lenin-eda649f794", "section-002", "一 教条主义和“批评自由”", "《怎么办？》"),
            ]:
                page.goto(
                    f"{origin}/?book={book_id}&section={section_id}",
                    wait_until="domcontentloaded",
                )
                wait_for_reader(page)
                assert page.locator("#book-title").inner_text() == title
                assert page.locator("#section-title").inner_text() == section_text
                assert route_params(page.url).get("book") == book_id
                print(f"direct reader route retained: PASS — {book_id}/{section_id}")

            static_author = open("authors/lenin/index.html", encoding="utf-8").read()
            assert static_author.count(">怎么办？</a>") == 1
            static_count = re.search(r"本地收录 (\d+) 篇", static_author)
            assert static_count and int(static_count.group(1)) == count
            assert "texts/howto/part-03/" in static_author
            assert "texts/mx-lenin-eda649f794/section-002/" not in static_author
            book_index = json.loads(Path("book-index.json").read_text(encoding="utf-8"))
            books = {book["id"]: book for book in book_index["books"]}
            for book_id in ("howto", "mx-lenin-eda649f794"):
                book = books[book_id]
                assert Path(f"books/{book_id}/index.html").is_file()
                for section in book["sections"]:
                    section_id = section["id"]
                    assert Path(f"{book['sectionPath']}/{section_id}.json").is_file()
                    assert Path(f"texts/{book_id}/{section_id}/index.html").is_file()

            for author_id, preserved_ids in [
                ("marx", {"mx-marx-72fc4a449f", "mx-marx-6ada1c8b56", "mx-marx-f11d3f0ca7", "mx-marx-42c236acf6"}),
                ("engels", {"mx-engels-1e0fdedec5", "mx-engels-7a4e965cae"}),
            ]:
                static_author_page = Path(f"authors/{author_id}/index.html").read_text(encoding="utf-8")
                for book_id in preserved_ids:
                    assert f"texts/{book_id}/" in static_author_page, (author_id, book_id)

            for book_id, source_suffix, date in [
                ("mx-marx-72fc4a449f", "letter-18760504.htm", "1876年5月4日"),
                ("mx-marx-6ada1c8b56", "letter-18761021.htm", "1876年10月21日"),
                ("mx-engels-1e0fdedec5", "engels-1890-8-5.htm", None),
                ("mx-engels-7a4e965cae", "engels-1890-10-27.htm", "1890年10月27日"),
            ]:
                book = books[book_id]
                assert book["sourceUrl"].endswith(source_suffix), (book_id, book["sourceUrl"])
                section_path = Path(book["sectionPath"]) / f"{book['sections'][0]['id']}.json"
                body = json.loads(section_path.read_text(encoding="utf-8"))["html"]
                if date:
                    assert date in body, (book_id, date)

            print("static Lenin author page is consolidated; both editions retain SEO pages: PASS")
            print("all howto/MIA sections and separate letter/edition search routes remain: PASS")

            browser.close()


if __name__ == "__main__":
    main()
