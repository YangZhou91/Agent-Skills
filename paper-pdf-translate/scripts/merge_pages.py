"""Replace explicitly retranslated pages while retaining the other translated pages."""
import argparse
from pathlib import Path
import pymupdf as fitz

ap=argparse.ArgumentParser()
ap.add_argument('--target',required=True)
ap.add_argument('--repair',required=True)
ap.add_argument('--pages',required=True,help='Comma-separated 1-based page numbers')
args=ap.parse_args()
target=Path(args.target)
src=fitz.open(target)
repair=fitz.open(args.repair)
pages={int(p)-1 for p in args.pages.split(',')}
out=fitz.open()
for i in range(len(src)):
    out.insert_pdf(repair if i in pages else src,from_page=i,to_page=i)
temp=target.with_suffix('.tmp.pdf')
out.save(temp,garbage=4,deflate=True)
src.close()
temp.replace(target)
