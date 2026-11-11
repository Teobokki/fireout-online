"""ANA wardrobe sculpts: BIKINI (coral bandeau two-piece, bare legs + feet, flip-flops) and POLICE (original fictional
TOKYO NEON PD uniform: short-sleeve navy shirt, cap, gold badge, boots). Writes cache/char_bikini.npz, cache/char_police.npz"""
import numpy as np, sys, time
sys.path.insert(0, '/workspace/fireout-shine-concept/src')
from sdflib import *
import head as H
import character as C
S = C.S; t0 = time.time()
def mesh(out, name, f, bmin, bmax, h, keep=None):
    V_, F_ = mesh_sdf(f, bmin, bmax, h)
    if keep is not None: V_, F_, _ = keep_faces(V_, F_, keep)
    out[name + '_V'] = V_; out[name + '_F'] = F_; print(name, len(V_), round(time.time() - t0, 1), flush=True)
def foot(p, side):
    a, R = C.shoe_frame(side); q = (p - V(a[0], a[1], 0)) @ R
    d = ellipsoid(q, (0, 0.030, 0.045), (0.030, 0.040, 0.040))
    d = smin(d, ellipsoid(q, (0, -0.055, 0.030), (0.036, 0.080, 0.026)), 0.025)
    d = smin(d, ellipsoid(q, (0, -0.135, 0.018), (0.034, 0.040, 0.016)), 0.02)
    return smax(d, 0.004 - q[:, 2], 0.003)
def legs_skin(p):
    d = C.body_noarms(p)      # arms hang free at the sides now; they live in the 'body' mesh
    for sd in ('R', 'L'): d = smin(d, foot(p, sd), 0.02)
    return d
def flipflop(p, side):
    a, R = C.shoe_frame(side); q = (p - V(a[0], a[1], 0)) @ R
    q2 = q.copy(); q2[:, 2] = 0.03
    fp = foot(q2 @ R.T + V(a[0], a[1], 0), side) - 0.006
    d = smax(fp, np.abs(q[:, 2] - 0.002) - 0.0055, 0.002)
    for sx in (-1, 1):
        d = np.minimum(d, capsule(q, V(0, -0.122, 0.010), V(sx * 0.033, -0.060, 0.034), 0.0035))
    return d
def bikini_top(p): return C.torso(p, top=False) - 0.0026     # follows each cup (natural cleavage), no bridging
def bikini_top_keep(c):
    x, y, z = np.abs(c[:, 0]), c[:, 1], c[:, 2]
    front = (y < 0.0) & (z > 1.138) & (z < 1.292 - 0.10 * np.maximum(x - 0.10, 0) - 0.050 * np.exp(-(x / 0.026) ** 2))
    back = (y >= 0.0) & (z > 1.192) & (z < 1.232)
    return front | back
def bikini_bot(p): return C.body_noarms(p) - 0.0026     # v1.0.3: arms are free, keep them out of the swimsuit
def bikini_bot_keep(c):
    x, z = np.abs(c[:, 0]), c[:, 2]
    return (z < 0.962) & (z > 0.812 + 0.62 * np.maximum(x - 0.034, 0))
def shirt(p):
    d = C.torso(p, top=True) - 0.0048
    for sd in ('R', 'L'):
        s, e = S['sho' + sd], S['elb' + sd]
        d = smin(d, round_cone(p, s + V(0, 0, 0.01), C.lerp(s, e, 0.5), 0.054, 0.047), 0.03)
    return d
def shirt_keep(c):
    x, y, z = np.abs(c[:, 0]), c[:, 1], c[:, 2]
    collar = (x / 0.062) ** 2 + ((y - 0.010) / 0.058) ** 2 < 1.0
    keep = (z > 0.95) & ~(collar & (z > 1.36))
    for sd in ('R', 'L'):
        s, e = S['sho' + sd], S['elb' + sd]; ax = (e - s); t = ((c - s) @ ax) / (ax @ ax)
        keep &= ~((t > 0.48) & (np.sign(c[:, 0]) == np.sign(s[0])) & (np.abs(c[:, 0]) > 0.15))
    return keep
def cap_local(q):
    d = ellipsoid(q, (0, 0.030, 0.062), (0.112, 0.124, 0.080))
    d = smax(d, 0.040 - q[:, 2], 0.004)
    d = smax(d, -ellipsoid(q, (0, 0.030, 0.050), (0.104, 0.116, 0.070)), 0.002)   # hollow shell
    brim = ellipsoid(q, (0, -0.090, 0.046), (0.080, 0.058, 0.0055))
    brim = smax(brim, q[:, 1] + 0.055, 0.004)
    return np.minimum(d, brim)
def cap(p): return cap_local(C.to_head(p).astype(f32))
def boot(p, side):
    a = S['ank' + side]
    d = C.shoe_upper(p, side) - 0.002
    d = smin(d, round_cone(p, V(a[0], a[1] + 0.012, 0.05), V(a[0], a[1] + 0.008, 0.25), 0.050, 0.047), 0.03)
    return smax(d, p[:, 2] - 0.255, 0.004)
