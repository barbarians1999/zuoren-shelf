"""Build the requested shelf edition from the verified local PDF conversion."""
import collections
import hashlib
import html
import json
import re
import shutil
import sys
from pathlib import Path
import fitz

ROOT = Path(__file__).resolve().parents[1]
INPUT = Path(sys.argv[1])
SOURCE = Path(sys.argv[2])
BOOK_ID = 'socialist-political-economy-shanghai-1976'
BOOK = ROOT / 'books' / BOOK_ID
BOOK.mkdir(parents=True, exist_ok=True)
(BOOK / 'sections').mkdir(exist_ok=True)
(BOOK / 'assets').mkdir(exist_ok=True)
data = json.loads((INPUT / 'structured.json').read_text())
report = json.loads((INPUT / 'conversion-report.json').read_text())
assert data['metadata']['source_sha256'] == '1e9e6841182c08bcfd8bef87d30c2d982d46386d1c6b229c1c5b23169bbd8310'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == data['metadata']['source_sha256']
pdf = fitz.open(SOURCE)
crops = {
    'source-page-049.png': (49, (48, 261, 350, 381)),
    'source-page-065.png': (65, (48, 349, 350, 501)),
    'source-page-066.png': (66, (48, 65, 350, 184)),
    'source-page-449.png': (449, (48, 365, 350, 500)),
    'distribution-original-p371.png': (401, (48, 65, 350, 320)),
    'footnote-original-p413.png': (445, (48, 478, 350, 527)),
}
for name, (page, box) in crops.items():
    pdf[page-1].get_pixmap(matrix=fitz.Matrix(4,4), clip=fitz.Rect(box), alpha=False).save(str(BOOK / 'assets' / name))

def inline(text, notes):
    escaped = html.escape(text)
    def reference(match):
        marker = match.group()
        note = next((n for n in notes if marker in n['markers']), None)
        if note:
            return f'<sup><a href="#{note["id"]}">{marker}</a></sup>'
        return f'<sup>{marker}</sup>'
    return re.sub(r'[①-⑳]', reference, escaped)

def diagram_list(items):
    # Indentation is authored from the checked source image; no flattened PDF order.
    out=[];previous=-1
    for text,depth in items:
        if depth>previous:
            out.append('<ul>'*(depth-previous))
        elif depth<previous:
            out.append('</li></ul>'*(previous-depth)+'</li>')
        else:out.append('</li>')
        out.append('<li>'+html.escape(text));previous=depth
    out.append('</li></ul>'*(previous+1))
    return ''.join(out)

def picture(element):
    path=f'books/{BOOK_ID}/{element["asset"]}'
    return f'<figure><img src="{path}" alt="{html.escape(element["alt"])}" loading="lazy"><figcaption>{html.escape(element["alt"])}</figcaption></figure>'

def page_html(page, front=False):
    n=page['pdf_page'];notes=page['notes'];out=[]
    if not page['elements'] and not notes:return ''
    # The five part title pages are represented as TOC groups, not fake chapters.
    elems=[e for e in page['elements'] if front or not (e['type']=='heading' and e['level']==2 and re.match(r'^第.+篇',e['text']))]
    if not elems and not notes:return ''
    printed=f'原书第 {page["printed_page"]} 页 · ' if page['printed_page'] else ''
    out.append(f'<section class="page reflow-page" id="pdf-page-{n}"><div class="page-marker">{printed}PDF 第 {n} 页</div>')
    for e in elems:
        kind=e['type']
        if kind=='heading':
            level=max(2,min(5,e['level']-1))
            out.append(f'<h{level}>{html.escape(e["text"])}</h{level}>')
        elif kind=='figure':out.append(picture(e)+diagram_list(e['text']))
        elif kind=='source_image':out.append(picture(e))
        elif kind=='table':
            lines='\n'.join(e['text'])
            out.append(picture(e)+'<details><summary>表格提取文字（以原图为准）</summary><div class="table-scroll"><pre>'+html.escape(lines)+'</pre></div></details>')
        elif kind=='source_lines_text':
            out.append('<p>'+inline(e['text'],notes).replace('\n','<br>\n')+'</p>')
        else:out.append('<p>'+inline(e['text'],notes)+'</p>')
    for note in notes:
        out.append(f'<aside class="footnote" id="{note["id"]}"><p>{note["markers"]} {html.escape(note["text"])}</p></aside>')
        # Shared printed notes keep one visible original and hidden lookup aliases.
        for marker in note['markers'][1:]:
            out.append(f'<aside class="footnote" hidden data-note-group="{note["id"]}"><p>{marker} {html.escape(note["text"])}</p></aside>')
    out.append('</section>')
    return '\n'.join(out)

