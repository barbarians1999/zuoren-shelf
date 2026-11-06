# 搜索收录入口

## 当前页面结构

书架继续使用原有 `?book={book.id}&section={section.id}` 阅读链接和交互阅读器。`scripts/generate_search_pages.py` 根据 `book-index.json` 与章节 JSON 生成可直接访问的静态页面：

- `books/{book.id}/`：书籍介绍、真实正文节选和完整篇目目录。
- `texts/{book.id}/{section.id}/`：章节标题、原始正文和回到阅读器的链接。
- `authors/{author.id}/`：作者作品目录。
- `catalog/`：从书架可见的书目与文章目录。
- `sitemap.xml`：主页、书目、作者和可读章节的规范 URL。

纯目录章节用现有 `readerHidden` 标记排除。没有正文的标题/页码入口和完全重复的正文不生成独立搜索页；作者目录遵循书架当前显示的版本去重规则。书籍 ID、章节 ID 和正文文件沿用已有清单，不重编号。章节页面保留源 JSON 中的正文 HTML，插图链接改为 GitHub Pages 项目站点路径。旧分享链接仍按原参数打开阅读器。

《共产主义运动中的“左派”幼稚病》的 15 条标题差异已逐项核对，其中 3 条索引标题依据正文标题更正；一条无法确认是印刷标题的描述性标签已记录在[标题校核说明](search-page-title-review.md)。

## 重新生成

更新书目或章节正文后，在仓库根目录运行：

```bash
python3 scripts/generate_search_pages.py
```

脚本不需要额外依赖。它写入清单标记的页面；再次运行会更新这些页面并清理已不在书目中的旧生成页面。脚本会拒绝覆盖未登记的同名文件。

可以用另一项目路径验证生成器：

```bash
python3 scripts/generate_search_pages.py \
  --base-url https://example.test/preview-shelf/ \
  --output-dir /tmp/zuoren-search-preview
```

## 发布后检查

获得批准并发布后，可在已验证的 Search Console 资源中提交：

```text
https://barbarians1999.github.io/zuoren-shelf/sitemap.xml
```

之后检查“网页索引”与“效果”报告；Google 何时抓取、选择哪些页面收录、展示哪些摘要和排名，均由 Google 决定，站点不能强制或保证。

## 语言

站点内容和目标读者目前以中文为主，主页和生成页都标记为 `zh-CN`。本次不生成机器翻译、英文摘要或多语言路由；这可以避免翻译与原作内容不一致以及低质量的重复页面。只有在将来有人审校了完整的另一语言界面或译文后，再为实际存在的语言版本添加对应页面和 `hreflang`。
