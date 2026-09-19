import glob, os
from pathlib import Path as _P
from playwright.sync_api import sync_playwright
HERE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BASE=_P(HERE).resolve()
def safe_path(x):
    p=_P(x).resolve(); p.relative_to(_BASE); return p
def safe_open(x,mode='r',**kw):
    return open(safe_path(x),mode,**kw)
names=sorted(glob.glob(os.path.join(HERE,'_preview','*.png')))
cells=[f'<figure><img src="file:///{n.replace(os.sep,"/")}"/><figcaption>{os.path.basename(n)}</figcaption></figure>' for n in names]
html=f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
body{{margin:0;background:#555;font:11px sans-serif}}
.g{{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;padding:7px}}
figure{{margin:0;border:1px solid #222;background:#fff}}img{{width:100%;display:block}}
figcaption{{padding:2px 5px;font-weight:700}}</style></head><body><div class="g">{''.join(cells)}</div></body></html>"""
safe_open(os.path.join(HERE,'_build','_full.html'),'w',encoding='utf-8').write(html)
with sync_playwright() as pw:
    b=pw.chromium.launch(headless=True)
    pg=b.new_context(viewport={"width":1560,"height":1000},device_scale_factor=1).new_page()
    pg.goto('file:///'+os.path.join(HERE,'_build','_full.html').replace(os.sep,'/'),wait_until='load'); pg.wait_for_timeout(3000)
    for i,y in enumerate(range(0,40000,980)):
        pg.evaluate(f"window.scrollTo(0,{y})"); pg.wait_for_timeout(950)
        pg.screenshot(path=os.path.join(HERE,'_build',f'_all{i}.png'))
        if pg.evaluate("window.scrollY") < y-5 and y>0: break
    b.close()
print('ok')
