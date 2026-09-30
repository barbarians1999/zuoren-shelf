(() => {
  const shelf = document.querySelector('#shelf');
  const bookList = document.querySelector('#book-list');
  const bookSearch = document.querySelector('#book-search');
  const shelfCount = document.querySelector('#shelf-count');
  const categoryFilters = document.querySelector('#category-filters');
  const reader = document.querySelector('#reader');
  const desktopReader = document.querySelector('#desktop-reader');
  const mobileReader = document.querySelector('#mobile-reader');
  const desktopToc = document.querySelector('#desktop-toc');
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
  const modeQuery = window.matchMedia('(max-width: 700px)');

  let books = [];
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
  const progressPrefix = 'reading-desk:progress:v1:';
  const activeBookKey = 'reading-desk:active-book:v1';
  const blockSelector = 'h1,h2,h3,h4,h5,h6,p,li,blockquote,summary,img';
  const sectionCache = new Map();

  const categories = [
    { id: 'all', label: '全部' },
    { id: 'classics', label: '马列经典' },
    { id: 'china', label: '中国史与革命' },
    { id: 'international', label: '国际共运史' },
    { id: 'literature', label: '文学与回忆录' },
    { id: 'economics', label: '政治经济' }
  ];
  window.bookCategoryById = Object.freeze({
    'howto': 'classics', 'jintui-text': 'classics', 'zuopai-text': 'classics', 'lenin-selected': 'classics',
    'natural-dialectics': 'classics', 'women-socialism': 'classics', 'imperialism': 'classics',
    'state-and-revolution': 'classics', 'manifesto': 'classics', 'german-ideology': 'classics',
    'class-struggles-france': 'classics', 'eighteenth-brumaire': 'classics', 'civil-war': 'classics',
    'ludwig-feuerbach': 'classics', 'anti-duhring': 'classics', 'british-working-class': 'classics',
    'bloodfire': 'china', 'maodazhuan-text': 'china', 'mao-selected': 'china', 'obtain-authority': 'china',
    'wenge-history': 'china', 'republic-course': 'china', 'two-routes-course': 'china',
    'ccp-history-course-upper': 'china', 'ccp-history-course-lower': 'china',
    'history': 'international', 'bolshevik-text': 'international', 'soviet-party-history-vol1': 'international',
    'soviet-party-history-vol2': 'international', 'russian-workers': 'international',
    'route-dispute': 'international',
    'german-revolution-1878-1919': 'international', 'international-movement-course-vol1': 'international',
    'international-movement-course-vol2': 'international', 'international-movement-course-vol3': 'international',
    'international-movement-course-vol4': 'international',
    'huangjin-text': 'literature', 'qibenyu-text': 'literature', 'zhangchunqiao-letters': 'literature',
    'luxun-text': 'literature', 'red-star-over-china': 'literature', 'fanshen': 'literature',
    'shenfan': 'literature', 'great-reversal': 'literature', 'shanghai-morning': 'literature', 'redrock': 'literature',
    'global-monopoly-text': 'economics', 'keynes-china-crisis': 'economics',
    'political-economy-introduction': 'economics'
  });

  const escapeText = (value) => String(value).replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
  const isMobileReader = () => modeQuery.matches;
  const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

  async function loadBooks() {
    const response = await fetch('book-index.json', { cache: 'no-store' });
    if (!response.ok) throw new Error('books unavailable');
    const data = await response.json();
    books = data.books || [];
    renderCategoryFilters();
    renderShelf();
    const activeBook = readStored(activeBookKey);
    const index = books.findIndex((book) => book.id === activeBook);
    if (index !== -1) openReader(index);
  }

  function renderCategoryFilters() {
    categoryFilters.innerHTML = categories.map((category) => {
      const count = category.id === 'all'
        ? books.length
        : books.filter((book) => window.bookCategoryById[book.id] === category.id).length;
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

  function renderShelf() {
    const terms = bookSearch.value.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
    const visible = books.map((book, index) => ({ book, index, saved: readProgress(book) }))
      .filter(({ book }) => activeCategory === 'all' || window.bookCategoryById[book.id] === activeCategory)
      .filter(({ book }) => terms.every((term) => `${book.title} ${book.author}`.toLocaleLowerCase().includes(term)))
      .sort((a, b) => Number(Boolean(b.saved)) - Number(Boolean(a.saved)) || a.index - b.index);
    shelfCount.textContent = terms.length || activeCategory !== 'all' ? `找到 ${visible.length} 本` : `共 ${books.length} 本`;
    bookList.innerHTML = visible.length ? visible.map(({ book, index, saved }) => {
      const isScan = book.type === 'scan';
      const units = isScan ? `${book.pageCount} 页` : `${book.sections.length} 个阅读单元`;
      const status = isScan ? '逐页加载' : '分段加载';
      return `<article class="book-card ${saved ? 'ready' : ''}"><div><p class="eyebrow">${saved ? '继续阅读' : '书籍'}</p><h2>${escapeText(book.title)}</h2><p class="book-byline">${escapeText(book.author)} · ${escapeText(units)}</p><p class="book-note">${escapeText(book.note || '')}</p></div><div class="book-foot"><span class="book-status">${escapeText(status)}</span><button class="open-button" type="button" data-book="${index}" aria-label="${saved ? '继续阅读' : '打开'}《${escapeText(book.title)}》">${saved ? '继续阅读' : '打开阅读'}</button></div></article>`;
    }).join('') : '<p class="shelf-empty">没有找到这本书，试试书名中的其他字或作者名。</p>';
    bookList.querySelectorAll('[data-book]').forEach((button) => button.addEventListener('click', () => openReader(Number(button.dataset.book))));
  }

  function renderToc() {
    if (!currentBook) return;
    const html = currentBook.type === 'scan'
      ? '<p class="toc-hint">使用下方章节按钮翻页</p>'
      : currentBook.sections.map((section, index) => {
        const chapterHeading = section.chapter && section.chapter !== currentBook.sections[index - 1]?.chapter
          ? `<h3 class="toc-group">${escapeText(section.chapter)}</h3>` : '';
        return `${chapterHeading}<button class="toc-link ${index === current ? 'active' : ''}" data-index="${index}" data-level="${section.level || 0}" type="button">${section.chapter ? '' : `${index + 1}. `}${escapeText(section.title)}</button>`;
      }).join('');
    desktopToc.innerHTML = html;
    mobileToc.innerHTML = html;
    [desktopToc, mobileToc].forEach((nav) => nav.querySelectorAll('.toc-link').forEach((button) => button.addEventListener('click', () => {
      closeToc(false);
      openSection(Number(button.dataset.index));
    })));
  }

  function setTocOpen(open, returnFocus = true) {
    const wasOpen = mobileTocPanel.classList.contains('is-open');
    if (open && readerMode !== 'mobile') return;
    if (open) setMobileChrome(true);
    mobileTocPanel.inert = !open;
    mobileViewport.inert = open;
    mobileReader.querySelector('.mobile-reader-head').inert = open;
    if (!open && wasOpen && returnFocus && readerMode === 'mobile') {
      setMobileChrome(true, true);
      mobileTocToggle.focus({ preventScroll: true });
    } else if (!open && mobileTocPanel.contains(document.activeElement)) {
      document.activeElement.blur();
    }
    mobileTocPanel.setAttribute('aria-hidden', String(!open));
    if (open) mobileTocPanel.setAttribute('aria-modal', 'true');
    else mobileTocPanel.removeAttribute('aria-modal');
    mobileTocPanel.classList.toggle('is-open', open);
    mobileTocBackdrop.classList.toggle('is-open', open);
    mobileTocToggle.setAttribute('aria-expanded', String(open));
    document.body.classList.toggle('mobile-toc-open', open);
    if (open) {
      const active = mobileToc.querySelector('.active') || mobileTocClose;
      active.focus({ preventScroll: true });
      const rect = active.getBoundingClientRect();
      const panelRect = mobileTocPanel.getBoundingClientRect();
      mobileTocPanel.scrollTop += rect.top - panelRect.top - mobileTocPanel.clientHeight / 2;
    }
  }

  function closeToc(returnFocus = true) { setTocOpen(false, returnFocus); }

  function setMobileChrome(visible, autoHide = false) {
    mobileReader.classList.toggle('chrome-visible', visible);
    mobileReader.setAttribute('aria-label', visible ? '阅读控件已显示' : '阅读控件已隐藏');
    if (hideChromeTimer) window.clearTimeout(hideChromeTimer);
    if (visible && autoHide && isMobileReader()) hideChromeTimer = window.setTimeout(() => {
      if (!mobileTocPanel.classList.contains('is-open') && !mobileReader.querySelector('.mobile-reader-head :focus-visible')) setMobileChrome(false);
    }, 5000);
  }

  function syncBookMeta() {
    const total = currentBook.type === 'scan' ? currentBook.pageCount : currentBook.sections.length;
    document.querySelector('#section-count').textContent = currentBook.type === 'scan' ? `${total} 页` : `${total} 个阅读单元`;
    document.querySelector('#book-title').textContent = currentBook.title;
    document.querySelector('#book-author').textContent = currentBook.author;
    document.querySelector('#mobile-book-title').textContent = currentBook.title;
    document.querySelector('#mobile-reading-position').textContent = `${current + 1} / ${total}`;
    desktopPrevChapter.disabled = current === 0;
    desktopNextChapter.disabled = current === total - 1;
  }

  function syncSectionMeta() {
    const title = currentBook.type === 'scan' ? `第 ${current + 1} 页` : currentBook.sections[current].title;
    document.querySelector('#section-title').textContent = title;
    document.querySelector('#mobile-section-title').textContent = title;
    const bodyIncludesTitle = currentBook.type !== 'scan' && currentBook.sections[current].bodyIncludesTitle === true;
    document.querySelector('#section-title').classList.toggle('is-hidden', bodyIncludesTitle);
    document.querySelector('#mobile-section-title').classList.toggle('is-hidden', bodyIncludesTitle);
    document.querySelector('#reading-position').textContent = `${current + 1} / ${currentBook.type === 'scan' ? currentBook.pageCount : currentBook.sections.length}`;
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
  function scrollOwner(mode) { return mode === 'mobile' ? mobileViewport : document.scrollingElement; }
  function readingTop(mode) {
    return mode === 'mobile' ? mobileViewport.getBoundingClientRect().top + 12
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
    const viewport = scrollOwner(mode);
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
    if (!currentBook || !lastPosition || reader.classList.contains('is-hidden')) return;
    writeStored(progressPrefix + currentBook.id, {
      version: 1, source: currentBook.sectionPath || currentBook.pagePath,
      sectionId: sectionIdentity(currentBook, current), position: lastPosition
    });
  }

  function rememberPosition() {
    if (rendering || !currentBook || reader.classList.contains('is-hidden')) return;
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
    const viewport = scrollOwner(mode);
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
    if (mode === 'mobile') mobileViewport.scrollTo({ top, behavior: 'instant' });
    else window.scrollTo({ top, behavior: 'instant' });
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

  async function renderSection(mode, saved = null) {
    const token = ++renderToken;
    rendering = true;
    const target = contentFor(mode);
    syncSectionMeta();
    updateScanSummary();
    target.setAttribute('aria-busy', 'true');
    target.innerHTML = '<p class="loading-copy" role="status">正在打开这一节……</p>';
    try {
      const html = currentBook.type === 'scan' ? scanHtml(currentBook, current) : await getSectionHtml(currentBook.sections[current]);
      if (token !== renderToken) return;
      target.innerHTML = html;
      wrapTables(target);
      const notes = target.querySelectorAll('details');
      if (Array.isArray(saved?.openNotes)) saved.openNotes.forEach((i) => {
        if (Number.isInteger(i) && notes[i]) notes[i].open = true;
      });
      await Promise.all(Array.from(target.querySelectorAll('img')).map((img) => img.decode().catch(() => {})));
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
    if (!currentBook) return;
    rememberPosition();
    persistProgress();
    const total = currentBook.type === 'scan' ? currentBook.pageCount : currentBook.sections.length;
    current = clamp(index, 0, total - 1);
    rendering = true;
    lastPosition = { atStart: true };
    persistProgress();
    renderToc();
    syncBookMeta();
    renderSection(readerMode);
  }

  function openReader(bookIndex) {
    currentBook = books[bookIndex];
    if (!currentBook) return;
    const saved = readProgress(currentBook);
    current = saved ? saved.index : 0;
    lastPosition = saved?.position || { atStart: true };
    rendering = true;
    writeStored(activeBookKey, currentBook.id);
    shelf.classList.add('is-hidden');
    reader.classList.remove('is-hidden');
    document.body.classList.add('book-open');
    renderToc();
    syncBookMeta();
    activateReaderMode(true, lastPosition);
  }

  function closeReader() {
    rememberPosition();
    persistProgress();
    ++renderToken;
    rendering = false;
    closeToc(false);
    writeStored(activeBookKey, null);
    reader.classList.add('is-hidden');
    shelf.classList.remove('is-hidden');
    document.body.classList.remove('book-open', 'mobile-reader-open', 'mobile-toc-open');
    setMobileChrome(false);
    renderShelf();
    const bookIndex = books.indexOf(currentBook);
    currentBook = null;
    window.scrollTo({ top: 0, behavior: 'instant' });
    shelf.querySelector(`[data-book="${bookIndex}"]`)?.focus({ preventScroll: true });
  }

  document.querySelectorAll('[data-size]').forEach((button) => button.addEventListener('click', () => {
    const sizes = { small: '1rem', medium: 'clamp(1.08rem, 1.8vw, 1.24rem)', large: 'clamp(1.28rem, 2.2vw, 1.5rem)' };
    document.documentElement.style.setProperty('--reading-size', sizes[button.dataset.size]);
  }));
  document.querySelectorAll('[data-spacing="wide"]').forEach((button) => button.addEventListener('click', () => {
    document.documentElement.style.setProperty('--reading-leading', '2.25');
  }));

  mobileTocToggle.addEventListener('click', (event) => { event.stopPropagation(); setTocOpen(!mobileTocPanel.classList.contains('is-open')); });
  mobileTocClose.addEventListener('click', (event) => { event.stopPropagation(); closeToc(); });
  mobileTocBackdrop.addEventListener('click', () => closeToc());
  desktopPrevChapter.addEventListener('click', () => openSection(current - 1));
  desktopNextChapter.addEventListener('click', () => openSection(current + 1));
  desktopBack.addEventListener('click', closeReader);
  mobileBack.addEventListener('click', (event) => { event.stopPropagation(); closeReader(); });

  mobileViewport.addEventListener('click', (event) => {
    if (event.target.closest('button, details, summary, a, input, select')) return;
    setMobileChrome(!mobileReader.classList.contains('chrome-visible'), true);
  });

  window.addEventListener('scroll', queueProgress, { passive: true });
  mobileViewport.addEventListener('scroll', queueProgress, { passive: true });
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
      if (tocOpen) closeToc(); else setMobileChrome(false);
    }
    if (event.key === 'Tab' && tocOpen) {
      const focusable = Array.from(mobileTocPanel.querySelectorAll('button:not([disabled])'));
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
  loadBooks().catch(() => { bookList.innerHTML = '<div class="loading-card">暂时无法打开书架，请稍后重试。</div>'; });
})();
