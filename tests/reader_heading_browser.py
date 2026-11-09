"""Browser regressions for split chapter headings and title font selection."""

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from reader_routes import static_server


ROOT = Path(__file__).resolve().parents[1]
CASES = [
    ("zuopai-text", "section-009", "二 布尔什维克成功的基本条件之一", 2),
    ("zuopai-text", "section-010", "三 布尔什维主义历史的几个主要阶段", 2),
    ("zuopai-text", "section-013", "五 德国“左派”共产党人。领袖、政党、阶级、群众间的相互关系", 3),
    ("zuopai-text", "section-014", "六 革命家应当不应当在反动工会里做工作？", 2),
    ("zuopai-text", "section-018", "十 几点结论", 2),
    ("zuopai-text", "section-019", "二 德国的共产党人和独立党人", 2),
    ("zuopai-text", "section-021", "四 由正确的前提作出的错误结论", 2),
    ("civil-war", "section-008", "附录 一", 2),
]


def wait_reader(page, mode="desktop"):
    content = "#desktop-content" if mode == "desktop" else "#mobile-content"
    title = "#section-title" if mode == "desktop" else "#mobile-section-title"
    page.wait_for_function(
        "selector => { const node = document.querySelector(selector); "
        "return node && node.getAttribute('aria-busy') === 'false' && node.firstElementChild; }",
        arg=content,
        timeout=20000,
    )
    return page.locator(content), page.locator(title)


def assert_duplicate_render(page, mode, title_text, segment_count):
    content, title = wait_reader(page, mode)
    assert title.inner_text() == title_text
    assert title.is_visible(), "the generated chapter title remains visible"
    segments = content.locator(".duplicate-chapter-title-segment")
    assert segments.count() == segment_count
    for segment in segments.all():
        assert segment.get_attribute("aria-hidden") == "true"
        assert not segment.is_visible()
        source_id = segment.get_attribute("id")
        if source_id:
            assert content.locator(f"#{source_id}").count() == 1, "source heading IDs stay in the DOM"
    return content, title


def platform_fonts(page, selector):
    session = page.context.new_cdp_session(page)
    session.send("DOM.enable")
    session.send("CSS.enable")
    root = session.send("DOM.getDocument")["root"]["nodeId"]
    node = session.send("DOM.querySelector", {"nodeId": root, "selector": selector})["nodeId"]
    return session.send("CSS.getPlatformFontsForNode", {"nodeId": node})["fonts"]


