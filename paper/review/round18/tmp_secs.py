import re

text = open('main.tex', encoding='utf-8').read()
lines = text.split('\n')

sec_re = re.compile(r'\\section\*?\{([^}]*)\}')
pos = []
for i, l in enumerate(lines):
    m = sec_re.match(l)
    if m:
        pos.append((i, m.group(1)))
pos.append((len(lines), 'END (appendix)'))

print('=== per-section char counts (tex source incl. float bodies) ===')
for k in range(len(pos) - 1):
    s, name = pos[k]
    e = pos[k + 1][0]
    c = sum(len(l) for l in lines[s:e])
    # rough page estimate: ~5500 chars/page double-spaced 12pt
    print(f'{name[:58]:60s} {c:7d} chars  ~{c/5500:.1f} pp')
print()

print('=== floats ===')
fl_re = re.compile(r'\\begin\{(figure|table|algorithm)\}(\[[^\]]*\])?')
for m in fl_re.finditer(text):
    start = m.start()
    end_marker = '\\end{' + m.group(1) + '}'
    end = text.find(end_marker, start)
    block = text[start:end]
    line_no = text[:start].count('\n') + 1
    lab = re.search(r'\\label\{([^}]*)\}', block)
    cap = re.search(r'\\caption(?:\[[^\]]*\])?\{(.{0,130})', block, re.S)
    capt = cap.group(1).replace('\n', ' ') if cap else ''
    print(f'L{line_no:4d} {m.group(1):9s} opts={m.group(2) or "-":5s} label={(lab.group(1) if lab else "??"):24s} :: {capt[:105]}')
print()

print('=== abstract / title / keywords ===')
t = re.search(r'\\title\{([^}]*)\}', text)
a = re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}', text, re.S)
k = re.search(r'\\begin\{keyword\}(.*?)\\end\{keyword\}', text, re.S)
if t:
    print('TITLE:', t.group(1))
if a:
    body = re.sub(r'\s+', ' ', a.group(1)).strip()
    print(f'ABSTRACT ({len(body)} chars, ~{len(body.split())} words):')
    print(body)
if k:
    print('KEYWORDS:', re.sub(r'\s+', ' ', k.group(1)).replace('\\sep', ' | ').strip())
