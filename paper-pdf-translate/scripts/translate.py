"""Bound network retries and prevent the upstream Bing 1000-char truncation."""
import re
import runpy
import sys

import requests
import tenacity

original_request = requests.Session.request


def timed_request(self, *args, **kwargs):
    kwargs.setdefault('timeout', (15, 60))
    return original_request(self, *args, **kwargs)


requests.Session.request = timed_request

import pdf2zh.converter as converter
from pdf2zh.translator import BingTranslator

original_retry = converter.retry


def bounded_retry(*args, **kwargs):
    kwargs.setdefault('stop', tenacity.stop_after_attempt(4))
    return original_retry(*args, **kwargs)


converter.retry = bounded_retry
original_bing = BingTranslator.do_translate


def complete_bing(self, text):
    chunks = []
    remaining = text
    while len(remaining) > 900:
        split_at = remaining.rfind(' ', 400, 900)
        if split_at < 0:
            split_at = 900
        chunks.append(remaining[:split_at])
        remaining = remaining[split_at:].lstrip()
    if remaining:
        chunks.append(remaining)
    result = ' '.join(original_bing(self, chunk) for chunk in chunks)
    # The layout engine requires exact formula placeholder spelling.
    result = re.sub(r'\{\s*[vV]\s*(\d+)\s*\}', r'{v\1}', result)
    expected = re.findall(r'\{v\d+\}', text)
    actual = re.findall(r'\{v\d+\}', result)
    if sorted(expected) != sorted(actual):
        # Some services omit repeated mathematical references as redundant.
        # Translate the surrounding fragments separately so every original
        # formula is retained in its exact source order, rather than guessing
        # where a missing formula belongs in the translated sentence.
        parts = re.split(r'(\{v\d+\})', text)
        translated = []
        for part in parts:
            if not part.strip() or re.fullmatch(r'\{v\d+\}', part):
                translated.append(part)
            elif re.search(r'[A-Za-z]{2}', part):
                translated.append(complete_bing(self, part))
            else:
                translated.append(part)
        result = ' '.join(translated)
        if sorted(expected) != sorted(re.findall(r'\{v\d+\}', result)):
            raise ValueError('Translation changed formula placeholders after safe fallback')
    return result


BingTranslator.do_translate = complete_bing
# CMBX is ordinary bold Computer Modern text, frequently used for headings.
# The upstream default mistakenly protects it as a formula font.
if '-f' not in sys.argv and '--vfont' not in sys.argv:
    sys.argv += ['-f', r'(CM(?:MI|SY|EX)|MS.M|XY|MT|BL|RM|EU|LA|RS|LINE|LCIRCLE|TeX-|rsfs|txsy|wasy|stmary|.*Mono|.*Code|.*Sym|.*Math)']
runpy.run_module('pdf2zh.pdf2zh', run_name='__main__')
