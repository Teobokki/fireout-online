"""v1.0.4: build assets/jp_font.otf - Noto Sans CJK JP Bold (SIL Open Font License 1.1) subset to FULL JIS X 0208
(all kana + 6,355 level-1/2 kanji, i.e. every common Japanese character) plus every character used anywhere in the
game's text, so no dialogue line or sign can ever show a missing glyph. Run with a Python that has fontTools."""
import os, re, glob
from fontTools import subset
from fontTools.ttLib import TTCollection
CJK = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
chars = set()
for hi in range(0xA1, 0xFF):                 # every JIS X 0208 code point via EUC-JP
    for lo in range(0xA1, 0xFF):
        try: chars.add(bytes([hi, lo]).decode("euc_jp"))
        except UnicodeDecodeError: pass
chars |= set(chr(c) for c in range(0x20, 0x7F)) | set("・ー－〜！？。、「」『』（）【】…‥￥¥▲▼◀▶●★☆♪→←↑↓○×％＆＋：；")
for fn in glob.glob("*.py"):                 # plus everything the game's code / dialogue / data actually contains
    chars |= set(c for c in open(fn, encoding="utf-8").read() if ord(c) > 0x7F)
import json
for fn in glob.glob("assets/voice/*.json"): chars |= set(c for c in open(fn, encoding="utf-8").read() if ord(c) > 0x7F)
f = TTCollection(CJK).fonts[0]
opt = subset.Options(); opt.layout_features = ["*"]; opt.name_IDs = ["*"]; opt.notdef_outline = True; opt.name_legacy = True
sb = subset.Subsetter(opt); sb.populate(text="".join(sorted(chars))); sb.subset(f)
f.flavor = None; f.save("assets/jp_font.otf")
print("jp_font.otf:", len(f.getBestCmap()), "glyphs mapped,", os.path.getsize("assets/jp_font.otf") // 1024, "KB")
