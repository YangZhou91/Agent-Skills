"""Compare PDF structure and render contact sheets; visual QA remains separate."""
import argparse
import json
import re
from pathlib import Path

import pymupdf as fitz
from PIL import Image, ImageDraw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True)
    ap.add_argument('--folder', default='translated')
    ap.add_argument('--only', help='Render and check one paper id, merging existing checks')
    args = ap.parse_args()
    root = Path(args.root)
    qa = root / 'qa' / args.folder
    qa.mkdir(parents=True, exist_ok=True)
    checks_file=qa/'checks.json'
    results = json.loads(checks_file.read_text(encoding='utf-8')) if args.only and checks_file.exists() else []
    for original in sorted((root / 'original').glob('*.pdf')):
        if args.only and original.stem != args.only:
            continue
        mono = root / args.folder / (original.stem + '-mono.pdf')
        if not mono.exists():
            continue
        src, dst = fitz.open(original), fitz.open(mono)
        item = dict(id=original.stem, source_pages=len(src), translated_pages=len(dst), pages=[], visual_review='pending')
        sheets = []
        for idx, page in enumerate(dst):
            text = page.get_text()
            src_images = {x['digest'].hex() for x in src[idx].get_image_info(hashes=True)}
            dst_images = {x['digest'].hex() for x in page.get_image_info(hashes=True)}
            outside = []
            for block in page.get_text('dict')['blocks']:
                for line in block.get('lines', []):
                    for span in line['spans']:
                        r = fitz.Rect(span['bbox'])
                        if r.x0 < -1 or r.y0 < -1 or r.x1 > page.rect.width+1 or r.y1 > page.rect.height+1:
                            outside.append(span['text'][:80])
            item['pages'].append(dict(page=idx+1, cjk=len(re.findall(r'[\u4e00-\u9fff]', text)), replacement_chars=text.count('\ufffd'), same_size=tuple(src[idx].rect)==tuple(page.rect), source_image_count=len(src_images), images_retained=src_images.issubset(dst_images), outside=outside))
            pix = page.get_pixmap(matrix=fitz.Matrix(0.68, 0.68), alpha=False)
            thumb = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
            cell = Image.new('RGB', (430, 610), '#cccccc')
            thumb.thumbnail((420, 580))
            cell.paste(thumb, ((430-thumb.width)//2, 25))
            ImageDraw.Draw(cell).text((10, 7), f'Page {idx+1}', fill='black')
            sheets.append(cell)
            if len(sheets)==6 or idx==len(dst)-1:
                sheet=Image.new('RGB',(430*3,610*2),'#999999')
                for j, cell in enumerate(sheets):
                    sheet.paste(cell, ((j%3)*430, (j//3)*610))
                sheet.save(qa / f'{original.stem}-sheet-{idx//6+1:02d}.jpg', quality=90)
                sheets=[]
        results = [r for r in results if r['id'] != item['id']]
        results.append(item)
        first=dst[0].get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False)
        first.save(qa / f'{original.stem}-page-01.png')
        (qa / f'{original.stem}.txt').write_text('\n'.join(p.get_text() for p in dst),encoding='utf-8')
        print(f'{original.stem}: {len(src)} -> {len(dst)} pages, CJK {sum(p["cjk"] for p in item["pages"])}, images retained {all(p["images_retained"] for p in item["pages"])}',flush=True)
    (qa/'checks.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':
    main()
