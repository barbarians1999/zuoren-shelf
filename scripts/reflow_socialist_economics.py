"""Repair paragraphs in the verified 1976 Shanghai edition without reimporting text.

Usage: python scripts/reflow_socialist_economics.py ORIGINAL_PDF
The PDF is read only. Only this edition's sections, Markdown and provenance change.
"""
from pathlib import Path
from collections import Counter, defaultdict
import copy, hashlib, html as stdhtml, json, re, sys
from lxml import html, etree
import fitz

ROOT = Path(__file__).resolve().parents[1]
BOOK_ID = 'socialist-political-economy-shanghai-1976'
BOOK = ROOT / 'books' / BOOK_ID
PDF_SHA = '1e9e6841182c08bcfd8bef87d30c2d982d46386d1c6b229c1c5b23169bbd8310'
MATH_PAGES = {376,443,444,445,446,449,450,451,465}
SUPPLEMENT_PAGES = {445,449}
NORM = lambda s: re.sub(r'\s+', '', s)
PAGE_MARKER = re.compile(r'<!-- PDF第(\d+)页；原页码：[^>]* -->')


def inner(node):
    return (stdhtml.escape(node.text or '', quote=False)
            + ''.join(etree.tostring(c, encoding='unicode', method='html') for c in node))


def to_md(node):
    text = inner(node)
    text = re.sub(r'<sup><a href="#([^"]+)">[^<]+</a></sup>', lambda m:'[^'+m[1]+']', text)
    text = re.sub(r'<sup(?: [^>]*)?>([^<]+)</sup>', r'\1', text)
    text = re.sub(r'<br\s*/?>\n?', '  \n', text)
    return stdhtml.unescape(text).strip()


def html_offsets(fragment):
    chars=[]; offsets=[]
    for m in re.finditer(r'<[^>]*>|&(?:#\d+|#x[\da-fA-F]+|\w+);|[\s\S]',fragment):
        token=m[0]
        if token.startswith('<'):continue
        for char in stdhtml.unescape(token):
            if not char.isspace():chars.append(char);offsets.append(m.start())
    return ''.join(chars),offsets


def formula(text):
    text=text.strip()
    return (bool(re.match(r'^[ⅠⅡⅢIVX]+\s*\(',text))
            and len(re.findall(r'[一-龥]',text))<=1) or text.startswith('执行流通手段职能的货币必要量 =')


def unwrap_lines(fragment):
    pieces=re.split(r'<br\s*/?>\s*',fragment)
    if len(pieces)==1:return fragment,0
    result=pieces[0];removed=0
    for before,after in zip(pieces,pieces[1:]):
        a=html.fragment_fromstring(before or '<span></span>',create_parent='div').text_content().strip()
        b=html.fragment_fromstring(after or '<span></span>',create_parent='div').text_content().strip()
        only_note_or_punctuation=lambda t:bool(re.fullmatch(r'[①-⑳，。；：、！？“”‘’,.!?;:]+',t))
        keep=bool(a) and bool(b) and (formula(a) or formula(b)) and not (only_note_or_punctuation(a) or only_note_or_punctuation(b))
        result+=('<br>\n' if keep else '')+after
        removed+=not keep
    return result,int(removed)


def pdf_lines(pdf,page_number):
    lines=[]
    for block in pdf[page_number-1].get_text('dict',sort=True)['blocks']:
        for line in block.get('lines',[]):
            text=''.join(s['text'] for s in line['spans']).strip()
            sizes=[s['size'] for s in line['spans'] if s['text'].strip()]
            if not text or not sizes:continue
            size=max(sizes);x0,y0,x1,y1=line['bbox']
            if 8.5<=size<13.5 and 55<y0<510:
                lines.append({'text':text,'x':x0,'y':y0,'size':size})
    # Superscript fragments can be emitted ahead of the main line; group by baseline.
    grouped=[]
    for line in sorted(lines,key=lambda z:(z['y'],z['x'])):
        group=next((g for g in grouped if abs(g['y']-line['y'])<3),None)
        if group is None:group={'y':line['y'],'parts':[]};grouped.append(group)
        group['parts'].append(line)
    return [{'text':''.join(z['text'] for z in sorted(g['parts'],key=lambda z:z['x'])),
             'x':min(z['x'] for z in g['parts']), 'y':g['y'],
             'size':max(z['size'] for z in g['parts'])} for g in sorted(grouped,key=lambda z:z['y'])]


