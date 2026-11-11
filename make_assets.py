"""Builds every derived asset for FIREOUT ONLINE (icon, fonts, procedural textures, neon sign atlas, original audio).
Everything is generated here from scratch (only the cover art is supplied). Run before packaging."""
import os, sys, json, wave, math, numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance, ImageChops
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fs_data as D
ROOT = os.path.dirname(os.path.abspath(__file__)); A = os.path.join(ROOT, "assets"); T = os.path.join(A, "tex"); S = os.path.join(A, "sfx")
os.makedirs(T, exist_ok=True); os.makedirs(S, exist_ok=True)
CJK = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
rng = np.random.default_rng(2026)
def jp(size): return ImageFont.truetype(CJK, size, index=0)
def lat(size): return ImageFont.truetype(os.path.join(A, "ui_font.ttf"), size)

# ---------------- icon / backdrop
cov = Image.open(os.path.join(A, "cover.jpg")).convert("RGB")
w, h = cov.size; s = min(w, h)
sq = cov.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s))
# icon: crop the H-logo-free centre part (title + cars) for readability at small sizes
ic = sq.crop((int(s * 0.04), int(s * 0.10), int(s * 0.96), int(s * 0.98))).resize((256, 256), Image.LANCZOS)
ic.save(os.path.join(A, "icon.png"))
ic.save(os.path.join(A, "icon.ico"), sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
bg = sq.resize((1920, 1920), Image.LANCZOS).crop((0, 420, 1920, 1500)).filter(ImageFilter.GaussianBlur(28))
ImageEnhance.Brightness(bg).enhance(0.5).save(os.path.join(A, "backdrop.jpg"), quality=88)

# ---------------- JP font: full JIS X 0208 subset of Noto Sans CJK JP Bold (SIL OFL) - see tools_jp_font.py (v1.0.4)
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools_jp_font.py"), encoding="utf-8").read())

def glow_text(img, xy, text, font, col, anchor="mm", blur=(18, 7), core=(1, 1, 1), stroke=0):
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.text(xy, text, font=font, fill=tuple(int(c * 255) for c in col) + (255,), anchor=anchor, stroke_width=stroke)
    for b in blur:
        g = lay.filter(ImageFilter.GaussianBlur(b)); img.alpha_composite(g); img.alpha_composite(g)
    img.alpha_composite(lay)
    lay2 = Image.new("RGBA", img.size, (0, 0, 0, 0)); d2 = ImageDraw.Draw(lay2)
    cc = tuple(int((0.55 * c + 0.45 * k) * 255) for c, k in zip(col, core)) + (255,)
    d2.text(xy, text, font=font, fill=cc, anchor=anchor)
    img.alpha_composite(lay2.filter(ImageFilter.GaussianBlur(0.6)))

# ---------------- neon sign atlas (2048x2048): 32 horizontal 512x128 + 32 vertical 128x512
atlas = Image.new("RGBA", (2048, 2048), (0, 0, 0, 255)); meta = {"h": [], "v": []}
def sign_bg(wd, ht, col, style):
    im = Image.new("RGBA", (wd, ht), (0, 0, 0, 255)); d = ImageDraw.Draw(im)
    if style == 0:      # dark panel + neon tube border
        d.rectangle((0, 0, wd, ht), fill=(10, 8, 18, 255))
        lay = Image.new("RGBA", (wd, ht), (0, 0, 0, 0)); dl = ImageDraw.Draw(lay)
        dl.rounded_rectangle((7, 7, wd - 8, ht - 8), radius=10, outline=tuple(int(c * 255) for c in col) + (255,), width=4)
        im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(5))); im.alpha_composite(lay)
    elif style == 1:    # light box: bright coloured panel (text drawn dark)
        g = np.linspace(1.0, 0.75, ht)[:, None, None] * np.array(col)[None, None, :] * 255
        arr = np.broadcast_to(g, (ht, wd, 3)).astype(np.uint8)
        im = Image.fromarray(arr).convert("RGBA"); d = ImageDraw.Draw(im)
        d.rectangle((0, 0, wd - 1, ht - 1), outline=(255, 255, 255, 255), width=3)
    else:               # white light box with coloured text
        d.rectangle((0, 0, wd, ht), fill=(235, 238, 245, 255)); d.rectangle((0, 0, wd - 1, ht - 1), outline=(140, 140, 150, 255), width=4)
    return im
