"""Dense Tokyo-style facade textures: 2048px HD tile = 32 m wide x 28 m tall (8 floors of 3.5 m).
Thin window grids, mostly dark glass, ~30% warm/cool lit windows, floor bands, mullions. Six building styles."""
import numpy as np, os
from PIL import Image, ImageDraw, ImageFilter
T = "assets/tex"; W = 2048; PX = W / 32.0  # v1.0.5.4 HD          # px per metre
DAY = False
def lit_col(r, warm):
    k = r.uniform(0.6, 1.0)
    if DAY:   # daytime: no lit windows, just varied reflections of sky/clouds in the glass
        k = r.uniform(0.75, 1.05); return (int(150 * k), int(185 * k), int(215 * k)) if r.random() < 0.7 else (int(205 * k), int(220 * k), int(232 * k))
    if r.random() < warm: return (int(255 * k), int(196 * k), int(120 * k))
    if r.random() < 0.7: return (int(185 * k), int(220 * k), int(255 * k))
    return (int(235 * k), int(235 * k), int(215 * k))
def make(seed, wall, glass, floors_px, win_w, gap, lit, warm, band, style):
    r = np.random.default_rng(seed); im = Image.new("RGB", (W, W), wall); d = ImageDraw.Draw(im)
    fh = W // 8
    for f in range(8):
        y0 = f * fh
        d.rectangle((0, y0, W, y0 + band), fill=tuple(int(c * 0.55) for c in wall))       # floor slab
        if style == "curtain":
            d.rectangle((0, y0 + band, W, y0 + fh - 3), fill=glass)
            x = 0
            while x < W:
                if r.random() < lit:
                    run = int(r.integers(1, 4)); c = lit_col(r, warm)
                    d.rectangle((x + 2, y0 + band + 4, min(W, x + run * win_w) - 2, y0 + fh - 8), fill=c)
                    x += run * win_w
                else: x += win_w
            for x in range(0, W, win_w): d.line((x, y0 + band, x, y0 + fh), fill=tuple(int(c * 0.6) for c in wall), width=3)
        else:
            x = gap // 2; wy0 = y0 + band + (10 if style != "apart" else 8); wy1 = y0 + fh - (18 if style != "strip" else 26)
            if style == "strip":   # concrete office: continuous ribbon windows
                d.rectangle((0, wy0, W, wy1), fill=glass)
            while x + win_w <= W:
                if style == "strip":
                    if r.random() < lit: d.rectangle((x, wy0 + 2, x + win_w, wy1 - 2), fill=lit_col(r, warm))
                    d.line((x, wy0, x, wy1), fill=tuple(int(c * 0.8) for c in wall), width=4)
                else:
                    c = lit_col(r, warm) if r.random() < lit else glass
                    d.rectangle((x, wy0, x + win_w, wy1), fill=c)
                    d.line((x + win_w // 2, wy0, x + win_w // 2, wy1), fill=tuple(int(v * 0.5) for v in wall), width=2)   # mullion
                    if c != glass and r.random() < 0.35:   # blinds / curtains
                        for yy in range(wy0, wy1, 6): d.line((x, yy, x + win_w, yy), fill=tuple(int(v * 0.75) for v in c))
                    if style == "apart":     # balcony rail
                        d.rectangle((x - gap // 2, wy1 + 2, x + win_w + gap // 2, wy1 + 12), fill=tuple(min(255, int(v * 1.25)) for v in wall))
                        if r.random() < 0.25: d.rectangle((x + 4, wy1 - 18, x + 20, wy1), fill=(90, 90, 110))   # AC unit
                x += win_w + gap
    im = im.filter(ImageFilter.GaussianBlur(0.6))
    # subtle grime / variation
    n = r.normal(0, 6, (W, W, 1)); a = np.clip(np.asarray(im, float) + n, 0, 255)
    if DAY:   # sky reflection: brighter, bluer towards the top of each floor band + soft diagonal cloud streaks
        yy = np.linspace(0, 1, W)[:, None, None]; xx = np.linspace(0, 1, W)[None, :, None]
        a = a * (0.92 + 0.16 * (1 - yy)) + 10 * np.sin((xx * 3 + yy * 1.5) * 6.28)
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(os.path.join(T, "facade%d%s.png" % (seed, "_day" if DAY else "")))
S = int(PX)
make(0, (30, 34, 44), (12, 18, 30), 0, int(1.6 * PX), 0, 0.30, 0.35, 10, "curtain")      # dark glass tower
make(1, (78, 76, 80), (16, 18, 26), 0, int(1.2 * PX), int(0.5 * PX), 0.30, 0.55, 14, "grid")   # concrete office grid
make(2, (60, 56, 52), (14, 14, 20), 0, int(1.4 * PX), int(0.9 * PX), 0.33, 0.75, 12, "apart")  # apartments w/ balconies
make(3, (66, 66, 72), (14, 16, 24), 0, int(2.2 * PX), 0, 0.30, 0.45, 16, "strip")    # ribbon-window mid-rise
make(4, (24, 40, 46), (10, 22, 28), 0, int(1.3 * PX), 0, 0.28, 0.25, 8, "curtain")   # teal glass
make(5, (88, 70, 60), (16, 14, 18), 0, int(1.0 * PX), int(0.7 * PX), 0.38, 0.85, 12, "grid")   # small shop building, warm

def glass_tower(day):
    """slim modern glass tower: blue/white reflective curtain wall, thin vertical mullions every 1.5 m, floor lines"""
    r = np.random.default_rng(66)
    yy = np.linspace(0, 1, W)[:, None]; xx = np.linspace(0, 1, W)[None, :]
    if day:
        base = np.stack([120 + 50 * (1 - yy) + 0 * xx, 160 + 40 * (1 - yy) + 0 * xx, 205 + 30 * (1 - yy) + 0 * xx], -1)
        base += 18 * np.sin((xx * 2.0 + yy * 0.8) * 6.28)[..., None]
    else:
        base = np.stack([14 + 0 * xx + 0 * yy, 22 + 0 * xx + 0 * yy, 36 + 0 * xx + 8 * (1 - yy)], -1)
    a = base.copy(); fh = W // 8; mw = int(1.5 * PX)
    for f in range(8):
        y0 = f * fh
        for x in range(0, W, mw):
            if not day and r.random() < 0.28:
                c = np.array(lit_col(r, 0.3), float); a[y0 + 8:y0 + fh - 6, x + 2:x + mw - 2] = c
            elif day: a[y0 + 8:y0 + fh - 6, x + 2:x + mw - 2] *= r.uniform(0.9, 1.08)
        a[y0:y0 + 6] = (230, 236, 242) if day else (40, 44, 54)
    for x in range(0, W, mw): a[:, x:x + 3] = (235, 240, 245) if day else (46, 50, 60)
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.5)).save(os.path.join(T, "facade6%s.png" % ("_day" if day else "")))
glass_tower(False)
DAY = True
make(0, (200, 206, 214), (105, 145, 185), 0, int(1.6 * PX), 0, 0.30, 0.35, 10, "curtain")      # dark glass tower
make(1, (176, 172, 166), (70, 95, 120), 0, int(1.2 * PX), int(0.5 * PX), 0.30, 0.55, 14, "grid")   # concrete office grid
make(2, (196, 186, 172), (70, 90, 110), 0, int(1.4 * PX), int(0.9 * PX), 0.33, 0.75, 12, "apart")  # apartments w/ balconies
make(3, (186, 186, 190), (80, 110, 140), 0, int(2.2 * PX), 0, 0.30, 0.45, 16, "strip")    # ribbon-window mid-rise
make(4, (190, 205, 210), (90, 160, 175), 0, int(1.3 * PX), 0, 0.28, 0.25, 8, "curtain")   # teal glass
make(5, (190, 160, 140), (70, 85, 100), 0, int(1.0 * PX), int(0.7 * PX), 0.38, 0.85, 12, "grid")   # small shop building, warm
glass_tower(True)
DAY = False
print("facades ok")
# street-level shop fronts: convenience store, ramen shop, arcade, shutter, pharmacy, cafe (512x128 tile = 16 m)
from PIL import ImageFont
im = Image.new("RGB", (1024, 128), (18, 16, 24)); d = ImageDraw.Draw(im)
shops = [((240, 245, 250), (40, 160, 90)), ((255, 205, 140), (200, 40, 30)), ((255, 150, 220), (120, 40, 200)),
         ((70, 72, 80), None), ((235, 250, 255), (30, 110, 220)), ((255, 220, 170), (120, 70, 40)), ((240, 245, 250), (230, 120, 20)), ((60, 62, 70), None)]
for k, (glass, stripe) in enumerate(shops):
    x0 = k * 128 + 6
    if stripe is None:      # closed shutter
        d.rectangle((x0, 28, x0 + 116, 124), fill=glass)
        for yy in range(30, 124, 5): d.line((x0, yy, x0 + 116, yy), fill=(45, 46, 54))
        continue
    d.rectangle((x0, 30, x0 + 116, 124), fill=glass)
    for xx in range(x0, x0 + 116, 29): d.line((xx, 30, xx, 124), fill=tuple(int(v * 0.6) for v in glass), width=2)
    d.rectangle((x0 + 6, 70, x0 + 110, 76), fill=tuple(int(v * 0.75) for v in glass))   # shelves
    d.rectangle((x0 + 6, 96, x0 + 110, 102), fill=tuple(int(v * 0.75) for v in glass))
    d.rectangle((x0, 6, x0 + 116, 26), fill=stripe)
    d.rectangle((x0, 14, x0 + 116, 18), fill=(250, 250, 250))
im.save(os.path.join(T, "shopfront.png")); print("shopfront ok")
