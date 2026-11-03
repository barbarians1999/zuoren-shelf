"""Check author-page manifesto entries and retained direct routes."""

from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import sync_playwright

from reader_routes import static_server


HIDDEN_EDITION_IDS = {"mx-marx-manifesto-1920", "mx-marx-8b258427cf"}
MANIFESTO_ID = "manifesto"


def route_params(url):
    return {key: values[-1] for key, values in parse_qs(urlsplit(url).query).items()}


def main():
    with static_server() as origin:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                executable_path="/usr/bin/chromium",
                args=["--no-sandbox", "--disable-cache"],
            )
            page = browser.new_page(viewport={"width": 1365, "height": 900})
            for author_id in ("marx", "engels"):
                page.goto(f"{origin}/?author={author_id}", wait_until="domcontentloaded")
                page.wait_for_selector("#author-featured-list a")
                links = page.locator("#author-featured-list a").evaluate_all(
                    "nodes => nodes.map(a => ({text: a.innerText, href: a.getAttribute('href')}))"
                )
                ids = {route_params(link["href"]).get("book") for link in links}
                assert ids & HIDDEN_EDITION_IDS == set(), (author_id, links)
                manifesto_rows = [
                    link for link in links
                    if route_params(link["href"]).get("book") == MANIFESTO_ID
                ]
                assert len(manifesto_rows) == 1, (author_id, manifesto_rows)
                assert manifesto_rows[0]["text"].strip() == "共产党宣言"
                assert any("《共产党宣言》传入年表" == link["text"].strip() for link in links)
                if author_id == "engels":
                    assert any("一八八八年英文版序言" in link["text"] for link in links)
                print(f"{author_id} author page keeps only the 1848 manifesto entry: PASS")

            for book_id, title, section_title in [
                ("mx-marx-manifesto-1920", "共产党宣言（陈望道译本）", "第一章 有产者及无产者"),
                ("mx-marx-8b258427cf", "繁体版《共產黨宣言》", "第一章 有產者及無產者"),
            ]:
                page.goto(
                    f"{origin}/?author=engels&book={book_id}&section=section-002",
                    wait_until="domcontentloaded",
                )
                page.wait_for_function(
                    "() => { const e = document.querySelector('#reader'); "
                    "return e && !e.classList.contains('is-hidden'); }",
                    timeout=15000,
                )
                assert page.locator("#book-title").inner_text() == title
                assert page.locator("#section-title").inner_text() == section_title
                assert route_params(page.url).get("book") == book_id
                print(f"legacy direct route remains readable: PASS — {title}")
            browser.close()


if __name__ == "__main__":
    main()
