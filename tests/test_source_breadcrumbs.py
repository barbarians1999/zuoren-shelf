import unittest

from source_breadcrumbs import find_breadcrumb, iter_sections
from source_pagination import nav_groups


def section_html(book_id, section_id):
    for book, section, path, record in iter_sections():
        if book["id"] == book_id and section["id"] == section_id:
            return record["html"], record
    raise AssertionError(f"missing section {book_id}/{section_id}")


class SourceBreadcrumbTests(unittest.TestCase):
    def test_navigation_prefix_removed_from_jewish_question_but_body_and_source_metadata_remain(self):
        content, record = section_html("mx-marx-jewish-question", "section-001")
        self.assertIsNone(find_breadcrumb(content))
        self.assertNotIn("中文马克思主义文库", content[:300])
        self.assertIn("德国的犹太人渴望解放", content)
        self.assertIn("——编者注", content)
        self.assertEqual(record["sourceUrl"], "https://www.marxists.org/chinese/marx-engels2/01/02.htm")

    def test_navigation_prefix_removed_from_other_work_types(self):
        cases = [
            ("marx-capital-1", "section-008", "商品首先是一个外界的对象"),
            ("lenin-two-tactics", "section-002", "当前革命时期的日程"),
            ("mx-mao-22d9034b3e", "section-001", "修身"),
        ]
        for book_id, section_id, expected_text in cases:
            with self.subTest(book_id=book_id, section_id=section_id):
                content, _ = section_html(book_id, section_id)
                self.assertIsNone(find_breadcrumb(content))
                self.assertIn(expected_text, content)

    def test_related_edition_and_translation_links_are_kept(self):
        related, _ = section_html("mx-marx-7724075762", "section-001")
        other_translation, _ = section_html("mx-stalin-b53d61f111", "section-001")
        edition_note, _ = section_html("mx-mao-3fa6182fc7", "section-001")
        self.assertIn("相关链接：<a", related)
        self.assertIn("恩格斯</a>", related)
        self.assertIn("另一译本：<a", other_translation)
        self.assertIn("无线电广播（1941年7月3日）</a>", other_translation)
        self.assertIn("毛选二卷删改版：<a", edition_note)

    def test_no_pure_source_breadcrumbs_remain_in_catalog(self):
        self.assertEqual(sum(find_breadcrumb(record.get("html", "")) is not None
                             for _, _, _, record in iter_sections()), 0)

    def test_no_source_pagination_bars_remain_in_catalog(self):
        self.assertEqual(sum(len(nav_groups(record.get("html", "")))
                             for _, _, _, record in iter_sections()), 0)


if __name__ == "__main__":
    unittest.main()
