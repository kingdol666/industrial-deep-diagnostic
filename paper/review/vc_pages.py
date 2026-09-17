import subprocess
import re

pdf = r'D:\codes\myskills\industrial-deep-diagnostic\paper\main.pdf'
cap_pat = re.compile(r'(Figure \d+:|Table [A-Za-z]?\d+:)')
cite_pat = re.compile(r'Fig\. (\d)|Table (\d[A-Za-z]?)')

first_cite = {}
cap_pages = {}
sec_pages = {}

for page in range(1, 70):
    out = subprocess.run(['pdftotext', '-f', str(page), '-l', str(page), pdf, '-'],
                         capture_output=True, text=True, errors='replace').stdout
    for mm in cap_pat.finditer(out):
        key = mm.group(1).rstrip(':')
        if key not in cap_pages:
            cap_pages[key] = page
    for mm in cite_pat.finditer(out):
        key = ('Fig. ' + mm.group(1)) if mm.group(1) else ('Table ' + mm.group(2))
        if key not in first_cite and key not in cap_pages:
            first_cite[key] = page
    for sm in re.finditer(r'^(\d+)\. [A-Z]', out, re.M):
        n = sm.group(1)
        if ('sec' + n) not in sec_pages:
            sec_pages['sec' + n] = page

print('--- Float caption pages ---')
for k in sorted(cap_pages, key=lambda x: (x.split()[0], int(re.sub(r"[A-Za-z]", '', x.split()[1]) or 0))):
    print(k, '-> page', cap_pages[k])
print('--- First in-text citation pages (float pages excluded) ---')
for k, v in sorted(first_cite.items()):
    print(k, '-> first cited page', v)
print('--- Section start pages ---')
print(sec_pages)
