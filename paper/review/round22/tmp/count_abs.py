import re

line = open('main.tex', encoding='utf-8').read().split('\n')[53]
t = line.replace(r'\mbox{\textsc{competing\_set}}', 'COMPETING_SET')
t = re.sub(r'\\ref\{[^}]*\}', '7.2', t)
t = re.sub(r'\\emph\{([^}]*)\}', r'\1', t)
t = t.replace('---', ' ')
words = t.split()
print('word count:', len(words))
print('parentheticals:', re.findall(r'\([^)]*\)', t))
for s in ['identity-strict', 'branch-localized', 'keyword instrument',
          'one of three blind', 'byte-identically']:
    print('  "%s" in abstract ->' % s, s in t)
