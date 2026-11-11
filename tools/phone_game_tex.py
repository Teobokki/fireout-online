import json, sys
src = open('/workspace/fireout-online/tools/phone_make.py').read(); src = src[:src.index('# ===== ANA')]
exec(src)
from PIL import ImageEnhance
OUTG = '/workspace/fireout-online/assets/tex/'
def wall_base(wall):
    img = wall.resize((SW, SH)).convert("RGBA")
    dark = Image.new("RGBA", (SW, SH), (6, 6, 14, 150)); img.alpha_composite(dark)      # dim so in-game app text stays readable
    status_bar(img, time=" ")
    ImageDraw.Draw(img).rounded_rectangle([SW/2-150, SH-50, SW/2+150, SH-38], 6, fill=(255, 255, 255, 220))
    return img
meta = {}
for who, frame, wall in (("ana", (40, 90, 220), wall_tokyo(SW, SH)), ("daniel", (120, 200, 60), wall_beach(SW, SH))):
    lay, (sx, sy, sw, sh, sr) = phone_front(wall_base(wall), frame, 1100)
    lay = lay.crop((40, 40, lay.width - 20, lay.height - 10))           # trim shadow padding a little
    sx -= 40; sy -= 40
    lay.save(OUTG + "phone_%s.png" % who)
    meta[who] = {"size": lay.size, "screen": [sx, sy, sw, sh]}
    if who == "ana":
        cr = crack_screen(Image.new("RGBA", (SW, SH), (0, 0, 0, 0)), (120, SH - 150)).resize((sw, sh), Image.LANCZOS)
        a = cr.getchannel("A").point(lambda v: int(v * 0.8)); cr.putalpha(a)
        full = Image.new("RGBA", lay.size, (0, 0, 0, 0)); m = rmask((sw, sh), sr)
        full.paste(cr, (sx, sy), ImageChops.multiply(m, a.resize((sw, sh)) if False else m))
        full.save(OUTG + "phone_ana_crack.png")
json.dump(meta, open(OUTG + "phone_meta.json", "w")); print(meta)
