"""Japanese NPC lines, generated OFFLINE at build time with Open JTalk (pyopenjtalk) + HTS voice "Mei"
(Nagoya Institute of Technology / MMDAgent, CC BY 3.0). Output: assets/voice/ja_<n>.wav + entries in index.json"""
import os, sys, json, wave, numpy as np, pyopenjtalk
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fs_lines import LINES_JA, LINES_JA2, NPC_JA
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "voice")
idxp = os.path.join(OUT, "index.json"); idx = json.load(open(idxp, encoding="utf-8")) if os.path.exists(idxp) else {}
idx["ja"] = []
VAR = [(1.0, 0.0), (1.05, 2.0), (0.95, -1.5), (1.0, 3.5)]
def say(jp, fn, sp, ht):
    x, sr = pyopenjtalk.tts(jp, speed=sp, half_tone=ht)
    n = int(len(x) * 16000 / sr); y = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x)
    y = y / max(1, np.abs(y).max()) * 26000
    with wave.open(os.path.join(OUT, fn), "wb") as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(y.astype(np.int16).tobytes())
for i, (dist, jp, en) in enumerate(LINES_JA + LINES_JA2):
    sp, ht = VAR[i % len(VAR)]; fn = "ja_%02d.wav" % i; say(jp, fn, sp, ht)
    idx["ja"].append({"file": fn, "district": dist, "text": jp, "en": en})
# v1.0.4 grouped NPC speech (police, taxi driver, shop staff, ramen staff, rivals...) - Japanese with English subtitles
DEEP = {"police": -5.0, "busted": -5.0, "taxi_board": -6.0, "taxi_go": -6.0, "taxi_arrive": -6.0, "op119": 1.0, "rival": -2.0}
for g, items in NPC_JA.items():
    idx["ja_" + g] = []
    for i, (jp, en) in enumerate(items):
        fn = "jg_%s_%d.wav" % (g, i); say(jp, fn, 1.05 if g in ("police", "scared", "jacked") else 1.0, DEEP.get(g, VAR[i % len(VAR)][1]))
        idx["ja_" + g].append({"file": fn, "district": "*", "text": jp, "en": en})
json.dump(idx, open(idxp, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("ja voices ok", len(idx["ja"]))
