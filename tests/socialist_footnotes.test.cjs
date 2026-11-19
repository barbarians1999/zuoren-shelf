// Requires jsdom@26.1.0. This checks the actual reader-note program, without a browser.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { JSDOM } = require('jsdom');
const root = path.resolve(__dirname, '..');
const id = 'socialist-political-economy-shanghai-1976';
const index = JSON.parse(fs.readFileSync(path.join(root, 'book-index.json'), 'utf8'));
const book = index.books.find(b => b.id === id);
const code = fs.readFileSync(path.join(root, 'reader-notes.js'), 'utf8');
const compact = s => s.replace(/\s+/g, '');
const loadSection = section => JSON.parse(fs.readFileSync(path.join(root, book.sectionPath, section + '.json'), 'utf8'));

test('all 360 authored links keep their exact original note; two unresolved marks stay unresolved', async () => {
  let links = 0, unresolved = [];
  for (const section of book.sections.filter(s => !s.readerHidden)) {
    const dom = new JSDOM('<main id="reading"></main>', {url:'https://example.test/', runScripts:'outside-only'});
    const {window} = dom;
    window.eval(code);
    const reading = window.document.getElementById('reading');
    reading.innerHTML = loadSection(section.id).html;
    const pageIds = [...reading.querySelectorAll('[id^="pdf-page-"]')].map(n => n.id);
    const expected = [...reading.querySelectorAll('sup a[href^="#"]')].map(link => {
      const target = link.getAttribute('href').slice(1), marker = link.textContent;
      const choices = [...reading.querySelectorAll('aside.footnote')].filter(n => n.id === target || n.getAttribute('data-note-group') === target);
      const note = choices.find(n => n.textContent.trim().startsWith(marker)) || choices[0];
      assert.ok(note, target);
      return compact(note.textContent.replace(/^\s*[①-⑳]\s*/, ''));
    });
    await window.ReaderNotes.prepare(reading, {...book, sections:[]});
    const buttons = [...reading.querySelectorAll('button.footnote-trigger')];
    assert.equal(buttons.length, expected.length, section.id);
    for (let i = 0; i < buttons.length; i++) {
      const note = window.document.createElement('div');note.innerHTML = buttons[i]._noteHtml;
      assert.equal(compact(note.textContent), expected[i], section.id+' note '+i);
    }
    for (const sup of reading.querySelectorAll('sup')) unresolved.push([sup.getAttribute('data-source-pdf-page'),sup.textContent]);
    assert.deepEqual([...reading.querySelectorAll('[id^="pdf-page-"]')].map(n => n.id),pageIds);
    if (buttons.length) {
      buttons[0].click();
      assert.equal(window.document.querySelector('.footnote-popover').hidden,false);
      assert.equal(buttons[0].getAttribute('aria-expanded'),'true');
    }
    links += buttons.length;window.close();
  }
  assert.equal(links,360);
  assert.deepEqual(unresolved,[['425','①'],['517','②']]);
});

test('other books keep the existing same-page marker lookup', async () => {
  const dom=new JSDOM('<main id="reading"><section class="page"><p>A<sup>①</sup></p><aside class="footnote"><p>① first page note</p></aside></section><section class="page"><p>B<sup>①</sup></p><aside class="footnote"><p>① second page note</p></aside></section></main>',{url:'https://example.test/',runScripts:'outside-only'});
  dom.window.eval(code);
  const reading=dom.window.document.getElementById('reading');
  await dom.window.ReaderNotes.prepare(reading,{id:'another-book',sections:[]});
  const notes=[...reading.querySelectorAll('.footnote-trigger')].map(n=>n._noteHtml);
  assert.match(notes[0],/first page note/);assert.match(notes[1],/second page note/);
  dom.window.close();
});
