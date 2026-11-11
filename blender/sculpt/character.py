import numpy as np, json, sys, time
sys.path.insert(0, '/workspace/fireout-shine-concept/src')
from sdflib import *
import head as H

# ---------------- pose / rig (world, character faces -Y, feet at z=0) ----------------
HEAD_O = V(0.0, -0.030, 1.578)
HEAD_R = (rotz(np.radians(16)) @ rotx(np.radians(3)) @ roty(np.radians(-7))).astype(f32)   # columns = local axes
def to_head(p): return (p - HEAD_O) @ HEAD_R
def from_head(q): return q @ HEAD_R.T + HEAD_O

S = {}
for sx, side in ((-1, 'R'), (1, 'L')):
    S['sho' + side] = V(sx * 0.175, 0.008, 1.355 + (-0.006 if side == 'R' else 0.004))
    # v1.0.3: relaxed arms hanging at the sides (was: hands tucked into the trouser pockets)
    S['elb' + side] = V(sx * 0.205, 0.030, 1.085)
    S['wri' + side] = V(sx * 0.230, -0.005, 0.855)
    S['hnd' + side] = V(sx * 0.235, -0.018, 0.770)
S['hipR'] = V(-0.085, 0.0, 0.888); S['hipL'] = V(0.085, 0.0, 0.874)
S['kneR'] = V(-0.088, -0.006, 0.483); S['kneL'] = V(0.097, -0.058, 0.474)
S['ankR'] = V(-0.090, 0.022, 0.078); S['ankL'] = V(0.130, -0.046, 0.076)
FOOT_YAW = {'R': np.radians(-8), 'L': np.radians(24)}
NECK_TOP = V(0.0, 0.026, 1.50); NECK_BOT = V(0.0, 0.008, 1.36)
SEAM_Z = 1.455

def lerp(a, b, t): return a + (b - a) * t

BUST_SCALE = 1.0      # 1.0 = natural medium (all outfits); the bikini variant uses a larger setting
def torso(p, top=False):
    k = 1.0 if not top else 1.6
    d = ellipsoid(p, (0, 0.010, 1.230), (0.128, 0.090, 0.160))                      # ribcage
    d = smin(d, ellipsoid(p, (0, 0.012, 1.315), (0.146, 0.080, 0.075)), 0.03 * k)    # upper chest
    # natural medium bust: fuller lower pole, slight outward set, proportionate to an athletic frame
    bs = BUST_SCALE; by = -0.062 - 0.010 * (bs - 1) / 0.15; bz = 1.222 - 0.006 * (bs - 1) / 0.15
    bust = smin(ellipsoid(p, (-0.055, by, bz), (0.062 * bs, 0.060 * bs, 0.058 * bs)),
                ellipsoid(p, (0.055, by, bz), (0.062 * bs, 0.060 * bs, 0.058 * bs)), 0.02 if not top else 0.07)
    bust = smin(bust, smin(ellipsoid(p, (-0.057, by - 0.008, bz - 0.017 * bs), (0.052 * bs, 0.050 * bs, 0.044 * bs)),
                           ellipsoid(p, (0.057, by - 0.008, bz - 0.017 * bs), (0.052 * bs, 0.050 * bs, 0.044 * bs)), 0.02 if not top else 0.07), 0.02)
    d = smin(d, bust, 0.035 if not top else 0.05)
    d = smin(d, ellipsoid(p, (0, 0.014, 1.070), (0.117, 0.080, 0.110)), 0.05 * k)    # waist
    d = smin(d, ellipsoid(p, (0, -0.010, 0.990), (0.118, 0.076, 0.085)), 0.04 * k)   # belly
    d = smin(d, ellipsoid(p, (0, 0.012, 0.915), (0.165, 0.104, 0.105)), 0.05 * k)    # pelvis
    for sx in (-1, 1):
        d = smin(d, ellipsoid(p, (sx * 0.062, 0.055, 0.878), (0.076, 0.062, 0.085)), 0.03)  # glutes
        d = smin(d, ellipsoid(p, (sx * 0.080, 0.080, 1.285), (0.052, 0.022, 0.065)), 0.03)  # scapula
        d = smin(d, round_cone(p, (sx * 0.040, 0.030, 1.425), (sx * 0.150, 0.020, 1.385), 0.028, 0.022), 0.03)  # trapezius
        d = smin(d, capsule(p, (sx * 0.022, -0.050, 1.372), (sx * 0.150, -0.012, 1.392), 0.0085), 0.014)    # clavicle
        if top:
            sh = S['sho' + ('R' if sx < 0 else 'L')]
            d = smin(d, ellipsoid(p, sh + V(-sx * 0.012, -0.002, -0.015), (0.040, 0.046, 0.05)), 0.02)
    return d

