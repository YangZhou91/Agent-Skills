"""Validate batch deliverables and package the Chinese reading PDFs."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path
import pymupdf as fitz

ap=argparse.ArgumentParser()
ap.add_argument('--root',required=True)
ap.add_argument('--manifest',required=True)
ap.add_argument('--zip-name',default='中文论文合集.zip')
args=ap.parse_args()
root=Path(args.root)
items=json.loads(Path(args.manifest).read_text(encoding='utf-8'))
checks={r['id']:r for r in json.loads((root/'qa/translated/checks.json').read_text(encoding='utf-8'))}
visual=json.loads((root/'qa/visual-review.json').read_text(encoding='utf-8'))['papers']
status={}
for item in items:
    ident=item['id']
    src=fitz.open(root/'original'/f'{ident}.pdf')
    mono=fitz.open(root/'translated'/f'{ident}-mono.pdf')
    dual=fitz.open(root/'translated'/f'{ident}-dual.pdf')
    assert len(src)==len(mono) and len(dual)==2*len(src),f'Page count mismatch: {ident}'
    for i in range(len(src)):
        assert src[i].get_text()==dual[2*i].get_text(),f'Dual original mismatch: {ident}, {i+1}'
        assert mono[i].get_text()==dual[2*i+1].get_text(),f'Dual translation mismatch: {ident}, {i+1}'
    report=checks[ident]
    assert all(p['same_size'] and p['images_retained'] and not p['outside'] and not p['replacement_chars'] for p in report['pages']),f'PDF structure QA failed: {ident}'
    assert ident in visual,f'Visual review missing: {ident}'
    status[ident]=dict(item,download='complete',translation='complete',automatic_checks='pass',visual_review='completed with recorded scope',source_pages=len(src),chinese_pages=len(mono),bilingual_pages=len(dual),sha256=hashlib.sha256((root/'original'/f'{ident}.pdf').read_bytes()).hexdigest())
(root/'status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
with zipfile.ZipFile(root/args.zip_name,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=5) as archive:
    for item in items:
        p=root/'translated'/f'{item["id"]}-mono.pdf'
        archive.write(p,p.name)
    archive.write(root/'manifest.json','manifest.json')
print(json.dumps(dict(papers=len(items),pages=sum(s['source_pages'] for s in status.values()),chinese_pdfs=len(items),bilingual_pdfs=len(items),zip=str(root/args.zip_name),bytes=(root/args.zip_name).stat().st_size),ensure_ascii=False))