parts=[h['title'].replace('\u3000',' ') for h in json.loads((INPUT/'extracted.json').read_text())['outline'] if h['depth']==0 and h['title'].startswith('第')]
chapters=[h['title'].replace('\u3000',' ') for h in json.loads((INPUT/'extracted.json').read_text())['outline'] if h['depth']==1]
assert len(chapters)==15 and len(parts)==5
groups=[0,0,1,1,1,1,1,2,2,3,3,3,4,4,4]
ranges=[(23,74),(75,112),(113,158),(159,204),(205,252),(253,278),(281,310),(311,360),(361,390),(391,440),(441,474),(475,512),(513,524),(525,534),(535,551)]
sections=[{'id':'front-matter','title':'封面与原目录','level':0,'readerHidden':True,'pages':list(range(1,11))+[279,280]}, {'id':'preface','title':'序言','level':0,'pages':list(range(11,23))}]
sections += [{'id':f'chapter-{i+1:02d}','title':title,'level':0,'chapter':parts[groups[i]],'pages':list(range(start,end+1))} for i,(title,(start,end)) in enumerate(zip(chapters,ranges))]
assert sorted(p for s in sections for p in s['pages'])==list(range(1,552))
for section in sections:
    page_list=section['pages']
    body='\n'.join(page_html(data['pages'][p-1],front=section.get('readerHidden',False)) for p in page_list)
    if section['id']=='preface':
        body += f'<p>本书依据用户提供的1976年9月上海版PDF文字层整理，未经逐字校勘。<a href="books/{BOOK_ID}/book.md" download>下载整书Markdown</a> · <a href="books/{BOOK_ID}/source-review.md">查看版本与校核说明</a>。原书PDF第425页和第517页的未配对注号保留，未补造注释。</p>'
    entry={k:v for k,v in section.items() if k!='pages'}
    entry['sourcePdfPages']=page_list
    entry['html']=body
    (BOOK/'sections'/f'{section["id"]}.json').write_text(json.dumps(entry,ensure_ascii=False,indent=2)+'\n')