def arm(p, side):
    s, e, w, h = S['sho' + side], S['elb' + side], S['wri' + side], S['hnd' + side]
    sx = -1 if side == 'R' else 1
    d = round_cone(p, s, e, 0.043, 0.031)
    d = smin(d, ellipsoid(p, s + V(sx * 0.006, -0.002, -0.026), (0.043, 0.047, 0.058)), 0.02)   # deltoid
    fw = V(0, -0.008, 0)
    d = smin(d, round_cone(p, lerp(s, e, 0.25) + fw, lerp(s, e, 0.78) + fw, 0.033, 0.027), 0.02)   # biceps
    d = smin(d, round_cone(p, lerp(s, e, 0.20) - fw * 1.6, lerp(s, e, 0.72) - fw * 1.2, 0.034, 0.027), 0.02)  # triceps
    d = smin(d, round_cone(p, e, w, 0.033, 0.0215), 0.012)
    d = smin(d, round_cone(p, lerp(e, w, 0.08) + V(sx * 0.006, -0.004, 0), lerp(e, w, 0.55), 0.036, 0.025), 0.02)  # forearm mass
    d = smin(d, round_cone(p, w, h, 0.024, 0.021), 0.01)                                     # hand (relaxed, at the side)
    d = smin(d, ellipsoid(p, lerp(w, h, 0.55) + V(-sx * 0.004, -0.004, 0), (0.014, 0.030, 0.042)), 0.012)  # palm / fingers
    return d

def leg(p, side):
    hp, kn, an = S['hip' + side], S['kne' + side], S['ank' + side]
    d = round_cone(p, hp, kn, 0.088, 0.050)
    d = smin(d, round_cone(p, kn, an, 0.050, 0.030), 0.02)
    d = smin(d, round_cone(p, lerp(kn, an, 0.12) + V(0, 0.01, 0), lerp(kn, an, 0.5) + V(0, 0.012, 0), 0.052, 0.036), 0.02)
    return d

def neck_core(p):
    q = p.copy(); q[:, 0] = q[:, 0] / 0.88
    return round_cone(q, NECK_BOT, NECK_TOP, 0.052, 0.046) * 0.9

def neck(p):
    d = neck_core(p)
    for sx in (-1, 1):   # sternocleidomastoid
        top = from_head(V(sx * 0.055, 0.068, -0.045)[None])[0]
        d = smin(d, round_cone(p, V(sx * 0.013, -0.036, 1.378), top, 0.0065, 0.010), 0.012)
    return d

def head_world(p): return H.head_local(to_head(p))

def body(p):
    d = torso(p)
    d = smin(d, neck(p), 0.03)
    for sd in ('R', 'L'):
        d = smin(d, arm(p, sd), 0.022)
        d = smin(d, leg(p, sd), 0.03)
    return d

def body_noarms(p):
    d = torso(p)
    d = smin(d, neck(p), 0.03)
    for sd in ('R', 'L'):
        d = smin(d, leg(p, sd), 0.03)
    return d

def arms(p): return np.minimum(arm(p, 'R'), arm(p, 'L'))

def skin(p):
    d = body(p)
    # only evaluate head where it matters
    m = p[:, 2] > 1.40
    if m.any():
        dh = np.full(len(p), 1.0, f32); dh[m] = head_world(p[m])
        d = smin(d, dh, 0.022)
    return d

# ---------------- clothing ----------------
def tank_sdf(p):
    d = torso(p, top=True) - 0.0028
    # gentle horizontal wrinkles near the waist / under bust
    wav = np.sin(p[:, 2] * 210 + 3 * vnoise(p * 40)) * np.exp(-((p[:, 2] - 1.05) / 0.06) ** 2)
    return d - 0.0009 * wav

def tank_keep(c):
    x, y, z = np.abs(c[:, 0]), c[:, 1], c[:, 2]
    neck_front = 1.272 + 0.050 * (np.minimum(x, 0.09) / 0.09) ** 2
    neck_back = 1.325 + 0.008 * (np.minimum(x, 0.09) / 0.09) ** 2
    zn = np.where(y < 0.01, neck_front, neck_back)
    inner = (x < 0.122) & (z < zn)
    outer = (x >= 0.122) & (z < 1.232 - 0.25 * np.maximum(x - 0.14, 0)) & (z < zn + 0.2)
    return (inner | outer) & (z > 0.975)

