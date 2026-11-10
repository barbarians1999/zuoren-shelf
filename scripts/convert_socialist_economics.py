from pathlib import Path
import sys, json, re, hashlib, collections, html
from pypdf import PdfReader
import pdfplumber
SRC=Path(sys.argv[1]); BASE=Path(sys.argv[2]); BASE.mkdir(parents=True,exist_ok=True)
NORM=lambda s:re.sub(r'\s+','',s)
CIRCLE=re.compile(r'[①-⑳]')
reader=PdfReader(SRC)
outline=[]
def walk(xs,depth=0):
    for x in xs:
        if isinstance(x,list):walk(x,depth+1)
        else:outline.append({'title':x.title,'page':reader.get_destination_page_number(x)+1,'depth':depth})
walk(reader.outline)
raw=[p.extract_text() or '' for p in reader.pages]
by_page=collections.defaultdict(list)
for h in outline:by_page[h['page']].append(h)
layout=[]
with pdfplumber.open(SRC) as pdf:
    for n,p in enumerate(pdf.pages,1):
        lines=[]
        for ln in p.extract_text_lines(layout=False,strip=True,return_chars=True):
            cs=ln.pop('chars'); counts=collections.Counter(round(c['size'],1) for c in cs)
            ln['size']=max(counts,key=counts.get) if counts else 0
            lines.append(ln)
        layout.append({'page':n,'lines':lines,'images':len(p.images)})
        p.close()