shutil.copyfile(INPUT/'book.md', BOOK/'book.md')
source={**data['metadata'],'markdown_sha256':hashlib.sha256((BOOK/'book.md').read_bytes()).hexdigest(),'source_anomalies':report['source_anomalies'],'math_content_stream_pages':report['math_content_stream_pages'],'sourceMirror':'https://www.bannedthought.net/China/MaoEra/PoliticalEconomy/PoliticalEconomyOfSocialism-Shanghai-1976-9-Chinese-OCR-sm.pdf','mirrorVerification':'云端工作副本与用户本地原稿SHA-256完全一致。','sectionPdfPages':{s['id']:s['pages'] for s in sections}}
(BOOK/'source.json').write_text(json.dumps(source,ensure_ascii=False,indent=2)+'\n')
(BOOK/'source-review.md').write_text('''# 版本与校核说明

本书为上海《社会主义政治经济学》编写小组1976年9月《未定稿第二版讨论稿》，上、下册合编。来源是用户提供的《社会主义政治经济学 (全一册).pdf》，551个PDF页面，正文原页码止于513页。

## 转换范围

- 使用完整文字层，无需OCR。保留整书Markdown、封面与原目录、五篇十五章、全部原注和图表。
- 原PDF的141条层级书签均已匹配；网页按序言和十五章加载，五篇用目录分组呈现，封面和重复的原目录保存在Markdown及原始数据中。
- 原书共有357组页下注，对应360个注号。共用一条注释的多个注号仍指向同一原注，按原PDF页隔离，防止重号串注。
- 复杂表格保留原图，提取文字只作辅助。分配树状图另附按原图校对的层级文字。
- 数学字体的字框位置会导致常规布局提取错序。PDF第376、443—446、449—451、465页按PDF内容流顺序整理；第376页货币公式及第465页资本有机构成分式据原图线性表示。
- 本稿未经逐字校勘。原稿疑误不作推测性修改。

## 保留的原稿疑点

- PDF第425页（原395页）有“①31”标记，原页没有对应页下注，保留原标记。
- PDF第517页（原481页）第一条注释印为“①324”，后有③注，正文②未能配对，保留原文。
- PDF第443页（原411页）公式旁有极小的“285 F”字串，保留。
- PDF第449页（原417页）表中第二年末栏印为8,220，正文写“14倍”，表底写“1.4倍”；均按原稿保留，以附图为准。
- PDF第445页低位数学字串按原内容流恢复顺序，并附原注图；没有补写原文不存在的字母。

## 文件校验

原PDF SHA-256：1e9e6841182c08bcfd8bef87d30c2d982d46386d1c6b229c1c5b23169bbd8310。

公开扫描镜像与用户本地原稿字节完全一致：[1976年9月扫描镜像](https://www.bannedthought.net/China/MaoEra/PoliticalEconomy/PoliticalEconomyOfSocialism-Shanghai-1976-9-Chinese-OCR-sm.pdf)。本地原稿未作修改。
''',encoding='utf-8')

index_path=ROOT/'book-index.json';index=json.loads(index_path.read_text())
book={'id':BOOK_ID,'title':'社会主义政治经济学（1976年上海版）','author':'上海《社会主义政治经济学》编写小组','format':'本地PDF文字层转Markdown阅读版','note':'1976年9月未定稿第二版讨论稿，上下册合编。保留五篇十五章、原注及图表；文字层整理稿，未经逐字校勘。原稿未配对注号与疑误保留，详见版本与校核说明。','type':'text','sectionPath':f'books/{BOOK_ID}/sections','source':{'filename':source['source_filename'],'sha256':source['source_sha256'],'editionStatement':'1976年9月，上海，未定稿第二版讨论稿，上下册合编。','conversion':'文字层转Markdown，保留原注和图表，按章加载。未经逐字校勘。'},'sections':[{k:v for k,v in s.items() if k!='pages'} for s in sections]}
positions=[i for i,b in enumerate(index['books']) if b['id']==BOOK_ID]
if positions:index['books'][positions[0]]=book
else:
    pos=next(i for i,b in enumerate(index['books']) if b['id']=='political-economy-introduction')
    index['books'].insert(pos+1,book)
index_path.write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n')
app=ROOT/'app.js';content=app.read_bytes()
needle=b"    'economic-accounting-ownership': 'economics',"
if BOOK_ID.encode() not in content:
    content=content.replace(needle,needle+b"\r\n    '"+BOOK_ID.encode()+b"': 'economics',")
    app.write_bytes(content)
homepage=ROOT/'index.html';homepage.write_text(homepage.read_text().replace('app.js?v=split-title-20261109','app.js?v=economics-1976-20261110'))
print(json.dumps({'bookId':BOOK_ID,'pages':len(data['pages']),'sections':len(sections),'readableSections':16,'notes':source['footnote_records'],'assets':list(crops)},ensure_ascii=False))
