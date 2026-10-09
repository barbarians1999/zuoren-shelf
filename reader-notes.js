(() => {
  'use strict';
  const noteCache = new Map();
  const extraSources = {
    'jintui-text': { 'section-026': false, 'section-027': true },
    'zuopai-text': { 'section-022': false }
  };
  const noteContainers = 'aside.footnote, aside.ocr-notes, details.book-notes';
  const noteHeading = /^(?:原作)?(?:注释|原注|译注|编者注)[：:]?$/;
  const markerPattern = /^\s*([①-⑳]|[［\[]?原注\s*[0-9０-９]+[］\]]?|[［\[（(【][0-9０-９]+[］\]）)】]|[0-9０-９]{1,3}(?=\s|[、．:：《“「\u3400-\u9fff]|\.(?![0-9０-９]))|[*†‡])(?:[、.．:：]\s*)?\s*/;
  let epoch = 0;
  let popover = null;
  let activeTrigger = null;

  function key(value) {
    const raw = String(value).trim();
    if (/^[①-⑳]$/.test(raw)) return `circle:${raw.normalize('NFKC')}`;
    const normalized = raw.normalize('NFKC').replace(/[\[\]()【】\s]/g, '');
    if (/^原注\d+$/.test(normalized)) return `original:${normalized.slice(2)}`;
    if (/^\d+$/.test(normalized)) return `number:${normalized}`;
    return /^(?:[*†‡]|注)$/.test(normalized) ? `symbol:${normalized}` : '';
  }

  function restoreMarkup(html) {
    // Decode only bare formatting tags. Never turn escaped attributes/scripts
    // from a book into active HTML.
    return String(html).replace(/&(?:amp;)?lt;\s*(\/?)\s*(sup|sub)\s*&(?:amp;)?gt;/gi, '<$1$2>');
  }

  function safeHtml(html) {
    const template = document.createElement('template');
    template.innerHTML = html;
    template.content.querySelectorAll('script,style,iframe,object,embed,link,form,input,button,img').forEach((node) => node.remove());
    template.content.querySelectorAll('*').forEach((node) => {
      Array.from(node.attributes).forEach((attribute) => node.removeAttribute(attribute.name));
      if (!/^(P|BR|STRONG|B|EM|I|SPAN|BLOCKQUOTE|UL|OL|LI|SUP|SUB|HR|CODE)$/.test(node.tagName)) node.replaceWith(...node.childNodes);
    });
    return template.innerHTML;
  }

  function withoutPrefix(node, count) {
    const copy = node.cloneNode(true);
    const walker = document.createTreeWalker(copy, NodeFilter.SHOW_TEXT);
    let text;
    while (count > 0 && (text = walker.nextNode())) {
      const removed = Math.min(count, text.nodeValue.length);
      text.nodeValue = text.nodeValue.slice(removed);
      count -= removed;
    }
    return `<p>${safeHtml(copy.innerHTML)}</p>`;
  }

  function collectDefinitions(root, startInNotes = false) {
    const definitions = [];
    let inNotes = startInNotes;
    let current = null;
    root.querySelectorAll('h1,h2,h3,h4,h5,h6,p,li,aside.footnote').forEach((node) => {
      if (node.closest('aside.footnote') && !node.matches('aside.footnote')) return;
      const text = node.textContent;
      const compact = text.replace(/\s+/g, '');
      if (noteHeading.test(compact)) { inNotes = true; current = null; return; }
      const container = node.closest(noteContainers);
      const match = text.match(markerPattern);
      if (/^H[1-6]$/.test(node.tagName) && !(inNotes && match)) { inNotes = false; current = null; return; }
      const eligible = inNotes || Boolean(container) || /——编者注|（编者注）/.test(text);
      if (eligible && match && key(match[1])) {
        current = { key: key(match[1]), html: withoutPrefix(node, match[0].length), nodes: [node], scope: node.closest('section.page') || root, container };
        definitions.push(current);
      } else if (current && (inNotes || (container && container === current.container))) {
        current.html += `<p>${safeHtml(node.innerHTML)}</p>`;
        current.nodes.push(node);
      } else current = null;
    });
    return definitions;
  }

  async function bookDefinitions(book) {
    if (noteCache.has(book.id)) return noteCache.get(book.id);
    const extra = extraSources[book.id] || {};
    const candidates = (book.sections || []).filter((section) => noteHeading.test(section.title.replace(/\s+/g, ''))
      || Object.hasOwn(extra, section.id));
    const pending = Promise.all(candidates.map(async (section) => {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 8000);
      try {
        const response = await fetch(`${book.sectionPath}/${encodeURIComponent(section.id)}.json`, { cache: 'no-store', signal: controller.signal });
        if (!response.ok) throw new Error('notes unavailable');
        const data = await response.json();
        const root = document.createElement('div');
        root.innerHTML = restoreMarkup(data.html);
        const startsInNotes = noteHeading.test(section.title.replace(/\s+/g, '')) || extra[section.id] === true;
        return collectDefinitions(root, startsInNotes).map(({ key: noteKey, html }) => ({ key: noteKey, html }));
      } finally { clearTimeout(timer); }
    })).then((groups) => ({ notes: groups.flat(), failed: false })).catch(() => {
      noteCache.delete(book.id);
      return { notes: [], failed: true };
    });
    noteCache.set(book.id, pending);
    return pending;
  }

  function close(restoreFocus = false) {
    if (popover) popover.hidden = true;
    if (activeTrigger) {
      activeTrigger.setAttribute('aria-expanded', 'false');
      if (restoreFocus && activeTrigger.isConnected) activeTrigger.focus({ preventScroll: true });
    }
    activeTrigger = null;
  }

  function clear() { epoch++; close(); }

  function show(trigger, keyboard) {
    if (activeTrigger === trigger) { close(); return; }
    close();
    if (!popover) {
      popover = document.createElement('div');
      popover.className = 'footnote-popover';
      popover.id = 'reader-note-popover';
      popover.setAttribute('role', 'dialog');
      popover.setAttribute('aria-label', '注释');
      popover.addEventListener('click', (event) => { if (event.target.closest('.footnote-close')) close(true); });
      document.body.appendChild(popover);
    }
    popover.innerHTML = `<div class="footnote-popover-copy">${trigger._noteHtml}</div><button type="button" class="footnote-close" aria-label="关闭注释">×</button>`;
    activeTrigger = trigger;
    trigger.setAttribute('aria-expanded', 'true');
    popover.hidden = false;
    popover.scrollTop = 0;
    const anchor = trigger.getBoundingClientRect();
    const box = popover.getBoundingClientRect();
    const edge = 12;
    const left = Math.max(edge, Math.min(anchor.left, window.innerWidth - box.width - edge));
    const maxTop = Math.max(edge, window.innerHeight - box.height - edge);
    let top = anchor.bottom + 8;
    if (top > maxTop) top = anchor.top - box.height - 8;
    popover.style.left = `${left}px`;
    popover.style.top = `${Math.max(edge, Math.min(top, maxTop))}px`;
    if (keyboard) popover.querySelector('button').focus({ preventScroll: true });
  }

  function button(label, note) {
    const trigger = document.createElement('button');
    trigger.type = 'button';
    trigger.className = 'footnote-trigger';
    trigger.textContent = label;
    trigger.setAttribute('aria-label', `查看注释 ${label}`);
    trigger.setAttribute('aria-haspopup', 'dialog');
    trigger.setAttribute('aria-controls', 'reader-note-popover');
    trigger.setAttribute('aria-expanded', 'false');
    trigger._noteHtml = note.html;
    trigger.addEventListener('click', (event) => { event.stopPropagation(); show(trigger, event.detail === 0); });
    return trigger;
  }

  function isExponent(sup) {
    if (sup.closest('math,.math,.katex,mjx-container,code,pre')) return true;
    const previous = sup.previousSibling;
    return previous?.nodeType === Node.TEXT_NODE && /(?:\b[A-Za-z]|[0-9]+|\))$/.test(previous.textContent) && /^[-+−]?\d+$/.test(sup.textContent.trim());
  }

  async function prepare(target, book) {
    const ticket = epoch;
    const external = await bookDefinitions(book);
    if (ticket !== epoch) return;
    const local = collectDefinitions(target);
    const definitionNodes = new Set(local.flatMap((note) => note.nodes));
    const consumed = new Set();
    const lookup = (marker, reference) => {
      const noteKey = key(marker);
      const scope = reference.parentElement.closest('section.page') || target;
      const nearby = local.filter((note) => note.key === noteKey && note.scope === scope);
      if (nearby.length) return nearby.find((note) => reference.compareDocumentPosition(note.nodes[0]) & Node.DOCUMENT_POSITION_FOLLOWING) || nearby[0];
      const candidates = external.notes.filter((note) => note.key === noteKey);
      const unique = new Map(candidates.map((note) => [note.html, note]));
      return unique.size === 1 ? unique.values().next().value : null;
    };
    const insideDefinition = (node) => [...definitionNodes].some((definition) => definition === node || definition.contains(node));
    target.querySelectorAll('sup').forEach((sup) => {
      if (insideDefinition(sup) || isExponent(sup)) return;
      const note = lookup(sup.textContent, sup);
      if (note) {
        sup.replaceWith(button(sup.textContent, note));
        (note.nodes || []).forEach((node) => consumed.add(node));
      } else if (key(sup.textContent) && external.failed) {
        sup.replaceWith(button(sup.textContent, { html: '<p>注释暂时无法加载，请重开本节重试。</p>' }));
      } else if (key(sup.textContent)) sup.remove();
      else sup.replaceWith(...sup.childNodes);
    });
    const walker = document.createTreeWalker(target, NodeFilter.SHOW_TEXT);
    const textNodes = [];
    let node;
    while ((node = walker.nextNode())) {
      if (!node.parentElement.closest(`${noteContainers},sup,sub,button,a,code,pre,math`) && !insideDefinition(node)) textNodes.push(node);
    }
    textNodes.forEach((text) => {
      const matches = [...text.nodeValue.matchAll(/[［\[](?:原注\s*)?[0-9０-９]+[］\]]/g)];
      if (!matches.length) return;
      const fragment = document.createDocumentFragment();
      let offset = 0;
      let changed = false;
      matches.forEach((match) => {
        fragment.append(text.nodeValue.slice(offset, match.index));
        const note = lookup(match[0], text);
        if (note) {
          fragment.append(button(match[0], note));
          (note.nodes || []).forEach((definition) => consumed.add(definition));
          changed = true;
        } else fragment.append(match[0]);
        offset = match.index + match[0].length;
      });
      fragment.append(text.nodeValue.slice(offset));
      if (changed) text.replaceWith(fragment);
    });
    consumed.forEach((definition) => definition.remove());
    target.querySelectorAll(noteContainers).forEach((container) => {
      const body = container.cloneNode(true);
      body.querySelectorAll('summary').forEach((summary) => summary.remove());
      if (!body.textContent.trim()) container.remove();
    });
  }

  document.addEventListener('pointerdown', (event) => {
    if (activeTrigger && !event.target.closest('.footnote-trigger,.footnote-popover')) close();
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && activeTrigger) {
      event.preventDefault();
      event.stopImmediatePropagation();
      close(true);
    }
  }, true);
  document.addEventListener('scroll', (event) => {
    if (activeTrigger && !(event.target instanceof Element && event.target.closest('.footnote-popover'))) close();
  }, true);
  window.addEventListener('resize', () => close());
  window.ReaderNotes = Object.freeze({ restoreMarkup, prepare, clear });
})();
