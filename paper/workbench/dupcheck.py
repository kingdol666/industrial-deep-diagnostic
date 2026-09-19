import re, collections
txt = open('main.tex', encoding='utf-8').read()
txt = re.sub(r'[^\]%.*', '', txt)
flat = re.sub(r'\s+', ' ', txt)
sents = re.split(r'(?<=[.!?]) ', flat)
norm = [re.sub(r'\[a-zA-Z]+|[{}]', '', s).strip().lower() for s in sents]
norm = [n for n in norm if len(n.split()) >= 12]
c = collections.Counter(norm)
dups = {k: v for k, v in c.items() if v > 1}
print('DUPLICATED SENTENCES >=12 words:', len(dups))
for k, v in dups.items():
    print('-', v, ':', k[:140])
