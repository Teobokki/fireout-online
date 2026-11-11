"""Pre-generates NPC voice clips OFFLINE at build time with Piper TTS (run on the build box only).
Voices: en_US-kristin-medium (LibriVox, public domain), en_US-joe-medium (CC0), en_US-libritts_r-medium (LibriTTS-R, CC BY 4.0).
Output: assets/voice/<key>_<n>.wav + assets/voice/index.json"""
import os, sys, json, wave, subprocess, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fs_lines import LINES, SCARED, JACKED
VD = "/workspace/tts_voices"; OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "voice")
os.makedirs(OUT, exist_ok=True)
PIPER = "/workspace/.venv-tts/bin/piper"
def synth(text, model, path, spk=None, scale=1.0):
    cmd = [PIPER, "-m", os.path.join(VD, model + ".onnx"), "-f", path, "--length-scale", str(scale)]
    if spk is not None: cmd += ["--speaker", str(spk)]
    subprocess.run(cmd, input=text.encode(), check=True, capture_output=True)
def f0(path):
    with wave.open(path) as w: sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float)
    fr = []
    for i in range(0, len(x) - 2048, 1024):
        s = x[i:i + 2048]
        if np.abs(s).mean() < 600: continue
        ac = np.correlate(s, s, "full")[2047:]; lo, hi = sr // 400, sr // 70
        k = lo + np.argmax(ac[lo:hi]); fr.append(sr / k)
    return float(np.median(fr)) if fr else 0
def to16k(path):
    with wave.open(path) as w: sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(float)
    n = int(len(x) * 16000 / sr); y = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x)
    y = y / max(1, np.abs(y).max()) * 26000
    with wave.open(path, "wb") as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(y.astype(np.int16).tobytes())
# pick feminine-sounding LibriTTS-R speakers (NPC bodies share the heroine base mesh)
voices = [("en_US-kristin-medium", None, 1.0)]
if "--scan" in sys.argv or not os.path.exists(os.path.join(OUT, "speakers.json")):
    fem = []
    for spk in range(0, 120, 3):
        p = "/tmp/spk.wav"; synth("Hello there, what a lovely evening in the city.", "en_US-libritts_r-medium", p, spk)
        f = f0(p)
        if f > 185: fem.append((spk, f))
        if len(fem) >= 4: break
    json.dump(fem, open(os.path.join(OUT, "speakers.json"), "w"))
fem = json.load(open(os.path.join(OUT, "speakers.json")))
voices += [("en_US-libritts_r-medium", s, 1.0) for s, _ in fem]
idx = {"ambient": [], "scared": [], "jacked": []}
for group, items in (("ambient", LINES), ("scared", [("*", t) for t in SCARED]), ("jacked", [("*", t) for t in JACKED])):
    for i, (dist, text) in enumerate(items):
        m, spk, sc = voices[i % len(voices)]
        fn = "%s_%02d.wav" % (group, i); p = os.path.join(OUT, fn)
        synth(text, m, p, spk, sc); to16k(p)
        idx[group].append({"file": fn, "district": dist, "text": text, "voice": i % len(voices)})
from fs_game_banter import BANTER
idx["banter"] = []
for i, (who, text) in enumerate(BANTER):
    fn = "banter_%02d.wav" % i; p = os.path.join(OUT, fn)
    synth(text, "en_US-kristin-medium" if who == "ana" else "en_US-joe-medium", p, None, 1.0); to16k(p)
    idx["banter"].append({"file": fn, "who": who, "text": text})
json.dump(idx, open(os.path.join(OUT, "index.json"), "w"), indent=1, ensure_ascii=False)
print("voices ok", len(idx["ambient"]), "speakers", fem)