def main():
    report_dir = Path("/workspace/reports/zuoren-heading-font-review")
    report_dir.mkdir(parents=True, exist_ok=True)
    with static_server() as origin, sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path="/usr/bin/chromium",
            args=["--no-sandbox", "--disable-cache"],
        )
        try:
            context = browser.new_context(viewport={"width": 1365, "height": 900}, color_scheme="light")
            page = context.new_page()
            page.goto(f"{origin}/?book=zuopai-text&section=section-009", wait_until="domcontentloaded")
            content, title = assert_duplicate_render(page, "desktop", CASES[0][2], 2)
            source = json.loads((ROOT / "books/zuopai-text/sections/section-009.json").read_text(encoding="utf-8"))
            expected_first_paragraph = page.evaluate(
                "html => new DOMParser().parseFromString(html, 'text/html').querySelector('p').textContent",
                source["html"],
            )
            assert content.locator("p").first.inner_text() == expected_first_paragraph
            assert content.locator("#h-13").count() == 1
            assert content.locator("#h-14").count() == 1
            assert "布尔什维克成功的 基本条件之一" in content.evaluate("element => element.textContent")

            font_result = page.evaluate(
                "async () => { await document.fonts.load('700 1rem \"Source Han Serif SC Web\"', '二布尔什维克成功的基本条件之一'); "
                "await document.fonts.ready; const e=document.querySelector('#section-title'); const s=getComputedStyle(e); "
                "return {family:s.fontFamily,weight:s.fontWeight,synthesis:s.fontSynthesis,loaded:document.fonts.check('700 1rem \"Source Han Serif SC Web\"')}; }"
            )
            assert font_result["family"].startswith('"Source Han Serif SC Web"'), font_result
            assert font_result["weight"] == "700" and font_result["synthesis"] == "none", font_result
            assert font_result["loaded"] is True, font_result
            font_faces = platform_fonts(page, "#section-title")
            assert any("Source Han Serif" in item["familyName"] for item in font_faces), font_faces
            page.screenshot(path=str(report_dir / "desktop-split-heading.png"))

            # The body and storage position survive normal chapter navigation and reopening.
            page.locator("#next-button").click()
            page.wait_for_function("new URL(location.href).searchParams.get('section') === 'section-010'")
            assert_duplicate_render(page, "desktop", CASES[1][2], 2)
            page.wait_for_function(
                "JSON.parse(localStorage.getItem('reading-desk:progress:v1:zuopai-text') || 'null')?.sectionId === 'section-010'"
            )
            page.locator("#back-button").click()
            page.wait_for_function("document.querySelector('#reader').classList.contains('is-hidden')")
            card = page.locator("#book-list article.book-card").filter(has_text="共产主义运动中的“左派”幼稚病")
            assert card.count() == 1
            card.locator(".open-button").click()
            page.wait_for_function("new URL(location.href).searchParams.get('section') === 'section-010'")
            assert_duplicate_render(page, "desktop", CASES[1][2], 2)

            # Check every exact-match result from the corpus scan, plus wrappers in civil-war.
            for book_id, section_id, expected_title, count in CASES:
                page.goto(f"{origin}/?book={book_id}&section={section_id}", wait_until="domcontentloaded")
                assert_duplicate_render(page, "desktop", expected_title, count)

            # A similar but incomplete title stays visible in both places.
            page.goto(f"{origin}/?book=zuopai-text&section=section-008", wait_until="domcontentloaded")
            partial_content, partial_title = wait_reader(page)
            assert partial_title.is_visible()
            assert partial_content.locator(".duplicate-chapter-title-segment").count() == 0
            partial_heading = partial_content.locator("h1,h2,h3,h4").first
            assert partial_heading.is_visible()
            assert "在什么意义上可以说" in partial_heading.inner_text()

            # A repeated title after an opening paragraph is not treated as a chapter title.
            fixture = json.loads((ROOT / "books/zuopai-text/sections/section-009.json").read_text(encoding="utf-8"))
            fixture["html"] = '<p id="opening">正文开头。</p><h2 id="fixture-number">二</h2><h4 id="fixture-title">布尔什维克成功的 基本条件之一</h4><p>正文保留。</p>'
            page.route("**/zuopai-text/sections/section-009.json", lambda route: route.fulfill(
                status=200, content_type="application/json", body=json.dumps(fixture, ensure_ascii=False)
            ))
            page.goto(f"{origin}/?book=zuopai-text&section=section-009", wait_until="domcontentloaded")
            body_content, body_title = wait_reader(page)
            assert body_title.is_visible()
            assert body_content.locator(".duplicate-chapter-title-segment").count() == 0
            assert body_content.locator("#fixture-number").is_visible()
            assert body_content.locator("#fixture-title").is_visible()
            assert body_content.locator("#opening").inner_text() == "正文开头。"
            page.unroute("**/zuopai-text/sections/section-009.json")

            # Existing inline and external footnotes continue to work.
            page.goto(f"{origin}/?book=imperialism&section=section-003", wait_until="domcontentloaded")
            notes_content, _ = wait_reader(page)
            triggers = notes_content.locator("button.footnote-trigger")
            assert triggers.count() >= 1
            triggers.first.click()
            assert page.locator(".footnote-popover").is_visible()
            page.keyboard.press("Escape")
            assert not page.locator(".footnote-popover").is_visible()

            # Mobile layout and dark theme retain the same single visible title.
            mobile = browser.new_context(viewport={"width": 390, "height": 844}, color_scheme="light")
            phone = mobile.new_page()
            phone.goto(f"{origin}/?book=zuopai-text&section=section-009", wait_until="domcontentloaded")
            mobile_content, mobile_title = assert_duplicate_render(phone, "mobile", CASES[0][2], 2)
            phone.evaluate(
                "async () => { await document.fonts.load('700 1.15rem \"Source Han Serif SC Web\"', '二布尔什维克成功的基本条件之一'); await document.fonts.ready; }"
            )
            mobile_font_faces = platform_fonts(phone, "#mobile-section-title")
            assert any("Source Han Serif" in item["familyName"] for item in mobile_font_faces), mobile_font_faces
            phone.locator("#mobile-reading-viewport").click(position={"x": 12, "y": 200})
            phone.locator(".mobile-font-settings > summary").click()
            phone.locator(".mobile-font-settings [data-theme-choice='dark']").click()
            assert phone.evaluate("document.documentElement.dataset.theme") == "dark"
            assert mobile_title.is_visible() and mobile_content.locator(".duplicate-chapter-title-segment").count() == 2
            assert phone.evaluate("document.documentElement.scrollWidth <= innerWidth")
            phone.locator(".mobile-font-settings > summary").click()
            phone.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")
            phone.screenshot(path=str(report_dir / "mobile-dark-split-heading.png"))
            phone.set_viewport_size({"width": 320, "height": 568})
            assert phone.evaluate("document.documentElement.scrollWidth <= innerWidth")
            mobile.close()

            # If both bundled web font files are blocked, system CJK serif fallback still renders the heading.
            fallback = browser.new_context(viewport={"width": 1280, "height": 800})
            fallback.route("**/fonts/*", lambda route: route.abort())
            fallback_page = fallback.new_page()
            fallback_page.goto(f"{origin}/?book=zuopai-text&section=section-009", wait_until="domcontentloaded")
            _, fallback_title = assert_duplicate_render(fallback_page, "desktop", CASES[0][2], 2)
            fallback_font_faces = platform_fonts(fallback_page, "#section-title")
            assert fallback_font_faces, "a system fallback font renders the heading"
            assert not any("Source Han Serif" in item["familyName"] or "Shelf Title Serif" in item["familyName"] for item in fallback_font_faces), fallback_font_faces
            assert fallback_title.is_visible()
            fallback.close()

            print("split-title browser, font, theme, mobile, notes, and progress checks: PASS")
            context.close()
        finally:
            browser.close()


if __name__ == "__main__":
    main()
