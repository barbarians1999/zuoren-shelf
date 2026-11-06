"""Browser regression checks for reader links; requires Playwright and Chromium."""

import json
import sys
import time
from contextlib import contextmanager
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from threading import Thread

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


class ShelfHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def translate_path(self, path):
        path = urlsplit(path).path
        if path == "/shelf":
            path = "/"
        elif path.startswith("/shelf/"):
            path = path[len("/shelf"):]
        return super().translate_path(path)

    def log_message(self, _format, *_args):
        pass


class QuietThreadingHTTPServer(ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        if isinstance(sys.exc_info()[1], (BrokenPipeError, ConnectionResetError)):
            return
        super().handle_error(request, client_address)


@contextmanager
def static_server():
    server = QuietThreadingHTTPServer(("127.0.0.1", 0), ShelfHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def verify_catalog_identity():
    data = json.loads((ROOT / "book-index.json").read_text(encoding="utf-8"))
    ids = [book["id"] for book in data["books"]]
    assert len(ids) == len(set(ids)), "bookId values must be unique"
    sections_checked = 0
    for book in data["books"]:
        section_ids = [section["id"] for section in book.get("sections", [])]
        assert all(section_ids), f"missing section ID in {book['id']}"
        assert len(section_ids) == len(set(section_ids)), f"duplicate section ID in {book['id']}"
        section_path = ROOT / book.get("sectionPath", "")
        for section_id in section_ids:
            assert (section_path / f"{section_id}.json").is_file(), f"missing content: {book['id']} / {section_id}"
            sections_checked += 1
    print(f"catalog identity: PASS ({len(ids)} books, {sections_checked} sections; IDs unique per book and files present)")


def new_page(browser, viewport=None, clipboard=False, origin=None):
    viewport = viewport or {"width": 1365, "height": 900}
    context = browser.new_context(viewport=viewport)
    if clipboard:
        context.grant_permissions(["clipboard-read", "clipboard-write"], origin=origin)
    return context, context.new_page()


def assert_reader(page, title):
    assert page.locator("#reader").is_visible()
    assert page.locator("#book-title").inner_text() == title


def run():
    verify_catalog_identity()
    with static_server() as origin:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, executable_path="/usr/bin/chromium", args=["--no-sandbox", "--disable-cache"])

            # Search -> ordinary book -> copy -> browser back/forward.
            context, page = new_page(browser, clipboard=True, origin=origin)
            page.goto(origin + "/", wait_until="networkidle")
            page.locator("#book-search").fill("共产党宣言")
            page.locator("#book-list .open-button").first.click()
            page.wait_for_selector("#desktop-content h1, #desktop-content h2, #desktop-content p")
            assert_reader(page, "共产党宣言")
            params = dict(pair.split("=", 1) for pair in urlsplit(page.url).query.split("&"))
            assert params["book"] == "manifesto" and params["section"] == "section-001"
            page.locator("#desktop-share-button").click()
            copied = page.evaluate("navigator.clipboard.readText()")
            assert copied == page.url, (copied, page.url)
            page.go_back(wait_until="domcontentloaded")
            assert page.locator("#reader").get_attribute("class").find("is-hidden") >= 0
            page.go_forward(wait_until="domcontentloaded")
            assert_reader(page, "共产党宣言")
            print("home search, reader route, clipboard copy, browser back/forward: PASS")
            context.close()

            # The original single-volume shelf card and an author-page single-volume entry each keep stable routes.
            context, page = new_page(browser, clipboard=True, origin=origin)
            page.goto(origin + "/", wait_until="networkidle")
            page.locator("#book-list .book-card").filter(has_text="怎么办").locator(".open-button").click()
            assert_reader(page, "怎么办")
            assert "book=howto" in page.url and "section=part-01" in page.url
            page.locator("#desktop-share-button").click()
            shared_url = page.evaluate("navigator.clipboard.readText()")
            assert shared_url == page.url
            page.go_back(wait_until="domcontentloaded")
            assert page.locator("#shelf").is_visible()
            page.go_forward(wait_until="domcontentloaded")
            assert_reader(page, "怎么办")
            context.close()
            context, page = new_page(browser, clipboard=True, origin=origin)
            page.goto(shared_url, wait_until="networkidle")
            assert_reader(page, "怎么办")
            page.reload(wait_until="networkidle")
            assert_reader(page, "怎么办")
            context.close()

            context, page = new_page(browser, clipboard=True, origin=origin)
            page.goto(origin + "/?author=marx", wait_until="networkidle")
            assert page.locator('link[rel="canonical"]').get_attribute("href") == f"{origin}/authors/marx/"
            assert "马克思" in page.title()
            page.locator("#author-featured-list .featured-work a").filter(has_text="资本论第一卷").first.click()
            page.wait_for_function("new URL(location.href).searchParams.get('book') === 'marx-capital-1'")
            assert_reader(page, "资本论第一卷")
            assert "section=section-008" in page.url
            page.locator("#desktop-share-button").click()
            author_book_url = page.evaluate("navigator.clipboard.readText()")
            assert author_book_url == page.url
            context.close()
            context, page = new_page(browser)
            page.goto(author_book_url, wait_until="networkidle")
            assert_reader(page, "资本论第一卷")
            assert "section=" in page.url
            print("original single-volume home card and Marx author-page book link: direct URL, reload, and history PASS")
            context.close()

            # User-specified legacy single books route from their original shelf cards, not only author links.
            for book_id, title, section_id, section_title in [
                ("history", "联共（布）党史简明教程", "front", "前言与目录"),
                ("obtain-authority", "获得权威——上海地下党群众工作的历史经验与启示", "section-002", "导 论"),
            ]:
                context, page = new_page(browser, clipboard=True, origin=origin)
                page.goto(origin + "/", wait_until="networkidle")
                page.locator("#book-list .book-card").filter(has_text=title).locator(".open-button").click()
                assert_reader(page, title)
                assert f"book={book_id}" in page.url and f"section={section_id}" in page.url, page.url
                assert page.locator("#section-title").inner_text() == section_title
                expected_canonical = f"{origin}/texts/{book_id}/{section_id}/"
                assert page.locator('link[rel="canonical"]').get_attribute("href") == expected_canonical
                assert section_title in page.title() and "左人书架" in page.title()
                assert section_title in page.locator('meta[name="description"]').get_attribute("content")
                assert page.locator("#book-list .open-button").first.get_attribute("href").startswith(f"{origin}/books/")
                page.locator("#desktop-share-button").click()
                copied_url = page.evaluate("navigator.clipboard.readText()")
                assert copied_url == page.url
                page.go_back(wait_until="domcontentloaded")
                assert page.locator("#shelf").is_visible()
                page.go_forward(wait_until="domcontentloaded")
                assert_reader(page, title)
                new_tab = context.new_page()
                new_tab.goto(copied_url, wait_until="networkidle")
                assert_reader(new_tab, title)
                assert new_tab.locator("#section-title").inner_text() == section_title
                new_tab.reload(wait_until="networkidle")
                assert_reader(new_tab, title)
                context.close()
            print("specified legacy books — history and 获得权威: original cards, copied URLs, new tabs, refresh, back/forward PASS")

            # Direct link, hard refresh, section navigation, and same-tab position storage.
            context, page = new_page(browser)
            link = origin + "/?book=history&section=section-007"
            page.goto(link, wait_until="networkidle")
            assert_reader(page, "联共（布）党史简明教程")
            title = "第一章 为在俄国建立社会民主工党而斗争(1883－1901年)"
            assert not page.locator("#section-title").is_visible()
            assert page.locator("#desktop-content h2.chapter-heading").first.inner_text() == title
            assert page.locator("#desktop-content > p").first.inner_text().startswith("一、俄国农奴制度")
            toc_target = page.locator("#desktop-toc .toc-link").filter(has_text="二、俄国民粹主义")
            assert toc_target.get_attribute("href") == f"{origin}/texts/history/section-008/"
            page.evaluate("window.scrollTo(0, 450)")
            page.wait_for_timeout(450)
            position_keys = page.evaluate("Object.keys(sessionStorage).filter(k => k.startsWith('reading-desk:route-position:v1:'))")
            assert position_keys, "reader position should be stored in this tab's sessionStorage"
            assert "position" not in page.url and "scroll" not in page.url
            page.reload(wait_until="networkidle")
            assert_reader(page, "联共（布）党史简明教程")
            assert page.evaluate("window.scrollY") > 0
            page.locator("#desktop-toc .toc-link").filter(has_text="二、俄国民粹主义").click()
            assert page.locator("#section-title").inner_text().startswith("二、俄国民粹主义")
            assert "section=section-008" in page.url
            print("direct URL, refresh, session-only position, chapter query update, duplicate-title rendering: PASS")
            context.close()

            # Footnote superscripts are excluded only from comparison, not from the rendered body.
            context, page = new_page(browser)
            page.goto(origin + "/?book=history&section=section-002", wait_until="networkidle")
            assert not page.locator("#section-title").is_visible()
            heading_text = page.locator("#desktop-content h2.chapter-heading").first.inner_text()
            assert heading_text.startswith("代序言") and "联共（布）党史简明教程" in heading_text
            context.close()

            # Multi-section anthology and a one-section work use existing IDs.
            context, page = new_page(browser, clipboard=True, origin=origin)
            page.goto(origin + "/?author=mao&book=mao-selected&section=section-023", wait_until="networkidle")
            assert_reader(page, "毛泽东选集（一至七卷）")
            page.locator("#desktop-toc .toc-link").filter(has_text="矛盾论").click()
            assert "section=section-024" in page.url
            page.locator("#desktop-share-button").click()
            assert page.evaluate("navigator.clipboard.readText()") == page.url
            context.close()
            context, page = new_page(browser)
            page.goto(origin + "/?book=manifesto&section=section-009", wait_until="networkidle")
            assert_reader(page, "共产党宣言")
            assert page.locator("#section-title").inner_text() == "共产党宣言"
            print("anthology section navigation and single-work direct link: PASS")
            context.close()

            # Explicitly marked pure tables of contents stay out of reading navigation; old links normalize forward.
            for book_id, hidden_id, expected_id, book_title in [
                ("german-ideology", "section-001", "section-002", "德意志意识形态"),
                ("lenin-selected", "section-002", "section-003", "列宁选集（一至四卷）"),
                ("stalin-trotsky-bukharin", "section-001", "section-002", "斯大林反对托洛茨基主义和布哈林主义的斗争"),
                ("stalin-era", "section-005", "section-006", "斯大林时代"),
                ("bloodfire", "section-003", "section-004", "血火铸丰碑"),
                ("bettelheim-industrial-organization", "section-003", "section-004", "中国的文化大革命与工业组织"),
                ("global-monopoly-text", "front", "section-002", "全球化时代垄断资本的矛盾运动"),
                ("mao-selected", "front", "section-002", "毛泽东选集（一至七卷）"),
                ("obtain-authority", "front", "section-002", "获得权威——上海地下党群众工作的历史经验与启示"),
                ("natural-dialectics", "front", "section-002", "自然辩证法"),
                ("luxun-text", "front", "section-002", "鲁迅——中国文化革命的巨人"),
                ("economic-accounting-ownership", "section-001", "section-002", "经济核算与所有制形式"),
                ("international-movement-course-vol1", "section-001", "section-002", "国际共产主义运动史讲义初稿·第一册"),
                ("route-dispute", "front", "route", "关于国际共产主义运动总路线的论战"),
            ]:
                context, page = new_page(browser)
                page.goto(origin + f"/?book={book_id}&section={hidden_id}", wait_until="networkidle")
                assert_reader(page, book_title)
                assert f"section={expected_id}" in page.url, page.url
                assert page.locator("#route-notice").is_visible()
                toc_titles = page.locator("#desktop-toc .toc-link").evaluate_all(
                    "nodes => nodes.map(node => node.textContent.replace(/^\\d+(?:\\.\\d+)*\\.\\s*/, ''))"
                )
                assert "目录" not in toc_titles, (book_id, toc_titles)
                page.reload(wait_until="networkidle")
                assert f"section={expected_id}" in page.url
                context.close()
            # Default opening and adjacent navigation skip hidden entries without changing section IDs.
            context, page = new_page(browser)
            page.goto(origin + "/", wait_until="networkidle")
            page.locator("#book-search").fill("德意志意识形态")
            page.locator("#book-list .open-button").first.click()
            assert_reader(page, "德意志意识形态")
            assert "section=section-002" in page.url
            context.close()
            context, page = new_page(browser)
            page.goto(origin + "/?book=stalin-era&section=section-004", wait_until="networkidle")
            page.locator("#next-button").click()
            assert "section=section-006" in page.url
            page.locator("#prev-button").click()
            assert "section=section-004" in page.url
            context.close()
            # Mixed sections with real text remain available even when their title says 目录.
            for book_id, section_id, section_title, body_marker in [
                ("jintui-text", "section-007", "进一步，退两步", "当持久的顽强"),
                ("class-struggles-france", "section-001", "1848年至1850年的法兰西阶级斗争", "革命的失败"),
            ]:
                context, page = new_page(browser)
                page.goto(origin + f"/?book={book_id}&section={section_id}", wait_until="networkidle")
                assert_reader(page, section_title)
                assert f"section={section_id}" in page.url
                toc_titles = page.locator("#desktop-toc .toc-link").evaluate_all(
                    "nodes => nodes.map(node => node.textContent.replace(/^\\d+(?:\\.\\d+)*\\.\\s*/, ''))"
                )
                assert "目录" in toc_titles
                assert body_marker in page.locator("#desktop-content").inner_text()
                context.close()
            print("pure directory pages hidden; defaults/navigation skip them; old URLs redirect; mixed substantive sections preserved: PASS")

            # Hiding the final section falls back to the preceding readable stable ID.
            context, page = new_page(browser)
            terminal_expected = {}
            def hide_terminal_section(route):
                response = route.fetch()
                data = response.json()
                manifesto = next(book for book in data["books"] if book["id"] == "manifesto")
                manifesto["sections"][-1]["readerHidden"] = True
                terminal_expected["id"] = manifesto["sections"][-2]["id"]
                route.fulfill(response=response, json=data)
            page.route("**/book-index.json", hide_terminal_section)
            page.goto(origin + "/?book=manifesto&section=section-020", wait_until="networkidle")
            assert_reader(page, "共产党宣言")
            assert f"section={terminal_expected['id']}" in page.url, page.url
            assert page.locator("#desktop-share-button").is_enabled()
            print("terminal hidden section URL falls back to previous readable section: PASS")
            context.close()

            # All-hidden data renders an explicit empty state with safe controls and a clean shelf exit.
            context, page = new_page(browser)
            page_errors = []
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            def hide_all_sections(route):
                response = route.fetch()
                data = response.json()
                manifesto = next(book for book in data["books"] if book["id"] == "manifesto")
                for section in manifesto["sections"]:
                    section["readerHidden"] = True
                route.fulfill(response=response, json=data)
            page.route("**/book-index.json", hide_all_sections)
            page.goto(origin + "/?book=manifesto&section=section-001", wait_until="networkidle")
            assert_reader(page, "共产党宣言")
            assert "本书当前没有可阅读的正文内容" in page.locator("#desktop-content").inner_text()
            assert page.locator("#desktop-share-button").is_disabled()
            assert page.locator("#prev-button").is_disabled() and page.locator("#next-button").is_disabled()
            params = dict(pair.split("=", 1) for pair in urlsplit(page.url).query.split("&") if pair)
            assert params.get("book") == "manifesto" and "section" not in params, page.url
            page.locator("#back-button").click()
            assert page.locator("#shelf").is_visible()
            assert "book" not in dict(pair.split("=", 1) for pair in urlsplit(page.url).query.split("&") if pair)
            page.locator("#book-search").fill("共产党宣言")
            page.locator("#book-list .open-button").first.click()
            assert_reader(page, "共产党宣言")
            params = dict(pair.split("=", 1) for pair in urlsplit(page.url).query.split("&") if pair)
            assert params.get("book") == "manifesto" and "section" not in params, page.url
            assert "本书当前没有可阅读的正文内容" in page.locator("#desktop-content").inner_text()
            page.locator("#back-button").click()
            assert page.locator("#shelf").is_visible()
            page.wait_for_load_state("networkidle")
            assert not page_errors, page_errors
            context.close()

            context, page = new_page(browser, viewport={"width": 390, "height": 844})
            page.route("**/book-index.json", hide_all_sections)
            page.goto(origin + "/?book=manifesto&section=section-001", wait_until="networkidle")
            assert "本书当前没有可阅读的正文内容" in page.locator("#mobile-content").inner_text()
            page.locator("#mobile-reading-viewport").click(position={"x": 150, "y": 80}, force=True)
            assert page.locator("#mobile-share-button").is_disabled()
            page.locator("#mobile-back-button").click()
            assert page.locator("#shelf").is_visible()
            page.wait_for_load_state("networkidle")
            print("all-hidden book empty state, disabled share/navigation, safe URL, desktop/mobile shelf exit: PASS")
            context.close()

            # Invalid identities degrade to the shelf with a visible message.
            context, page = new_page(browser)
            for bad_link, message in [
                ("/?book=does-not-exist&section=section-001", "书籍标识无效"),
                ("/?book=history&section=not-a-section", "章节标识无效"),
            ]:
                page.goto(origin + bad_link, wait_until="networkidle")
                assert not page.locator("#reader").is_visible()
                assert page.locator("#route-notice").is_visible()
                assert message in page.locator("#route-notice").inner_text()
                assert "book" not in dict(pair.split("=", 1) for pair in urlsplit(page.url).query.split("&") if pair)
            print("invalid book/chapter fallback: PASS")
            context.close()

            # Clipboard denial opens a selectable manual-copy fallback.
            context, page = new_page(browser)
            page.add_init_script("Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: () => Promise.reject(new Error('denied')) } });")
            page.goto(origin + "/?book=history&section=section-007", wait_until="networkidle")
            page.locator("#desktop-share-button").click()
            page.wait_for_function("document.querySelector('#share-dialog').open")
            value = page.locator("#share-url").input_value()
            selection = page.locator("#share-url").evaluate("e => [e.selectionStart, e.selectionEnd]")
            assert value == page.url and selection == [0, len(value)]
            print("clipboard rejection manual-copy selection: PASS")
            context.close()

            # Same-origin deployment beneath a path prefix keeps its prefix.
            context, page = new_page(browser, clipboard=True, origin=origin)
            page.goto(origin + "/shelf/?book=history&section=section-007", wait_until="networkidle")
            assert_reader(page, "联共（布）党史简明教程")
            page.locator("#desktop-share-button").click()
            copied = page.evaluate("navigator.clipboard.readText()")
            assert urlsplit(copied).path.startswith("/shelf/")
            assert "section=section-007" in copied
            assert urlsplit(page.locator('link[rel="canonical"]').get_attribute("href")).path == "/shelf/texts/history/section-007/"
            print("subpath deployment URL preservation: PASS")
            context.close()

            # A delayed old section response must not overwrite a later TOC selection.
            context, page = new_page(browser)
            def slow_section(route):
                time.sleep(0.55)
                route.continue_()
            page.route("**/sections/section-007.json", slow_section)
            page.goto(origin + "/?book=history&section=section-007", wait_until="domcontentloaded")
            page.wait_for_selector("#desktop-toc .toc-link[data-index='7']")
            page.locator("#desktop-toc .toc-link[data-index='7']").click()
            page.wait_for_function("document.querySelector('#section-title').textContent.startsWith('二、俄国民粹主义')")
            page.wait_for_timeout(650)
            assert page.locator("#section-title").inner_text().startswith("二、俄国民粹主义")
            print("delayed section response race: PASS")
            context.close()

            context, page = new_page(browser)
            page.route("**/sections/section-007.json", slow_section)
            page.goto(origin + "/?book=history&section=section-007", wait_until="domcontentloaded")
            page.wait_for_selector("#desktop-toc .toc-link[data-index='7']")
            page.locator("#back-button").click()
            page.locator("#book-search").fill("毛泽东选集")
            page.locator("#book-list .open-button").first.click()
            page.wait_for_function("document.querySelector('#book-title').textContent.includes('毛泽东选集')")
            page.wait_for_timeout(650)
            assert "毛泽东选集" in page.locator("#book-title").inner_text()
            assert page.locator("#section-title").inner_text() == "第一卷"
            assert "section=section-002" in page.url
            assert "作者与目录" not in page.locator("#desktop-toc").inner_text()
            assert "第一章 为在俄国建立社会民主工党" not in page.locator("#desktop-content").inner_text()
            print("delayed cross-book response race: PASS")
            context.close()

            # A route-local edit to the section payload proves paragraph promotion keeps IDs and content.
            context, page = new_page(browser)
            def fixture_index(route):
                response = route.fetch()
                data = response.json()
                history = next(book for book in data["books"] if book["id"] == "history")
                section = next(item for item in history["sections"] if item["id"] == "section-007")
                section["title"] = "第一章，测试标题"
                route.fulfill(response=response, json=data)
            page.route("**/sections/section-007.json", lambda route: route.fulfill(
                status=200, content_type="application/json",
                body=json.dumps({"html": '<p id="fixture-heading">第一章，测试标题</p><p>真实副标题段落</p>'})
            ))
            page.route("**/book-index.json", fixture_index)
            page.goto(origin + "/?book=history&section=section-007", wait_until="networkidle")
            assert not page.locator("#section-title").is_visible()
            assert page.locator("#desktop-content h2#fixture-heading").inner_text() == "第一章，测试标题"
            assert page.locator("#desktop-content > p").first.inner_text() == "真实副标题段落"
            print("render-only paragraph promotion preserves ID and following content: PASS")
            context.close()

            # Mobile reader gets the same route and title behavior; reveal controls before TOC.
            context, page = new_page(browser, viewport={"width": 390, "height": 844})
            page.goto(origin + "/?book=history&section=section-007", wait_until="networkidle")
            assert page.locator("#mobile-reader").is_visible()
            assert not page.locator("#mobile-section-title").is_visible()
            assert page.locator("#mobile-content h2.chapter-heading").first.inner_text() == title
            page.locator("#mobile-reading-viewport").click(position={"x": 150, "y": 80}, force=True)
            page.locator("#mobile-share-button").click()
            page.wait_for_function("document.querySelector('#share-dialog').open || !document.querySelector('#share-status').hidden")
            if page.locator("#share-dialog").is_visible():
                assert page.locator("#share-url").input_value() == page.url
                page.locator("#share-dialog button[type='submit']").click()
            else:
                assert "已复制" in page.locator("#share-status").inner_text()
            page.locator("#mobile-toc-toggle-button").click()
            page.locator("#mobile-toc .toc-link").filter(has_text="二、俄国民粹主义").click()
            assert page.locator("#mobile-section-title").inner_text().startswith("二、俄国民粹主义")
            print("mobile deduplication, share controls, and TOC navigation: PASS")
            context.close()

            browser.close()


if __name__ == "__main__":
    run()
