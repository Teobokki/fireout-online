"""Original procedural SFX: horn, door, switch, dial/ring (EX IX G9 phone)."""
import numpy as np, wave, os
SR = 44100
def save(name, x):
    x = np.clip(x, -1, 1); d = (x * 32000).astype(np.int16)
    with wave.open(os.path.join("assets", "sfx", name + ".wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(d.tobytes())
def env(n, a=0.01, r=0.1):
    e = np.ones(n); na = int(a * SR); nr = int(r * SR)
    e[:na] = np.linspace(0, 1, na); e[-nr:] *= np.linspace(1, 0, nr); return e
t = np.arange(int(0.55 * SR)) / SR
horn = sum(np.sign(np.sin(2 * np.pi * f * t)) * 0.25 for f in (392, 494)) 
horn = np.convolve(horn, np.ones(12) / 12, "same") * env(len(t), 0.01, 0.06) * 0.8
save("horn", horn)
t = np.arange(int(0.35 * SR)) / SR; rng = np.random.default_rng(3)
thud = np.sin(2 * np.pi * 70 * t) * np.exp(-t * 22) + rng.normal(0, 1, len(t)) * np.exp(-t * 60) * 0.35
clk = np.zeros_like(t); i = int(0.02 * SR); clk[i:i + 300] = rng.normal(0, 1, 300) * np.exp(-np.arange(300) / 60)
save("door", (thud + clk * 0.6) * 0.8)
t = np.arange(int(0.45 * SR)) / SR
f = 300 + 900 * t / 0.45
sw = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(len(t), 0.02, 0.15) * 0.5 + np.sin(2 * np.pi * 1320 * t) * np.exp(-((t - 0.38) * 30) ** 2) * 0.4
save("switch", sw)
# dial: original two-tone ring pattern x2
seg = []
for k in range(2):
    tt = np.arange(int(0.9 * SR)) / SR
    tone = (np.sin(2 * np.pi * 523 * tt) + np.sin(2 * np.pi * 659 * tt) * 0.8) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 12 * tt)))
    tone *= env(len(tt), 0.01, 0.05) * 0.35
    seg += [tone, np.zeros(int(0.4 * SR))]
save("dial", np.concatenate(seg))
print("sfx ok")
# weapons (original procedural): pistol, smg, shotgun, taser, swing, heavy swing, hit, empty click
def shot(name, dur, f0, decay, noise_amt, body):
    t = np.arange(int(dur * SR)) / SR; rng = np.random.default_rng(len(name))
    x = rng.normal(0, 1, len(t)) * np.exp(-t * decay) * noise_amt + np.sin(2 * np.pi * f0 * t * (1 - t * 2)) * np.exp(-t * body) * 0.8
    x = np.convolve(x, np.ones(6) / 6, "same"); save(name, x / max(1e-6, np.abs(x).max()) * 0.9)
shot("pistol", 0.35, 140, 28, 1.0, 22); shot("smg", 0.16, 180, 45, 1.0, 40); shot("shotgun", 0.6, 90, 12, 1.2, 9)
t = np.arange(int(0.5 * SR)) / SR
save("taser", (np.sign(np.sin(2 * np.pi * 60 * t)) * 0.3 + np.random.default_rng(1).normal(0, 0.4, len(t)) * (np.sin(2 * np.pi * 120 * t) > 0)) * env(len(t), 0.01, 0.1) * 0.7)
for nm, d, f in (("swing", 0.25, 1.0), ("swing_heavy", 0.4, 0.6)):
    t = np.arange(int(d * SR)) / SR; n = np.random.default_rng(5).normal(0, 1, len(t))
    w = np.convolve(n, np.ones(int(30 / f)) / int(30 / f), "same") * np.sin(np.pi * t / d) ** 2
    save(nm, w / np.abs(w).max() * 0.6)
t = np.arange(int(0.2 * SR)) / SR
save("hit", (np.sin(2 * np.pi * 90 * t) * np.exp(-t * 30) + np.random.default_rng(2).normal(0, 1, len(t)) * np.exp(-t * 50) * 0.5) * 0.8)
t = np.arange(int(0.08 * SR)) / SR
save("empty", np.random.default_rng(3).normal(0, 1, len(t)) * np.exp(-t * 120) * 0.5)
print("weapon sfx ok")
