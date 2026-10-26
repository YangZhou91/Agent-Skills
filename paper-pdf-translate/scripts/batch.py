"""Download public paper PDFs and run resumable layout-preserving translation."""
import argparse
import hashlib
import json
import subprocess
import sys
import time
import urllib.request
import shutil
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--root', required=True)
    ap.add_argument('--service', default='bing')
    ap.add_argument('--download-only', action='store_true')
    ap.add_argument('--only')
    ap.add_argument('--pages')
    ap.add_argument('--force', action='store_true')
    args = ap.parse_args()
    root = Path(args.root).resolve()
    for folder in ('original', 'translated', 'logs', 'qa'):
        (root / folder).mkdir(parents=True, exist_ok=True)
    items = json.loads(Path(args.manifest).read_text(encoding='utf-8-sig'))
    status_file = root / 'status.json'
    status = json.loads(status_file.read_text(encoding='utf-8')) if status_file.exists() else {}
    for item in items:
        ident = item['id']
        if args.only and ident != args.only:
            continue
        record = status.setdefault(ident, dict(item))
        source = root / 'original' / f'{ident}.pdf'
        try:
            if not source.exists():
                for attempt in range(3):
                    try:
                        if shutil.which('curl.exe'):
                            result = subprocess.run(['curl.exe', '-f', '-L', '--max-time', '120', '--silent', '--show-error', item['url']], capture_output=True, timeout=130)
                            result.check_returncode()
                            data = result.stdout
                        else:
                            request = urllib.request.Request(item['url'], headers={'User-Agent': 'Mozilla/5.0 (academic PDF download)'})
                            with urllib.request.urlopen(request, timeout=90) as response:
                                data = response.read()
                        if not data.startswith(b'%PDF'):
                            raise ValueError('Response is not a PDF')
                        source.write_bytes(data)
                        break
                    except Exception:
                        if attempt == 2:
                            raise
                        time.sleep(3 * (attempt + 1))
            data = source.read_bytes()
            if not data.startswith(b'%PDF'):
                raise ValueError('Cached source is not a PDF')
            record.update(download='complete', bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
            print(f'{ident}: downloaded {len(data)} bytes', flush=True)
            if not args.download_only:
                out = root / ('pilot' if args.pages else 'translated')
                out.mkdir(exist_ok=True)
                mono = out / f'{ident}-mono.pdf'
                dual = out / f'{ident}-dual.pdf'
                if args.force or not (mono.exists() and dual.exists()):
                    cmd = [sys.executable, '-X', 'utf8', str(Path(__file__).with_name('translate.py')), str(source), '-o', str(out), '-s', args.service, '-li', 'en', '-lo', 'zh', '-t', '4']
                    if args.pages:
                        cmd += ['-p', args.pages]
                    log_path = root / 'logs' / f'{ident}{"-pilot" if args.pages else ""}.log'
                    print(f'{ident}: translating with {args.service}', flush=True)
                    with log_path.open('w', encoding='utf-8') as log:
                        result = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, timeout=3600)
                    if result.returncode or not (mono.exists() and dual.exists()):
                        raise RuntimeError(f'Translation failed; see {log_path}')
                    (root/'qa'/f'{ident}-regions-restored.json').unlink(missing_ok=True)
                record['pilot' if args.pages else 'translation'] = 'complete'
                record['service'] = args.service
                record.pop('error', None)
                print(f'{ident}: translation complete', flush=True)
        except Exception as exc:
            record['error'] = str(exc)
            print(f'{ident}: ERROR {exc}', flush=True)
        status_file.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
