"""v1.0.4 art for IX LAPTOPOS G9 (wallpaper, app icons, browser buttons, trash icon) and MISTO 2 (icon + lenses/frames).
All original drawings made here with PIL. Run: python3 tools_laptop_art.py"""
import os, math, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
B = os.path.dirname(os.path.abspath(__file__)); T = os.path.join(B, "assets", "tex")
UI = os.path.join(B, "assets", "ui_font.ttf"); JP = os.path.join(B, "assets", "jp_font.otf")
def F(p, s): return ImageFont.truetype(p, s)
rng = random.Random(4)
# ---- wallpaper: dusk gradient, neon skyline, "G9" monogram
W, H = 1600, 1000
im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im)
for y in range(H):
    t = y / H; d.line([(0, y), (W, y)], fill=(int(20 + 90 * t), int(10 + 20 * t), int(60 + 60 * (1 - t))))
d.ellipse((1050, 420, 1350, 720), fill=(255, 120, 150))
for k in range(60):
    x = rng.randint(-40, W); w = rng.randint(40, 120); h = rng.randint(120, 420)
    d.rectangle((x, H - h, x + w, H), fill=(14, 10, 30))
    for wy in range(H - h + 12, H - 10, 22):
        for wx in range(x + 8, x + w - 8, 16):
            if rng.random() < 0.35: d.rectangle((wx, wy, wx + 7, wy + 10), fill=rng.choice([(255, 200, 120), (120, 220, 255), (255, 120, 200)]))