(BASE/'extracted.json').write_text(json.dumps({'pages':raw,'outline':outline},ensure_ascii=False),encoding='utf-8')
(BASE/'layout.json').write_text(json.dumps(layout,ensure_ascii=False),encoding='utf-8')
issues=[];pages=[];headings=[]
for pg in layout:
    n=pg['page'];lines=pg['lines'];used=set();hstarts={};printed=[]
    for i,l in enumerate(lines):
        if l['top']>500 and re.fullmatch(r'\d+',l['text']) and 9.5<l['size']<10.5:
            used.add(i);printed.append(l['text'])
        elif n==445 and l['top']>510 and l['text'].endswith(' 413'):
            # Low-position formula text shares a visual baseline with page number 413.
            l['text']=l['text'][:-4];l['size']=8.0;printed.append('413')
    for h in by_page[n]:
        found=[]
        for i in range(len(lines)):
            for span in range(1,4):
                if i+span<=len(lines) and NORM(''.join(z['text'] for z in lines[i:i+span]))==NORM(h['title']):found.append((i,span))
        if len(found)!=1:raise ValueError(('Heading match',n,h,found))
        i,span=found[0];level=2 if h['depth']==0 else h['depth']+2
        hstarts[i]=(span,{'type':'heading','level':level,'text':h['title'].replace('\u3000',' '),'source_lines':list(range(i,i+span))})
    note_start=None
    for i,l in enumerate(lines):
        if 7.5<=l['size']<=8.1 and re.match(r'[①-⑳].+',l['text']) and n!=401:
            note_start=i;break
    notes=[]
    if note_start is not None:
        for i in range(note_start,len(lines)):
            if i in used:continue
            l=lines[i]
            if not 7.5<=l['size']<=8.1:
                issues.append({'kind':'non_note_after_note','pdf_page':n,'text':l['text']});continue
            m=re.match(r'([①-⑳]+)\s*(.*)',l['text'])
            if m:
                marks=m.group(1);nums='-'.join(str(ord(c)-ord('①')+1) for c in marks)
                notes.append({'id':f'p{n:03d}-note{nums}','markers':marks,'text':m.group(2),'source_lines':[i]})
            elif notes:notes[-1]['text']+=l['text'];notes[-1]['source_lines'].append(i)
            else:raise ValueError(('Orphan footnote',n,l['text']))
            used.add(i)
    elements=[]
    if n==1:
        elements.append({'type':'heading','level':1,'text':'社会主义政治经济学','source_lines':[0]});used.add(0)
    # Keep a source rendering beside complicated vector tables/formulae. Export these PNGs separately.
    if n==449:
        elements.append({'type':'source_image','asset':'assets/source-page-449.png','alt':'原书第417页注①的原表格；保留原稿数字，提取文字仅作辅助'})
    table_starts={}
    table_ranges={49:(262,379),65:(350,499),66:(66,182)}
    if n in table_ranges:
        top,bottom=table_ranges[n]
        ids=[i for i,l in enumerate(lines) if top<=l['top']<bottom]
        table_starts[ids[0]]={'type':'table','asset':f'assets/source-page-{n:03d}.png','alt':f'PDF第{n}页原表格','text':[lines[i]['text'] for i in ids],'source_lines':ids}
        used.update(ids[1:])
    if n==401:
        ids=[i for i,l in enumerate(lines) if l['top']<320]
        diagram=[('社会主义社会的总产品',0),('国民收入',1),('积累基金',2),('扩大生产基金：用于工业、农业及运输业等生产性基本建设和增加企业的流动资金',3),('非生产性基本建设基金：用于文化、教育、卫生部门，国家行政和国防部门的基本建设以及工农业生产部门的非生产性基本建设',3),('社会后备基金：社会主义国家和企业为了备战备荒，防止再生产过程的意外中断而用作后备的物资储备，如国家的原料、燃料和粮食储备以及人民公社的粮食储备等',3),('消费基金',2),('国家管理基金：用于国家行政管理和国防开支方面的支出',3),('文教卫生基金：用于科学、教育、保健、艺术事业方面的支出',3),('社会保证基金：社会主义国家和企业用于劳动保险、公费医疗和社会救济方面的支出',3),('以上三项基金支出，包括各该部门职工的工资支付在内',3),('生产和流通中的个人消费基金：用来支付从事生产和流通工作的职工工资和社员的劳动报酬',3),('补偿已消耗的生产资料',1)]
        a=collections.Counter(NORM(''.join(lines[i]['text'] for i in ids)))
        b=collections.Counter(NORM(''.join(t for t,d in diagram)))
        if a!=b:raise ValueError(('Diagram character mismatch',a-b,b-a))
        elements.append({'type':'figure','asset':'assets/distribution-original-p371.png','alt':'原书第371页：社会主义社会总产品的分配图','text':diagram,'source_lines':ids});used.update(ids)
    current=None
    def flush():
        global current
        if current:elements.append(current);current=None
    for i,l in enumerate(lines):
        if i in used:continue
        if i in table_starts:
            flush();elements.append(table_starts[i]);used.add(i);continue
        if i in hstarts:
            flush();span,h=hstarts[i];elements.append(h);used.update(range(i,i+span));continue
        text=l['text']
        if n<=10 or n==279:
            flush();elements.append({'type':'paragraph','text':text,'source_lines':[i]});used.add(i);continue
        prev=lines[i-1] if i else None
        start=l['x0']>=(87 if 8.5<=l['size']<10.5 else 68) and l['size']>=8.5
        gap=prev is not None and l['top']-prev['bottom']>13
        size_change=current is not None and abs(l['size']-current.get('font_size',l['size']))>1.4
        if current and (start or gap or size_change):flush()
        if current is None:current={'type':'paragraph','text':text,'source_lines':[i],'font_size':l['size']}
        else:
            sep=' ' if re.search(r'[A-Za-z0-9]$',current['text']) and re.match(r'[A-Za-z0-9]',text) else ''
            current['text']+=sep+text;current['source_lines'].append(i)
        used.add(i)
    flush()
    assert used==set(range(len(lines))),(n,'Unconsumed lines')
    refs=collections.Counter(c for e in elements if e['type']=='paragraph' for c in CIRCLE.findall(e['text']))
    marks=collections.Counter(c for nt in notes for c in nt['markers'])
    if refs!=marks:issues.append({'kind':'note_count_mismatch','pdf_page':n,'refs':dict(refs),'notes':dict(marks)})
    if n==445:
        elements.append({'type':'source_image','asset':'assets/footnote-original-p413.png','alt':'原书第413页脚注原貌：数学字串按原稿保留'})
    pages.append({'pdf_page':n,'printed_page':','.join(printed),'elements':elements,'notes':notes})
# CambriaMath has inaccurate bounding boxes in this PDF. On these pages only,
# retain the PDF content-stream order rather than sorting mathematical runs by y.
math_pages=(376,443,444,445,446,449,450,451,465)
for n in math_pages:
    p=pages[n-1]
    text=raw[n-1]
    first=re.match(r'^\s*(\d+)\s*\n',text)
    if first:
        p['printed_page']=first.group(1);text=text[first.end():]
    note_matches=list(re.finditer(r'\n[ \t]*([①-⑳]+)[ \t]+',text))
    body=text[:note_matches[0].start()] if note_matches else text
    assert len(note_matches)==len(p['notes']),(n,'Math page note count')
    for j,(match,note) in enumerate(zip(note_matches,p['notes'])):
        assert match.group(1)==note['markers']
        end=note_matches[j+1].start() if j+1<len(note_matches) else len(text)
        note['text']=''.join(line.strip() for line in text[match.end():end].splitlines())
    if n==376:
        body,count=re.subn(r'执行流通手段职能的货币必要量\s*=\s*有待用现金实现的商品价格总额\s*\n单位货币的流通次数',
            '执行流通手段职能的货币必要量 = 有待用现金实现的商品价格总额 / 单位货币的流通次数',body)
        assert count==1
    if n==465:
        body,count=re.subn(r'资本有机构成�\s*c\s*v�', '资本有机构成（c/v）',body)
        assert count==1
    source_images=[e for e in p['elements'] if e['type']=='source_image']
    heading_map={NORM(h['title']):h for h in by_page[n]}
    elements=[];buffer=[]
    def flush_stream():
        if buffer:
            elements.append({'type':'source_lines_text','text':'\n'.join(buffer),'extraction':'pdf-content-stream'})
            buffer.clear()
    for line in body.splitlines():
        clean=line.strip()
        if not clean:
            flush_stream();continue
        h=heading_map.get(NORM(clean))
        if h:
            flush_stream();elements.append({'type':'heading','level':2 if h['depth']==0 else h['depth']+2,'text':h['title'].replace('\u3000',' ')})
        else:buffer.append(clean)
    flush_stream()
    p['elements']=elements+source_images