def strap_mesh(sx, nl=90, nw=7, width=0.021):
    ctrl = np.array([(sx * 0.103, -0.040, 1.300), (sx * 0.106, -0.060, 1.345), (sx * 0.108, -0.035, 1.395), (sx * 0.110, 0.010, 1.418),
                     (sx * 0.106, 0.055, 1.395), (sx * 0.101, 0.085, 1.345), (sx * 0.099, 0.090, 1.315)], f32)
    from hair_util import catmull
    P = catmull(ctrl, np.linspace(0, 1, nl)).astype(f32)
    def fs(p): return skin(p) - 0.0026
    for _ in range(5):
        d = fs(P); n = grad(fs, P, 4e-4); P = P - n * d[:, None]
    n = grad(fs, P, 4e-4)
    t = np.gradient(P, axis=0); t /= np.linalg.norm(t, axis=1, keepdims=True)
    b = np.cross(t, n); b /= np.linalg.norm(b, axis=1, keepdims=True)
    G = P[:, None, :] + b[:, None, :] * (np.linspace(-0.5, 0.5, nw) * width)[None, :, None]
    G = G.reshape(-1, 3).astype(f32)
    for _ in range(4):
        d = fs(G); n2 = grad(fs, G, 4e-4); G = G - n2 * d[:, None]
    F = []
    for i in range(nl - 1):
        for j in range(nw - 1):
            a = i * nw + j; F += [[a, a + nw, a + nw + 1], [a, a + nw + 1, a + 1]]
    F = np.array(F, np.int32)
    if sx < 0: F = F[:, ::-1]
    return G, F

def trousers_sdf(p):
    low = smin(smin(ellipsoid(p, (0, 0.012, 0.915), (0.165, 0.104, 0.105)),
                    ellipsoid(p, (0, -0.010, 0.990), (0.118, 0.076, 0.085)), 0.04),
               ellipsoid(p, (0, 0.014, 1.050), (0.117, 0.080, 0.110)), 0.05)
    for sx in (-1, 1):
        low = smin(low, ellipsoid(p, (sx * 0.062, 0.055, 0.878), (0.076, 0.062, 0.085)), 0.03)
    d = low - 0.011
    for sd in ('R', 'L'):
        hp, kn, an = S['hip' + sd], S['kne' + sd], S['ank' + sd]
        hem = V(kn[0] + (an[0] - kn[0]) * 0.6, kn[1] + 0.012, 0.022)
        lg = smin(round_cone(p, hp + V(0, 0.004, 0.02), kn + V(0, 0.002, 0), 0.100, 0.074),
                  round_cone(p, kn + V(0, 0.002, 0), hem, 0.074, 0.084), 0.04)
        # front crease ridge
        axis = normalize(hem - kn)
        d = smin(d, lg, 0.035)
    # drape folds: low-frequency noise + horizontal ripples near knees and hem breaks
    n = fbm(p * V(18, 18, 7), 3)
    rip = np.sin(p[:, 2] * 95 + 4 * vnoise(p * 9)) * (np.exp(-((p[:, 2] - 0.50) / 0.09) ** 2) + 1.4 * np.exp(-((p[:, 2] - 0.06) / 0.05) ** 2))
    return d - 0.0035 * n - 0.0016 * rip

def trousers_keep(c): return (c[:, 2] < 1.012) & (c[:, 2] > 0.024)

def belt_sdf(p):
    dt = trousers_sdf(p)
    return smax(np.abs(dt + 0.0005) - 0.0024, np.abs(p[:, 2] - 0.990) - 0.0145, 0.001)

def buckle_sdf(p):
    c = V(0.0, 0.0, 0.990)
    # find front surface: place at trouser front ~ y
    q = p - V(0, BUCKLE_Y, 0.990)
    outer = round_box(q + V(0, 0, 0), (0, 0, 0), (0.024, 0.004, 0.017), 0.003)
    inner = round_box(q, (0, 0, 0), (0.016, 0.01, 0.010), 0.002)
    return smax(outer, -inner, 0.001)

def shoe_frame(side):
    a = S['ank' + side]; yaw = FOOT_YAW[side]
    R = rotz(yaw)
    return a, R

def shoe_upper(p, side):
    a, R = shoe_frame(side)
    q = (p - V(a[0], a[1], 0)) @ R
    d = ellipsoid(q, (0, 0.040, 0.050), (0.038, 0.048, 0.048))
    d = smin(d, ellipsoid(q, (0, -0.055, 0.042), (0.044, 0.085, 0.040)), 0.03)
    d = smin(d, ellipsoid(q, (0, -0.150, 0.030), (0.042, 0.062, 0.030)), 0.03)
    d = smax(d, 0.016 - q[:, 2], 0.004)
    d = smax(d, -ellipsoid(q, (0, 0.025, 0.105), (0.034, 0.045, 0.03)), 0.006)  # collar opening
    return d

