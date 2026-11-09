const test = require('node:test');
const assert = require('node:assert/strict');
const { isDuplicateFirstTitle, isDuplicateHeadingSequence } = require('../reader-heading.js');

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

test('matches a complete chapter title split across consecutive source headings', () => {
  assert.equal(isDuplicateHeadingSequence('二 布尔什维克成功的基本条件之一', ['二', '布尔什维克成功的 基本条件之一'], 'H2'), true);
  assert.equal(isDuplicateHeadingSequence('五 德国“左派”共产党人。领袖、政党、阶级、群众间的相互关系', ['五', '德国“左派”共产党人。', '领袖、政党、阶级、群众间的相互关系'], 'H2'), true);
  assert.equal(isDuplicateHeadingSequence('附录 一', ['附 录', '一'], 'H2'), true);
});

test('does not match partial titles, mismatched chapter numbers, or a single heading', () => {
  assert.equal(isDuplicateHeadingSequence('二 布尔什维克成功的基本条件之一', ['二', '布尔什维克成功的基本条件'], 'H2'), false);
  assert.equal(isDuplicateHeadingSequence('第一章 党史', ['第二章', '党史'], 'H2'), false);
  assert.equal(isDuplicateHeadingSequence('二 标题', ['二 标题'], 'H2'), false);
  assert.equal(isDuplicateHeadingSequence('二 标题', ['二', ''], 'H2'), false);
});

test('does not erase meaningful punctuation or subtitles', () => {
  assert.equal(isDuplicateFirstTitle('第一章，党史', '第一章党史', 'P'), false);
  assert.equal(isDuplicateFirstTitle('第一章 党史：副标题', '第一章 党史', 'P'), false);
});

test('does not treat prose or list items as a duplicated title block', () => {
  assert.equal(isDuplicateFirstTitle('正文', '这是正文。', 'P'), false);
  assert.equal(isDuplicateFirstTitle('同名标题', '同名标题', 'LI'), false);
});
