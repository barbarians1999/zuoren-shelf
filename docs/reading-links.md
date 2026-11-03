# 阅读链接与标题去重

## 分享链接

当前静态书目使用查询路由：

```text
?book={book.id}&section={section.id}
```

作者页打开作品时会保留 `author={author.id}`。分享链接基于当前 URL 修改查询参数，不改 pathname，因此站点部署在子路径时路径前缀会保留。链接不使用题名或当前排序位置作为标识。

`book-index.json` 是现有身份的来源。一个阅读位置由 `book.id` 与该书 `sections[].id` 共同标识；这些 ID 在当前清单中已逐书唯一，正文文件通过 `sectionPath/{section.id}.json` 寻址。维护书目时不要为重排、改题名或插入新篇而重编号现有 ID；新增章节应在该书范围内分配未使用的 ID。自动检查会验证当前 ID 唯一性以及正文文件存在性。

书架按钮打开作品时创建一个浏览器历史项；目录切换更新当前项，所以后退回到此前页面/书架，前进回到已分享的阅读位置。直接打开或刷新链接会按固定 ID 解析。书籍或章节 ID 无效时显示书架和提示，并清除无效路由参数。当前清单没有扫描版书籍；若以后添加扫描版，须另行定义稳定页 ID 后再开放分享。

滚动位置写入当前标签页的 `sessionStorage`，不进入 URL，也不会随链接共享。新标签页打开链接时从章节开头开始。现有每书阅读进度仍继续保存于原有本地存储。

点击阅读器中的“分享链接”会调用 Clipboard API。复制失败时打开手动复制对话框，并选中只读链接输入框。

## 正文标题去重规则

`reader-heading.js` 仅比较本节第一个非空 `h1`–`h6` 或 `p` 与章节题名。比较前应用 NFKC、移除空白，并忽略正文首标题末尾的 `*` 脚注标记；正文上标只从比较副本中排除。兼容形式（例如全角/半角字符）会由 NFKC 统一，但普通标点不会被删除。带“第…章”前缀时，双方必须都有编号且编号相同；只有一边带编号或两边编号不同都不去重。副标题或首段正文只要还有额外文字，就不会匹配。

命中后只隐藏应用生成的外层题名。若正文原首块是段落，渲染层将该段落提升为 `h2.chapter-heading`，复制原有属性并移动原节点内容，保留锚点与正文；源 JSON 不变。

## 隐藏导入的纯目录页

对确认整节只列原书目录的章节，在 `book-index.json` 的章节项标记 `readerHidden: true`。当前标记项：`bloodfire/section-003`、`stalin-trotsky-bukharin/section-001`、`stalin-era/section-005`、`german-ideology/section-001`、`lenin-selected/section-002`、`bettelheim-industrial-organization/section-003`、`global-monopoly-text/front`、`mao-selected/front`、`obtain-authority/front`、`natural-dialectics/front`、`luxun-text/front`、`economic-accounting-ownership/section-001`、`international-movement-course-vol1/section-001`、`route-dispute/front`。复合标题候选也逐节检查了内容；这些标记项只有书名/封面信息和目录，未混入前言或正文。章节 ID 与 JSON 正文文件保留，原书侧栏目录不会展示这些项；主页默认入口、前后章和站内目录均跳过它们。旧分享链接仍由原书 ID 解析，随后规范到被隐藏项之后的第一个可读章节并显示提示。

不按标题关键词自动隐藏。全书共检查 480 本、35 个标题含“目录/目次”的章节项；14 项经内容确认只含目录而标记隐藏。`jintui-text/section-007` 与 `class-struggles-france/section-001` 虽标题恰为“目录”，同一章节还包含正文，故保留。其余复合标题逐项核对：凡含出版说明、编者前言、献词、正文、照片/编目资料或仅书名页而非目录者均保留；`natural-dialectics/section-036` 是正文内讨论“四束手稿目录”的章节，也保留。

如果一本书没有任何可读章节，阅读器显示空内容提示，将 URL 规范为仅含 `book` 而不带 `section`，禁用前后章和分享按钮，并允许返回书架。若旧链接指向末尾隐藏章节，则回退到此前最近的可读章节；若指向中间隐藏章节，则前进到之后最近的可读章节。

## 清理正文顶部的原站目录导航

`tests/source_breadcrumbs.py` 只识别首个 `<hr>` 之前的纯导航块：链接必须全部指向 marxists.org 的 `index.htm` 索引页，链接外只能出现箭头/分隔符，外层只能是链接或简单表格包装。脚本删除该导航块及其紧随的分隔线，不触碰 `sourceUrl` 元数据和其余正文。它不会清除标注“相关链接”“另一译本”“译本”等有意义的交叉链接，也不会修改脚注、正文内链接或正文段落。

本次全目录清除了 1,096 个导航块，分布在 16 本书。清理前的逐项记录保存在 `tests/source_breadcrumbs_report.json`；可用 `python3 tests/source_breadcrumbs.py` 检查是否仍有匹配项，`--apply` 才会写入清理。验证命令：

```bash
python3 -m unittest discover -s tests -p 'test_source_breadcrumbs.py' -v
python3 tests/source_breadcrumbs.py
python3 tests/source_breadcrumbs_browser.py
```

单元测试检查《论犹太人问题》正文和来源元数据、其他书型的正文保留、语义链接保留及全清单无剩余纯导航；浏览器检查该文顶部、马克思文本中的相关链接、斯大林另一译本和毛泽东文章版本链接。

## 回归检查

标题比较的纯逻辑测试使用 Node 内置测试运行器：

```bash
node --test tests/reader_heading.test.cjs
```

端到端测试在本地启动临时静态服务，不调用远端：

```bash
python3 tests/reader_routes.py
```

第二条命令需要当前环境已安装 Playwright Python 包和 Chromium；项目没有因此新增运行时依赖。脚本覆盖清单 ID 唯一性/正文文件、单行本主页卡片/搜索/马克思作者页入口（包括《联共（布）党史简明教程》和《获得权威》）、剪贴板成功与失败回退、普通书/毛选/单篇作品、新上下文及硬刷新、浏览器后退/前进、章节切换、子路径部署、无效路由、桌面/移动端、标题重复与脚注、副标题保留、隐藏目录页旧 URL/默认入口/前后章、末尾隐藏回退、全隐藏空状态与禁用动作、保留混合正文，以及迟到的章节/跨书请求竞态。

全量书目路由验收使用单独脚本：

```bash
python3 -u tests/reader_routes_full.py
```

它逐项检查每本书的所有章节 ID 唯一性和对应正文 JSON 文件，共 5481 项；再逐本打开 480 本书，在独立浏览器上下文验证分享 URL、实际加载的正文资源、复制规范链接和刷新。75 本主页卡片由真实按钮点击并复制；作者页实际渲染的 398 本单篇/作品链接作为来源；毛泽东作者页刻意合并展示的 7 个重复条目仍逐本直接路由验收。成功/失败/跳过逐本记录在 `tests/reader_routes_full_results.json`。最近一次完整运行结果为 480/480 通过、0 失败、0 跳过；主页卡片 75/75，作者页入口 398 本，另有 7 本刻意合并的毛选重复条目通过直接路由检查。
