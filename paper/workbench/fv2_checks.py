import re

BS = chr(92)  # backslash
tex = open(r'D:\codes\myskills\industrial-deep-diagnostic\paper\main.tex', encoding='utf-8').read()

# --- Abstract extraction (no regex backslashes needed) ---
i = tex.find('begin{abstract}')
j = tex.find('end{abstract}')
abs_text = tex[i + len('begin{abstract}'):j]

# --- Doubled-word check across whole file ---
dups = re.findall(r'\b([A-Za-z]+)\s+\1\b', tex, re.I)
print("doubled words in whole main.tex:", dups if dups else "NONE")

# --- Abstract word count ---
clean = re.sub(r'\$[^$]*' + BS + '$', 'MATH', abs_text)  # inline math -> one token
clean = re.sub(BS + '+[A-Za-z]+', ' ', clean)             # drop commands (one or more backslashes + letters)
clean = clean.replace('{', ' ').replace('}', ' ').replace('~', ' ')
clean = clean.replace('---', ' ').replace('--', ' ')
words = clean.split()
print("abstract word count:", len(words))

# --- resizebox: match the THIRD brace group (the content) ---
lines = tex.splitlines()
for idx, l in enumerate(lines):
    if 'resizebox' not in l:
        continue
    # find start of the content group: after \resizebox{...}{!}{
    st = l.find('{!}')  # second arg
    if st == -1:
        st = l.find('{')
    # locate the '{' that opens the content group
    pos = l.find('{', st + 3)
    depth = 0
    closer = None
    started = False
    for ii in range(idx, min(idx + 150, len(lines))):
        seg = l if ii == idx else lines[ii]
        startch = pos if ii == idx else 0
        for ch in seg[startch:]:
            if ch == '{':
                depth += 1
                started = True
            elif ch == '}':
                depth -= 1
                if started and depth == 0:
                    closer = ii + 1
                    break
        if closer:
            break
    print(f"resizebox @ line {idx+1}: content-group closer @ line {closer}")
