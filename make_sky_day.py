"""procedural daytime sky (equirect, seamless in azimuth): deep blue gradient, layered cumulus, sun glow, horizon haze"""
import numpy as np
from PIL import Image, ImageFilter
W, H = 2048, 1024; rng = np.random.default_rng(2026)
def noise(gw, gh):
    a = rng.random((gh, gw)).astype(np.float32)
    t = np.tile(a, (1, 3)); im = Image.fromarray((t * 255).astype(np.uint8)).resize((W * 3, H), Image.BICUBIC)
    return np.asarray(im, np.float32)[:, W:2 * W] / 255.0
def fbm(base, oct_):
    s = 0; amp = 1; tot = 0
    for o in range(oct_):
        s = s + noise(base * 2 ** o, max(2, base * 2 ** o // 4)) * amp; tot += amp; amp *= 0.5
    return s / tot
y = np.linspace(1, 0, H)[:, None]            # v: 1 = zenith (top row), 0.5 = horizon
el = (y - 0.5) * np.pi                       # elevation (rad)
u = np.linspace(0, 1, W, endpoint=False)[None, :]
e = np.clip(el / (np.pi / 2), 0, 1)
zen = np.array([0.10, 0.32, 0.78]); hor = np.array([0.62, 0.80, 0.96])
k = (1 - e) ** 2.6
sky = zen[None, None] * (1 - k[..., None]) + hor[None, None] * k[..., None]
sky = np.broadcast_to(sky, (H, W, 3)).copy()
# sun
su, se = 0.30, np.radians(38)
du = np.minimum(np.abs(u - su), 1 - np.abs(u - su)) * 2 * np.pi
cosd = np.sin(el) * np.sin(se) + np.cos(el) * np.cos(se) * np.cos(du)
ang = np.arccos(np.clip(cosd, -1, 1))
sky += (np.exp(-ang / 0.06) * 1.2 + np.exp(-ang / 0.35) * 0.25)[..., None] * np.array([1.0, 0.95, 0.85])
# cumulus: heaps of soft round puffs with flat grey bases and sunlit tops; smaller and flatter towards the horizon
detail = fbm(48, 4)
cov = np.zeros((H, W), np.float32); top = np.zeros((H, W), np.float32)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
def row(elev): return (0.5 - elev / np.pi) * H
for c in range(24):
    e0 = np.radians(rng.uniform(2.0, 26.0)); cu = rng.uniform(0, 1) * W
    sc = 14 + 70 * (e0 / np.radians(26)) ** 1.2 * rng.uniform(0.7, 1.3)    # px
    by = row(e0)
    for p in range(int(rng.integers(14, 30))):
        px = cu + rng.normal(0, 1.0) * sc * 1.3; r = sc * rng.uniform(0.5, 1.0)
        py = by - r * 0.4 - abs(rng.normal(0, 0.7)) * sc * 0.9
        x0, x1 = int(px - r * 1.5), int(px + r * 1.5); y0, y1 = int(max(0, py - r * 1.5)), int(min(H, by + 2))
        if y1 <= y0: continue
        xs = np.arange(x0, x1) % W; sub = np.s_[y0:y1]
        dx = (np.arange(x0, x1)[None, :] - px); dy = (np.arange(y0, y1)[:, None] - py)
        dd = np.sqrt(dx ** 2 + dy ** 2) / r * (0.8 + 0.5 * detail[y0:y1][:, xs])
        v = np.clip(1.4 - dd * 1.4, 0, 1) * (np.arange(y0, y1)[:, None] <= by)
        lit = np.clip(1 - (dy + r) / (2 * r), 0, 1) * 0.5 + np.clip(-(dx * 0.6 + dy) / r, 0, 1) * 0.5
        blk = cov[sub][:, xs]; tb = top[sub][:, xs]
        m = v > blk
        tb = np.where(m, lit, tb); blk = np.maximum(blk, v)
        cov[y0:y1, xs] = blk; top[y0:y1, xs] = tb
cov = np.asarray(Image.fromarray((cov * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3.0)), np.float32) / 255
top = np.asarray(Image.fromarray((top * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2.5)), np.float32) / 255
up = np.roll(cov, 14, axis=0); dn = np.roll(cov, -6, axis=0)
shade = np.clip(0.97 + 0.08 * np.clip(cov - up, 0, 1) - 0.40 * np.clip(cov - dn, 0, 1) + (detail - 0.5) * 0.14, 0.6, 1.08)
cloud = np.stack([shade * 0.98, shade * 0.99, shade * 1.03], -1) + (np.exp(-ang / 0.5) * 0.12)[..., None]
cov = np.clip(cov * 1.4, 0, 1)
sky = sky * (1 - cov[..., None]) + cloud * cov[..., None]
# horizon haze + below-horizon fill
haze = np.exp(-np.abs(el) / 0.07)[..., None]
sky = sky * (1 - haze * 0.55) + np.array([0.80, 0.88, 0.95]) * haze * 0.55
below = (el < 0)[..., 0] if el.ndim == 3 else (el < 0)
sky[np.broadcast_to(el < 0, (H, W))] = np.array([0.72, 0.82, 0.90])
Image.fromarray((np.clip(sky, 0, 1) * 255).astype(np.uint8)).save("assets/tex/sky_day.jpg", quality=92)
print("sky ok")
