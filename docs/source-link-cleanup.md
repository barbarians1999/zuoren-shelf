# Imported source navigation cleanup

This cleanup removes two kinds of external Marxists.org navigation copied into section HTML:

1. Pure breadcrumbs before the first `<hr>`: every link points to an `index.htm` index, and text outside links is only arrow/separator punctuation. This removed 1,096 blocks across 16 books.
2. Footer pagination bars: an adjacent group of at least two links labeled `上一篇` / `下一篇` or `上一页` / `下一页`, optionally with `回目录` / `目录`, all pointing to Marxists.org. This removed 1,091 bars across 13 books. The associated link count was 3,245: `上一篇` 81, `下一篇` 83, `上一页` 995, `下一页` 995, `回目录` 91, and `目录` 1,000.

The two source links on 《论犹太人问题》 pointed to the previous source page (`.../01/01.htm`) and next source page (`.../01/03.htm`); `回目录` pointed to the source collection index (`.../01/index.htm`). These links sat in a footer bar after the text and before the editor notes. The local reader already has its own section navigation, so the imported bar was removed. The author’s article, editor notes, source metadata, and in-text references remain intact.

Only exact source-navigation link groups are removed. Other links labeled `相关链接`, `另一译本`, `译本`, edition notes, and prose references remain. The site-generated TOC and previous/next section controls are unchanged; a browser check confirms the 998-entry Mao anthology TOC and next-section button still work.

## Repeatable checks

```bash
python3 tests/source_breadcrumbs.py
python3 tests/source_pagination.py
python3 -m unittest discover -s tests -p 'test_source_breadcrumbs.py' -v
python3 tests/source_breadcrumbs_browser.py
python3 tests/reader_routes.py
```

Use `--apply` with either scanner only when new matching blocks should be removed. Either scanner accepts `--report <path>` to save a pre-cleanup inventory with section identities and matching source URLs.
