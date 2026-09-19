import glob, os, sys
from pathlib import Path as _P
from playwright.sync_api import sync_playwright
HERE=os.path.abspath('.')
_BASE=_P(HERE).resolve()
def safe_path(x):
    p=_P(x).resolve(); p.relative_to(_BASE); return p
def safe_open(x,mode='r',**kw):
    return open(safe_path(x),mode,**kw)
names=sorted(glob.glob(os.path.join(HERE,'_preview','*.png')))
if len(sys.argv)>1: names=[n for n in names if os.path.basename(n)[:2] in sys.argv[1].split(',')]
cells=[f'<figure><img src="file:///{n.replace(os.sep,"/")}"/><figcaption>{os.path.basename(n)}</figcaption></figure>' for n in names]
html=f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
body{{margin:0;background:#fff;font:12px sans-serif}}
.g{{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;padding:10px}}
figure{{margin:0;border:1px solid #bbb}}img{{width:100%;display:block}}
figcaption{{padding:3px 6px;font-weight:700}}</style></head><body><div class="g">{''.join(cells)}</div></body></html>"""
safe_open(os.path.join(HERE,'_sheet.html'),'w',encoding='utf-8').write(html)
with sync_playwright() as pw:
    b=pw.chromium.launch(headless=True)
    pg=b.new_context(viewport={"width":1440,"height":900},device_scale_factor=1).new_page()
    pg.goto('file:///'+os.path.join(HERE,'_sheet.html').replace(os.sep,'/'),wait_until='load')
    pg.wait_for_timeout(2000)
    for i,y in enumerate(range(0,20000,850)):
        pg.evaluate(f"window.scrollTo(0,{y})"); pg.wait_for_timeout(900)
        if pg.evaluate("window.scrollY") < y-5 and y>0: break
        pg.screenshot(path=os.path.join(HERE,f'_sheet{i}.png'))
    b.close()
print('ok')
