"""v1.0.3: articulated-looking hands (palm + 4 fingers + thumb) for ANA / DANIEL, relaxed and gripping variants.
Built in world (sculpt) space at each wrist from the rig, replaces the mitten hand end of the forearm in game_char.py.
Run: python hands.py [ana|daniel]  -> cache[_daniel]/hands.npz (handR_V/F, handL_V/F, gripR_V/F, gripL_V/F)"""
import sys, numpy as np, time
sys.path.insert(0, '/workspace/fireout-shine-concept/src')
from sdflib import *
WHO = sys.argv[1] if len(sys.argv) > 1 else 'ana'
if WHO == 'daniel':
    import daniel; import character as C; SC = 1.09; OUT = '/workspace/fireout-shine-concept/cache_daniel/hands.npz'
else:
    import character as C; SC = 1.0; OUT = '/workspace/fireout-shine-concept/cache/hands.npz'
S = C.S
def nrm(v): return v / np.linalg.norm(v)
def frame(side):
    sx = -1 if side == 'R' else 1
    w0 = S['wri' + side].astype(np.float64); d = nrm(S['hnd' + side] - w0)                # u: down the hand
    inw = np.array([-sx, 0, 0], float); inw = nrm(inw - d * (inw @ d))                 # w: toward the body (palm side)
    fwd = np.cross(inw, d) * (-sx); fwd = nrm(fwd - d * (fwd @ d)); fwd = fwd if fwd[1] < 0 else -fwd   # v: forward (-Y)
    return w0, d, fwd, inw
def rot(a, axis, ang):
    axis = nrm(axis); c, s = np.cos(ang), np.sin(ang)
    return a * c + np.cross(axis, a) * s + axis * (axis @ a) * (1 - c)
# finger table: (v offset, length, radius, fan deg)  index -> pinky (index at the front)
FING = [(0.0272, 0.071, 0.0078, 8.0), (0.0091, 0.078, 0.0081, 2.5), (-0.0091, 0.073, 0.0076, -3.5), (-0.0268, 0.058, 0.0068, -9.5)]
def hand_sdf(side, curl):
    W0, U, Vf, Wn = frame(side)
    k = SC
    def L(u, v, w): return (W0 + (U * u + Vf * v + Wn * w) * k).astype(f32)
    def sdf(p):
        d = capsule(p, L(-0.026, 0, 0), L(0.016, 0, 0.0), 0.0224 * k)                          # wrist cuff (covers the forearm cut)
        palm = ellipsoid(p, L(0.052, 0.0, 0.002), (0.0, 0.0, 0.0)) if False else None
        # palm: rounded slab spanning the knuckles
        pts = [L(0.030, v, 0.002) for v in (-0.020, 0.0, 0.020)] + [L(0.078, v, 0.000) for v in (-0.024, -0.008, 0.008, 0.024)]
        pl = None
        for a in pts[:3]:
            for b in pts[3:]:
                c_ = capsule(p, a, b, 0.0125 * k); pl = c_ if pl is None else np.minimum(pl, c_)
        d = smin(d, pl, 0.012 * k)
        d = smin(d, ellipsoid(p, L(0.040, 0.020, 0.010), (0.024 * k, 0.020 * k, 0.014 * k)), 0.010 * k)   # thenar (thumb pad)
        fing = None
        for (v, ln, r, fan) in FING:
            seg = [0.46, 0.30, 0.24]; ang = [curl[0], curl[1], curl[2]]
            pos = np.array([0.084, v, 0.0]); dirv = np.array([1.0, np.tan(np.radians(fan)), 0.0]); dirv = nrm(dirv)
            rr = r
            for sl, a in zip(seg, ang):
                dirv = rot(dirv, np.array([0.0, 1.0, 0.0]) * -1, np.radians(a))   # curl toward the palm (+w)
                nxt = pos + dirv * ln * sl
                c_ = round_cone(p, L(*pos), L(*nxt), rr * k, rr * 0.88 * k)
                fing = c_ if fing is None else np.minimum(fing, c_)
                pos = nxt; rr *= 0.88
        d = smin(d, fing, 0.0035 * k)          # tiny blend only at the knuckles: fingers stay separate
        # thumb: from the thenar, down + forward + across toward the palm
        pos = np.array([0.028, 0.030, 0.011]); dirv = nrm(np.array([0.80 - 0.35 * curl[3], 0.34 - 0.18 * curl[3], 0.28 + 0.6 * curl[3]]))
        rr = 0.0098
        th = None
        for sl, a in ((0.034, 0.0), (0.030, 12 + 25 * curl[3])):
            dirv = rot(dirv, np.array([0.0, 1.0, 0.0]) * -1, np.radians(a))
            nxt = pos + dirv * sl
            c_ = round_cone(p, L(*pos), L(*nxt), rr * k, rr * 0.86 * k); th = c_ if th is None else np.minimum(th, c_)
            pos = nxt; rr *= 0.86
        d = smin(d, th, 0.006 * k)
        return d
    return sdf, W0
out = {}; t0 = time.time()
for name, curl in (('hand', (10, 20, 16, 0.0)), ('grip', (70, 80, 45, 1.0))):
    for sd in ('R', 'L'):
        f, W0 = hand_sdf(sd, curl)
        V_, F_ = mesh_sdf(f, W0 - 0.15, W0 + 0.15, 0.0009, verbose=False)
        out[name + sd + '_V'] = V_; out[name + sd + '_F'] = F_; print(name + sd, len(V_), round(time.time() - t0, 1), flush=True)
np.savez(OUT, **out); print('HANDS OK', OUT)
