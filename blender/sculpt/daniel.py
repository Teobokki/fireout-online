"""DANIEL - original male co-protagonist (floral T-shirt, jeans, sneakers). Re-uses the SDF sculpt pipeline with a
male anatomy pass and a short textured crop. Writes cache_daniel/char.npz, hair.npz, rig.json"""
import numpy as np, json, sys, time, os
sys.path.insert(0, '/workspace/fireout-shine-concept/src')
from sdflib import *
import head as H
import character as C
OUT = '/workspace/fireout-shine-concept/cache_daniel/'; os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(77)
# ---- skeleton: broader shoulders, slightly longer arms, narrower hips
S = C.S
for sd, sx in (('R', -1), ('L', 1)):
    S['sho' + sd] = V(sx * 0.200, 0.010, 1.372); S['elb' + sd] = V(sx * 0.228, 0.032, 1.088)   # v1.0.3: arms hang at the sides
    S['wri' + sd] = V(sx * 0.245, -0.005, 0.852); S['hnd' + sd] = V(sx * 0.250, -0.018, 0.765)
S['hipR'] = V(-0.090, 0.0, 0.890); S['hipL'] = V(0.090, 0.0, 0.884)
C.NECK_TOP = V(0.0, 0.026, 1.50); C.NECK_BOT = V(0.0, 0.010, 1.36)
def torso_m(p, top=False):
    k = 1.0 if not top else 1.5
    d = ellipsoid(p, (0, 0.012, 1.235), (0.134, 0.088, 0.168))
    d = smin(d, ellipsoid(p, (0, 0.008, 1.322), (0.168, 0.080, 0.080)), 0.03 * k)
    pec = smin(ellipsoid(p, (-0.062, -0.048, 1.272), (0.066, 0.034, 0.050)), ellipsoid(p, (0.062, -0.048, 1.272), (0.066, 0.034, 0.050)), 0.03)
    d = smin(d, pec, 0.03)
    d = smin(d, ellipsoid(p, (0, 0.014, 1.078), (0.110, 0.074, 0.115)), 0.05 * k)
    d = smin(d, ellipsoid(p, (0, -0.006, 0.998), (0.106, 0.070, 0.085)), 0.04 * k)
    d = smin(d, ellipsoid(p, (0, 0.012, 0.922), (0.128, 0.086, 0.100)), 0.05 * k)
    for sx in (-1, 1):
        d = smin(d, ellipsoid(p, (sx * 0.052, 0.046, 0.885), (0.058, 0.050, 0.074)), 0.03)
        d = smin(d, ellipsoid(p, (sx * 0.090, 0.082, 1.290), (0.060, 0.024, 0.070)), 0.03)
        d = smin(d, round_cone(p, (sx * 0.045, 0.030, 1.440), (sx * 0.175, 0.020, 1.395), 0.036, 0.028), 0.03)
        d = smin(d, capsule(p, (sx * 0.024, -0.052, 1.380), (sx * 0.170, -0.012, 1.400), 0.009), 0.014)
        if top:
            sh = S['sho' + ('R' if sx < 0 else 'L')]
            d = smin(d, ellipsoid(p, sh + V(-sx * 0.012, -0.002, -0.015), (0.050, 0.054, 0.056)), 0.02)
    return d
def arm_m(p, side):
    s, e, w, h = S['sho' + side], S['elb' + side], S['wri' + side], S['hnd' + side]
    sx = -1 if side == 'R' else 1
    d = round_cone(p, s, e, 0.043, 0.031)
    d = smin(d, ellipsoid(p, s + V(sx * 0.008, -0.002, -0.028), (0.046, 0.048, 0.060)), 0.02)
    fw = V(0, -0.009, 0)
    d = smin(d, round_cone(p, C.lerp(s, e, 0.25) + fw, C.lerp(s, e, 0.78) + fw, 0.034, 0.027), 0.02)
    d = smin(d, round_cone(p, C.lerp(s, e, 0.20) - fw * 1.6, C.lerp(s, e, 0.72) - fw * 1.2, 0.034, 0.026), 0.02)
    d = smin(d, round_cone(p, e, w, 0.032, 0.022), 0.012)
    d = smin(d, round_cone(p, C.lerp(e, w, 0.08) + V(sx * 0.006, -0.004, 0), C.lerp(e, w, 0.55), 0.035, 0.025), 0.02)
    d = smin(d, round_cone(p, w, h, 0.025, 0.022), 0.01)
    d = smin(d, ellipsoid(p, C.lerp(w, h, 0.55) + V(-sx * 0.004, -0.004, 0), (0.015, 0.032, 0.044)), 0.012)   # palm / fingers
    return d
def neck_core_m(p):
    q = p.copy(); q[:, 0] = q[:, 0] / 0.88
    return round_cone(q, C.NECK_BOT, C.NECK_TOP, 0.053, 0.048) * 0.88