def fingerprint(root):
    notes=[(n.get('id'),n.get('data-note-group'),n.get('hidden'),NORM(n.text_content()))
           for n in root.xpath('.//aside[contains(@class,"footnote")]')]
    return {
        'body_sha256':hashlib.sha256(NORM(''.join(p.text_content() for p in root.xpath('.//section[contains(@class,"page")]/p'))).encode()).hexdigest(),
        'headings':[(e.tag,NORM(e.text_content())) for e in root.xpath('.//h2|.//h3|.//h4|.//h5')],
        'notes':notes,
        'superscripts':[(NORM(e.text_content()),e[0].get('href') if len(e) else None) for e in root.xpath('.//sup')],
        'images':[(e.get('src'),e.get('alt')) for e in root.xpath('.//img')],
        'lists_tables':[(e.tag,NORM(e.text_content())) for e in root.xpath('.//ul|.//ol|.//pre|.//table')],
        'ids':sorted(root.xpath('.//*[@id]/@id')),
    }


def page_number(node):
    return int(node.get('data-source-pdf-page') or node.get('id').removeprefix('pdf-page-'))


def md_records(text):
    matches=list(PAGE_MARKER.finditer(text));records={}
    for i,m in enumerate(matches):
        end=matches[i+1].start() if i+1<len(matches) else len(text)
        blocks=[b.strip() for b in re.split(r'\n\s*\n',text[m.end():end]) if b.strip()]
        notes=[b for b in blocks if re.match(r'^\[\^p\d+-note[^\]]+\]:',b)]
        records[int(m[1])]={'comment':m[0],'blocks':[b for b in blocks if b not in notes],'notes':notes}
    assert len(records)==551
    return text[:matches[0].start()].rstrip(),records


def md_find(record,node,start=0):
    expected=NORM(to_md(node))
    found=[i for i,b in enumerate(record['blocks']) if i>=start and NORM(b)==expected]
    if not found:raise AssertionError(('Markdown/HTML paragraph mismatch',expected[:80]))
    return found[0]


