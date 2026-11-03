(function (root, factory) {
  const matcher = factory();
  if (typeof module === 'object' && module.exports) module.exports = matcher;
  else root.ReaderHeadingMatcher = matcher;
})(typeof window !== 'undefined' ? window : globalThis, function () {
  const chineseDigits = { 零: 0, 〇: 0, 一: 1, 二: 2, 两: 2, 三: 3, 四: 4, 五: 5, 六: 6, 七: 7, 八: 8, 九: 9 };
  const chineseUnits = { 十: 10, 百: 100, 千: 1000, 万: 10000 };

  function parseChapterNumber(value) {
    if (/^\d+$/.test(value)) return String(Number(value));
    if (![...value].some((char) => chineseUnits[char])) {
      return [...value].map((char) => chineseDigits[char]).join('');
    }
    let total = 0, section = 0, digit = 0;
    for (const char of value) {
      if (Object.hasOwn(chineseDigits, char)) digit = chineseDigits[char];
      else if (chineseUnits[char] === 10000) {
        total += (section + digit) * chineseUnits[char]; section = 0; digit = 0;
      } else if (chineseUnits[char]) {
        section += (digit || 1) * chineseUnits[char]; digit = 0;
      }
    }
    return String(total + section + digit);
  }

  function headingParts(value) {
    let text = String(value).normalize('NFKC').replace(/\s+/gu, '').replace(/\*+$/u, '');
    const chapter = text.match(/^第([0-9]+|[零〇一二两三四五六七八九十百千万]+)章/);
    let chapterNumber = null;
    if (chapter) {
      chapterNumber = parseChapterNumber(chapter[1]);
      text = text.slice(chapter[0].length);
    }
    return { chapterNumber, text };
  }

  function isDuplicateFirstTitle(sectionTitle, bodyTitle, tagName) {
    if (!/^(H[1-6]|P)$/.test(String(tagName).toUpperCase())) return false;
    const section = headingParts(sectionTitle);
    const body = headingParts(bodyTitle);
    if ((section.chapterNumber === null) !== (body.chapterNumber === null)) return false;
    if (section.chapterNumber !== body.chapterNumber) return false;
    return Boolean(section.text && section.text === body.text);
  }

  return { isDuplicateFirstTitle };
});