gl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); g = ImageDraw.Draw(gl)
g.text((W // 2, 330), "G9", font=F(UI, 300), fill=(255, 255, 255, 60), anchor="mm")
g.text((W // 2, 520), "IX LAPTOPOS", font=F(UI, 64), fill=(255, 255, 255, 90), anchor="mm")
im = Image.alpha_composite(im.convert("RGBA"), gl); im.convert("RGB").save(os.path.join(T, "ix_wall.png"))
# ---- app icons (rounded tiles with simple drawn symbols)
def tile(name, c1, c2, draw):
    S = 256; t = Image.new("RGBA", (S, S), (0, 0, 0, 0)); m = Image.new("L", (S, S), 0)
    ImageDraw.Draw(m).rounded_rectangle((8, 8, S - 8, S - 8), 56, fill=255)
    gr = Image.new("RGBA", (S, S))
    gd = ImageDraw.Draw(gr)
    for y in range(S):
        u = y / S; gd.line([(0, y), (S, y)], fill=tuple(int(a + (b - a) * u) for a, b in zip(c1, c2)) + (255,))
    t.paste(gr, (0, 0), m); dd = ImageDraw.Draw(t); draw(dd, S); t.save(os.path.join(T, "ix_icon_%s.png" % name))
W_ = (255, 255, 255, 255)
tile("bank", (40, 170, 120), (10, 90, 60), lambda d, S: (d.rectangle((60, 110, 196, 190), outline=W_, width=10), d.text((128, 150), "¥", font=F(JP, 70), fill=W_, anchor="mm"),
                                                           d.polygon([(50, 105), (128, 55), (206, 105)], fill=W_)))
tile("map", (60, 140, 230), (20, 60, 140), lambda d, S: (d.polygon([(60, 70), (110, 50), (150, 70), (196, 50), (196, 190), (150, 210), (110, 190), (60, 210)], outline=W_, width=8),
                                                        d.ellipse((140, 90, 176, 126), fill=(255, 80, 80, 255))))
tile("shop", (255, 150, 40), (200, 70, 20), lambda d, S: (d.rectangle((70, 100, 186, 200), fill=W_), d.arc((95, 60, 161, 140), 180, 360, fill=W_, width=10)))
tile("music", (200, 60, 220), (100, 20, 140), lambda d, S: (d.ellipse((60, 160, 110, 205), fill=W_), d.ellipse((140, 140, 190, 185), fill=W_),
                                                           d.line([(105, 180), (105, 70), (185, 55), (185, 160)], fill=W_, width=12)))
tile("email", (240, 70, 90), (150, 20, 50), lambda d, S: (d.rectangle((55, 80, 201, 180), outline=W_, width=10), d.line([(55, 80), (128, 140), (201, 80)], fill=W_, width=10)))
tile("photos", (255, 200, 60), (230, 110, 40), lambda d, S: [d.ellipse((128 - 30 + 45 * math.cos(a), 128 - 30 + 45 * math.sin(a), 128 + 30 + 45 * math.cos(a), 128 + 30 + 45 * math.sin(a)),
                                                                        fill=(255, 255, 255, 150)) for a in [k * math.pi / 3 for k in range(6)]])
tile("browser", (40, 200, 220), (20, 80, 160), lambda d, S: (d.ellipse((50, 50, 206, 206), outline=W_, width=10), d.ellipse((95, 50, 161, 206), outline=W_, width=8),
                                                            d.line([(50, 128), (206, 128)], fill=W_, width=8)))
tile("power", (90, 90, 100), (40, 40, 50), lambda d, S: (d.arc((60, 60, 196, 196), -60, 240, fill=W_, width=14), d.line([(128, 45), (128, 125)], fill=W_, width=14)))
# ---- MISTO 2 icon: original stylised mist swirl + "2" on a lavender -> mint gradient (no ghost, no yellow)
def misto(d, S):
    for k, (y, r) in enumerate(((100, 70), (140, 85), (176, 60))):
        d.arc((128 - r, y - 26, 128 + r, y + 26), 200 + 10 * k, 520 - 10 * k, fill=(255, 255, 255, 230), width=12)
    d.text((182, 74), "2", font=F(UI, 84), fill=(255, 255, 255, 255), anchor="mm")
tile("misto2", (150, 110, 255), (60, 220, 200), misto)
tile("online", (255, 90, 160), (90, 40, 200), lambda d, S: (d.ellipse((70, 70, 186, 186), outline=W_, width=10), d.ellipse((40, 110, 90, 160), fill=W_), d.ellipse((166, 110, 216, 160), fill=W_)))
# ---- browser buttons + trash
def btn(name, draw, S=96):
    t = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(t); draw(d, S); t.save(os.path.join(T, "ix_%s.png" % name))
btn("back", lambda d, S: d.polygon([(66, 18), (22, 48), (66, 78)], fill=W_))
btn("fwd", lambda d, S: d.polygon([(30, 18), (74, 48), (30, 78)], fill=W_))
btn("reload", lambda d, S: (d.arc((18, 18, 78, 78), 40, 330, fill=W_, width=10), d.polygon([(70, 10), (82, 40), (54, 36)], fill=W_)))
btn("trash", lambda d, S: (d.rectangle((24, 30, 72, 86), outline=W_, width=7), d.line([(16, 24), (80, 24)], fill=W_, width=8), d.rectangle((38, 12, 58, 22), fill=W_),
                           d.line([(40, 40), (40, 76)], fill=W_, width=5), d.line([(56, 40), (56, 76)], fill=W_, width=5)))
btn("flame", lambda d, S: (d.polygon([(48, 6), (78, 50), (70, 82), (48, 92), (26, 82), (18, 50), (34, 30), (40, 50)], fill=(255, 120, 30, 255)),
                           d.polygon([(48, 44), (62, 66), (56, 84), (40, 84), (34, 66)], fill=(255, 220, 80, 255))))
# ---- MISTO 2 lenses / frames: 1280x720 RGBA overlays (composited onto the snap)
LW, LH = 1280, 720
def lens(name, draw):
    t = Image.new("RGBA", (LW, LH), (0, 0, 0, 0)); d = ImageDraw.Draw(t); draw(t, d); t.save(os.path.join(T, "misto_%s.png" % name))
def sparkles(t, d):
    for _ in range(70):
        x, y, r = rng.randint(0, LW), rng.randint(0, LH), rng.randint(5, 18); c = rng.choice([(255, 255, 255), (255, 210, 255), (200, 240, 255), (255, 240, 160)])
        d.polygon([(x, y - r * 2), (x + r // 3, y - r // 3), (x + r * 2, y), (x + r // 3, y + r // 3), (x, y + r * 2), (x - r // 3, y + r // 3), (x - r * 2, y), (x - r // 3, y - r // 3)], fill=c + (230,))
def cat(t, d):        # selfie framing: head is around the upper centre
    for sx in (-1, 1):
        cx = 640 + sx * 95
        d.polygon([(cx - 60, 205), (cx + sx * 30, 65), (cx + 60, 205)], fill=(40, 30, 40, 255))
        d.polygon([(cx - 32, 195), (cx + sx * 22, 105), (cx + 32, 195)], fill=(255, 150, 190, 255))
    for sx in (-1, 1):
        for k in range(3): d.line([(640 + sx * 40, 330 + k * 12), (640 + sx * 150, 315 + k * 22)], fill=(255, 255, 255, 220), width=4)
    d.ellipse((628, 318, 652, 334), fill=(255, 120, 160, 255))
def shades(t, d):
    for sx in (-1, 1): d.rounded_rectangle((640 + sx * 72 - 62, 228, 640 + sx * 72 + 62, 290), 26, fill=(10, 10, 20, 235), outline=(255, 70, 160, 255), width=6)
    d.line([(630, 245), (650, 245)], fill=(255, 70, 160, 255), width=8)
    d.polygon([(560, 238), (590, 238), (585, 254)], fill=(255, 255, 255, 140)); d.polygon([(704, 238), (734, 238), (729, 254)], fill=(255, 255, 255, 140))
def frame_fs(t, d):
    d.rectangle((0, 0, LW, LH), outline=(255, 60, 160, 255), width=26); d.rectangle((26, 26, LW - 26, LH - 26), outline=(60, 230, 255, 255), width=8)
    d.rectangle((LW // 2 - 300, LH - 110, LW // 2 + 300, LH - 30), fill=(20, 8, 40, 220))
    d.text((LW // 2, LH - 70), "FIREOUT ONLINE", font=F(UI, 56), fill=(255, 80, 170, 255), anchor="mm")
def frame_tokyo(t, d):
    d.rectangle((0, 0, LW, 90), fill=(200, 20, 40, 220)); d.rectangle((0, LH - 90, LW, LH), fill=(200, 20, 40, 220))
    d.text((LW // 2, 45), "TOKYO  東京", font=F(JP, 54), fill=(255, 255, 255, 255), anchor="mm")
    d.text((LW // 2, LH - 45), "ネオン東京より愛をこめて  -  WITH LOVE FROM NEON TOKYO", font=F(JP, 30), fill=(255, 255, 255, 255), anchor="mm")
    d.ellipse((LW - 160, 110, LW - 40, 230), fill=(230, 20, 40, 255))
for nm, f in (("sparkle", sparkles), ("cat", cat), ("shades", shades), ("frame_fs", frame_fs), ("frame_tokyo", frame_tokyo)): lens(nm, f)
print("laptop / MISTO 2 art OK")
# ---- MISTO 2 canned reply snaps from contacts
def reply(name, draw):
    t = Image.new("RGB", (640, 360)); d = ImageDraw.Draw(t); draw(t, d); t.save(os.path.join(T, "misto_reply_%s.png" % name))
def r_ramen(t, d):
    d.rectangle((0, 0, 640, 360), fill=(90, 40, 20)); d.ellipse((170, 120, 470, 330), fill=(240, 240, 235)); d.ellipse((190, 130, 450, 290), fill=(200, 120, 40))
    for k in range(9): d.arc((220 + k * 18, 160, 300 + k * 18, 260), 0, 180, fill=(250, 220, 120), width=6)
    d.ellipse((330, 170, 390, 220), fill=(255, 255, 240)); d.ellipse((345, 182, 375, 208), fill=(255, 180, 40)); d.rectangle((250, 150, 300, 200), fill=(30, 50, 30))
    d.line([(420, 60), (330, 230)], fill=(200, 160, 100), width=8); d.line([(450, 70), (350, 235)], fill=(200, 160, 100), width=8)
def r_beach(t, d):
    for y in range(360): d.line([(0, y), (640, y)], fill=(int(255 - y * 0.2), int(150 + y * 0.1), int(120 + y * 0.3)))
    d.ellipse((260, 120, 380, 240), fill=(255, 220, 120)); d.rectangle((0, 230, 640, 300), fill=(40, 90, 170)); d.rectangle((0, 300, 640, 360), fill=(230, 200, 140))
def r_neon(t, d):
    d.rectangle((0, 0, 640, 360), fill=(15, 10, 35))
    for k in range(12):
        x = 30 + k * 52; h = 120 + (k * 37) % 160; d.rectangle((x, 360 - h, x + 44, 360), fill=(30, 20, 60))
        d.rectangle((x + 8, 360 - h + 20, x + 36, 360 - h + 60), fill=[(255, 60, 160), (60, 230, 255), (255, 210, 60)][k % 3])
def r_site(t, d):
    d.rectangle((0, 0, 640, 360), fill=(150, 190, 230)); d.rectangle((0, 260, 640, 360), fill=(200, 170, 120))
    for k in range(5): d.rectangle((120 + k * 70, 260 - 40 * k, 190 + k * 70, 260), fill=(160, 120, 90), outline=(90, 60, 40), width=3)
    d.ellipse((470, 200, 530, 230), fill=(255, 200, 0)); d.rectangle((480, 215, 520, 260), fill=(255, 120, 20))
for nm, f in (("ramen", r_ramen), ("beach", r_beach), ("neon", r_neon), ("site", r_site)): reply(nm, f)
print("MISTO replies OK")
