"""Completeness, footnote and discovery checks for the 1976 Shanghai edition."""
import hashlib
import json
import re
import unittest
from pathlib import Path
from lxml import html

ROOT = Path(__file__).resolve().parents[1]
BOOK_ID = 'socialist-political-economy-shanghai-1976'
BOOK = ROOT / 'books' / BOOK_ID


class SocialistEconomicsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = json.loads((BOOK/'source.json').read_text())
        cls.book = next(b for b in json.loads((ROOT/'book-index.json').read_text())['books'] if b['id']==BOOK_ID)
        cls.sections = [json.loads((BOOK/'sections'/f'{s["id"]}.json').read_text()) for s in cls.book['sections']]

    def test_source_and_markdown_identity(self):
        self.assertEqual(self.source['source_sha256'], '1e9e6841182c08bcfd8bef87d30c2d982d46386d1c6b229c1c5b23169bbd8310')
        content=(BOOK/'book.md').read_bytes()
        self.assertEqual(hashlib.sha256(content).hexdigest(), self.source['markdown_sha256'])
        text=content.decode()
        self.assertEqual(len(re.findall(r'<!-- PDF第\d+页；',text)),551)
        self.assertEqual(len(re.findall(r'^\[\^p\d+-note[^\]]+\]:',text,re.M)),357)
        self.assertEqual(len(re.findall(r'^### 第.+章',text,re.M)),15)
        self.assertEqual(len(re.findall(r'^## 第.+篇',text,re.M)),5)
        self.assertEqual(text.count('·未定稿第二版讨论稿·'),2)
        self.assertNotIn('\ufffd',text)
        for asset in re.findall(r'!\[[^\]]*\]\(([^)]+)\)',text):
            self.assertTrue((BOOK/asset).is_file(),asset)

    def test_every_pdf_page_is_assigned_once(self):
        pages=[p for s in self.sections for p in s['sourcePdfPages']]
        self.assertEqual(sorted(pages), list(range(1,552)))
        readable=[s for s in self.book['sections'] if not s.get('readerHidden')]
        self.assertEqual(len(readable),16)
        self.assertEqual(readable[0]['id'],'preface')
        self.assertEqual(len({s.get('chapter') for s in readable[1:]}),5)

    def test_footnotes_are_page_scoped_and_only_known_anomalies_remain(self):
        unmatched=[];visible_notes=0;references=0;all_ids=[]
        for s in self.sections:
            tree=html.fragment_fromstring(s['html'],create_parent='article')
            all_ids.extend(tree.xpath('//*[@id]/@id'))
            for page in tree.xpath('.//section[contains(concat(" ",normalize-space(@class)," ")," page ")]'):
                notes=page.xpath('.//aside[contains(@class,"footnote")]')
                visible_notes+=sum('hidden' not in n.attrib for n in notes)
                markers={re.match(r'\s*([①-⑳])',n.text_content()).group(1) for n in notes}
                for sup in page.xpath('.//sup'):
                    text=sup.text_content();references+=1
                    if text not in markers:unmatched.append((page.get('id'),text))
            for img in tree.xpath('.//img'):
                self.assertTrue((ROOT/img.get('src')).is_file())
            self.assertFalse(tree.xpath('.//script|.//iframe|.//*[@onload]|.//*[@onclick]'))
        self.assertEqual(visible_notes,357)
        self.assertEqual(references,362)
        self.assertEqual(unmatched,[('pdf-page-425','①'),('pdf-page-517','②')])
        self.assertEqual(len(all_ids),len(set(all_ids)))

    def test_math_order_and_source_anomalies_are_preserved(self):
        chapter11=next(s for s in self.sections if s['id']=='chapter-11')['html']
        self.assertIn('Ⅰ(4000c + 1000v + 1000m) = 6000',chapter11)
        self.assertIn('资本有机构成（c/v）越来越高',chapter11)
        self.assertIn('Ⅰv + m，就是马克思再生产公式中的Ⅰ(v + m)',chapter11)
        self.assertIn('285 F',chapter11)
        self.assertIn('8,220',chapter11)
        self.assertNotIn('\ufffd',chapter11)
        self.assertIn('①324',re.sub(r'\s+', '', next(s for s in self.sections if s['id']=='chapter-13')['html']))

    def test_search_pages_and_category_are_present(self):
        self.assertTrue((BOOK/'index.html').is_file())
        for s in self.book['sections']:
            if not s.get('readerHidden'):
                self.assertTrue((ROOT/'texts'/BOOK_ID/s['id']/'index.html').is_file())
        self.assertIn(BOOK_ID,(ROOT/'catalog/index.html').read_text())
        self.assertIn(BOOK_ID,(ROOT/'sitemap.xml').read_text())
        self.assertIn(f"'{BOOK_ID}': 'economics'",(ROOT/'app.js').read_text())


if __name__=='__main__':
    unittest.main()
