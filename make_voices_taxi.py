"""v1.0.4 JP TAXI driver lines in British English, pre-rendered OFFLINE at build time with Piper TTS and the
en_GB "northern_english_male" medium voice (dataset: OpenSLR 83, CC BY-SA 4.0). The game ships the WAVs - no runtime TTS.
Run: /workspace/piperenv/bin/python make_voices_taxi.py"""
import os, json, wave
from piper import PiperVoice
B = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(B, "assets", "voice")
MODEL = os.environ.get("PIPER_MODEL", "/workspace/piper_voices/en_GB-northern_english_male-medium.onnx")
LINES = {"hello": ["Hello! Where to today?", "Hiya! Where are we off to?"],
         "go": ["Right, off we go.", "Lovely, buckle up then."],
         "arrive": ["Here we are.", "Here we are, safe and sound."],
         "pay": ["Cheers, have a good one.", "Mind how you go."],
         "oops": ["Whoops! Anyway...", "Lovely day for it!", "As I was saying...", "Nearly there!", "Didn't see him there. Anyway!", "Never mind, we're fine!"]}
v = PiperVoice.load(MODEL)
idxp = os.path.join(OUT, "index.json"); idx = json.load(open(idxp, encoding="utf-8"))
for k, lines in LINES.items():
    idx["taxi_en_" + k] = []
    for i, t in enumerate(lines):
        fn = "taxi_en_%s_%d.wav" % (k, i)
        with wave.open(os.path.join(OUT, fn), "wb") as w: v.synthesize_wav(t, w) if hasattr(v, "synthesize_wav") else v.synthesize(t, w)
        idx["taxi_en_" + k].append({"file": fn, "district": "*", "text": t})
json.dump(idx, open(idxp, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("taxi en-GB voices ok")
