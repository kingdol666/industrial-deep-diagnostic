import re

tex = open(r'D:\codes\myskills\industrial-deep-diagnostic\paper\main.tex', encoding='utf-8').read()

m = re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}', tex, re.S)
abs_text = m.group(1)
abs_clean = re.sub(r'\$[^$]*\$|[{}~]', ' ', abs_text)
abs_clean = re.sub(r'\\textsc\{[^}]*\}', 'X', abs_clean)
abs_clean = re.sub(r'\\[a-zA-Z]+', ' ', abs_clean)
words = [w for w in re.split(r'\s+', abs_clean) if w.strip()]
print('Abstract words:', len(words))

print('---Highlights---')
for line in open(r'D:\codes\myskills\industrial-deep-diagnostic\paper\highlights.md', encoding='utf-8'):
    line = line.strip()
    if line.startswith('- '):
        h = line[2:]
        print(len(h), '|', h)

print('---Table environments in source order---')
for i, mm in enumerate(re.finditer(r'\\begin\{table\}.*?\\caption\{(.*?)\}', tex, re.S), 1):
    cap = re.sub(r'\s+', ' ', mm.group(1))[:75]
    lab = re.search(r'\\label\{(.*?)\}', tex[mm.start():mm.start() + 2500])
    print(i, '|', (lab.group(1) if lab else 'NO LABEL'), '|', cap)

print('---Figure environments in source order---')
for i, mm in enumerate(re.finditer(r'\\begin\{figure\}.*?\\label\{(.*?)\}', tex, re.S), 1):
    print(i, '|', mm.group(1))
