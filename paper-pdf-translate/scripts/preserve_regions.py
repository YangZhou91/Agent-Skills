"""Restore explicitly selected original regions (e.g. author names), then rebuild dual PDF."""
import argparse
import json
from pathlib import Path
import pymupdf as fitz

ap=argparse.ArgumentParser()
ap.add_argument('--root',required=True)
ap.add_argument('--regions',required=True,help='JSON object: paper id -> list of {page,rect}')
args=ap.parse_args()
root=Path(args.root)
for ident,regions in json.loads(Path(args.regions).read_text(encoding='utf-8')).items():
    mono_path=root/'translated'/f'{ident}-mono.pdf'
    if not mono_path.exists():
        continue
    marker=root/'qa'/f'{ident}-regions-restored.json'
    if marker.exists() and json.loads(marker.read_text(encoding='utf-8')) == regions:
        continue
    src=fitz.open(root/'original'/f'{ident}.pdf')
    dst=fitz.open(mono_path)
    for region in regions:
        idx=region['page']-1
        rect=fitz.Rect(region['rect'])
        page=dst[idx]
        page.add_redact_annot(rect,fill=(1,1,1))
        page.apply_redactions(images=0,graphics=0)
        if 'text' in region:
            remaining=page.insert_textbox(rect,region['text'],fontname='china-s',fontsize=region.get('fontsize',8),color=(0,0,0))
            if remaining < 0:
                raise ValueError(f'Replacement text does not fit: {ident}, page {idx+1}')
        else:
            page.show_pdf_page(rect,src,idx,clip=rect)
    temp=mono_path.with_suffix('.tmp.pdf')
    dst.save(temp,garbage=4,deflate=True)
    dst.close()
    temp.replace(mono_path)
    dst=fitz.open(mono_path)
    dual=fitz.open()
    for idx in range(len(src)):
        dual.insert_pdf(src,from_page=idx,to_page=idx)
        dual.insert_pdf(dst,from_page=idx,to_page=idx)
    dual.save(root/'translated'/f'{ident}-dual.pdf',garbage=4,deflate=True)
    marker.write_text(json.dumps(regions),encoding='utf-8')
    print(ident,flush=True)
