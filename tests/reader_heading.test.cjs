const test = require('node:test');
const assert = require('node:assert/strict');
const { isDuplicateFirstTitle } = require('../reader-heading.js');

test('keeps an exact repeated section title on the body heading', () => {
  assert.equal(isDuplicateFirstTitle('第一章 为党史而斗争', '第一章 为党史而斗争', 'P'), true);
});

test('normalizes compatibility punctuation, whitespace, and equivalent chapter digits', () => {
  assert.equal(isDuplicateFirstTitle('第１章：党史', '第一章: 党史', 'H1'), true);
});

test('ignores the known trailing asterisk footnote marker for comparison', () => {
  assert.equal(isDuplicateFirstTitle('实践论', '实践论*', 'H3'), true);
});

test('preserves different explicit chapter numbers', () => {
  assert.equal(isDuplicateFirstTitle('第一章 党史', '第二章 党史', 'P'), false);
});

test('does not match when only one side has a chapter number', () => {
  assert.equal(isDuplicateFirstTitle('党史', '第二章 党史', 'P'), false);
  assert.equal(isDuplicateFirstTitle('第一章 党史', '党史', 'P'), false);
});

test('does not erase meaningful punctuation or subtitles', () => {
  assert.equal(isDuplicateFirstTitle('第一章，党史', '第一章党史', 'P'), false);
  assert.equal(isDuplicateFirstTitle('第一章 党史：副标题', '第一章 党史', 'P'), false);
});

test('does not treat prose or list items as a duplicated title block', () => {
  assert.equal(isDuplicateFirstTitle('正文', '这是正文。', 'P'), false);
  assert.equal(isDuplicateFirstTitle('同名标题', '同名标题', 'LI'), false);
});
