const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.join(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'app.js'), 'utf8');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const functions = source.slice(source.indexOf('  function applyReadingFont('), source.indexOf('  function readingFontReady('));
function setup() {
  const writes = [];
  const buttons = ['system', 'source-han', 'fangsong', 'hanyi-shufang'].flatMap(font => [0, 1].map(() => ({dataset: {readingFont: font}, setAttribute(key, value) { this[key] = value; }})));
  const context = {document: {documentElement: {dataset: {}}, querySelectorAll: () => buttons}, localStorage: {setItem: (...args) => writes.push(args)}, fontPreferenceKey: 'reading-desk:font-family:v1'};
  vm.createContext(context);
  vm.runInContext(functions, context);
  return {...context, writes, buttons};
}
test('new or invalid preference defaults to Hanyi without overwriting storage', () => {
  for (const value of [null, undefined, '', 'unknown', 1, {}]) {
    const c = setup(); c.applyReadingFont(value);
    assert.equal(c.document.documentElement.dataset.readingFont, 'hanyi-shufang');
    assert.equal(c.writes.length, 0);
    assert.equal(c.buttons.filter(b => b['aria-pressed'] === 'true').length, 2);
  }
});
test('all explicit saved choices, including default/system, are retained', () => {
  for (const font of ['system', 'source-han', 'fangsong', 'hanyi-shufang']) {
    const c = setup(); c.applyReadingFont(font);
    assert.equal(c.document.documentElement.dataset.readingFont, font);
    assert.equal(c.writes.length, 0);
  }
  const c = setup(); c.applyReadingFont('song');
  assert.equal(c.document.documentElement.dataset.readingFont, 'source-han');
});
test('selecting default persists and restores it rather than selecting Hanyi again', () => {
  const c = setup(); c.applyReadingFont('system', true);
  assert.equal(c.writes[0][1], '"system"');
  c.applyReadingFont(JSON.parse(c.writes[0][1]));
  assert.equal(c.document.documentElement.dataset.readingFont, 'system');
});
test('unavailable storage still lets the visitor select a font', () => {
  const c = setup(); c.localStorage.setItem = () => { throw new Error('unavailable'); };
  c.applyReadingFont('system', true);
  assert.equal(c.document.documentElement.dataset.readingFont, 'system');
});
test('both desktop and mobile retain default and initially indicate Hanyi', () => {
  assert.equal((html.match(/data-reading-font="system" aria-pressed="false">默认/g) || []).length, 2);
  assert.equal((html.match(/data-reading-font="hanyi-shufang" aria-pressed="true"/g) || []).length, 2);
  assert.ok(source.includes('applyReadingFont(readStored(fontPreferenceKey))'));
});
test('bundled font and platform fallbacks remain available', () => {
  const css = fs.readFileSync(path.join(root, 'styles.css'), 'utf8');
  assert.ok(fs.statSync(path.join(root, 'fonts/HanyiShufang55W.ttf')).size > 0);
  assert.match(css, /HanyiShufang55W\.ttf/);
  assert.match(css, /font-display: swap/);
  assert.match(css, /"Songti SC", serif/);
});
