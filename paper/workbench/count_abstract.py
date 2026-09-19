import re
src = open(r'D:\codes\myskills\industrial-deep-diagnostic\paper\main.tex', encoding='utf-8').read()
m = re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}', src, re.S)
abs_text = m.group(1).strip()
t = abs_text.replace(r'\mbox{\textsc{competing\_set}}', 'COMPETINGSET')
t = re.sub(r'\$[^$]*\$', 'X', t)
t = re.sub(r'\\[a-zA-Z]+', '', t)
t = re.sub(r'[{}~]', ' ', t)
words = [w for w in re.split(r'\s+', t) if re.search(r'[A-Za-z0-9]', w)]
print('WORD COUNT:', len(words))
# check qualifiers present
checks = {
    'recall caveat (family agreement, never identity)': 'never identity' in abs_text,
    'recorded-replay qualifier': 'recorded replays of live calls' in abs_text,
    'timestamps-excluded qualifier': 'timestamps excluded' in abs_text,
    'cap-flags qualification': 'capped' in abs_text and 'competing' in abs_text.lower(),
    'recall caveat': 'never identity' in abs_text,
}
for k, v in checks.items():
    print(f'{k}: {v}')
# duplicated word check
dups = re.findall(r'\b(\w+)\s+\1\b', t)
print('duplicated words:', dups)
# duplicate sentence check within abstract
sents = re.split(r'(?<=[.;])\s+', t)
seen = {}
for s in sents:
    key = re.sub(r'\W+', '', s.lower())[:60]
    seen[key] = seen.get(key, 0) + 1
print('repeated sentence keys:', {k: v for k, v in seen.items() if v > 1})
