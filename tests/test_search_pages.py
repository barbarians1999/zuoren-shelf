"""Static discovery-page generator checks; uses a tiny isolated source tree."""

import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import generate_search_pages as search_pages  # noqa: E402


class SearchPageGenerationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.source = self.root / "source"
        self.output = self.root / "output"
        (self.source / "sections").mkdir(parents=True)
        self.base_url = "https://example.test/preview-shelf/"
        self.book_index_path = self.source / "book-index.json"
        self.data = {
            "books": [
                {
                    "id": "demo-book",
                    "title": "示例书目",
                    "author": "示例作者",
                    "format": "阅读副本",
                    "note": "原文排版说明",
                    "type": "text",
                    "sectionPath": "sections",
                    "sections": [
                        {"id": "part-1", "title": "第一篇：正文入口"},
                        {"id": "index", "title": "目录页", "readerHidden": True},
                        {"id": "part-2", "title": "第二篇：继续阅读"},
                        {"id": "empty-heading", "title": "只有标题的空篇目"},
                        {"id": "part-2-copy", "title": "第二篇：重复副本"},
                    ],
                },
                {
                    "id": "empty-scan",
                    "title": "扫描版示例",
                    "author": "编者",
                    "type": "scan",
                    "sections": [],
                    "pageCount": 3,
                },
                {
                    "id": "hidden-author-duplicate",
                    "title": "作者目录隐藏的重复版本",
                    "authorOnly": True,
                    "type": "text",
                    "sectionPath": "sections",
                    "sections": [{"id": "hidden-entry", "title": "隐藏版本正文"}],
                },
            ],
            "authorIndex": [
                {
                    "id": "writer",
                    "name": "示例作者",
                    "featuredWorks": [
                        {
                            "title": "作者作品标题",
                            "bookId": "demo-book",
                            "sectionId": "part-1",
                            "year": "1930",
                        },
                        {"title": "外部来源作品", "url": "https://example.org/source"},
                    ],
                }
            ],
        }
        self._write_index()
        self._write_section("part-1", '<p>第一篇的真实正文内容。</p><img src="books/demo-book/assets/example.jpg" alt="插图">')
        self._write_section("index", "不应进入搜索页的纯目录内容。")
        self._write_section("part-2", "第二篇的真实正文内容。")
        self._write_section("empty-heading", "<h1>只有标题的空篇目</h1>")
        self._write_section("part-2-copy", "第二篇的真实正文内容。")
        self._write_section("hidden-entry", "隐藏版本的正文不应进入公开目录。")

    def tearDown(self):
        self.temp_dir.cleanup()

    def _write_index(self):
        self.book_index_path.write_text(json.dumps(self.data, ensure_ascii=False), encoding="utf-8")

    def _write_section(self, section_id, body):
        (self.source / "sections" / f"{section_id}.json").write_text(
            json.dumps({"id": section_id, "title": section_id, "html": body}, ensure_ascii=False),
            encoding="utf-8",
        )

    def test_pages_are_canonical_linked_and_use_the_project_subpath(self):
        counts = search_pages.build(self.source, self.output, self.base_url)
        self.assertEqual(counts, {"books": 2, "authors": 1, "articles": 2, "sitemap_urls": 7, "generated_files": 7})

        article_path = self.output / "texts/demo-book/part-1/index.html"
        article = article_path.read_text(encoding="utf-8")
        self.assertIn('<html lang="zh-CN">', article)
        self.assertIn("第一篇：正文入口", article)
        self.assertIn("第一篇的真实正文内容。", article)
        self.assertIn('src="/preview-shelf/books/demo-book/assets/example.jpg"', article)
        self.assertIn('rel="canonical" href="https://example.test/preview-shelf/texts/demo-book/part-1/"', article)
        self.assertIn('href="https://example.test/preview-shelf/?book=demo-book&amp;section=part-1"', article)

        book_page = (self.output / "books/demo-book/index.html").read_text(encoding="utf-8")
        self.assertIn("篇目目录（2 篇）", book_page)
        self.assertIn('href="https://example.test/preview-shelf/texts/demo-book/part-2/"', book_page)
        self.assertNotIn("part-2-copy", book_page)
        self.assertNotIn("empty-heading", book_page)
        self.assertFalse((self.output / "texts/demo-book/part-2-copy/index.html").exists())
        self.assertFalse((self.output / "texts/demo-book/empty-heading/index.html").exists())
        self.assertFalse((self.output / "books/hidden-author-duplicate/index.html").exists())
        catalog_page = (self.output / "catalog/index.html").read_text(encoding="utf-8")
        self.assertNotIn("作者目录隐藏的重复版本", catalog_page)
        author_page = (self.output / "authors/writer/index.html").read_text(encoding="utf-8")
        self.assertIn("作者作品标题", author_page)
        self.assertIn("外部来源作品", author_page)

        sitemap = ET.parse(self.output / "sitemap.xml").getroot()
        urls = [node.text for node in sitemap.findall(f"{{{search_pages.SITEMAP_NS}}}url/{{{search_pages.SITEMAP_NS}}}loc")]
        self.assertEqual(len(urls), 7)
        self.assertIn(self.base_url + "texts/demo-book/part-1/", urls)
        self.assertNotIn(self.base_url + "texts/demo-book/part-2-copy/", urls)
        self.assertNotIn(self.base_url + "texts/demo-book/empty-heading/", urls)
        self.assertNotIn(self.base_url + "texts/demo-book/index/", urls)
        self.assertIn(self.base_url + "books/empty-scan/", urls)

    def test_rerun_removes_only_manifest_pages_that_became_stale(self):
        search_pages.build(self.source, self.output, self.base_url)
        unrelated = self.output / "keep-me"
        unrelated.mkdir(parents=True)
        self.data["books"][0]["sections"] = [
            section for section in self.data["books"][0]["sections"]
            if section["id"] not in {"part-2", "part-2-copy"}
        ]
        self._write_index()
        counts = search_pages.build(self.source, self.output, self.base_url)
        self.assertEqual(counts["articles"], 1)
        self.assertFalse((self.output / "texts/demo-book/part-2/index.html").exists())
        self.assertTrue(unrelated.is_dir())


if __name__ == "__main__":
    unittest.main()