_head = H.head_local
def head_m(q0, with_neck=False):
    d = _head(q0, with_neck)
    qm = q0.copy(); qm[:, 0] = np.abs(qm[:, 0])
    # slimmer lower face: carve cheek/jowl volume, then a lean defined jawline and a narrow chin with a slight point
    d = ssub(d, ellipsoid(qm, (0.074, -0.022, -0.070), (0.024, 0.034, 0.034)), 0.012)
    d = ssub(d, ellipsoid(qm, (0.078, -0.012, -0.035), (0.016, 0.030, 0.026)), 0.012)                      # less cheek volume                      # jowl/lower-cheek slimming
    d = smin(d, round_cone(qm, (0.050, 0.058, -0.080), (0.011, -0.024, -0.113), 0.0085, 0.0060), 0.008)   # sharp jaw line
    d = smin(d, ellipsoid(q0, (0, -0.030, -0.110), (0.0125, 0.0095, 0.0115)), 0.006)                       # narrow chin point
    d = ssub(d, ellipsoid(q0, (0, 0.006, -0.140), (0.048, 0.036, 0.022)), 0.010)                           # under-jaw: neck/jaw separation
    d = smin(d, ellipsoid(qm, (0.027, -0.011, 0.023), (0.026, 0.010, 0.0085)), 0.011)                     # brow ridge
    return d
_tr = C.trousers_sdf
def trousers_slim(p):
    q = p.copy(); q[:, 0] = q[:, 0] / 0.93; q[:, 1] = q[:, 1] / 0.95
    return _tr(q) * 0.93
C.trousers_sdf = trousers_slim
C.torso = torso_m; C.arm = arm_m; C.neck_core = neck_core_m; H.head_local = head_m
# ---- clothes
def tshirt_sdf(p):
    d = torso_m(p, top=True) - 0.0055
    for sd in ('R', 'L'):
        s, e = S['sho' + sd], S['elb' + sd]
        d = smin(d, round_cone(p, s + V(0, 0, 0.01), C.lerp(s, e, 0.52), 0.060, 0.052), 0.03)
    wav = np.sin(p[:, 2] * 160 + 3 * vnoise(p * 30)) * np.exp(-((p[:, 2] - 1.02) / 0.07) ** 2)
    return d - 0.0012 * wav - 0.002 * fbm(p * 12, 2)
def tshirt_keep(c):
    x, y, z = np.abs(c[:, 0]), c[:, 1], c[:, 2]
    crew = (x / 0.072) ** 2 + ((y - 0.012) / 0.066) ** 2 < 1.0
    neck = crew & (z > 1.40)
    keep = (z > 0.935) & ~neck
    for sd in ('R', 'L'):
        s, e = S['sho' + sd], S['elb' + sd]; ax = (e - s); t = ((c - s) @ ax) / (ax @ ax)
        keep &= ~((t > 0.50) & (np.sign(c[:, 0]) == np.sign(s[0])) & (np.abs(c[:, 0]) > 0.16))
    return keep
