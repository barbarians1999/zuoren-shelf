"""Formatting-only regression for the 1963 general-line proposal.
Paragraph boundaries cross-checked against the MIA Chinese transcription;
wording and original notes remain the existing edition, not a replacement.
"""
import hashlib
import html
import json
import re
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
def text(value):
    return re.sub(r"\s+", "", html.unescape(re.sub(r"<[^>]*>", "", value)))
class RouteFormatTests(unittest.TestCase):
    def test_structure_and_text_preservation(self):
        doc = json.loads((ROOT / "books/route-dispute/sections/route.json").read_text())
        markup = doc["html"]
        notes = re.findall(r"<aside.*?</aside>", markup)
        body = text(re.sub(r"<aside.*?</aside>", "", markup))
        self.assertEqual(hashlib.sha256(body.encode()).hexdigest(), "24ac281e575297346b6b8af98044a2977ba3b8cecc3a2647b4f2709d007d96a6")
        self.assertEqual(hashlib.sha256("".join(map(text, notes)).encode()).hexdigest(), "f83b80e2f2e12fae75f5261d9d26812082b6c9610a22f2ec16fc5416fe928d9b")
        self.assertEqual(len(notes), 7)
        self.assertEqual(markup.count("<h1>"), 1)
        headings = re.findall(r"<h2>(.*?)</h2>", markup)
        self.assertEqual(len(headings), 25)
        self.assertEqual(headings[0], "（一）")
        self.assertEqual(headings[-1], "（二十五）")
        self.assertNotIn("革命原</p>", markup)
        self.assertIn("特别是提出了关于国际共产主义运动总路线的问题", markup)
        self.assertGreater(markup.count("<p>"), 300)
if __name__ == "__main__":
    unittest.main()
