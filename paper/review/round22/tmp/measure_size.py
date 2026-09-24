from PIL import Image
import numpy as np

def cap_height(png, box, thresh=128):
    """Return the vertical extent (px) of dark pixels in crop box (l,t,r,b)."""
    im = Image.open(png).convert('L')
    a = np.array(im.crop(box))
    dark = a < thresh
    rows = np.where(dark.any(axis=1))[0]
    if len(rows) == 0:
        return None
    return int(rows[-1] - rows[0] + 1), box

base = 'pagepng/'
# p-58: body paragraph below table, word "released" at start of para
print('p58 body "released repository" :', cap_height(base+'p-58.png', (203, 688, 260, 706)))
# p-58: A1 header row "TEP fault"
print('p58 A1 header "TEP fault"     :', cap_height(base+'p-58.png', (203, 310, 260, 326)))
# p-58: A1 first cell "IDV1 A/C feed-ratio" region
print('p58 A1 cell "IDV1 A/C"         :', cap_height(base+'p-58.png', (203, 344, 260, 360)))
# p-59: A2 first column "SKAB inlet-valve"
print('p59 A2 cell "SKAB inlet-valve" :', cap_height(base+'p-59.png', (203, 420, 262, 436)))
# p-59: A2 caption first line "Table A2: Per-Scenario"
print('p59 A2 caption line 1          :', cap_height(base+'p-59.png', (203, 196, 262, 212)))
# p-26: Table 6 header "Metric"
print('p26 T6 header "Metric"         :', cap_height(base+'p-26.png', (203, 336, 250, 352)))
# p-26: Table 6 cell "Resolved Top-1"
print('p26 T6 cell "Resolved Top-1"   :', cap_height(base+'p-26.png', (203, 360, 250, 378)))
# p-26: Table 6 caption first line
print('p26 T6 caption line 1          :', cap_height(base+'p-26.png', (203, 196, 250, 212)))