def main():
    t0 = time.time(); out = {}
    def do(name, f, bmin, bmax, h, keep=None):
        Vv, Ff = mesh_sdf(f, bmin, bmax, h)
        if keep is not None: Vv, Ff, _ = keep_faces(Vv, Ff, keep)
        out[name + '_V'] = Vv; out[name + '_F'] = Ff; print(name, len(Vv), round(time.time() - t0, 1), flush=True); return Vv
    Vh = do('head', C.skin, (-0.14, -0.15, C.SEAM_Z), (0.14, 0.20, 1.72), 0.0009)
    m = H.head_masks(C.to_head(Vh)); m['eyelid'] *= 0; m['lips'] *= 0.35; m['blush'] *= 0.5
    for k, v in m.items(): out['head_m_' + k] = v.astype(f32)
    do('body', C.skin, (-0.33, -0.16, 0.70), (0.33, 0.17, C.SEAM_Z), 0.002)
    do('tank', tshirt_sdf, (-0.29, -0.16, 0.92), (0.29, 0.16, 1.49), 0.0022, tshirt_keep)
    do('trousers', C.trousers_sdf, (-0.25, -0.18, 0.0), (0.27, 0.18, 1.04), 0.0025, C.trousers_keep)
    ys = np.linspace(-0.2, 0, 400).astype(f32); P = np.stack([np.zeros_like(ys), ys, np.full_like(ys, 0.99)], 1)
    C.BUCKLE_Y = float(ys[np.argmax(C.trousers_sdf(P) < 0)]) - 0.004
    do('belt', C.belt_sdf, (-0.22, -0.16, 0.965), (0.22, 0.16, 1.015), 0.0014)
    do('buckle', C.buckle_sdf, (-0.035, C.BUCKLE_Y - 0.02, 0.965), (0.035, C.BUCKLE_Y + 0.02, 1.015), 0.0008)
    for sd in ('R', 'L'):
        a = S['ank' + sd]
        do('shoeU' + sd, lambda p, s=sd: C.shoe_upper(p, s), (a[0] - 0.13, a[1] - 0.25, 0.0), (a[0] + 0.13, a[1] + 0.13, 0.15), 0.0018)
        do('shoeS' + sd, lambda p, s=sd: C.shoe_sole(p, s), (a[0] - 0.13, a[1] - 0.25, -0.002), (a[0] + 0.13, a[1] + 0.13, 0.03), 0.0015)
    rig = {'HEAD_O': C.HEAD_O.tolist(), 'HEAD_R': C.HEAD_R.tolist(), 'EYE_X': H.EYE_X * 1.04, 'EYE_R': H.EYE_R, 'EYE_Y': H.EYE_Y,
           'S': {k: v.tolist() for k, v in S.items()}, 'BUCKLE_Y': C.BUCKLE_Y, 'SEAM_Z': C.SEAM_Z}
    json.dump(rig, open(OUT + 'rig.json', 'w'), indent=1); np.savez(OUT + 'char.npz', **out)
    # ---- short textured crop + brows + lashes (copied from Ana's groom, pushed onto this head)
    fh = H.head_local
    C0 = V(0, 0.045, 0.015)
    dirs = rng.normal(size=(60000, 3)).astype(f32); dirs /= np.linalg.norm(dirs, axis=1, keepdims=True); dirs = dirs[dirs[:, 2] > -0.6]
    lo = np.zeros(len(dirs), f32); hi = np.full(len(dirs), 0.2, f32)
    for _ in range(26):
        mid = (lo + hi) / 2; ins = fh((C0 + dirs * mid[:, None]).astype(f32)) < 0; lo = np.where(ins, mid, lo); hi = np.where(ins, hi, mid)
    R = (C0 + dirs * hi[:, None]).astype(f32)
    x, y, z = np.abs(R[:, 0]), R[:, 1], R[:, 2]
    ok = (z > 0.074 - 0.030 * (x / 0.062) ** 2 - np.maximum(y, 0) * 0.7) | (y > 0.035)
    ok &= ~(np.sqrt((x - 0.070) ** 2 + (y - 0.080) ** 2 / 0.8 + (z + 0.012) ** 2 / 1.6) < 0.030) & (z > -0.045) & ~((y < 0.045) & (z < 0.04))
    # v1.0.3: modern short cut - no long ends: higher sideburns / tapered nape (was: long locks down past the ears and over the neck)
    ok &= z > np.where(y < 0.10, 0.012, -0.028)
    R = R[ok][:26000]
    n = grad(fh, R, 3e-4)
    up = V(0, 0, 1); fwd = V(0, -1, 0)
    dirv = (fwd * 0.6 + up * 0.5)[None] + rng.normal(0, 0.25, (len(R), 3)).astype(f32)
    dirv -= n * (dirv * n).sum(1, keepdims=True); dirv /= np.linalg.norm(dirv, axis=1, keepdims=True)
    L = rng.uniform(0.022, 0.042, len(R)).astype(f32) * (1 - 0.45 * (R[:, 2] < 0.03))
    L *= np.clip((R[:, 2] + 0.035) / 0.11, 0.30, 1.0).astype(f32)      # sides/back clipped short, length kept on top
    lay = rng.uniform(0.001, 0.010, len(R)).astype(f32) * (0.5 + 0.5 * (R[:, 2] > 0.06))
    NP = 7; St = np.zeros((len(R), NP, 3), f32)
    for j in range(NP):
        t = j / (NP - 1)
        St[:, j] = R + n * (lay * np.sin(np.pi * min(t * 1.4, 1) / 2))[:, None] + dirv * (L * t)[:, None] + n * (0.004 * t * t)
    Pw = C.from_head(St.reshape(-1, 3)).astype(f32)
    Ha = np.load('/workspace/fireout-shine-concept/cache/hair.npz')
    def push(P_):
        q = C.to_head(P_).astype(f32)
        for _ in range(3):
            d = fh(q); bad = d < 0.0006
            if bad.any(): q[bad] -= grad(fh, q[bad]) * (d[bad] - 0.0006)[:, None]
        return C.from_head(q).astype(f32)
    hair = {'scalp_P': Pw, 'scalp_N': np.full(len(R), NP, np.int32), 'brow_P': push(Ha['brow_P']), 'brow_N': Ha['brow_N'],
            'lash_P': Ha['lash_P'], 'lash_N': Ha['lash_N']}
    np.savez(OUT + 'hair.npz', **hair); print('daniel total', round(time.time() - t0, 1))
if __name__ == '__main__':
    main()