def shoe_sole(p, side):
    a, R = shoe_frame(side)
    q = (p - V(a[0], a[1], 0)) @ R
    q2 = q.copy(); q2[:, 2] = 0.035
    fp = shoe_upper(q2 @ R.T + V(a[0], a[1], 0), side) - 0.004
    return smax(fp, np.abs(q[:, 2] - 0.012) - 0.012, 0.004)

def choker_sdf(p):
    ds = neck(p)
    return smax(np.abs(ds - 0.0016) - 0.0012, np.abs(p[:, 2] - SEAM_Z) - 0.0070, 0.0008)

BUCKLE_Y = 0.0
def main(head_h=0.0006, body_h=0.0015, cloth_h=0.002, only=None):
    global BUCKLE_Y
    out = {}
    t0 = time.time()
    def do(name, f, bmin, bmax, h, keep=None):
        if only and name not in only: return
        t = time.time()
        Vv, Ff = mesh_sdf(f, bmin, bmax, h)
        if keep is not None: Vv, Ff, _ = keep_faces(Vv, Ff, keep)
        out[name + '_V'] = Vv; out[name + '_F'] = Ff
        print(name, len(Vv), 'verts', round(time.time() - t, 1), 's', flush=True)
        return Vv
    Vh = do('head', skin, (-0.13, -0.15, SEAM_Z), (0.13, 0.20, 1.71), head_h)
    if Vh is not None:
        for k, v in H.head_masks(to_head(Vh)).items(): out['head_m_' + k] = v.astype(f32)
    do('body', skin, (-0.31, -0.16, 0.70), (0.31, 0.17, SEAM_Z), body_h)
    do('tank', tank_sdf, (-0.20, -0.15, 0.94), (0.20, 0.14, 1.47), cloth_h * 0.75, tank_keep)
    if not only or 'straps' in only:
        Vs, Fs = [], []; off = 0
        for sx in (-1, 1):
            v, f_ = strap_mesh(sx); Vs.append(v); Fs.append(f_ + off); off += len(v)
        out['straps_V'] = np.concatenate(Vs); out['straps_F'] = np.concatenate(Fs)
    do('trousers', trousers_sdf, (-0.25, -0.18, 0.0), (0.27, 0.18, 1.04), cloth_h, trousers_keep)
    # buckle position from trouser front at x=0
    ys = np.linspace(-0.2, 0, 400).astype(f32)
    P = np.stack([np.zeros_like(ys), ys, np.full_like(ys, 0.99)], 1)
    dd = trousers_sdf(P); BUCKLE_Y = float(ys[np.argmax(dd < 0)]) - 0.004
    do('belt', belt_sdf, (-0.22, -0.16, 0.965), (0.22, 0.16, 1.015), 0.0012)
    do('buckle', buckle_sdf, (-0.035, BUCKLE_Y - 0.02, 0.965), (0.035, BUCKLE_Y + 0.02, 1.015), 0.0006)
    for sd in ('R', 'L'):
        a = S['ank' + sd]
        do('shoeU' + sd, lambda p, s=sd: shoe_upper(p, s), (a[0] - 0.13, a[1] - 0.25, 0.0), (a[0] + 0.13, a[1] + 0.13, 0.15), 0.0015)
        do('shoeS' + sd, lambda p, s=sd: shoe_sole(p, s), (a[0] - 0.13, a[1] - 0.25, -0.002), (a[0] + 0.13, a[1] + 0.13, 0.03), 0.0012)
    do('choker', choker_sdf, (-0.08, -0.08, SEAM_Z - 0.012), (0.08, 0.09, SEAM_Z + 0.012), 0.0006)
    rig = {'HEAD_O': HEAD_O.tolist(), 'HEAD_R': HEAD_R.tolist(), 'EYE_X': H.EYE_X * 1.04, 'EYE_R': H.EYE_R, 'EYE_Y': H.EYE_Y,
           'S': {k: v.tolist() for k, v in S.items()}, 'BUCKLE_Y': BUCKLE_Y, 'SEAM_Z': SEAM_Z}
    json.dump(rig, open('/workspace/fireout-shine-concept/cache/rig.json', 'w'), indent=1)
    np.savez('/workspace/fireout-shine-concept/cache/char.npz', **out)
    print('total', round(time.time() - t0, 1))

if __name__ == '__main__':
    hh = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0006
    bh = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0015
    ch = float(sys.argv[3]) if len(sys.argv) > 3 else 0.002
    main(hh, bh, ch)