def repair(pdf_path):
    assert hashlib.sha256(pdf_path.read_bytes()).hexdigest()==PDF_SHA,'Unexpected edition'
    metadata=json.loads((BOOK/'source.json').read_text())
    assert metadata['source_sha256']==PDF_SHA
    if metadata.get('paragraphRepair'):
        print(json.dumps({'status':'already repaired','metadata':metadata['paragraphRepair']},ensure_ascii=False));return
    pdf=fitz.open(pdf_path)
    documents=[]
    for path in sorted((BOOK/'sections').glob('*.json')):
        data=json.loads(path.read_text())
        if data['id']=='front-matter':continue
        root=html.fragment_fromstring(data['html'],create_parent='article')
        documents.append({'path':path,'data':data,'root':root,'before':fingerprint(root)})
    markdown=(BOOK/'book.md').read_text();intro,md=md_records(markdown)
    splits=[];unmatched=[];unwrapped=0;boundary_breaks=0; joins=[];pages={};parents={}
    # Restore known paragraphs and ordinary line wraps on the nine content-stream pages.
    for document in documents:
        for page in document['root'].xpath('./section[contains(@class,"page")]'):
            n=page_number(page);pages[n]=page
            for sup in page.xpath('./p//sup[not(a)]'):sup.set('data-source-pdf-page',str(n))
            if n not in MATH_PAGES:continue
            starts=[line for line in pdf_lines(pdf,n)
                    if 68<=line['x']<=95 and 10.5<line['size']<11.6
                    and re.match(r'^[“「（(]?[一-龥]',line['text'])]
            old_paragraphs=list(page.xpath('./p'));cursor=0
            # Repeated printed paragraph openings are paired by their source order.
            ranges=[];page_plain=''
            for old in old_paragraphs:
                part,offsets=html_offsets(inner(old))
                ranges.append((old,len(page_plain),len(page_plain)+len(part),offsets))
                page_plain+=part
            planned=defaultdict(set)
            for prefix,count in Counter(NORM(line['text'])[:20] for line in starts).items():
                locations=[m.start() for m in re.finditer(re.escape(prefix),page_plain)]
                if len(locations)!=count:
                    unmatched.append({'pdf_page':n,'kind':'ambiguous printed paragraph opening','prefix':prefix,'printed_count':count,'text_count':len(locations)})
                    continue
                for location in locations:
                    for old,start,end,offsets in ranges:
                        if start<=location<end:
                            if location>start:planned[old].add(offsets[location-start])
                            break
            for old in old_paragraphs:
                if not old.xpath('.//br'):continue
                md_index=md_find(md[n],old,cursor)
                fragment=inner(old);cuts={0}|planned[old]
                boundary_breaks+=sum(bool(re.search(r'<br\s*/?>\s*$',fragment[:cut])) for cut in cuts if cut)
                cuts=sorted(cuts)+[len(fragment)];new=[]
                for a,b in zip(cuts,cuts[1:]):
                    piece,count=unwrap_lines(fragment[a:b]);unwrapped+=count
                    p=html.fragment_fromstring('<p>'+piece+'</p>')
                    if NORM(p.text_content()):new.append(p)
                assert NORM(''.join(p.text_content() for p in new))==NORM(old.text_content())
                md[n]['blocks'][md_index:md_index+1]=[to_md(p) for p in new]
                cursor=md_index+len(new)
                at=page.index(old);tail=old.tail;page.remove(old)
                for j,p in enumerate(new):page.insert(at+j,p)
                new[-1].tail=tail
                if len(new)>1:splits.append({'pdf_page':n,'paragraphs_before':1,'paragraphs_after':len(new),'starts':[p.text_content()[:28] for p in new]})
    # Identify continuations from the first printed line, not terminal punctuation.
    for document in documents:
        own=[p for p in document['root'].xpath('./section[contains(@class,"page")]')]
        for left,right in zip(own,own[1:]):
            a,b=page_number(left),page_number(right)
            if b!=a+1:continue
            left_flow=[e for e in left if e.tag not in ('aside',) and 'page-marker' not in e.get('class','')]
            right_flow=[e for e in right if e.tag not in ('aside',) and 'page-marker' not in e.get('class','')]
            if not left_flow or not right_flow or right_flow[0].tag!='p':continue
            trailing=[]
            while left_flow and left_flow[-1].tag=='figure' and a in SUPPLEMENT_PAGES:trailing.append(left_flow.pop())
            if not left_flow or left_flow[-1].tag!='p':continue
            first=pdf_lines(pdf,b)
            if not first:continue
            line=first[0];threshold=87 if line['size']<10.5 else 68
            target=right_flow[0];prefix=NORM(target.text_content())[:12]
            if line['x']>=threshold or not prefix or prefix not in NORM(line['text']):continue
            # A display equation retains its intentional line boundary.
            if formula(target.text_content().splitlines()[0]):continue
            previous=left_flow[-1]
            joins.append({'section':document['data']['id'],'from_pdf_page':a,'to_pdf_page':b,
                          'first_line_x':round(line['x'],2),'font_size':round(line['size'],2),
                          'previous_tail':previous.text_content()[-40:],'continuation_head':target.text_content()[:40]})
            parents[target]=previous
    # Record Markdown paragraph positions before moving HTML nodes.
    positions={}
    for n,page in pages.items():
        ps=page.xpath('./p')
        if ps:
            first=md_find(md[n],ps[0]);last=md_find(md[n],ps[-1],first)
            positions[n]=(first,last)
    incoming={j['to_pdf_page']:j for j in joins};outgoing={j['from_pdf_page']:j for j in joins}
    # Merge actual paragraphs. Move the existing page ID to a zero-text inline anchor.
    for j in joins:
        left,right=pages[j['from_pdf_page']],pages[j['to_pdf_page']]
        source=right.xpath('./p')[0]
        target=parents[source]
        while target in parents:target=parents[target]
        marker=etree.Element('span',{'id':right.get('id'),'data-source-pdf-page':str(j['to_pdf_page'])})
        right.attrib.pop('id');right.set('data-source-pdf-page',str(j['to_pdf_page']))
        marker.tail=source.text or '';target.append(marker)
        for child in list(source):source.remove(child);target.append(child)
        right.remove(source)
    # Keep all 551 original page comments and every original note definition.
    result=[intro];active=None;pending=[]
    for n,record in md.items():
        blocks=record['blocks'];first,last=positions.get(n,(-1,-1))
        is_in=n in incoming;is_out=n in outgoing
        if is_in:
            assert active is not None,(n,'No preceding paragraph')
            result[active]+=record['comment']+blocks[first]
            if not (is_out and first==last):
                result.extend(pending);pending=[];active=None
        else:result.append(record['comment'])
        for i,block in enumerate(blocks):
            if is_in and i==first:continue
            if is_out and i>last:pending.append(block);continue
            if is_out and i==last:active=len(result)
            result.append(block)
        if is_out:pending.extend(record['notes'])
        else:result.extend(record['notes'])
    assert not pending and active is None
    new_markdown='\n\n'.join(result)+'\n'
    assert PAGE_MARKER.findall(new_markdown)==PAGE_MARKER.findall(markdown)
    def md_body(text):
        text=re.sub(r'<!--.*?-->','',text,flags=re.S)
        text=re.sub(r'^\[\^p\d+-note[^\]]+\]:.*$','',text,flags=re.M)
        text=re.sub(r'!\[[^\]]*\]\([^)]*\)','',text)
        text=re.sub(r'<details>.*?</details>','',text,flags=re.S)
        text=re.sub(r'^#{1,6} .*$', '',text,flags=re.M)
        return NORM(text)
    assert md_body(new_markdown)==md_body(markdown),'Markdown body characters changed'
    markdown_body_sha=hashlib.sha256(md_body(markdown).encode()).hexdigest()
    old_notes=re.findall(r'^\[\^p\d+-note[^\]]+\]:.*$',markdown,re.M)
    new_notes=re.findall(r'^\[\^p\d+-note[^\]]+\]:.*$',new_markdown,re.M)
    assert old_notes==new_notes,'Markdown footnotes changed'
    # The ordered body characters and all protected structures must be identical.
    for document in documents:
        after=fingerprint(document['root'])
        assert after==document['before'],(document['data']['id'],'protected content changed')
    report={'version':1,'source_pdf_sha256':PDF_SHA,'base_commit':'fa41bfa4d12090d5bb2c8e78b700337b83006634',
            'markdown_body_sha256':markdown_body_sha,'cross_page_joins':joins,'math_page_splits':splits,'ordinary_hard_breaks_removed':unwrapped-boundary_breaks,'hard_breaks_converted_to_paragraph_boundaries':boundary_breaks,'total_hard_breaks_removed':unwrapped,
            'unmatched_indented_lines':unmatched,'section_body_sha256':{d['data']['id']:d['before']['body_sha256'] for d in documents},
            'protected_checks':{'body_characters_unchanged':True,'headings_unchanged':True,'original_notes_unchanged':True,'superscripts_and_links_unchanged':True,'images_lists_tables_unchanged':True,'all_existing_page_ids_preserved':True,'markdown_body_characters_unchanged':True,'markdown_note_definitions_unchanged':True,'all_551_markdown_page_comments_preserved':True}}
    for document in documents:
        document['data']['html']=(document['root'].text or '')+''.join(etree.tostring(e,encoding='unicode',method='html') for e in document['root'])
        document['path'].write_text(json.dumps(document['data'],ensure_ascii=False,indent=2)+'\n')
    (BOOK/'book.md').write_text(new_markdown)
    metadata['markdown_sha256']=hashlib.sha256((BOOK/'book.md').read_bytes()).hexdigest()
    metadata['paragraphRepair']={'version':1,'date':'2026-11-19','crossPageJoins':len(joins),'mathPages':sorted(MATH_PAGES),'ordinaryHardBreaksRemoved':unwrapped-boundary_breaks,'hardBreaksConvertedToParagraphBoundaries':boundary_breaks,'newParagraphBoundaries':sum(s['paragraphs_after']-1 for s in splits),'auditFile':'paragraph-repair.json','bodyTextUnchanged':True}
    (BOOK/'source.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
    (BOOK/'paragraph-repair.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'cross_page_joins':len(joins),'split_groups':len(splits),'new_paragraph_boundaries':sum(s['paragraphs_after']-1 for s in splits),'ordinary_hard_breaks_removed':unwrapped-boundary_breaks,'hard_breaks_converted_to_paragraph_boundaries':boundary_breaks,'total_hard_breaks_removed':unwrapped,'unmatched':unmatched},ensure_ascii=False))


if __name__=='__main__':repair(Path(sys.argv[1]))