for i, txt in enumerate(D.SIGNS_H):
    col = D.NEON[i % len(D.NEON)]; style = [0, 0, 1, 0, 2][i % 5]
    im = sign_bg(512, 128, col, style)
    size = 78 if len(txt) <= 5 else (64 if len(txt) <= 7 else 50)
    fnt = jp(size)
    if style == 0: glow_text(im, (256, 62), txt, fnt, col)
    elif style == 1: ImageDraw.Draw(im).text((256, 62), txt, font=fnt, fill=(15, 10, 25, 255), anchor="mm")
    else: ImageDraw.Draw(im).text((256, 62), txt, font=fnt, fill=tuple(int(c * 200) for c in col) + (255,), anchor="mm")
    x, y = (i % 4) * 512, (i // 4) * 128; atlas.paste(im, (x, y))
    meta["h"].append([x / 2048, 1 - (y + 128) / 2048, (x + 512) / 2048, 1 - y / 2048, style])
for i, txt in enumerate(D.SIGNS_V):
    col = D.NEON[(i * 3 + 1) % len(D.NEON)]; style = [0, 1, 0, 2][i % 4]
    im = sign_bg(128, 512, col, style)
    n = len(txt); size = min(92, int(470 / max(n, 1)) - 6)
    fnt = jp(size); yy = 256 - (n - 1) * (size + 4) / 2
    for k, ch in enumerate(txt):
        p = (64, int(yy + k * (size + 4)))
        if style == 0: glow_text(im, p, ch, fnt, col, blur=(12, 5))
        elif style == 1: ImageDraw.Draw(im).text(p, ch, font=fnt, fill=(15, 10, 25, 255), anchor="mm")
        else: ImageDraw.Draw(im).text(p, ch, font=fnt, fill=tuple(int(c * 200) for c in col) + (255,), anchor="mm")
    x, y = (i % 16) * 128, 1024 + (i // 16) * 512; atlas.paste(im, (x, y))
    meta["v"].append([x / 2048, 1 - (y + 512) / 2048, (x + 128) / 2048, 1 - y / 2048, style])
atlas.convert("RGB").save(os.path.join(T, "signs.png"))
json.dump(meta, open(os.path.join(T, "signs.json"), "w"))

# ---------------- building facade textures (8x8 window cells each, tileable)
def facade(seed, base, lit_p, warm):
    r = np.random.default_rng(seed); W = 512; im = Image.new("RGB", (W, W), base); d = ImageDraw.Draw(im)
    cw = W // 8
    for gy in range(8):
        d.rectangle((0, gy * cw, W, gy * cw + 7), fill=tuple(int(c * 0.6) for c in base))  # floor slab band
        for gx in range(8):
            x0, y0 = gx * cw + 9, gy * cw + 14; x1, y1 = x0 + cw - 18, y0 + cw - 22
            if r.random() < lit_p:
                k = r.uniform(0.55, 1.0)
                c = (255 * k, 205 * k, 140 * k) if r.random() < warm else (170 * k, 215 * k, 255 * k)
                if r.random() < 0.15: c = (255 * k, 120 * k, 200 * k)
                d.rectangle((x0, y0, x1, y1), fill=tuple(int(v) for v in c))
                if r.random() < 0.4:   # blinds
                    for yy in range(y0, y1, 5): d.line((x0, yy, x1, yy), fill=tuple(int(v * 0.7) for v in c))
            else:
                d.rectangle((x0, y0, x1, y1), fill=(14, 16, 24))
                d.line((x0, y1, x1, y0), fill=(26, 30, 44), width=2)
    im = im.filter(ImageFilter.GaussianBlur(0.7))
    return im
for i, (base, lp, wm) in enumerate([((28, 30, 40), 0.42, 0.7), ((36, 30, 36), 0.30, 0.4), ((22, 28, 34), 0.55, 0.3), ((40, 38, 44), 0.22, 0.8)]):
    facade(10 + i, base, lp, wm).save(os.path.join(T, "facade%d.png" % i))
# shop-front ground floor strip (lit shop windows / shutters), HD 2048x256
im = Image.new("RGB", (2048, 256), (20, 18, 26)); d = ImageDraw.Draw(im)
for k in range(4):
    x0 = k * 512 + 16; c = D.NEON[k * 2 % len(D.NEON)]
    d.rectangle((x0, 60, x0 + 448, 248), fill=(int(230 * 0.9), int(215 * 0.9), int(190 * 0.9)) if k % 2 == 0 else (60, 62, 70))
    d.rectangle((x0, 16, x0 + 448, 52), fill=tuple(int(v * 255) for v in c))
im.save(os.path.join(T, "shopfront.png"))

# ---------------- road / sidewalk (v1.0.5.4 HD 2048)
ASZ = 2048
n = rng.normal(0, 1, (ASZ, ASZ)); n = np.array(Image.fromarray(((n * 20) + 128).clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2)), float)
puddle = np.array(Image.fromarray((rng.random((128, 128)) * 255).astype(np.uint8)).resize((ASZ, ASZ), Image.BICUBIC).filter(ImageFilter.GaussianBlur(18)), float) / 255
grain = np.array(Image.fromarray((rng.random((ASZ, ASZ)) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.4)), float)
v = 28 + (n - 128) * 0.40 + (grain - 128) * 0.08
rgb = np.stack([v * 0.92, v * 0.94, v * 1.05], 2)
alpha = 220 - 90 * np.clip((puddle - 0.45) * 4, 0, 1)
Image.fromarray(np.dstack([rgb.clip(0, 255), alpha]).astype(np.uint8), "RGBA").save(os.path.join(T, "asphalt.png"))
sw = Image.new("RGB", (ASZ, ASZ), (62, 60, 66)); d = ImageDraw.Draw(sw)
for k in range(0, ASZ, 128):
    d.line((k, 0, k, ASZ), fill=(40, 38, 44), width=5); d.line((0, k, ASZ, k), fill=(40, 38, 44), width=5)
# fine aggregate noise
noise = Image.fromarray((rng.integers(0, 40, (ASZ, ASZ))).astype(np.uint8)).convert("L")
sw = Image.blend(sw, Image.merge("RGB", (noise, noise, noise)), 0.12)
sw.filter(ImageFilter.GaussianBlur(0.8)).save(os.path.join(T, "sidewalk.png"))

# ---------------- night sky (equirect 2048x1024, upper half used)
H, W = 1024, 2048
yy = np.linspace(0, 1, H)[:, None]                 # 0 top -> 1 bottom; horizon at 0.5
t = np.clip(yy / 0.5, 0, 1)
top = np.array([4, 5, 16]); mid = np.array([30, 14, 52]); hor = np.array([120, 40, 110])
col = np.where(t < 0.7, top + (mid - top) * (t / 0.7), mid + (hor - mid) * ((t - 0.7) / 0.3))
sky = np.broadcast_to(col[:, None, :], (H, W, 3)).astype(float).copy()
cl = np.array(Image.fromarray((rng.random((32, 128)) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(30)), float) / 255
band = np.exp(-((yy - 0.40) / 0.08) ** 2)
sky += (cl[..., None] ** 2) * band[..., None] * np.array([90, 40, 110]) * 0.8
for _ in range(1800):
    x, y = rng.integers(0, W), int(rng.random() ** 1.6 * H * 0.42); b = rng.uniform(80, 255)
    sky[y, x] = np.maximum(sky[y, x], [b, b, b * 1.05])
m = Image.fromarray(sky.clip(0, 255).astype(np.uint8)); d = ImageDraw.Draw(m)
for r_, a in ((70, 25), (46, 60), (30, 255)):
    d.ellipse((1500 - r_, 180 - r_, 1500 + r_, 180 + r_), fill=(min(255, 200 + a // 5), 205, 230) if a == 255 else (60 + a, 50 + a, 90 + a))
m = m.filter(ImageFilter.GaussianBlur(0.5)); sky = np.array(m, float)
sky[H // 2:] = hor
Image.fromarray(sky.clip(0, 255).astype(np.uint8)).save(os.path.join(T, "sky.jpg"), quality=90)

# ---------------- environment map for glossy car paint (equirect HD 1024x512)
E = np.zeros((512, 1024, 3)); ey = np.linspace(0, 1, 512)[:, None, None]
E += np.where(ey < 0.5, 8 + 50 * (ey / 0.5) ** 3, 6) * np.array([0.5, 0.4, 1.0])
for _ in range(90):
    x, y = rng.integers(0, 512), rng.integers(70, 140); c = np.array(D.NEON[rng.integers(0, len(D.NEON))]) * rng.uniform(120, 255)
    w_, h_ = rng.integers(3, 18), rng.integers(4, 40)
    E[max(0, y - h_):y, x:x + w_] = np.maximum(E[max(0, y - h_):y, x:x + w_], c)
E[118:124] += np.array([140, 90, 160])
for k in range(0, 512, 64): E[0:60, k:k + 30] += 50          # street-light strips overhead
env = Image.fromarray(E.clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3))
env.save(os.path.join(T, "env.png"))

# ---------------- sprites
def radial(sz, p=2.0):
    yv, xv = np.mgrid[-1:1:sz * 1j, -1:1:sz * 1j]; r = np.clip(1 - np.sqrt(xv ** 2 + yv ** 2), 0, 1) ** p
    return Image.fromarray(np.dstack([np.full_like(r, 255), np.full_like(r, 255), np.full_like(r, 255), r * 255]).astype(np.uint8), "RGBA")
radial(128, 2.2).save(os.path.join(T, "glow.png"))
radial(64, 0.7).save(os.path.join(T, "dot.png"))
# headlight cone on the ground (long soft triangle)
yv, xv = np.mgrid[0:1:256j, -1:1:128j]; r = np.clip(1 - np.abs(xv) / (0.15 + 0.85 * yv), 0, 1) ** 1.5 * (1 - yv) ** 1.2 * np.clip(yv * 8, 0, 1)
Image.fromarray(np.dstack([np.full_like(r, 255)] * 3 + [r * 255]).astype(np.uint8), "RGBA").save(os.path.join(T, "beam.png"))
# rain streak
r = np.zeros((64, 4)); r[:, 1:3] = np.linspace(0, 1, 64)[:, None] ** 1.5
Image.fromarray(np.dstack([np.full_like(r, 255)] * 3 + [r * 200]).astype(np.uint8), "RGBA").save(os.path.join(T, "streak.png"))
# minimap ring mask / vignette
yv, xv = np.mgrid[-1:1:512j, -1:1:512j]; rr = np.sqrt(xv ** 2 + yv ** 2)
vig = np.clip((rr - 0.55) / 0.6, 0, 1) ** 1.6
Image.fromarray(np.dstack([np.zeros_like(vig)] * 3 + [vig * 200]).astype(np.uint8), "RGBA").save(os.path.join(T, "vignette.png"))
# giant video-board image: cover art framed
vb = cov.resize((512, 512), Image.LANCZOS).crop((0, 64, 512, 448)); vb.save(os.path.join(T, "videoboard.jpg"), quality=88)

# ---------------- title logos (neon katakana title + latin subtitle) with alpha
def logo(path, W=1900, Hh=420, small=False):
    im = Image.new("RGBA", (W, Hh), (0, 0, 0, 0))
    glow_text(im, (W // 2, int(Hh * 0.40)), D.TITLE_JP, jp(132 if not small else 110), (1.0, 0.25, 0.65), blur=(26, 10))
    # gradient overlay on the core text
    msk = Image.new("L", (W, Hh), 0); ImageDraw.Draw(msk).text((W // 2, int(Hh * 0.40)), D.TITLE_JP, font=jp(132 if not small else 110), fill=255, anchor="mm")
    g = np.zeros((Hh, W, 3)); xs = np.linspace(0, 1, W)
    for i, c in enumerate([(1.0, 0.35, 0.7), (0.4, 0.9, 1.0), (1.0, 0.95, 0.75)]):
        g[..., i] = 255 * (c[i] if False else 1)
    g[..., 0] = 255 * (1.0 - 0.45 * xs); g[..., 1] = 255 * (0.55 + 0.4 * np.sin(xs * 3.1)); g[..., 2] = 255 * (0.75 + 0.25 * xs)
    gi = Image.fromarray(g.astype(np.uint8)).convert("RGBA"); gi.putalpha(ImageChops.multiply(msk, Image.new("L", (W, Hh), 235)))
    im.alpha_composite(gi)
    glow_text(im, (W // 2, int(Hh * 0.84)), "F I R E O U T   S H I N E", lat(66), (0.35, 0.9, 1.0), blur=(14, 5))
    im.save(path)
logo(os.path.join(T, "logo.png"))

# ---------------- audio (all original, synthesised here)
SR = 22050
def save(name, x, sr=SR):
    x = np.clip(x, -1, 1); dd = (x * 30000).astype(np.int16)
    with wave.open(os.path.join(S, name + ".wav"), "wb") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(sr); f.writeframes(dd.tobytes())
def tt(dur): return np.arange(int(SR * dur)) / SR
def env(n, a=0.01, r=0.3):
    e = np.ones(n); na = max(1, int(a * SR)); e[:na] = np.linspace(0, 1, na); return e * np.exp(-np.linspace(0, 1, n) / r)
def lp(x, k=0.1):
    y = np.zeros_like(x); acc = 0.0
    for i in range(len(x)): acc += k * (x[i] - acc); y[i] = acc
    return y
# engine loop: 1 s, base 55 Hz firing (integer cycles => seamless), harmonics + rasp
x = tt(1.0); f0 = 55.0
eng = sum(np.sin(2 * np.pi * f0 * k * x + k) / k ** 0.9 for k in range(1, 14))
eng += 0.5 * np.sign(np.sin(2 * np.pi * f0 * 2 * x)) * 0.3
noise = rng.standard_normal(len(x)); eng += 0.25 * lp(noise, 0.3) * (0.6 + 0.4 * np.sin(2 * np.pi * f0 * x))
save("engine", eng / np.max(np.abs(eng)) * 0.7)
x = tt(1.0); idle = sum(np.sin(2 * np.pi * 27.5 * k * x) / k for k in range(1, 9)) * (0.7 + 0.3 * np.sin(2 * np.pi * 13.75 * x))
save("engine_low", idle / np.max(np.abs(idle)) * 0.6)
# siren loop (2 s, two-tone wail) -- integer number of cycles
x = tt(2.0); fs = 760 + 260 * np.sin(2 * np.pi * 0.5 * x); ph = 2 * np.pi * np.cumsum(fs) / SR
sir = np.sign(np.sin(ph)) * 0.35 + np.sin(ph) * 0.4; save("siren", lp(sir, 0.35) * 0.8)
x = tt(1.0); save("skid", lp(rng.standard_normal(len(x)), 0.5) * 0.5 * (0.8 + 0.2 * np.sin(2 * np.pi * 7 * x)))
x = tt(1.0); save("wind", lp(rng.standard_normal(len(x)), 0.06) * 2.0)
x = tt(1.0); save("rain", lp(rng.standard_normal(len(x)), 0.7) * 0.25)
x = tt(0.9); save("nitro", (lp(rng.standard_normal(len(x)), 0.4) * 0.9 + np.sin(2 * np.pi * (200 + 900 * x) * x) * 0.2) * env(len(x), 0.02, 0.6))
x = tt(0.6); save("crash", (rng.standard_normal(len(x)) * 0.9 + np.sin(2 * np.pi * 60 * x) * 0.8) * env(len(x), 0.001, 0.18))
x = tt(0.25); save("bump", (lp(rng.standard_normal(len(x)), 0.2) * 1.5 + np.sin(2 * np.pi * 80 * x)) * env(len(x), 0.001, 0.15))
x = tt(0.35); save("checkpoint", (np.sin(2 * np.pi * 1320 * x) * (x < 0.12) + np.sin(2 * np.pi * 1760 * x) * (x >= 0.12)) * env(len(x), 0.005, 0.5) * 0.5)
x = tt(0.25); save("beep", np.sin(2 * np.pi * 880 * x) * env(len(x), 0.005, 0.6) * 0.5)
x = tt(0.7); save("go", (np.sin(2 * np.pi * 1760 * x) + 0.5 * np.sin(2 * np.pi * 2640 * x)) * env(len(x), 0.005, 0.5) * 0.45)
x = tt(0.07); save("click", np.sin(2 * np.pi * 1500 * x) * env(len(x), 0.001, 0.2) * 0.4)
x = tt(1.6); save("busted", sum(np.sin(2 * np.pi * f_ * x) * (x > d0) for f_, d0 in ((392, 0), (311, 0.35), (233, 0.7))) * 0.3 * env(len(x), 0.01, 0.7))
x = tt(1.6); save("win", sum(np.sin(2 * np.pi * f_ * x) * (x > d0) for f_, d0 in ((523, 0), (659, 0.15), (784, 0.3), (1046, 0.45))) * 0.22 * env(len(x), 0.01, 0.8))
x = tt(0.5); save("heat", (np.sin(2 * np.pi * 600 * x) * (np.sin(2 * np.pi * 8 * x) > 0)) * env(len(x), 0.005, 0.5) * 0.4)

# ---------------- music: original synthwave loops
def synth_track(bpm, bars, prog, seed, drive=True):
    r = np.random.default_rng(seed); beat = 60 / bpm; L = int(SR * beat * 4 * bars); out = np.zeros(L)
    tl = np.arange(L) / SR
    def note(f, start, dur, kind="saw", vol=0.2, rel=0.2):
        i0 = int(start * SR); n_ = int(dur * SR)
        if i0 >= L: return
        n_ = min(n_, L - i0); x_ = np.arange(n_) / SR
        if kind == "saw": w_ = 2 * ((x_ * f) % 1) - 1; w_ = lp(w_, 0.25) if n_ < 30000 else w_
        elif kind == "sq": w_ = np.sign(np.sin(2 * np.pi * f * x_)) * 0.6
        else: w_ = np.sin(2 * np.pi * f * x_)
        e = np.minimum(1, x_ / 0.005) * np.exp(-x_ / max(rel, 1e-3))
        out[i0:i0 + n_] += w_ * e * vol
    for bar in range(bars):
        root = prog[bar % len(prog)]; b0 = bar * 4 * beat
        for k in range(8):                                   # bass 8ths
            note(root / 2 * (2 if k % 4 == 3 else 1), b0 + k * beat / 2, beat / 2, "saw", 0.16, 0.18)
        arp = [1, 1.5, 2, 2.5198, 3, 2.5198, 2, 1.5]
        for k in range(16):                                  # arpeggio 16ths
            note(root * arp[k % 8] * 2, b0 + k * beat / 4, beat / 4, "sq", 0.035, 0.09)
        for f_ in (1, 1.2599, 1.4983):                       # pad (minor triad)
            note(root * f_ * 2, b0, beat * 4, "sin", 0.05, 2.5)
        if drive:
            for k in range(4):
                i0 = int((b0 + k * beat) * SR); n_ = int(0.25 * SR); x_ = np.arange(n_) / SR
                if i0 + n_ <= L: out[i0:i0 + n_] += np.sin(2 * np.pi * (50 + 120 * np.exp(-x_ * 30)) * x_) * np.exp(-x_ * 12) * 0.5
                if k % 2 == 1:
                    n2 = int(0.18 * SR)
                    if i0 + n2 <= L: out[i0:i0 + n2] += r.standard_normal(n2) * np.exp(-np.arange(n2) / SR * 22) * 0.22
            for k in range(8):
                i0 = int((b0 + k * beat / 2 + beat / 4) * SR); n_ = int(0.04 * SR)
                if i0 + n_ <= L: out[i0:i0 + n_] += r.standard_normal(n_) * np.exp(-np.arange(n_) / SR * 90) * 0.06
    # simple feedback echo for space
    dl = int(beat * 0.75 * SR); y = out.copy()
    for i in range(dl, L): y[i] += 0.28 * y[i - dl]
    return y / np.max(np.abs(y)) * 0.8
A_ = 55.0
save("music_race", synth_track(118, 16, [A_ * 2, A_ * 2 * 0.7937, A_ * 2 * 0.8909, A_ * 2 * 0.7491], 3))
save("music_menu", synth_track(92, 8, [A_ * 2 * 0.8909, A_ * 2 * 0.7491, A_ * 2, A_ * 2 * 0.6674], 5, drive=False))
print("assets ok")

# ---------------- original hibiscus floral print (Daniel's shirt), tileable 1024
def floral(path, S_=1024):
    r = np.random.default_rng(31)
    big = Image.new("RGB", (S_ * 3, S_ * 3), (16, 34, 70)); d = ImageDraw.Draw(big)
    items = [(r.uniform(0, S_), r.uniform(0, S_), r.uniform(0.6, 1.2), r.uniform(0, 6.28), r.integers(0, 3)) for _ in range(26)]
    leaves = [(r.uniform(0, S_), r.uniform(0, S_), r.uniform(0.7, 1.3), r.uniform(0, 6.28)) for _ in range(34)]
    for ox in (0, S_, 2 * S_):
        for oy in (0, S_, 2 * S_):
            for x, y, s, a, _ in []: pass
            for x, y, s, a in leaves:
                cx, cy = x + ox, y + oy; L_ = 110 * s
                pts = []
                for k in range(24):
                    t = k / 23 * math.pi
                    w_ = math.sin(t) * 34 * s; along = -L_ / 2 + L_ * k / 23
                    pts.append((along, w_))
                pts += [(p[0], -p[1]) for p in reversed(pts)]
                rp = [(cx + px * math.cos(a) - py * math.sin(a), cy + px * math.sin(a) + py * math.cos(a)) for px, py in pts]
                d.polygon(rp, fill=(30, 110, 70)); d.line([rp[0], rp[23]], fill=(70, 160, 100), width=3)
            for x, y, s, a, kind in items:
                cx, cy = x + ox, y + oy; R = 70 * s
                col = [(225, 40, 60), (250, 120, 40), (245, 90, 160)][kind]
                for p_ in range(5):
                    pa = a + p_ * 2 * math.pi / 5
                    px, py = cx + math.cos(pa) * R * 0.55, cy + math.sin(pa) * R * 0.55
                    d.ellipse((px - R * 0.5, py - R * 0.5, px + R * 0.5, py + R * 0.5), fill=col)
                d.ellipse((cx - R * 0.22, cy - R * 0.22, cx + R * 0.22, cy + R * 0.22), fill=(120, 10, 30))
                ex, ey = cx + math.cos(a + 0.6) * R * 0.75, cy + math.sin(a + 0.6) * R * 0.75
                d.line((cx, cy, ex, ey), fill=(250, 220, 90), width=5); d.ellipse((ex - 7, ey - 7, ex + 7, ey + 7), fill=(255, 230, 80))
    big.crop((S_, S_, 2 * S_, 2 * S_)).filter(ImageFilter.GaussianBlur(0.8)).save(path)
floral(os.path.join(T, "floral.png"))

# ---------------- FRGARAGE neon sign + boot splash
im = Image.new("RGBA", (1024, 256), (8, 6, 16, 255)); dd = ImageDraw.Draw(im)
dd.rounded_rectangle((10, 10, 1013, 245), radius=24, outline=(255, 60, 170, 255), width=6)
glow_text(im, (512, 128), "FRGARAGE", lat(150), (0.2, 0.95, 1.0), blur=(22, 8))
im.convert("RGB").save(os.path.join(T, "frgarage.png"))
sp = Image.new("RGBA", (1600, 900), (0, 0, 0, 255))
hl = Image.open("/workspace/hyperion-digital-ex/assets/icon_source_user.png").convert("RGBA"); hl.thumbnail((340, 340))
sp.alpha_composite(hl, ((1600 - hl.width) // 2, 200))
glow_text(sp, (800, 640), "EX Inc. / EX Inc.", lat(64), (1.0, 0.82, 0.25), blur=(16, 6))
ImageDraw.Draw(sp).text((800, 730), "presents", font=lat(36), fill=(200, 200, 210, 255), anchor="mm")
sp.convert("RGB").save(os.path.join(T, "splash.jpg"), quality=92)
print("extra assets ok")
