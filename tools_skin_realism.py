"""v1.0.4.1: give ANA's baked skin the realism MIYOYAZU's skin had - warmer, richer tone (same light colour family),
smoother, less speckled pores and a calmer fine normal map. Reads the original v1.0.4 textures from git so it is idempotent.
Usage: python3 tools_skin_realism.py"""
import io, subprocess, numpy as np
from PIL import Image, ImageFilter
GAIN = (1.031, 0.959, 0.893)          # luminance-preserving shift halfway toward MIYOYAZU's skin hue, 3% deeper
REF = "11ac252"                       # v1.0.4 release commit

def orig(path):
    return Image.open(io.BytesIO(subprocess.check_output(["git", "show", "%s:%s" % (REF, path)])))

def colour(path):
    im = orig(path); mode = im.mode; im = im.convert("RGBA")
    a = np.asarray(im).astype(np.float32); rgb = a[..., :3]
    soft = np.asarray(im.convert("RGB").filter(ImageFilter.GaussianBlur(1.2))).astype(np.float32); sharp = rgb * 0.45 + soft * 0.55   # calmer pores, like hers
    m = (rgb.sum(2) > 30)[..., None]
    out = np.where(m, sharp * np.array(GAIN, np.float32), rgb)
    a[..., :3] = np.clip(out, 0, 255)
    Image.fromarray(a.astype(np.uint8), "RGBA").convert(mode).save(path)

def normal(path, k=0.6):
    a = np.asarray(orig(path).convert("RGB").filter(ImageFilter.GaussianBlur(1.6))).astype(np.float32) / 127.5 - 1.0   # no sparkly speckle
    a[..., :2] *= k; a /= np.linalg.norm(a, axis=2, keepdims=True) + 1e-6
    Image.fromarray(np.clip((a + 1.0) * 127.5, 0, 255).astype(np.uint8)).save(path)

if __name__ == "__main__":
    for o in ("", "_crop", "_bikini", "_police"):
        colour("assets/tex/skin_c%s.png" % o); normal("assets/tex/skin_n%s.png" % o)
        for e in ("smile", "frown"):
            for r in ("mouth", "brow"):
                colour("assets/tex/face_heroine%s_%s_%s.png" % (o, e, r))
    print("ok")
