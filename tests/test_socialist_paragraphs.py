"""Source-backed paragraph and downloadable/static reading regressions."""
import hashlib,json,re,unittest
from pathlib import Path
from lxml import html
ROOT=Path(__file__).resolve().parents[1]
BOOK=ROOT/'books/socialist-political-economy-shanghai-1976'

class ParagraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit=json.loads((BOOK/'paragraph-repair.json').read_text())
        cls.sections={p.stem:json.loads(p.read_text()) for p in (BOOK/'sections').glob('*.json')}

    def test_ordered_body_characters_remain_identical(self):
        for section,expected in self.audit['section_body_sha256'].items():
            tree=html.fragment_fromstring(self.sections[section]['html'],create_parent='article')
            body=''.join(tree.xpath('.//section[contains(@class,"page")]/p//text()'))
            digest=hashlib.sha256(re.sub(r'\s+','',body).encode()).hexdigest()
            self.assertEqual(digest,expected,section)

    def test_known_continuations_are_single_real_paragraphs(self):
        for section,page,phrase in [('chapter-01',26,'悲惨生活，根源就是因为生产资料'),
                                    ('preface',12,'坚持阶级斗争、防止资本主义复辟指出了方向'),
                                    ('chapter-11',446,'社会纯收入。')]:
            tree=html.fragment_fromstring(self.sections[section]['html'],create_parent='article')
            anchor=tree.get_element_by_id('pdf-page-'+str(page))
            self.assertEqual(anchor.tag,'span')
            self.assertEqual(anchor.getparent().tag,'p')
            self.assertIn(phrase,re.sub(r'\s+','',anchor.getparent().text_content()))

    def test_real_math_page_paragraphs_and_equations_remain(self):
        tree=html.fragment_fromstring(self.sections['chapter-11']['html'],create_parent='article')
        page443=tree.get_element_by_id('pdf-page-443')
        paragraphs=page443.xpath('./p')
        self.assertEqual(len(paragraphs),9)
        self.assertTrue(paragraphs[3].text_content().startswith('首先，'))
        self.assertTrue(paragraphs[4].text_content().startswith('其次，'))
        self.assertTrue(paragraphs[5].text_content().startswith('最后，'))
        self.assertEqual(len(paragraphs[0].xpath('.//br')),1)
        self.assertIn('285 F',paragraphs[0].text_content())
        page444=tree.get_element_by_id('pdf-page-444')
        self.assertEqual(len(page444.xpath('./p')),7)
        self.assertEqual(len(page444.xpath('./p')[0].xpath('.//br')),1)

    def test_markdown_body_and_all_source_markers_remain(self):
        text=(BOOK/'book.md').read_text()
        self.assertEqual(len(re.findall(r'<!-- PDF第\d+页；',text)),551)
        body=re.sub(r'<!--.*?-->','',text,flags=re.S)
        body=re.sub(r'^\[\^p\d+-note[^\]]+\]:.*$','',body,flags=re.M)
        body=re.sub(r'!\[[^\]]*\]\([^)]*\)','',body)
        body=re.sub(r'<details>.*?</details>','',body,flags=re.S)
        body=re.sub(r'^#{1,6} .*$', '',body,flags=re.M)
        digest=hashlib.sha256(re.sub(r'\s+','',body).encode()).hexdigest()
        self.assertEqual(digest,self.audit['markdown_body_sha256'])
        self.assertIn('生活，根<!-- PDF第26页；原页码：12 -->源',text)
        self.assertIn('阶级斗争、<!-- PDF第12页；原页码：2 -->防止',text)

    def test_static_reading_pages_have_the_same_body(self):
        for section,expected in self.audit['section_body_sha256'].items():
            path=ROOT/'texts/socialist-political-economy-shanghai-1976'/section/'index.html'
            tree=html.fromstring(path.read_text())
            body=''.join(tree.xpath('//article[contains(@class,"seo-content")]//section[contains(@class,"page")]/p//text()'))
            digest=hashlib.sha256(re.sub(r'\s+','',body).encode()).hexdigest()
            self.assertEqual(digest,expected,section)

if __name__=='__main__':unittest.main()
