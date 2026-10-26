"""Create a local reader index and a reproducibility manifest."""
import argparse
import html
import json
from pathlib import Path
import pymupdf as fitz

ap=argparse.ArgumentParser()
ap.add_argument('--root',required=True)
ap.add_argument('--manifest',required=True)
ap.add_argument('--title',default='学术论文中文阅读')
args=ap.parse_args()
root=Path(args.root)
items=json.loads(Path(args.manifest).read_text(encoding='utf-8'))
rows=[]
for item in items:
    ident=item['id']
    item['pages']=len(fitz.open(root/'original'/f'{ident}.pdf'))
    links=[]
    for label,rel in [('中文',f'translated/{ident}-mono.pdf'),('双语对照',f'translated/{ident}-dual.pdf'),('英文原文',f'original/{ident}.pdf')]:
        links.append(f'<a href="{rel}">{label}</a>' if (root/rel).exists() else f'{label}待完成')
    rows.append(f'<tr><td>{html.escape(item["title"])}</td><td>{item["pages"]}</td><td>{" &nbsp; ".join(links)}</td><td><a href="{html.escape(item["url"])}">来源</a></td></tr>')
(root/'manifest.json').write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding='utf-8')
page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>COLLECTION_TITLE</title>
<style>body{max-width:1150px;margin:50px auto;font:16px/1.7 "Microsoft YaHei",sans-serif;color:#202530}h1{font-size:30px}table{border-collapse:collapse;width:100%}td,th{text-align:left;padding:15px;border-bottom:1px solid #ddd}a{color:#125ab1}p{color:#555}</style>
<h1>COLLECTION_TITLE</h1>
<p>COLLECTION_COUNTS。中文为机器翻译阅读版；保留原页面、分栏、公式和插图。作者信息保留原文，图内标签默认保留英文。技术术语与结论请结合英文原文核对。双语版按英文页、对应中文页交替排列。</p>
<table><thead><tr><th>论文</th><th>页数</th><th>阅读版本</th><th>公开来源</th></tr></thead><tbody>'''+''.join(rows)+'''</tbody></table><p>检查证据：<a href="qa/translated/checks.json">逐页结构检查</a>；qa/translated/ 目录保留逐页预览与提取文本。</p></html>'''
page=page.replace('COLLECTION_TITLE',html.escape(args.title)).replace('COLLECTION_COUNTS',f'{len(items)} 篇论文，{sum(x["pages"] for x in items)} 页原文')
(root/'论文目录.html').write_text(page,encoding='utf-8')
print(root/'论文目录.html')
