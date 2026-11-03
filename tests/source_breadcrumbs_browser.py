"""Browser smoke checks for cleaned source breadcrumbs and retained links."""

from playwright.sync_api import sync_playwright

from reader_routes import static_server


CASES = [
    ("mx-marx-jewish-question", "section-001", "论犹太人问题", None),
    ("mx-marx-7724075762", "section-001", "德意志意识形态（节选）", "恩格斯"),
    ("mx-stalin-b53d61f111", "section-001", "广播演说", "无线电广播（1941年7月3日）"),
    ("mx-mao-3fa6182fc7", "section-001", "〔未删节本〕抗日民族战争与抗日民族统一战线发展的新阶段（一九三八年十月十二日至十四日在中共扩大的六中全会的报告）", "中国共产党在民族战争中的地位"),
    ("marx-capital-1", "section-008", "资本论第一卷", None),
    ("mx-mao-22d9034b3e", "section-001", "1968年武汉版《毛泽东思想万岁》（文字版）", None),
]


def main():
    with static_server() as origin:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                executable_path="/usr/bin/chromium",
                args=["--no-sandbox", "--disable-cache"],
            )
            page = browser.new_page(viewport={"width": 1365, "height": 900})
            for book_id, section_id, book_title, retained_link_text in CASES:
                page.goto(
                    f"{origin}/?book={book_id}&section={section_id}",
                    wait_until="domcontentloaded",
                )
                page.wait_for_function(
                    "() => { const e = document.querySelector('#desktop-content'); "
                    "return e && e.firstElementChild && !e.firstElementChild.classList.contains('loading-copy'); }",
                    timeout=15000,
                )
                assert page.locator("#book-title").inner_text() == book_title
                content = page.locator("#desktop-content")
                if retained_link_text:
                    assert content.get_by_role("link", name=retained_link_text, exact=False).count() > 0
                if book_id == "mx-marx-jewish-question":
                    assert content.locator("a").count() == 0
                    assert page.locator("#prev-button").is_disabled()
                    assert page.locator("#next-button").is_disabled()
                if book_id == "marx-capital-1":
                    labels = content.locator("a").all_inner_texts()
                    assert not any(label.strip() in {"上一篇", "下一篇", "回目录"} for label in labels)
                    page.locator("#next-button").click()
                    page.wait_for_function("new URL(location.href).searchParams.get('section') === 'section-009'")
                    assert page.locator("#section-title").inner_text() == "第二章 交 换 过 程"
                if book_id == "mx-mao-22d9034b3e":
                    assert page.locator("#desktop-toc .toc-link").count() == 998
                    page.locator("#next-button").click()
                    page.wait_for_function("new URL(location.href).searchParams.get('section') === 'section-002'")
                    assert page.locator("#section-title").inner_text() == "读《明耻篇》后题词"
                print(f"rendered cleanup and retained link: PASS — {book_title}")
            browser.close()


if __name__ == "__main__":
    main()
