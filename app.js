(() => {
  const shelf = document.querySelector('#shelf');
  const bookList = document.querySelector('#book-list');
  const authorIndexNav = document.querySelector('#author-index');
  const authorView = document.querySelector('#author-view');
  const authorTitle = document.querySelector('#author-title');
  const authorBio = document.querySelector('#author-bio');
  const authorPortrait = document.querySelector('#author-profile-portrait');
  const authorProfiles = {
    marx: '卡尔·马克思（1818—1883），德国思想家、政治经济学批判者和国际工人运动活动家。他与恩格斯共同发展了历史唯物主义，其著作涉及资本主义经济、阶级斗争和革命。',
    engels: '弗里德里希·恩格斯（1820—1895），德国思想家和国际工人运动活动家。他与马克思长期合作，研究工人阶级状况、哲学和社会主义，并整理出版《资本论》后两卷。',
    lenin: '弗拉基米尔·伊里奇·列宁（1870—1924），俄国革命者、布尔什维克党领导人。他论述了帝国主义、国家、革命与社会主义建设，并参与领导十月革命和苏维埃政权建设。',
    stalin: '约瑟夫·维萨里奥诺维奇·斯大林（1878—1953），苏联政治领导人和马克思主义者。他的著作涉及民族问题、列宁主义、党内论争和苏联社会主义建设。',
    mao: '毛泽东（1893—1976），中国革命者、中国共产党和中华人民共和国的主要领导人。他的著作涉及中国革命、哲学、战争、社会主义建设和阶级斗争。'
  };
  const authorSummary = document.querySelector('#author-summary');
  const authorFeaturedList = document.querySelector('#author-featured-list');
  const authorFeaturedCount = document.querySelector('#author-featured-count');
  const authorFeaturedEmpty = document.querySelector('#author-featured-empty');
  const authorReferencesGroup = document.querySelector('#author-references-group');
  const authorReferences = document.querySelector('#author-references');
  const authorReferencesCount = document.querySelector('#author-references-count');
  const authorReferencesEmpty = document.querySelector('#author-references-empty');
  const authorClearFilters = document.querySelector('#author-clear-filters');
  const authorBack = document.querySelector('#author-back');
  const bookSearch = document.querySelector('#book-search');
  const bookSearchLabel = document.querySelector('label[for="book-search"]');
  const shelfCount = document.querySelector('#shelf-count');
  const categoryFilters = document.querySelector('#category-filters');
  const reader = document.querySelector('#reader');
  const desktopReader = document.querySelector('#desktop-reader');
  const mobileReader = document.querySelector('#mobile-reader');
  const desktopToc = document.querySelector('#desktop-toc');
  const desktopTocPanel = document.querySelector('#desktop-toc-panel');
  const desktopTocToggle = document.querySelector('#desktop-toc-toggle-button');
  const mobileToc = document.querySelector('#mobile-toc');
  const desktopContent = document.querySelector('#desktop-content');
  const mobileContent = document.querySelector('#mobile-content');
  const mobileViewport = document.querySelector('#mobile-reading-viewport');
  const mobileTocPanel = document.querySelector('#mobile-toc-panel');
  const mobileTocBackdrop = document.querySelector('#mobile-toc-backdrop');
  const mobileTocToggle = document.querySelector('#mobile-toc-toggle-button');
  const mobileTocClose = document.querySelector('#mobile-toc-close-button');
  const mobileBack = document.querySelector('#mobile-back-button');
  const desktopBack = document.querySelector('#back-button');
  const desktopPrevChapter = document.querySelector('#prev-button');
  const desktopNextChapter = document.querySelector('#next-button');
  const desktopShareButton = document.querySelector('#desktop-share-button');
  const mobileShareButton = document.querySelector('#mobile-share-button');
  const shareStatus = document.querySelector('#share-status');
  const shareDialog = document.querySelector('#share-dialog');
  const shareUrlInput = document.querySelector('#share-url');
  const shareCopyRetry = document.querySelector('#share-copy-retry');
  const routeNotice = document.querySelector('#route-notice');
  const modeQuery = window.matchMedia('(max-width: 700px)');
  const colorQuery = window.matchMedia('(prefers-color-scheme: dark)');
  const themeColor = document.querySelector('meta[name="theme-color"]');
  const metaDescription = document.querySelector('meta[name="description"]');
  const openGraphTitle = document.querySelector('meta[property="og:title"]');
  const openGraphDescription = document.querySelector('meta[property="og:description"]');
  const openGraphUrl = document.querySelector('meta[property="og:url"]');
  const canonicalLink = document.querySelector('link[rel="canonical"]');
  const homeTitle = document.title;
  const homeDescription = metaDescription?.content || '';
  const homeCanonical = canonicalLink?.href || window.location.href;

  function syncBrowserThemeColor() {
    themeColor.content = getComputedStyle(document.documentElement).getPropertyValue('--paper').trim();
  }
  colorQuery.addEventListener('change', syncBrowserThemeColor);
  syncBrowserThemeColor();

  let books = [];
  let authorIndex = [];
  let activeAuthor = null;
  let activeCategory = 'all';
  let currentBook = null;
  let current = 0;
  let readerMode = 'desktop';
  let renderToken = 0;
  let hideChromeTimer = null;
  let rendering = false;
  let lastPosition = null;
  let progressFrame = null;
  let progressTimer = null;
  let currentRouteKey = null;
  let shareStatusTimer = null;
  const routePositionPrefix = 'reading-desk:route-position:v1:';
  const progressPrefix = 'reading-desk:progress:v1:';
  const activeBookKey = 'reading-desk:active-book:v1';
  const fontPreferenceKey = 'reading-desk:font-family:v1';
  const sizePreferenceKey = 'reading-desk:font-size:v1';
  const spacingPreferenceKey = 'reading-desk:line-spacing:v1';
  const themePreferenceKey = 'reading-desk:theme:v1';
  let fontChoiceToken = 0;
  const blockSelector = 'h1,h2,h3,h4,h5,h6,p,li,blockquote,summary,img';
  const sectionCache = new Map();

  const categories = [
    { id: 'all', label: '全部' },
    { id: 'classics', label: '马克思主义理论与经典' },
    { id: 'china', label: '中国史与革命' },
    { id: 'international', label: '国际共运史' },
    { id: 'literature', label: '文学、回忆录与亲历记录' },
    { id: 'economics', label: '政治经济与阶级关系' }
  ];
  window.bookCategoryById = Object.freeze({
    'howto': 'classics', 'jintui-text': 'classics', 'zuopai-text': 'classics', 'lenin-selected': 'classics',
    'natural-dialectics': 'classics', 'women-socialism': 'classics', 'imperialism': 'classics',
    'state-and-revolution': 'classics', 'manifesto': 'classics', 'german-ideology': 'classics',
    'class-struggles-france': 'classics', 'eighteenth-brumaire': 'classics', 'civil-war': 'classics',
    'ludwig-feuerbach': 'classics', 'anti-duhring': 'classics', 'british-working-class': 'classics',
    'bloodfire': 'china', 'maodazhuan-text': 'china', 'mao-selected': 'china',
    'great-retreat': 'china', 'bettelheim-industrial-organization': 'china', 'obtain-authority': 'china',
    'long-revolution': 'china',
    'wenge-history': 'china', 'republic-course': 'china', 'two-routes-course': 'china',
    'ccp-history-course-upper': 'china', 'ccp-history-course-lower': 'china',
    'history': 'international', 'bolshevik-text': 'international', 'soviet-party-history-vol1': 'international',
    'soviet-party-history-vol2': 'international', 'russian-workers': 'international',
    'route-dispute': 'international',
    'german-revolution-1878-1919': 'international', 'international-movement-course-vol1': 'international',
    'international-movement-course-vol2': 'international', 'international-movement-course-vol3': 'international',
    'international-movement-course-vol4': 'international',
    'huangjin-text': 'literature', 'qibenyu-text': 'literature', 'zhangchunqiao-letters': 'literature',
    'luxun-text': 'china', 'red-star-over-china': 'literature', 'fanshen': 'literature',
    'shenfan': 'literature', 'great-reversal': 'literature', 'shanghai-morning': 'literature', 'redrock': 'literature',
    'global-monopoly-text': 'economics', 'keynes-china-crisis': 'economics',
    'political-economy-introduction': 'economics', 'new-workers-class-struggle': 'economics',
    'workers-revolutionary-philosophy-history': 'classics', 'class-struggle-in-contemporary-china': 'economics',
    'economic-accounting-ownership': 'economics',
    'ten-questions-soe': 'economics',
    'stalin-trotsky-bukharin': 'international',
    'stalin-era': 'international', 'transition-to-socialism': 'economics',
    'marx-wage-price-profit': 'classics', 'marx-capital-1': 'classics', 'marx-gotha-critique': 'classics',
    'engels-principles': 'classics', 'engels-authority': 'classics', 'engels-socialism': 'classics', 'engels-family-origin': 'classics',
    'lenin-two-tactics': 'classics', 'lenin-three-sources': 'classics', 'lenin-april-theses': 'classics', 'lenin-kautsky': 'classics',
    'stalin-anarchism-socialism': 'international', 'stalin-national-question': 'international', 'stalin-foundations': 'international', 'stalin-linguistics': 'international'
  });

  const escapeText = (value) => String(value).replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
  const isMobileReader = () => modeQuery.matches;
  const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

  function siteBaseUrl() {
    const url = new URL('.', window.location.href);
    url.search = '';
    url.hash = '';
    return url;
  }

  function seoBookUrl(book) {
    return new URL(`books/${encodeURIComponent(book.id)}/`, siteBaseUrl()).href;
  }

  function seoArticleUrl(book, section) {
    return new URL(`texts/${encodeURIComponent(book.id)}/${encodeURIComponent(section.id)}/`, siteBaseUrl()).href;
  }

  function seoAuthorUrl(author) {
    return new URL(`authors/${encodeURIComponent(author.id)}/`, siteBaseUrl()).href;
  }

  function syncRouteMetadata() {
    let title = homeTitle;
    let description = homeDescription;
    let canonical = homeCanonical;
    if (currentBook) {
      const section = currentBook.type === 'scan' ? null : currentBook.sections[current];
      const sectionTitle = section?.title || (currentBook.type === 'scan' ? `第 ${current + 1} 页` : '在线阅读');
      title = `${sectionTitle}｜${currentBook.title}｜左人书架`;
      description = `在线阅读《${currentBook.title}》${sectionTitle}。作者/编者：${currentBook.author}。左人书架提供中文阅读版和可分享的章节链接。`;
      canonical = section ? seoArticleUrl(currentBook, section) : seoBookUrl(currentBook);
    } else if (activeAuthor) {
      const count = (activeAuthor.featuredWorks || []).length;
      title = `${activeAuthor.name}作品与文章｜左人书架`;
      description = `左人书架收录${activeAuthor.name}的中文著作与文章，列出 ${count} 项作品入口和对应在线阅读链接。`;
      canonical = seoAuthorUrl(activeAuthor);
    }
    document.title = title;
    if (metaDescription) metaDescription.content = description;
    if (openGraphTitle) openGraphTitle.content = title;
    if (openGraphDescription) openGraphDescription.content = description;
    if (openGraphUrl) openGraphUrl.content = canonical;
    if (canonicalLink) canonicalLink.href = canonical;
  }

  function shouldInterceptLink(event) {
    return event.button === 0 && !event.defaultPrevented
      && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey;
  }

  function readerSectionEntries(book) {
    return book.type === 'scan' ? [] : (book.sections || [])
      .map((section, index) => ({ section, index }))
      .filter(({ section }) => section.readerHidden !== true);
  }

  function visibleSectionIndex(book, requestedIndex) {
    if (book.type === 'scan') return clamp(requestedIndex, 0, book.pageCount - 1);
    const entries = readerSectionEntries(book);
    if (!entries.length) return -1;
    const exact = entries.find((entry) => entry.index === requestedIndex);
    if (exact) return exact.index;
    return entries.find((entry) => entry.index > requestedIndex)?.index
      ?? entries.filter((entry) => entry.index < requestedIndex).at(-1)?.index
      ?? entries[0].index;
  }

  function visibleSectionPosition(book, index) {
    if (book.type === 'scan') return { position: index, total: book.pageCount };
    const entries = readerSectionEntries(book);
    const position = entries.findIndex((entry) => entry.index === index);
    return { position: Math.max(0, position), total: entries.length };
  }

  function adjacentSectionIndex(book, index, direction) {
    if (book.type === 'scan') return clamp(index + direction, 0, book.pageCount - 1);
    const entries = readerSectionEntries(book);
    if (!entries.length) return -1;
    const position = entries.findIndex((entry) => entry.index === index);
    return entries[clamp(position + direction, 0, entries.length - 1)]?.index ?? index;
  }

  function historyStateObject() {
    const state = window.history.state;
    return state && typeof state === 'object' && !Array.isArray(state) ? { ...state } : {};
  }

  function newRouteKey() {
    return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
  }

  function ensureRouteKey() {
    const state = historyStateObject();
    if (state.zuorenRouteKey) {
      currentRouteKey = state.zuorenRouteKey;
      return currentRouteKey;
    }
    currentRouteKey = newRouteKey();
    window.history.replaceState({ ...state, zuorenRouteKey: currentRouteKey }, '', window.location.href);
    return currentRouteKey;
  }

  function writeReaderLocation(historyMode = 'replace') {
    if (!currentBook) return;
    const url = new URL(window.location.href);
    url.searchParams.set('book', currentBook.id);
    const sectionId = currentBook.type === 'scan'
      ? String(current + 1)
      : currentBook.sections[current]?.id;
    if (sectionId) url.searchParams.set('section', sectionId);
    else url.searchParams.delete('section');
    if (activeAuthor) url.searchParams.set('author', activeAuthor.id);
    else url.searchParams.delete('author');
    const state = historyStateObject();
    currentRouteKey = historyMode === 'push' || !state.zuorenRouteKey
      ? newRouteKey() : state.zuorenRouteKey;
    const nextState = { ...state, zuorenRouteKey: currentRouteKey };
    if (historyMode === 'push') window.history.pushState(nextState, '', url);
    else window.history.replaceState(nextState, '', url);
  }

  function writeShelfLocation() {
    const url = new URL(window.location.href);
    url.searchParams.delete('book');
    url.searchParams.delete('section');
    const state = historyStateObject();
    currentRouteKey = newRouteKey();
    window.history.replaceState({ ...state, zuorenRouteKey: currentRouteKey }, '', url);
  }

  function routePositionFor(routeKey, book, sectionId) {
    if (!routeKey) return null;
    try {
      const saved = JSON.parse(sessionStorage.getItem(routePositionPrefix + routeKey));
      if (saved?.bookId !== book.id || saved?.sectionId !== sectionId) return null;
      return saved.position || null;
    } catch { return null; }
  }

  function persistRoutePosition() {
    if (!currentBook || !currentRouteKey || !lastPosition) return;
    const sectionId = currentBook.type === 'scan' ? String(current + 1) : currentBook.sections[current]?.id;
    try {
      sessionStorage.setItem(routePositionPrefix + currentRouteKey, JSON.stringify({
        bookId: currentBook.id, sectionId, position: lastPosition
      }));
    } catch { /* Sharing and reading still work if this tab cannot store its position. */ }
  }

  function showRouteNotice(message) {
    routeNotice.textContent = message || '';
    routeNotice.hidden = !message;
  }

  function clearReaderForLocationChange() {
    if (!reader.classList.contains('is-hidden')) {
      rememberPosition();
      persistProgress();
      ReaderNotes.clear();
      ++renderToken;
      rendering = false;
      closeToc(false);
      writeStored(activeBookKey, null);
    }
    currentBook = null;
    reader.classList.add('is-hidden');
    shelf.classList.remove('is-hidden');
    document.body.classList.remove('book-open', 'mobile-reader-open', 'mobile-toc-open');
    setMobileChrome(false);
  }

  function applyLocation({ initial = false, state = window.history.state } = {}) {
    const params = new URLSearchParams(window.location.search);
    const requestedAuthor = params.get('author');
    const requestedBookId = params.get('book');
    const requestedSectionId = params.get('section');
    activeAuthor = authorIndex.find((entry) => entry.id === requestedAuthor) || null;
    showRouteNotice('');
    if (!initial && currentBook && !reader.classList.contains('is-hidden')) {
      rememberPosition();
      persistProgress();
    }
    const routeState = state && typeof state === 'object' ? state : {};
    const nextRouteKey = routeState.zuorenRouteKey || null;

    if (params.has('book')) {
      const bookIndex = books.findIndex((book) => book.id === requestedBookId);
      const requestedBook = books[bookIndex];
      const sectionExists = requestedBook?.type !== 'scan'
        && requestedBook?.sections?.some((section) => section.id === requestedSectionId);
      if (bookIndex < 0) {
        clearReaderForLocationChange();
        currentRouteKey = nextRouteKey;
        if (!currentRouteKey) ensureRouteKey();
        renderShelf();
        writeShelfLocation();
        showRouteNotice('链接中的书籍标识无效，已返回书架。');
        return;
      }
      if (requestedBook.type !== 'scan' && !readerSectionEntries(requestedBook).length) {
        currentRouteKey = nextRouteKey;
        if (!currentRouteKey) ensureRouteKey();
        renderShelf();
        openReader(bookIndex, requestedSectionId, { historyMode: 'none' });
        return;
      }
      if (!requestedSectionId || !sectionExists) {
        clearReaderForLocationChange();
        currentRouteKey = nextRouteKey;
        if (!currentRouteKey) ensureRouteKey();
        renderShelf();
        writeShelfLocation();
        showRouteNotice('链接中的章节标识无效，已返回书架。');
        return;
      }
      currentRouteKey = nextRouteKey;
      if (!currentRouteKey) ensureRouteKey();
      renderShelf();
      const requestedSection = requestedBook.sections.find((section) => section.id === requestedSectionId);
      const position = requestedSection?.readerHidden
        ? null : routePositionFor(currentRouteKey, requestedBook, requestedSectionId);
      if (requestedSection?.readerHidden) {
        showRouteNotice(`《${requestedBook.title}》的原书目录页已隐藏，已跳到正文。`);
      }
      openReader(bookIndex, requestedSectionId, { historyMode: 'none', position });
      return;
    }

    clearReaderForLocationChange();
    currentRouteKey = nextRouteKey;
    if (!currentRouteKey) ensureRouteKey();
    renderShelf();
    if (initial && !params.has('author')) {
      const activeBook = readStored(activeBookKey);
      const index = books.findIndex((book) => book.id === activeBook);
      if (index !== -1) openReader(index, null, { historyMode: 'replace' });
    }
  }

  async function loadBooks() {
    const response = await fetch('book-index.json', { cache: 'no-store' });
    if (!response.ok) throw new Error('books unavailable');
    const data = await response.json();
    books = data.books || [];
    authorIndex = Array.isArray(data.authorIndex) ? data.authorIndex : [];
    renderCategoryFilters();
    applyLocation({ initial: true });
  }

  function renderCategoryFilters() {
    const shelfBooks = books.filter((book) => !book.authorOnly);
    categoryFilters.innerHTML = categories.map((category) => {
      const count = category.id === 'all'
        ? shelfBooks.length
        : shelfBooks.filter((book) => window.bookCategoryById[book.id] === category.id).length;
      return `<button class="category-filter" type="button" data-category="${category.id}" aria-pressed="${category.id === activeCategory}">${category.label}<span aria-hidden="true">${count}</span></button>`;
    }).join('');
    categoryFilters.querySelectorAll('[data-category]').forEach((button) => button.addEventListener('click', () => {
      activeCategory = button.dataset.category;
      categoryFilters.querySelectorAll('[data-category]').forEach((filter) => {
        filter.setAttribute('aria-pressed', String(filter.dataset.category === activeCategory));
      });
      renderShelf();
    }));
  }


  function filteredBooks(ids, terms) {
    return books.map((book, index) => ({ book, index, saved: readProgress(book) }))
      .filter(({ book }) => ids !== null || !book.authorOnly)
      .filter(({ book }) => ids === null || ids.includes(book.id))
      .filter(({ book }) => activeCategory === 'all' || window.bookCategoryById[book.id] === activeCategory)
      .filter(({ book }) => terms.every((term) => `${book.title} ${book.author}`.toLocaleLowerCase().includes(term)))
      .sort((a, b) => Number(Boolean(b.saved)) - Number(Boolean(a.saved)) || a.index - b.index);
  }

  function renderBookCards(target, items) {
    target.innerHTML = items.length ? items.map(({ book, index, saved }) => {
      return `<article class="book-card ${saved ? 'ready' : ''}"><div class="book-face"><h2>${escapeText(book.title)}</h2><p class="book-byline">${escapeText(book.author)}</p></div><div class="book-foot"><a class="open-button" href="${escapeText(seoBookUrl(book))}" data-book="${index}" aria-label="${saved ? '继续阅读' : '开始阅读'}《${escapeText(book.title)}》">${saved ? '继续阅读' : '开始阅读'}</a></div></article>`;
    }).join('') : '';
    target.querySelectorAll('[data-book]').forEach((link) => link.addEventListener('click', (event) => {
      if (!shouldInterceptLink(event)) return;
      event.preventDefault();
      openReader(Number(link.dataset.book));
    }));
  }

  function authorWorkLink(work, label, attributes = '') {
    const bookIndex = books.findIndex((book) => book.id === work.bookId);
    const book = books[bookIndex];
    const section = book?.sections?.find((item) => item.id === work.sectionId && item.readerHidden !== true);
    if (book && section) {
      const url = new URL(window.location.href);
      url.searchParams.set('author', activeAuthor.id);
      url.searchParams.set('book', book.id);
      url.searchParams.set('section', section.id);
      return `<a href="${escapeText(`${url.pathname}${url.search}`)}"${attributes}>${escapeText(label)}</a>`;
    }
    if (work.url) return `<a href="${escapeText(work.url)}" target="_blank" rel="noopener noreferrer"${attributes}>${escapeText(label)}</a>`;
    return `<span>${escapeText(label)}</span>`;
  }

  function renderAuthorFeaturedWorks(entry, terms) {
    const authorCategory = { marx: 'classics', engels: 'classics', lenin: 'classics', stalin: 'international', mao: 'china' }[entry.id];
    if (entry.id === 'mao') return renderMaoWorks(entry, terms);
    document.querySelector('#author-featured-title').firstChild.nodeValue = '作品与文章 · 按时间排列 ';
    const featuredWorks = (entry.featuredWorks || [])
      .filter((work) => {
        const inCategory = activeCategory === 'all' || authorCategory === activeCategory;
        return inCategory && terms.every((term) => work.title.toLocaleLowerCase().includes(term));
      })
      .sort((a, b) => {
        const yearA = Number(a.sortYear || String(a.year || '').match(/\d{4}/)?.[0] || Infinity);
        const yearB = Number(b.sortYear || String(b.year || '').match(/\d{4}/)?.[0] || Infinity);
        return yearA - yearB;
      });
    const uniqueWorks = dedupeAuthorWorks(featuredWorks);
    authorFeaturedCount.textContent = `（${uniqueWorks.length}）`;
    authorFeaturedEmpty.classList.toggle('is-hidden', uniqueWorks.length > 0);
    authorFeaturedEmpty.textContent = (entry.featuredWorks || []).length
      ? '当前搜索和分类没有匹配的作品。'
      : '暂未收录可在线阅读的作品。';
    authorFeaturedList.innerHTML = uniqueWorks.map((work) => {
      const year = work.year ? `<span class="featured-year">${escapeText(work.year)}</span>` : '';
      const priority = work.recommendation ? ` aria-label="重点篇目：${escapeText(work.title)}"` : '';
      return `<li${work.recommendation ? ' class="is-priority"' : ''}>${year}<div class="featured-work">${authorWorkLink(work, work.title, priority)}</div></li>`;
    }).join('');
    return uniqueWorks.length;
  }

  function dedupeAuthorWorks(works) {
    const seen = new Set();
    return works.filter((work) => {
      const key = `${work.bookId || work.url}|${work.title.normalize('NFKC').replace(/[\s\p{P}\p{S}]/gu, '')}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }

  function renderMaoWorks(entry, terms) {
    const selected = books.find((book) => book.id === 'mao-selected');
    if (!selected) return 0;
    const normalizeTitle = (title) => title.normalize('NFKC').replace(/刘易斯/g, '路易斯').replace(/[\s\p{P}\p{S}]/gu, '');
    const bySection = new Map((entry.featuredWorks || []).filter((work) => work.bookId === selected.id).map((work) => [work.sectionId, work]));
    const selectedTitles = new Set(selected.sections.filter((section) => section.level === 2).map((section) => normalizeTitle(section.title)));
    const isOtherEditionOfSelected = (work) => {
      if (work.bookId === selected.id) return false;
      const title = work.title.normalize('NFKC');
      const unabridged = /^〔未删节本〕/.test(title);
      const suffix = /[（(](?:原始版本|原版|讲话稿|异译本|异译|繁体(?:版)?|译本|版本[一-三\d]?|修订(?:本|版)|删节(?:本|版)|手稿|原稿)[）)]$/;
      const explicitEdition = unabridged || suffix.test(title);
      const candidates = [title.replace(/^〔未删节本〕/, '').replace(suffix, '')];
      if (unabridged) {
        const baseTitle = candidates[0].split(/[—–―]/, 1)[0];
        candidates.push(baseTitle, baseTitle.replace(/与/g, '和'));
      }
      return candidates.some((candidate) => selectedTitles.has(normalizeTitle(candidate))) || (explicitEdition && candidates.some((candidate) => selectedTitles.has(normalizeTitle(candidate.replace(/与/g, '和')))));
    };
    const groups = [];
    for (const section of selected.sections) {
      if (section.level === 0 && /^第[一二三四五六七]卷/.test(section.title)) groups.push({ title: section.title, works: [] });
      else if (section.level === 2 && groups.length) {
        const original = bySection.get(section.id);
        groups[groups.length - 1].works.push({ ...original, title: section.title, bookId: selected.id, sectionId: section.id });
      }
    }
    const extras = (entry.featuredWorks || []).filter((work) => work.bookId !== selected.id && !isOtherEditionOfSelected(work));
    groups.push({ title: '选集外文章', works: extras });
    let count = 0;
    const html = groups.map((group) => {
      const works = group.works.filter((work) => terms.every((term) => work.title.toLocaleLowerCase().includes(term)));
      if (!works.length) return '';
      count += works.length;
      const rows = works.map((work) => {
        const year = work.year ? `<span class="featured-year">${escapeText(work.year)}</span>` : '<span></span>';
        const priorityClass = work.recommendation ? ' class="is-priority"' : '';
        const priority = work.recommendation ? ` aria-label="重点篇目：${escapeText(work.title)}"` : '';
        return `<li${priorityClass}>${year}<div class="featured-work">${authorWorkLink(work, work.title, priority)}</div></li>`;
      }).join('');
      return `<li class="author-volume"><h4>${escapeText(group.title)}</h4></li>${rows}`;
    }).join('');
    document.querySelector('#author-featured-title').firstChild.nodeValue = '作品与文章 · 按选集排列 ';
    authorFeaturedList.innerHTML = html;
    authorFeaturedCount.textContent = `（${count}）`;
    authorFeaturedEmpty.classList.toggle('is-hidden', count > 0);
    authorFeaturedEmpty.textContent = '当前搜索没有匹配的作品。';
    return count;
  }

  function renderShelf() {
    const terms = bookSearch.value.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
    const filterActive = terms.length > 0 || activeCategory !== 'all';
    const entry = activeAuthor;
    authorIndexNav.hidden = Boolean(entry) || activeCategory !== 'all';
    categoryFilters.hidden = Boolean(entry);
    document.body.classList.toggle('author-page', Boolean(entry));
    bookSearch.placeholder = entry ? '搜索作品或文章' : '书名或作者';
    bookSearchLabel.textContent = entry ? `搜索${entry.name}的作品` : '找一本书';
    bookList.classList.toggle('is-hidden', Boolean(entry));
    authorView.classList.toggle('is-hidden', !entry);
    if (!entry) {
      const visible = filteredBooks(null, terms);
      shelfCount.textContent = filterActive ? `找到 ${visible.length} 本` : `共 ${books.filter((book) => !book.authorOnly).length} 本`;
      if (visible.length) renderBookCards(bookList, visible);
      else bookList.innerHTML = '<p class="shelf-empty">没有找到这本书，试试书名中的其他字或作者名。</p>';
      syncRouteMetadata();
      return;
    }

    const references = filteredBooks(entry.referenceIds, terms);
    authorTitle.textContent = entry.name;
    authorBio.textContent = authorProfiles[entry.id] || '';
    authorPortrait.className = `author-portrait author-profile-portrait portrait-${entry.id}`;
    const authoredCount = entry.id === 'mao' ? (entry.featuredWorks || []).length : dedupeAuthorWorks(entry.featuredWorks || []).length;
    authorSummary.textContent = entry.id === 'mao'
      ? '先按本地《毛泽东选集》的卷次和篇目排列，再列出选集外文章与其他版本。第六、七卷为静火版。'
      : `本地收录 ${authoredCount} 项作品与文章，按写作或发表时间排列。`;
    authorReferencesCount.textContent = `（${references.length}）`;
    const visibleWorks = renderAuthorFeaturedWorks(entry, terms);
    authorReferencesGroup.classList.toggle('is-hidden', entry.referenceIds.length === 0);
    authorClearFilters.classList.toggle('is-hidden', !filterActive);
    authorReferencesEmpty.classList.toggle('is-hidden', entry.referenceIds.length === 0 || references.length > 0);
    authorReferencesEmpty.textContent = '当前搜索和分类没有匹配的相关书目。';
    shelfCount.textContent = filterActive
      ? `筛选结果：${visibleWorks} 项作品，${references.length} 项相关书目`
      : `${entry.name}：${entry.id === 'mao' ? visibleWorks : authoredCount} 项作品，${references.length} 项相关书目`;
    if (entry.referenceIds.length) renderBookCards(authorReferences, references);
    syncRouteMetadata();
  }

  function renderToc() {
    if (!currentBook) return;
    const visibleSections = currentBook.type === 'scan' ? [] : readerSectionEntries(currentBook);
    const tocSections = visibleSections.filter(({ section }) => !/^注释$/.test(section.title.trim()));
    const hasToc = currentBook.type === 'scan' || tocSections.length > 1;
    desktopTocPanel.hidden = !hasToc;
    desktopTocToggle.hidden = !hasToc;
    mobileTocToggle.hidden = !hasToc;
    desktopReader.classList.toggle('toc-unneeded', !hasToc);
    const numbering = [];
    const html = currentBook.type === 'scan'
      ? '<p class="toc-hint">使用下方章节按钮翻页</p>'
      : visibleSections.map(({ section, index }, visibleIndex) => {
        let level = clamp(Number(section.level) || 0, 0, 4);
        if (section.chapter) level = Math.max(level, 1);
        const newChapter = section.chapter && section.chapter !== visibleSections[visibleIndex - 1]?.section.chapter;
        let chapterHeading = '';
        if (newChapter) {
          numbering.length = Math.min(numbering.length, 1);
          if (!numbering.length) numbering.push(0);
          numbering[0]++;
          chapterHeading = `<h3 class="toc-group">${numbering[0]}. ${escapeText(section.chapter)}</h3>`;
        }
        while (numbering.length <= level) numbering.push(0);
        numbering.length = level + 1;
        numbering[level]++;
        for (let parent = 0; parent < level; parent++) numbering[parent] ||= 1;
        const number = numbering.slice(0, level + 1).join('.');
        const currentAttribute = index === current ? ' aria-current="page"' : '';
        return `${chapterHeading}<a class="toc-link ${index === current ? 'active' : ''}" href="${escapeText(seoArticleUrl(currentBook, section))}" data-index="${index}" data-level="${level}"${currentAttribute}>${number}. ${escapeText(section.title)}</a>`;
      }).join('');
    desktopToc.innerHTML = html;
    mobileToc.innerHTML = html;
    [desktopToc, mobileToc].forEach((nav) => nav.querySelectorAll('.toc-link').forEach((link) => link.addEventListener('click', (event) => {
      if (!shouldInterceptLink(event)) return;
      event.preventDefault();
      closeToc(false);
      openSection(Number(link.dataset.index));
    })));
  }

  function setTocOpen(open, returnFocus = true) {
    const wasOpen = mobileTocPanel.classList.contains('is-open');
    if (open && readerMode !== 'mobile') return;
    if (open && !wasOpen) {
      rememberPosition();
      persistProgress();
    }
    mobileTocPanel.inert = !open;
    mobileViewport.inert = open;
    mobileReader.querySelector('.mobile-reader-head').inert = open;
    mobileTocPanel.setAttribute('aria-hidden', String(!open));
    if (open) mobileTocPanel.setAttribute('aria-modal', 'true');
    else mobileTocPanel.removeAttribute('aria-modal');
    mobileTocPanel.classList.toggle('is-open', open);
    mobileTocBackdrop.classList.toggle('is-open', open);
    mobileTocToggle.setAttribute('aria-expanded', String(open));
    document.body.classList.toggle('mobile-toc-open', open);
    if (open) {
      setMobileChrome(false);
      const active = mobileToc.querySelector('.active') || mobileTocClose;
      active.focus({ preventScroll: true });
      const rect = active.getBoundingClientRect();
      window.scrollTo({ top: Math.max(0, window.scrollY + rect.top + rect.height / 2 - window.innerHeight / 2), behavior: 'instant' });
    } else if (wasOpen) {
      if (readerMode === 'mobile') restorePosition(readerMode, lastPosition);
      if (returnFocus && readerMode === 'mobile') {
        setMobileChrome(true, true);
        mobileTocToggle.focus({ preventScroll: true });
      } else if (mobileTocPanel.contains(document.activeElement)) {
        document.activeElement.blur();
      }
    }
  }

  function closeToc(returnFocus = true) { setTocOpen(false, returnFocus); }

  function setDesktopTocCollapsed(collapsed) {
    desktopReader.classList.toggle('toc-collapsed', collapsed);
    desktopTocPanel.setAttribute('aria-hidden', String(collapsed));
    desktopTocPanel.inert = collapsed;
    desktopTocToggle.setAttribute('aria-expanded', String(!collapsed));
    desktopTocToggle.textContent = collapsed ? '展开目录' : '收起目录';
    writeStored('reading-desk:desktop-toc-collapsed:v1', collapsed);
  }

  function setMobileChrome(visible, autoHide = false) {
    mobileReader.classList.toggle('chrome-visible', visible);
    mobileReader.setAttribute('aria-label', visible ? '阅读控件已显示' : '阅读控件已隐藏');
    if (hideChromeTimer) window.clearTimeout(hideChromeTimer);
    if (visible && autoHide && isMobileReader()) hideChromeTimer = window.setTimeout(() => {
      if (!mobileTocPanel.classList.contains('is-open') && !mobileReader.querySelector('.settings[open]') && !mobileReader.querySelector('.mobile-reader-head :focus-visible')) setMobileChrome(false);
    }, 5000);
  }

  function syncBookMeta() {
    const total = currentBook.type === 'scan' ? currentBook.pageCount : visibleSectionPosition(currentBook, current).total;
    document.querySelector('#section-count').textContent = currentBook.type === 'scan'
      ? `${total} 页`
      : total === 0 ? '0 个可读章节' : `${total} 个阅读单元`;
    document.querySelector('#book-title').textContent = currentBook.title;
    document.querySelector('#book-author').textContent = currentBook.author;
    document.querySelector('#mobile-book-title').textContent = currentBook.title;
    const { position, total: visibleTotal } = currentBook.type === 'scan'
      ? { position: current, total }
      : visibleSectionPosition(currentBook, current);
    if (visibleTotal === 0) document.querySelector('#reading-position').textContent = '0 / 0';
    document.querySelector('#mobile-reading-position').textContent = `${position + 1} / ${visibleTotal}`;
    desktopPrevChapter.disabled = visibleTotal === 0 || position === 0;
    desktopNextChapter.disabled = visibleTotal === 0 || position === visibleTotal - 1;
    desktopShareButton.disabled = visibleTotal === 0;
    mobileShareButton.disabled = visibleTotal === 0;
  }

  function syncSectionMeta() {
    if (current < 0) return;
    const title = currentBook.type === 'scan' ? `第 ${current + 1} 页` : currentBook.sections[current].title;
    document.querySelector('#section-title').textContent = title;
    document.querySelector('#mobile-section-title').textContent = title;
    const bodyIncludesTitle = currentBook.type !== 'scan' && currentBook.sections[current].bodyIncludesTitle === true;
    document.querySelector('#section-title').classList.toggle('is-hidden', bodyIncludesTitle);
    document.querySelector('#mobile-section-title').classList.toggle('is-hidden', bodyIncludesTitle);
    const { position, total } = visibleSectionPosition(currentBook, current);
    document.querySelector('#reading-position').textContent = `${position + 1} / ${total}`;
    document.querySelector('#desktop-scan-summary').classList.toggle('is-hidden', currentBook.type !== 'scan');
    document.querySelector('#mobile-scan-summary').classList.toggle('is-hidden', currentBook.type !== 'scan');
  }

  function readStored(key) {
    try { return JSON.parse(localStorage.getItem(key)); } catch { return null; }
  }

  function writeStored(key, value) {
    try {
      if (value == null) localStorage.removeItem(key);
      else localStorage.setItem(key, JSON.stringify(value));
    } catch {
      document.querySelector('#progress-notice').hidden = false;
    }
  }

  function applyReadingFont(font, persist = false) {
    const legacyFont = font === 'song' ? 'source-han' : font;
    const allowed = ['system', 'source-han', 'fangsong', 'hanyi-shufang'];
    const selected = allowed.includes(legacyFont) ? legacyFont : 'system';
    document.documentElement.dataset.readingFont = selected;
    document.querySelectorAll('button[data-reading-font]').forEach((button) => {
      button.setAttribute('aria-pressed', String(button.dataset.readingFont === selected));
    });
    if (persist) {
      try { localStorage.setItem(fontPreferenceKey, JSON.stringify(selected)); } catch { /* The current choice still applies for this visit. */ }
    }
  }

  function readingFontReady(font = document.documentElement.dataset.readingFont) {
    const families = { 'source-han': 'Source Han Serif SC Web', fangsong: 'Zhaoye FangSong', 'hanyi-shufang': 'Hanyi Shufang Local First' };
    const family = families[font];
    if (!family || !document.fonts?.load) return Promise.resolve(true);
    return document.fonts.load(`16px "${family}"`, '阅读字体测试')
      .then((faces) => faces.some((face) => face.status === 'loaded'))
      .catch(() => false);
  }

  function setPressed(selector, value, attribute) {
    document.querySelectorAll(selector).forEach((button) => {
      button.setAttribute('aria-pressed', String(button.dataset[attribute] === value));
    });
  }

  function applyReadingSize(size, persist = false) {
    const sizes = { small: '1rem', medium: 'clamp(1.08rem, 1.8vw, 1.24rem)', large: 'clamp(1.28rem, 2.2vw, 1.5rem)' };
    const selected = Object.prototype.hasOwnProperty.call(sizes, size) ? size : 'medium';
    document.documentElement.style.setProperty('--reading-size', sizes[selected]);
    setPressed('button[data-size]', selected, 'size');
    if (persist) {
      try { localStorage.setItem(sizePreferenceKey, JSON.stringify(selected)); } catch { /* The current choice still applies for this visit. */ }
    }
  }

  function applyLineSpacing(spacing, persist = false) {
    const values = { tight: '1.75', normal: '2', wide: '2.25' };
    const selected = Object.prototype.hasOwnProperty.call(values, spacing) ? spacing : 'normal';
    document.documentElement.style.setProperty('--reading-leading', values[selected]);
    setPressed('button[data-spacing]', selected, 'spacing');
    if (persist) {
      try { localStorage.setItem(spacingPreferenceKey, JSON.stringify(selected)); } catch { /* The current choice still applies for this visit. */ }
    }
  }

  function applyTheme(theme, persist = false) {
    const selected = ['system', 'light', 'dark'].includes(theme) ? theme : 'system';
    if (selected === 'system') delete document.documentElement.dataset.theme;
    else document.documentElement.dataset.theme = selected;
    setPressed('button[data-theme-choice]', selected, 'themeChoice');
    syncBrowserThemeColor();
    if (persist) {
      try { localStorage.setItem(themePreferenceKey, JSON.stringify(selected)); } catch { /* The current choice still applies for this visit. */ }
    }
  }

  applyTheme(readStored(themePreferenceKey));
  document.querySelectorAll('button[data-theme-choice]').forEach(button => button.addEventListener('click', () => applyTheme(button.dataset.themeChoice, true)));
  applyReadingFont(readStored(fontPreferenceKey));
  applyReadingSize(readStored(sizePreferenceKey));
  applyLineSpacing(readStored(spacingPreferenceKey));

  function sectionIdentity(book, index) {
    return book.type === 'scan' ? String(index) : book.sections[index].id;
  }

  function readProgress(book) {
    const saved = readStored(progressPrefix + book.id);
    if (!saved || saved.version !== 1 || typeof saved.sectionId !== 'string') return null;
    const sectionId = book.type === 'scan' ? saved.sectionId : (book.progressAliases?.[saved.sectionId] || saved.sectionId);
    const index = book.type === 'scan' ? Number(sectionId) : book.sections.findIndex((s) => s.id === sectionId);
    const total = book.type === 'scan' ? book.pageCount : book.sections.length;
    if (!Number.isInteger(index) || index < 0 || index >= total) return null;
    if (saved.source !== (book.sectionPath || book.pagePath)) return null;
    return { ...saved, sectionId, index };
  }

  function contentFor(mode) { return mode === 'mobile' ? mobileContent : desktopContent; }

  function renderEmptyBookState() {
    ++renderToken;
    rendering = false;
    ReaderNotes.clear();
    document.querySelector('#section-title').classList.add('is-hidden');
    document.querySelector('#mobile-section-title').classList.add('is-hidden');
    document.querySelector('#section-title').textContent = '无可读章节';
    document.querySelector('#mobile-section-title').textContent = '无可读章节';
    const message = '<p class="empty-book-state" role="status">本书当前没有可阅读的正文内容。你可以返回书架选择其他书籍。</p>';
    [desktopContent, mobileContent].forEach((target) => {
      target.innerHTML = message;
      target.setAttribute('aria-busy', 'false');
    });
  }

  function readingTop(mode) {
    return mode === 'mobile' ? 12
      : document.querySelector('.topbar').getBoundingClientRect().bottom + desktopReader.querySelector('.reader-head').getBoundingClientRect().height + 12;
  }

  function sectionStart(mode) {
    if (mode === 'mobile') return 0;
    const title = document.querySelector('#section-title');
    const first = title.classList.contains('is-hidden') ? desktopContent : title;
    return Math.max(0, document.scrollingElement.scrollTop + first.getBoundingClientRect().top - readingTop(mode));
  }

  function readableBlock(el) {
    if (!el.getClientRects().length) return false;
    // Closed details descendants can have layout rectangles without being painted.
    for (let node = el.parentElement; node; node = node.parentElement) {
      if (node.tagName === 'DETAILS' && !node.open && !node.querySelector(':scope > summary')?.contains(el)) return false;
    }
    return true;
  }

  function capturePosition(mode = readerMode) {
    const content = contentFor(mode);
    const viewport = document.scrollingElement;
    const blocks = Array.from(content.querySelectorAll(blockSelector));
    const top = readingTop(mode);
    const block = blocks.findIndex((el) => readableBlock(el) && el.getBoundingClientRect().bottom > top);
    const rect = blocks[block]?.getBoundingClientRect();
    const max = Math.max(0, viewport.scrollHeight - viewport.clientHeight);
    return {
      atStart: viewport.scrollTop <= sectionStart(mode) + 2,
      block,
      fraction: rect ? clamp((top - rect.top) / Math.max(1, rect.height), 0, 1) : 0,
      gap: rect ? clamp(rect.top - top, 0, viewport.clientHeight) : 0,
      ratio: max ? clamp(viewport.scrollTop / max, 0, 1) : 0,
      openNotes: Array.from(content.querySelectorAll('details')).flatMap((el, i) => el.open ? [i] : [])
    };
  }

  function persistProgress() {
    window.clearTimeout(progressTimer);
    if (!currentBook || current < 0 || !lastPosition || reader.classList.contains('is-hidden')) return;
    persistRoutePosition();
    writeStored(progressPrefix + currentBook.id, {
      version: 1, source: currentBook.sectionPath || currentBook.pagePath,
      sectionId: sectionIdentity(currentBook, current), position: lastPosition
    });
  }

  function rememberPosition() {
    if (rendering || !currentBook || current < 0 || reader.classList.contains('is-hidden')) return;
    if (mobileTocPanel.classList.contains('is-open')) return;
    // A breakpoint event may arrive after CSS has already hidden the old surface.
    if ((isMobileReader() ? 'mobile' : 'desktop') !== readerMode) return;
    lastPosition = capturePosition();
  }

  function queueProgress() {
    if (progressFrame != null) return;
    progressFrame = requestAnimationFrame(() => {
      progressFrame = null;
      rememberPosition();
      window.clearTimeout(progressTimer);
      progressTimer = window.setTimeout(persistProgress, 250);
    });
  }

  function restorePosition(mode, saved) {
    const viewport = document.scrollingElement;
    let top = sectionStart(mode);
    if (saved && !saved.atStart) {
      const blocks = contentFor(mode).querySelectorAll(blockSelector);
      const block = Number.isInteger(saved.block) ? blocks[saved.block] : null;
      if (block && readableBlock(block)) {
        const rect = block.getBoundingClientRect();
        const fraction = Number.isFinite(saved.fraction) ? clamp(saved.fraction, 0, 1) : 0;
        const gap = Number.isFinite(saved.gap) ? clamp(saved.gap, 0, viewport.clientHeight) : 0;
        top = viewport.scrollTop + rect.top + fraction * rect.height - readingTop(mode) - gap;
      } else if (Number.isFinite(saved.ratio)) {
        top = clamp(saved.ratio, 0, 1) * Math.max(0, viewport.scrollHeight - viewport.clientHeight);
      }
    }
    window.scrollTo({ top, behavior: 'instant' });
  }

  function sectionCacheKey(section) { return `${currentBook.id}:${section.id}`; }

  async function getSectionHtml(section) {
    const key = sectionCacheKey(section);
    if (!sectionCache.has(key)) {
      const response = await fetch(`${currentBook.sectionPath}/${encodeURIComponent(section.id)}.json`, { cache: 'no-store' });
      if (!response.ok) throw new Error('section unavailable');
      const data = await response.json();
      sectionCache.set(key, data.html);
    }
    return sectionCache.get(key);
  }

  function scanHtml(book, page) {
    const pageNumber = String(page + 1).padStart(3, '0');
    return `<div class="scan-frame"><img class="scan-page" src="${book.pagePath.replace('{page}', pageNumber)}" alt="${escapeText(book.title)} 第 ${page + 1} 页" /></div>`;
  }

  function wrapTables(target) {
    target.querySelectorAll('table').forEach((table) => {
      const wrapper = document.createElement('div');
      wrapper.className = 'table-scroll';
      wrapper.setAttribute('role', 'region');
      wrapper.setAttribute('aria-label', '可横向滚动的表格');
      wrapper.setAttribute('tabindex', '0');
      table.parentNode.insertBefore(wrapper, table);
      wrapper.appendChild(table);
    });
  }


  function updateScanSummary() {
    if (!currentBook || currentBook.type !== 'scan') return;
    const text = `当前第 ${current + 1} 页，共 ${currentBook.pageCount} 页`;
    document.querySelector('#desktop-scan-summary').textContent = text;
    document.querySelector('#mobile-scan-summary').textContent = text;
  }

  async function renderSection(mode, saved = null, direction = 0) {
    if (current < 0) {
      renderEmptyBookState();
      return;
    }
    const token = ++renderToken;
    rendering = true;
    const target = contentFor(mode);
    target.classList.remove('page-turn-next', 'page-turn-prev');
    syncSectionMeta();
    updateScanSummary();
    ReaderNotes.clear();
    target.setAttribute('aria-busy', 'true');
    target.innerHTML = '<p class="loading-copy" role="status">正在打开这一节……</p>';
    try {
      const html = currentBook.type === 'scan' ? scanHtml(currentBook, current) : await getSectionHtml(currentBook.sections[current]);
      if (token !== renderToken) return;
      target.innerHTML = ReaderNotes.restoreMarkup(html);
      wrapTables(target);
      if (currentBook.type !== 'scan') await ReaderNotes.prepare(target, currentBook);
      if (token !== renderToken) return;
      // Some editions repeat the section title as their first content block.
      // Keep the source text and its anchors; hide only the generated title.
      let firstBlock = Array.from(target.querySelectorAll('h1,h2,h3,h4,h5,h6,p,li,blockquote'))
        .find((el) => !el.classList.contains('page-marker') && el.textContent.trim());
      const visibleHeadingText = (element) => {
        const copy = element.cloneNode(true);
        copy.querySelectorAll('sup').forEach((sup) => sup.remove());
        return copy.textContent;
      };
      const duplicateHeading = Boolean(firstBlock && ReaderHeadingMatcher.isDuplicateFirstTitle(
        currentBook.sections?.[current]?.title || '', visibleHeadingText(firstBlock), firstBlock.tagName
      ));
      if (duplicateHeading) {
        document.querySelector(mode === 'mobile' ? '#mobile-section-title' : '#section-title').classList.add('is-hidden');
        if (firstBlock.tagName === 'P') {
          const heading = document.createElement('h2');
          Array.from(firstBlock.attributes).forEach(({ name, value }) => heading.setAttribute(name, value));
          heading.classList.add('chapter-heading');
          heading.append(...firstBlock.childNodes);
          firstBlock.replaceWith(heading);
          firstBlock = heading;
        } else firstBlock.classList.add('chapter-heading');
      }
      // Treat source headings as children of the reader's generated section title.
      let previousHeadingLevel = 2;
      target.querySelectorAll('h1,h2,h3,h4,h5,h6').forEach((heading) => {
        const sourceLevel = Number(heading.tagName.slice(1));
        const level = duplicateHeading && heading === firstBlock
          ? 2
          : Math.max(3, Math.min(sourceLevel, previousHeadingLevel + 1));
        if (level !== sourceLevel) {
          const replacement = document.createElement(`h${level}`);
          Array.from(heading.attributes).forEach(({ name, value }) => replacement.setAttribute(name, value));
          const computed = getComputedStyle(heading);
          replacement.style.fontSize = computed.fontSize;
          replacement.style.marginBlockStart = computed.marginBlockStart;
          replacement.style.marginBlockEnd = computed.marginBlockEnd;
          replacement.style.lineHeight = computed.lineHeight;
          replacement.append(...heading.childNodes);
          heading.replaceWith(replacement);
        }
        previousHeadingLevel = level;
      });
      const notes = target.querySelectorAll('details');
      if (Array.isArray(saved?.openNotes)) saved.openNotes.forEach((i) => {
        if (Number.isInteger(i) && notes[i]) notes[i].open = true;
      });
      await Promise.all(Array.from(target.querySelectorAll('img')).map((img) => img.decode().catch(() => {})));
      if (direction) target.classList.add(direction > 0 ? 'page-turn-next' : 'page-turn-prev');
      requestAnimationFrame(() => {
        if (token !== renderToken || reader.classList.contains('is-hidden')) return;
        restorePosition(mode, saved);
        rendering = false;
        target.setAttribute('aria-busy', 'false');
        target.focus({ preventScroll: true });
        rememberPosition();
        persistProgress();
      });
    } catch {
      if (token === renderToken) {
        target.setAttribute('aria-busy', 'false');
        target.innerHTML = '<p class="loading-copy" role="status">这一节暂时无法打开，请点击目录后重试。</p>';
      }
    }
  }

  function activateReaderMode(force = false, saved = null) {
    if (!currentBook) return;
    const nextMode = isMobileReader() ? 'mobile' : 'desktop';
    if (!force && nextMode === readerMode) {
      return;
    }
    readerMode = nextMode;
    desktopReader.hidden = nextMode === 'mobile';
    mobileReader.hidden = nextMode !== 'mobile';
    document.body.classList.toggle('mobile-reader-open', nextMode === 'mobile');
    closeToc(false);
    setMobileChrome(false);
    renderSection(nextMode, saved);
  }

  function openSection(index) {
    if (!currentBook || current < 0) return;
    rememberPosition();
    persistProgress();
    const previousPosition = visibleSectionPosition(currentBook, current).position;
    const total = currentBook.type === 'scan' ? currentBook.pageCount : currentBook.sections.length;
    current = currentBook.type === 'scan'
      ? clamp(index, 0, total - 1)
      : visibleSectionIndex(currentBook, index);
    rendering = true;
    lastPosition = { atStart: true };
    writeReaderLocation('replace');
    syncRouteMetadata();
    persistProgress();
    renderToc();
    syncBookMeta();
    const nextPosition = visibleSectionPosition(currentBook, current).position;
    renderSection(readerMode, null, Math.sign(nextPosition - previousPosition));
  }

  function openReader(bookIndex, sectionId = null, { historyMode = 'push', position = null } = {}) {
    currentBook = books[bookIndex];
    if (!currentBook) return;
    const saved = readProgress(currentBook);
    const requestedSectionIndex = sectionId && currentBook.type !== 'scan'
      ? currentBook.sections.findIndex((section) => section.id === sectionId)
      : -1;
    const requestedIndex = requestedSectionIndex >= 0 ? requestedSectionIndex : saved ? saved.index : 0;
    current = currentBook.type === 'scan' ? requestedIndex : visibleSectionIndex(currentBook, requestedIndex);
    const savedPosition = saved?.index === current ? saved.position : null;
    lastPosition = position || (requestedSectionIndex >= 0 ? { atStart: true } : savedPosition || { atStart: true });
    rendering = true;
    if (historyMode === 'none') {
      ensureRouteKey();
      if (sectionId && currentBook.sections[current]?.id !== sectionId) writeReaderLocation('replace');
    }
    else writeReaderLocation(historyMode);
    syncRouteMetadata();
    writeStored(activeBookKey, currentBook.id);
    shelf.classList.add('is-hidden');
    reader.classList.remove('is-hidden');
    document.body.classList.add('book-open');
    renderToc();
    syncBookMeta();
    activateReaderMode(true, lastPosition);
  }

  function closeReader() {
    ReaderNotes.clear();
    rememberPosition();
    persistProgress();
    ++renderToken;
    rendering = false;
    closeToc(false);
    writeStored(activeBookKey, null);
    writeShelfLocation();
    reader.classList.add('is-hidden');
    shelf.classList.remove('is-hidden');
    document.body.classList.remove('book-open', 'mobile-reader-open', 'mobile-toc-open');
    setMobileChrome(false);
    const bookIndex = books.indexOf(currentBook);
    currentBook = null;
    renderShelf();
    syncRouteMetadata();
    window.scrollTo({ top: 0, behavior: 'instant' });
    shelf.querySelector(`[data-book="${bookIndex}"]`)?.focus({ preventScroll: true });
  }

  function readerShareUrl() {
    if (!currentBook || current < 0) return '';
    const url = new URL(window.location.href);
    url.searchParams.set('book', currentBook.id);
    url.searchParams.set('section', currentBook.type === 'scan'
      ? String(current + 1)
      : currentBook.sections[current]?.id || '');
    if (activeAuthor) url.searchParams.set('author', activeAuthor.id);
    else url.searchParams.delete('author');
    return url.href;
  }

  function announceShareStatus(message) {
    shareStatus.textContent = message;
    shareStatus.hidden = !message;
    window.clearTimeout(shareStatusTimer);
    if (message) shareStatusTimer = window.setTimeout(() => { shareStatus.hidden = true; }, 5000);
  }

  function showShareFallback(url) {
    shareUrlInput.value = url;
    document.querySelector('#share-dialog-help').textContent = '自动复制失败。链接已选中，可手动复制。';
    if (!shareDialog.open) shareDialog.showModal();
    requestAnimationFrame(() => {
      shareUrlInput.focus();
      shareUrlInput.select();
    });
    announceShareStatus('无法自动复制，请复制弹窗中已选中的链接。');
  }

  async function copyReaderLink() {
    const url = readerShareUrl();
    if (!url) return;
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard API unavailable');
      await navigator.clipboard.writeText(url);
      if (shareDialog.open) shareDialog.close();
      announceShareStatus('阅读链接已复制。');
    } catch {
      showShareFallback(url);
    }
  }

  document.querySelectorAll('[data-size]').forEach((button) => button.addEventListener('click', () => {
    rememberPosition();
    applyReadingSize(button.dataset.size, true);
    if (currentBook && !rendering && !reader.classList.contains('is-hidden')) {
      restorePosition(readerMode, lastPosition);
      rememberPosition();
      persistProgress();
    }
  }));
  document.querySelectorAll('[data-spacing]').forEach((button) => button.addEventListener('click', () => {
    rememberPosition();
    applyLineSpacing(button.dataset.spacing, true);
    if (currentBook && !rendering && !reader.classList.contains('is-hidden')) {
      restorePosition(readerMode, lastPosition);
      rememberPosition();
      persistProgress();
    }
  }));
  document.querySelectorAll('button[data-reading-font]').forEach((button) => button.addEventListener('click', () => {
    const choice = ++fontChoiceToken;
    const bookAtChoice = currentBook;
    const sectionAtChoice = current;
    const font = button.dataset.readingFont;
    rememberPosition();
    const position = lastPosition;
    applyReadingFont(font, true);
    document.querySelectorAll('.font-load-status').forEach((status) => {
      status.textContent = font === 'system' ? '' : '正在加载字体，正文仍可继续阅读。';
    });
    if (currentBook && !rendering && !reader.classList.contains('is-hidden')) {
      restorePosition(readerMode, position);
      rememberPosition();
      persistProgress();
    }
    const positionAfterChoice = lastPosition;
    if (font !== 'system') readingFontReady(font).then((loaded) => {
      if (choice !== fontChoiceToken || document.documentElement.dataset.readingFont !== font) return;
      document.querySelectorAll('.font-load-status').forEach((status) => {
        status.textContent = loaded ? '' : '字体未能载入，正文继续使用后备字体。';
      });
      if (loaded && currentBook === bookAtChoice && current === sectionAtChoice
          && lastPosition === positionAfterChoice && !rendering && !reader.classList.contains('is-hidden')) {
        restorePosition(readerMode, position);
        rememberPosition();
        persistProgress();
      }
    });
    const details = button.closest('details');
    if (details && font === 'system') {
      details.open = false;
      details.querySelector('summary')?.focus({ preventScroll: true });
    }
  }));
  mobileReader.querySelector('.mobile-font-settings').addEventListener('toggle', (event) => {
    if (readerMode === 'mobile') setMobileChrome(true, !event.target.open);
  });

  mobileTocToggle.addEventListener('click', (event) => { event.stopPropagation(); setTocOpen(!mobileTocPanel.classList.contains('is-open')); });
  setDesktopTocCollapsed(readStored('reading-desk:desktop-toc-collapsed:v1') === true);
  desktopTocToggle.addEventListener('click', () => {
    setDesktopTocCollapsed(!desktopReader.classList.contains('toc-collapsed'));
  });
  mobileTocClose.addEventListener('click', (event) => { event.stopPropagation(); closeToc(); });
  mobileTocBackdrop.addEventListener('click', () => closeToc());
  desktopPrevChapter.addEventListener('click', () => openSection(adjacentSectionIndex(currentBook, current, -1)));
  desktopNextChapter.addEventListener('click', () => openSection(adjacentSectionIndex(currentBook, current, 1)));
  desktopBack.addEventListener('click', closeReader);
  mobileBack.addEventListener('click', (event) => { event.stopPropagation(); closeReader(); });
  desktopShareButton.addEventListener('click', copyReaderLink);
  mobileShareButton.addEventListener('click', copyReaderLink);
  shareCopyRetry.addEventListener('click', copyReaderLink);
  window.addEventListener('popstate', (event) => {
    if (books.length) applyLocation({ state: event.state });
  });

  mobileViewport.addEventListener('click', (event) => {
    if (event.target.closest('button, details, summary, a, input, select')) return;
    setMobileChrome(!mobileReader.classList.contains('chrome-visible'), true);
  });

  window.addEventListener('scroll', queueProgress, { passive: true });
  // Ordinary resize/URL-bar changes never replace content or dismiss the drawer.
  window.addEventListener('resize', queueProgress, { passive: true });
  desktopContent.addEventListener('toggle', queueProgress, true);
  mobileContent.addEventListener('toggle', queueProgress, true);
  modeQuery.addEventListener('change', () => {
    if (reader.classList.contains('is-hidden')) return;
    // Layout is already switched here; use the last visible position, but read
    // disclosure state directly because a pending toggle event may not have run.
    lastPosition = {
      ...lastPosition,
      openNotes: Array.from(contentFor(readerMode).querySelectorAll('details')).flatMap((el, i) => el.open ? [i] : [])
    };
    persistProgress();
    activateReaderMode(false, lastPosition);
  });
  document.addEventListener('keydown', (event) => {
    if (reader.classList.contains('is-hidden')) return;
    const tocOpen = mobileTocPanel.classList.contains('is-open');
    if (event.key === 'Escape') {
      event.preventDefault();
      if (tocOpen) closeToc();
      else {
        const settings = reader.querySelector('.settings[open]');
        if (settings) {
          settings.open = false;
          settings.querySelector('summary')?.focus({ preventScroll: true });
        } else setMobileChrome(false);
      }
    }
    if (event.key === 'Tab' && tocOpen) {
      const focusable = Array.from(mobileTocPanel.querySelectorAll('button:not([disabled]), a[href]'));
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && (document.activeElement === first || !mobileTocPanel.contains(document.activeElement))) {
        event.preventDefault(); last.focus();
      } else if (!event.shiftKey && (document.activeElement === last || !mobileTocPanel.contains(document.activeElement))) {
        event.preventDefault(); first.focus();
      }
    }
  });

  // Keyboard users can reveal the same minimal controls without a pointer tap.
  mobileViewport.addEventListener('keydown', (event) => {
    if (event.key === 'Tab' && !mobileReader.classList.contains('chrome-visible')) {
      event.preventDefault();
      setMobileChrome(true);
      (event.shiftKey ? mobileTocToggle : mobileBack).focus({ preventScroll: true });
    }
  });
  function flushProgress() { rememberPosition(); persistProgress(); }
  window.addEventListener('pagehide', flushProgress);
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') flushProgress();
  });
  if ('scrollRestoration' in history) history.scrollRestoration = 'manual';

  bookSearch.addEventListener('input', renderShelf);
  authorBack.addEventListener('click', () => writeStored(activeBookKey, null));
  authorClearFilters.addEventListener('click', () => {
    bookSearch.value = '';
    activeCategory = 'all';
    categoryFilters.querySelectorAll('[data-category]').forEach((filter) => {
      filter.setAttribute('aria-pressed', String(filter.dataset.category === 'all'));
    });
    renderShelf();
  });
  loadBooks().catch(() => { bookList.innerHTML = '<div class="loading-card">暂时无法打开书架，请稍后重试。</div>'; });
})();