md=['<!-- 本文件由用户本地《社会主义政治经济学（全一册）》文字层 PDF 整理。1976年9月，上海《社会主义政治经济学》编写小组，未定稿第二版讨论稿。551个PDF页面；保留原页码与PDF页码。按原书书签、版式整理层级、段落与脚注；未经逐字校勘，原稿疑误不擅改。 -->\n']
heading_manifest=[]
for p in pages:
    n=p['pdf_page'];md.append(f"<!-- PDF第{n}页；原页码：{p['printed_page'] or '无'} -->\n")
    note_map={c:nt for nt in p['notes'] for c in nt['markers']}
    for e in p['elements']:
        if e['type']=='heading':
            text='#'*e['level']+' '+e['text']
            heading_manifest.append({'title':e['text'],'level':e['level'],'pdf_page':n,'printed_page':p['printed_page'],'markdown_line':sum(x.count('\n')+1 for x in md)+1})
        elif e['type']=='figure':
            text=f"![{e['alt']}]({e['asset']})\n\n"+'\n'.join('  '*d+'- '+t for t,d in e['text'])
        elif e['type']=='table':
            text=f"![{e['alt']}]({e['asset']})\n\n<details><summary>表格提取文字（以原图为准）</summary><pre>"+html.escape('\n'.join(e['text']))+'</pre></details>'
        elif e['type']=='source_image':text=f"![{e['alt']}]({e['asset']})"
        else:
            text=CIRCLE.sub(lambda m:f"[^{note_map[m.group()]['id']}]" if m.group() in note_map else m.group(),e['text'])
            if e['type']=='source_lines_text':text=text.replace('\n','  \n')
        md.append(text+'\n')
    for nt in p['notes']:md.append(f"[^{nt['id']}]: {nt['markers']} {nt['text']}\n")
mdtext='\n'.join(md);mdpath=BASE/'book.md';mdpath.write_text(mdtext,encoding='utf-8')
metadata={'title':'社会主义政治经济学','author':'上海《社会主义政治经济学》编写小组','edition':'未定稿第二版讨论稿','date':'1976年9月','source_filename':'社会主义政治经济学 (全一册).pdf','source_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),'pdf_pages':len(raw),'printed_body_last_page':'513','text_layer_chars':sum(map(len,raw)),'ocr_used':False,'outline_entries':len(outline),'chapters':15,'parts':5,'footnote_records':sum(len(p['notes']) for p in pages),'footnote_markers':sum(len(nt['markers']) for p in pages for nt in p['notes']),'quality':'文字层整理稿，未经逐字校勘；原稿疑误、重号及未配对注号保留。'}
report={**metadata,'issues':issues,'headings':heading_manifest,'markdown_sha256':hashlib.sha256(mdpath.read_bytes()).hexdigest(),'source_anomalies':[{'pdf_page':425,'printed_page':'395','detail':'正文有①31引用，原页未见对应页下注，不补造。'},{'pdf_page':517,'printed_page':'481','detail':'原页第一注印为①324，后有③注；正文②未配对。保持原文，不猜改为①②。'},{'pdf_page':445,'printed_page':'413','detail':'低位数学字串造成布局排序错位；按PDF内容流恢复原有字串顺序，另附原注图。'},{'pdf_page':443,'printed_page':'411','detail':'第一公式旁有极小字串285 F；原样保留，不猜改。'},{'pdf_page':449,'printed_page':'417','detail':'原表数字8,220及正文14倍与表底1.4倍均按原稿保留；原图为准。'},{'pdf_page':465,'printed_page':'433','detail':'据原页图把两个解码失败的括号恢复，分式以（c/v）线性表示。'}],'math_content_stream_pages':list(math_pages)}
(BASE/'structured.json').write_text(json.dumps({'metadata':metadata,'pages':pages},ensure_ascii=False),encoding='utf-8')
(BASE/'conversion-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='headings'},ensure_ascii=False,indent=2))
