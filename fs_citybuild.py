"""v1.0.4 BUILD (ANA's ability since v1.0.4.1), city style.

Builds are made the same way as the Shinko Ward buildings: real-scale solid meshes (boxes, cylinders, frustums, domes,
sloped and curved roofs) using the city's own facade textures (windows, glass curtain walls, shopfronts), flat painted
trim and simple baked shading - no voxels.  Every build also produces a list of solid volumes that is rasterised into
the walk-collision grid used by fs_miyo.Builds (walls block you, decks / roofs / steps can be stood on).

plan(text) -> (kind, label, opts)    fuzzy keyword match + typo correction, unknown words -> invented building
generate(kind, opts, seed) -> Model   geometry (per material MeshBuilders) + solids
"""
import math, random, re, difflib
from fs_geom import MB

L_DIR = (-0.45, -0.6, 0.66)          # baked "sun" direction for vertex shading (matches the city's look)


class SMB(MB):
    """MeshBuilder that bakes gentle directional shading into the vertex colours"""
    def quad(self, p0, p1, p2, p3, col=(1, 1, 1, 1), uv=((0, 0), (1, 0), (1, 1), (0, 1)), n=None):
        ax, ay, az = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]
        bx, by, bz = p3[0] - p0[0], p3[1] - p0[1], p3[2] - p0[2]
        nx, ny, nz = ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx
        l = math.sqrt(nx * nx + ny * ny + nz * nz)
        if l < 1e-9:      # degenerate (triangle as quad): use the other diagonal
            ax, ay, az = p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2]
            nx, ny, nz = ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx; l = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        nx, ny, nz = nx / l, ny / l, nz / l
        d = max(0.0, nx * L_DIR[0] + ny * L_DIR[1] + nz * L_DIR[2]) / 1.0
        f = 0.74 + 0.26 * d + 0.06 * nz
        def sh(c): return (min(1.0, c[0] * f), min(1.0, c[1] * f), min(1.0, c[2] * f), c[3] if len(c) > 3 else 1.0)
        cols = tuple(sh(c) for c in col) if isinstance(col[0], (tuple, list)) else sh(col)
        MB.quad(self, p0, p1, p2, p3, cols, uv, n=(nx, ny, nz))


class Model:
    def __init__(self):
        self.mb = {}; self.solids = []; self.signs = []

    def M(self, mat):
        if mat not in self.mb: self.mb[mat] = SMB("cb_" + mat)
        return self.mb[mat]

    # ---- collision volumes (local coords, metres) ---------------------------------------------------------------
    def solid_box(self, x0, y0, x1, y1, z0, z1): self.solids.append(("box", min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1), z0, z1))
    def solid_cyl(self, cx, cy, r, z0, z1): self.solids.append(("cyl", cx, cy, r, z0, z1))
    def solid_pyr(self, cx, cy, hx, hy, z0, h): self.solids.append(("pyr", cx, cy, hx, hy, z0, h))
    def solid_ridge(self, x0, y0, x1, y1, z0, h, axis): self.solids.append(("ridge", x0, y0, x1, y1, z0, h, axis))

    def intervals(self, x, y, pad=0.25):
        """solid z-intervals over a 0.5 m cell centred at (x, y): pad makes thin walls / posts always register"""
        out = []
        for s in self.solids:
            if s[0] == "box":
                if s[1] - pad <= x <= s[3] + pad and s[2] - pad <= y <= s[4] + pad: out.append((s[5], s[6]))
            elif s[0] == "cyl":
                if (x - s[1]) ** 2 + (y - s[2]) ** 2 <= (s[3] + pad * 0.7) ** 2: out.append((s[4], s[5]))
            elif s[0] == "ridge":
                if s[1] <= x <= s[3] and s[2] <= y <= s[4]:
                    if s[7] == "x": u = abs(y - (s[2] + s[4]) / 2) / ((s[4] - s[2]) / 2)
                    else: u = abs(x - (s[1] + s[3]) / 2) / ((s[3] - s[1]) / 2)
                    out.append((s[5], s[5] + s[6] * (1.0 - min(1.0, u))))
            elif s[0] == "pyr":
                u = max(abs(x - s[1]) / s[3], abs(y - s[2]) / s[4])
                if u <= 1.0: out.append((s[5], s[5] + s[6] * (1.0 - u)))
        return out

    def bounds(self):
        xs, ys = [], []
        for s in self.solids:
            if s[0] in ("box", "ridge"): xs += [s[1], s[3]]; ys += [s[2], s[4]]
            elif s[0] == "cyl": xs += [s[1] - s[3], s[1] + s[3]]; ys += [s[2] - s[3], s[2] + s[3]]
            else: xs += [s[1] - s[3], s[1] + s[3]]; ys += [s[2] - s[4], s[2] + s[4]]
        return (min(xs), min(ys), max(xs), max(ys)) if xs else (-1, -1, 1, 1)


# ================================================================ primitives
def fuv(w, h, z0=0.0):
    """city facade UVs: one texture tile = 32 m wide x 28 m tall (same as fs_world.building)"""
    return lambda f, ww, hh: ((0, z0 / 28.0), (ww / 32.0, z0 / 28.0), (ww / 32.0, (z0 + hh) / 28.0), (0, (z0 + hh) / 28.0))


def box(m, mat, x0, y0, z0, x1, y1, z1, col, solid=True, top=True, tex=True):
    b = m.M(mat)
    if mat.startswith("facade") or mat == "shopfront":
        b.box(x0, y0, z0, x1, y1, z1, col, top=False, uvs=fuv(x1 - x0, z1 - z0, z0) if tex else None)
        if top: m.M("flat").quad((x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1), (0.16, 0.16, 0.18, 1))
    else:
        b.box(x0, y0, z0, x1, y1, z1, col, top=top)
    if solid: m.solid_box(x0, y0, x1, y1, z0, z1)


def ring_pts(cx, cy, r, n, a0=0.0):
    return [(cx + r * math.cos(a0 + 2 * math.pi * k / n), cy + r * math.sin(a0 + 2 * math.pi * k / n)) for k in range(n)]


def frustum(m, mat, cx, cy, z0, z1, r0, r1, col, n=20, solid=True, cap=True, uv_scale=True):
    b = m.M(mat); A = ring_pts(cx, cy, r0, n); B = ring_pts(cx, cy, r1, n)
    circ = 2 * math.pi * max(r0, r1)
    for k in range(n):
        j = (k + 1) % n
        u0, u1 = (k / n) * circ / 32.0, ((k + 1) / n) * circ / 32.0
        uv = ((u0, z0 / 28.0), (u1, z0 / 28.0), (u1, z1 / 28.0), (u0, z1 / 28.0)) if uv_scale else ((0, 0), (1, 0), (1, 1), (0, 1))
        b.quad((A[k][0], A[k][1], z0), (A[j][0], A[j][1], z0), (B[j][0], B[j][1], z1), (B[k][0], B[k][1], z1), col, uv)
    if cap and r1 > 0.01:
        f = m.M("flat")
        for k in range(n):
            j = (k + 1) % n
            f.quad((B[k][0], B[k][1], z1), (B[j][0], B[j][1], z1), (cx, cy, z1), (cx, cy, z1), col)
    if solid: m.solid_cyl(cx, cy, max(r0, r1), z0, z1)


def dome(m, mat, cx, cy, z0, r, col, n=20, rings=8, squash=1.0, solid=True):
    b = m.M(mat)
    for i in range(rings):
        a0, a1 = (math.pi / 2) * i / rings, (math.pi / 2) * (i + 1) / rings
        r0, r1 = r * math.cos(a0), r * math.cos(a1); h0, h1 = z0 + r * squash * math.sin(a0), z0 + r * squash * math.sin(a1)
        A = ring_pts(cx, cy, r0, n); B = ring_pts(cx, cy, max(r1, 0.001), n)
        for k in range(n):
            j = (k + 1) % n
            b.quad((A[k][0], A[k][1], h0), (A[j][0], A[j][1], h0), (B[j][0], B[j][1], h1), (B[k][0], B[k][1], h1), col)
    if solid: m.solid_cyl(cx, cy, r * 0.85, z0, z0 + r * squash * 0.8)


def ellipsoid(m, mat, cx, cy, cz, rx, ry, rz, col, n=16, rings=10):
    b = m.M(mat)
    for i in range(rings):
        a0, a1 = -math.pi / 2 + math.pi * i / rings, -math.pi / 2 + math.pi * (i + 1) / rings
        for k in range(n):
            t0, t1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
            def P(a, t): return (cx + rx * math.cos(a) * math.cos(t), cy + ry * math.cos(a) * math.sin(t), cz + rz * math.sin(a))
            b.quad(P(a0, t0), P(a0, t1), P(a1, t1), P(a1, t0), col)


def gable(m, x0, y0, x1, y1, z, h, col, over=0.4, axis="x"):
    """smooth pitched roof (two slopes + gable ends); ridge along axis"""
    f = m.M("flat"); x0 -= over; y0 -= over; x1 += over; y1 += over
    if axis == "x":
        ym = (y0 + y1) / 2
        f.quad((x0, y0, z), (x1, y0, z), (x1, ym, z + h), (x0, ym, z + h), col)
        f.quad((x1, y1, z), (x0, y1, z), (x0, ym, z + h), (x1, ym, z + h), col)
        wall = (col[0] * 0.9, col[1] * 0.9, col[2] * 0.9, 1)
        f.quad((x0, y1, z), (x0, y0, z), (x0, ym, z + h), (x0, ym, z + h), wall); f.quad((x1, y0, z), (x1, y1, z), (x1, ym, z + h), (x1, ym, z + h), wall)
        m.solid_ridge(x0, y0, x1, y1, z, h, "x")
    else:
        xm = (x0 + x1) / 2
        f.quad((x0, y1, z), (x0, y0, z), (xm, y0, z + h), (xm, y1, z + h), col)
        f.quad((x1, y0, z), (x1, y1, z), (xm, y1, z + h), (xm, y0, z + h), col)
        m.solid_ridge(x0, y0, x1, y1, z, h, "y")


def curved_roof(m, cx, cy, hx, hy, z, h, col, over=1.4, lift=0.55, top=0.35, n=6, under=None):
    """Japanese hip roof as smooth geometry: concave slopes (lofted rings) whose corners sweep upwards"""
    f = m.M("flat"); under = under or (col[0] * 0.55, col[1] * 0.5, col[2] * 0.45, 1)
    rings = []
    for i in range(n + 1):
        t = i / n
        s = (1 - t) ** 1.6                                      # concave profile
        ex, ey = top * hx + (hx + over - top * hx) * s, top * hy + (hy + over - top * hy) * s
        zz = z + h * (1 - (1 - t) ** 0.7)
        rings.append((ex, ey, zz, s))
    def corner_pts(ex, ey, zz, s):
        up = lift * s * s                                       # corners curl up toward the eaves
        pts = []
        for (sx, sy) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            pts.append([(cx + sx * ex, cy + sy * ey, zz + up)])
            # mid-edge points (lower than corners -> the swept look)
        out = []
        for k in range(4):
            a = pts[k][0]; b = pts[(k + 1) % 4][0]
            for q in range(4):
                u = q / 4.0; mid_drop = up * math.sin(math.pi * u)
                out.append((a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u, a[2] + (b[2] - a[2]) * u - mid_drop))
        return out
    R = [corner_pts(*r) for r in rings]
    for i in range(n):
        A, B = R[i], R[i + 1]
        for k in range(len(A)):
            j = (k + 1) % len(A)
            f.quad(A[k], A[j], B[j], B[k], col)
    A = R[0]
    for k in range(len(A)):         # soffit (underside of the eaves)
        j = (k + 1) % len(A)
        f.quad(A[j], A[k], (cx + (A[k][0] - cx) * 0.6, cy + (A[k][1] - cy) * 0.6, z), (cx + (A[j][0] - cx) * 0.6, cy + (A[j][1] - cy) * 0.6, z), under)
    T = R[-1]
    for k in range(len(T)):         # flat cap
        j = (k + 1) % len(T)
        f.quad(T[k], T[j], (cx, cy, T[j][2]), (cx, cy, T[k][2]), col)
    m.solid_pyr(cx, cy, hx + over * 0.6, hy + over * 0.6, z, h)


def tree(m, x, y, s=1.0, pink=False, rng=None):
    rng = rng or random.Random(int(x * 7 + y * 13))
    frustum(m, "flat", x, y, 0.0, 2.6 * s, 0.2 * s, 0.14 * s, (0.30, 0.21, 0.15, 1), n=8, solid=False)
    m.solid_cyl(x, y, 0.25 * s, 0, 2.5 * s)
    c = (0.98, 0.62, 0.78, 1) if pink else rng.choice([(0.16, 0.36, 0.17, 1), (0.2, 0.42, 0.2, 1), (0.13, 0.3, 0.16, 1)])
    for k in range(4):
        a = rng.uniform(0, 6.28); d = rng.uniform(0.2, 0.7) * s
        ellipsoid(m, "flat", x + math.cos(a) * d, y + math.sin(a) * d, (3.3 + rng.uniform(-0.3, 0.6)) * s,
                  rng.uniform(1.1, 1.6) * s, rng.uniform(1.1, 1.6) * s, rng.uniform(0.9, 1.2) * s, c, n=18, rings=10)


def sign(m, text, x, y, z, w, h, face_y=-1, col=(0.08, 0.08, 0.1, 1), fg=(1, 0.85, 0.3, 1)):
    """a facade sign: a painted board + the text (TextNode added later by fs_miyo) - no glow"""
    box(m, "flat", x - w / 2, y - 0.12, z, x + w / 2, y + 0.12, z + h, col, solid=False)
    m.signs.append((text, x, y + face_y * 0.14, z + h / 2, h * 0.55, face_y, fg))


# ================================================================ archetypes
WOOD = (0.55, 0.16, 0.12, 1); PLASTER = (0.93, 0.9, 0.84, 1); TILE = (0.22, 0.24, 0.27, 1); STONE = (0.55, 0.53, 0.5, 1)
GOLD = (0.85, 0.68, 0.25, 1)


def a_house(m, o, rng):
    w, d = 9.0 * o["s"], 8.0 * o["s"]; fl = 2 if not o["small"] else 1
    h = 3.0 * fl
    box(m, "facade5", -w / 2, -d / 2, 0, w / 2, d / 2, h, rng.choice([(1, 1, 1, 1), (1.05, 0.97, 0.9, 1), (0.92, 0.95, 1.02, 1)]), top=True)
    m.M("flat").quad((-w / 2 - 0.4, d / 2 + 0.4, h - 0.02), (w / 2 + 0.4, d / 2 + 0.4, h - 0.02), (w / 2 + 0.4, -d / 2 - 0.4, h - 0.02), (-w / 2 - 0.4, -d / 2 - 0.4, h - 0.02), (0.42, 0.4, 0.38, 1))   # eaves soffit
    gable(m, -w / 2, -d / 2, w / 2, d / 2, h, 2.6 * o["s"], rng.choice([TILE, (0.45, 0.18, 0.14, 1), (0.2, 0.3, 0.38, 1)]), axis="x")
    box(m, "flat", -0.6, -d / 2 - 0.05, 0, 0.6, -d / 2 + 0.02, 2.1, (0.35, 0.22, 0.14, 1), solid=False)          # front door
    box(m, "flat", -1.0, -d / 2 - 1.2, 2.2, 1.0, -d / 2, 2.35, (0.3, 0.3, 0.32, 1), solid=False)                 # porch canopy
    box(m, "flat", -w / 2 - 0.6, -d / 2 - 3.2, 0, w / 2 + 0.6, -d / 2 - 3.0, 1.1, (0.7, 0.68, 0.64, 1))           # garden wall
    tree(m, w / 2 - 1.2, -d / 2 - 1.8, 0.8, rng=rng)
    return "a house"


def a_apartment(m, o, rng):
    w, d = 16 * o["s"], 11 * o["s"]; h = (18 if not o["tall"] else 32) * o["s"]
    box(m, rng.choice(["facade1", "facade2", "facade5"]), -w / 2, -d / 2, 0, w / 2, d / 2, h, (1, 1, 1, 1))
    for z in range(3, int(h) - 1, 3):     # balconies along the front
        box(m, "flat", -w / 2 + 0.4, -d / 2 - 1.1, z, w / 2 - 0.4, -d / 2, z + 0.12, (0.8, 0.8, 0.8, 1), solid=False)
        box(m, "flat", -w / 2 + 0.4, -d / 2 - 1.15, z + 0.12, w / 2 - 0.4, -d / 2 - 1.05, z + 1.0, (0.62, 0.66, 0.7, 1), solid=False)
    roof_kit(m, -w / 2, -d / 2, w / 2, d / 2, h, rng)
    return "an apartment block"


def roof_kit(m, x0, y0, x1, y1, h, rng):
    for k in range(rng.randint(2, 4)):          # AC units / water tank
        x = rng.uniform(x0 + 1.5, x1 - 2.5); y = rng.uniform(y0 + 1.5, y1 - 2.5)
        box(m, "flat", x, y, h, x + 1.1, y + 0.8, h + 0.9, (0.75, 0.76, 0.78, 1), solid=False)
    frustum(m, "flat", x1 - 2.2, y1 - 2.2, h, h + 2.2, 0.9, 0.9, (0.55, 0.57, 0.6, 1), n=12, solid=False)
    box(m, "flat", x0, y0, h, x1, y0 + 0.15, h + 1.0, (0.6, 0.6, 0.62, 1), solid=False)     # parapet
    box(m, "flat", x0, y1 - 0.15, h, x1, y1, h + 1.0, (0.6, 0.6, 0.62, 1), solid=False)


def a_skyscraper(m, o, rng):
    w = 16 * o["s"]; h = (70 if not o["tall"] else 120) * (0.6 if o["small"] else 1.0)
    fac = rng.choice(["facade6", "facade0", "facade4", "facade6"])
    box(m, fac, -w / 2, -w / 2, 0, w / 2, w / 2, h, rng.choice([(1, 1, 1, 1), (0.92, 0.96, 1.06, 1)]))
    i = w * 0.2; h2 = h + h * 0.18
    box(m, fac, -w / 2 + i, -w / 2 + i, h, w / 2 - i, w / 2 - i, h2, (1, 1, 1, 1))
    frustum(m, "flat", 0, 0, h2, h2 + 14, 0.35, 0.12, (0.8, 0.8, 0.84, 1), n=8, solid=False)          # antenna mast
    box(m, "shopfront", -w / 2 - 0.05, -w / 2 - 0.05, 0, w / 2 + 0.05, -w / 2 + 0.3, 4.2, (1, 1, 1, 1), solid=False, top=False)
    sign(m, o["title"], 0, -w / 2 - 0.3, 5.0, min(w * 0.8, 1.2 + 0.9 * len(o["title"])), 1.6)
    return "a skyscraper"


def a_pagoda(m, o, rng):
    tiers = 5 if not o["small"] else 3; base = 7.5 * o["s"]; th = 3.6 * o["s"]
    box(m, "flat", -base / 2 - 1.5, -base / 2 - 1.5, 0, base / 2 + 1.5, base / 2 + 1.5, 0.9, STONE)       # stone platform
    for k in range(5):                                                                                       # front steps
        box(m, "flat", -1.4, -base / 2 - 1.5 - 0.35 * (5 - k), 0, 1.4, -base / 2 - 1.5 - 0.35 * (4 - k), 0.18 * (k + 1), STONE)
    z = 0.9
    for t in range(tiers):
        s = 1.0 - 0.11 * t; hw = base / 2 * s
        box(m, "flat", -hw, -hw, z, hw, hw, z + th * 0.62, PLASTER)
        for (sx, sy) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):                                              # red corner posts
            box(m, "flat", sx * hw - 0.18 - (0.0 if sx < 0 else -0.0), sy * hw - 0.18, z, sx * hw + 0.18, sy * hw + 0.18, z + th * 0.62, WOOD, solid=False)
        box(m, "flat", -hw - 0.05, -hw - 0.05, z + th * 0.55, hw + 0.05, hw + 0.05, z + th * 0.62, WOOD, solid=False)   # beam
        box(m, "flat", -0.7 * s, -hw - 0.06, z, 0.7 * s, -hw + 0.02, z + th * 0.5, (0.3, 0.12, 0.1, 1), solid=False)   # door
        curved_roof(m, 0, 0, hw, hw, z + th * 0.62, th * 0.42, TILE, over=1.6 * s, lift=0.6 * s, top=0.55)
        z += th
    frustum(m, "flat", 0, 0, z - th * 0.38, z + 5.5 * o["s"], 0.28, 0.08, GOLD, n=10, solid=False)          # sorin spire
    for k in range(6):
        frustum(m, "flat", 0, 0, z + 0.4 + k * 0.6, z + 0.55 + k * 0.6, 0.55 - k * 0.05, 0.55 - k * 0.05, GOLD, n=10, solid=False)
    tree(m, -base / 2 - 4.5, -base / 2 + 1, 1.0, pink=True, rng=rng); tree(m, base / 2 + 4.5, -base / 2 + 2, 0.9, pink=True, rng=rng)
    return "a five-storey pagoda" if tiers == 5 else "a three-storey pagoda"


def a_temple(m, o, rng):
    w, d = 14 * o["s"], 10 * o["s"]
    box(m, "flat", -w / 2 - 1, -d / 2 - 1, 0, w / 2 + 1, d / 2 + 1, 1.0, STONE)
    box(m, "flat", -w / 2, -d / 2, 1.0, w / 2, d / 2, 5.0, PLASTER)
    for k in range(7):
        x = -w / 2 + k * w / 6
        frustum(m, "flat", x, -d / 2 - 0.6, 1.0, 5.0, 0.25, 0.25, WOOD, n=10)
    curved_roof(m, 0, 0, w / 2, d / 2, 5.0, 4.2 * o["s"], TILE, over=2.2, lift=0.8, top=0.25)
    torii(m, 0, -d / 2 - 9, 1.0)
    return "a temple"


def torii(m, x, y, s=1.0):
    r = (0.86, 0.18, 0.12, 1)
    for sx in (-1, 1):
        frustum(m, "flat", x + sx * 2.4 * s, y, 0, 5.2 * s, 0.32 * s, 0.26 * s, r, n=12)
        frustum(m, "flat", x + sx * 2.4 * s, y, 0, 0.6 * s, 0.4 * s, 0.4 * s, (0.1, 0.1, 0.1, 1), n=12, solid=False)
    box(m, "flat", x - 3.0 * s, y - 0.25 * s, 4.1 * s, x + 3.0 * s, y + 0.25 * s, 4.45 * s, r, solid=False)          # nuki
    f = m.M("flat"); n = 10                                                                                    # kasagi: curved top beam
    for k in range(n):
        u0, u1 = -1 + 2 * k / n, -1 + 2 * (k + 1) / n
        x0_, x1_ = x + u0 * 3.8 * s, x + u1 * 3.8 * s; z0_, z1_ = (5.25 + 0.35 * u0 * u0) * s, (5.25 + 0.35 * u1 * u1) * s
        for (ya, yb, za, zb) in ((y - 0.35 * s, y + 0.35 * s, 0, 0),):
            f.quad((x0_, ya, z0_), (x1_, ya, z1_), (x1_, ya, z1_ + 0.4 * s), (x0_, ya, z0_ + 0.4 * s), (0.1, 0.1, 0.1, 1))
            f.quad((x1_, yb, z1_), (x0_, yb, z0_), (x0_, yb, z0_ + 0.4 * s), (x1_, yb, z1_ + 0.4 * s), (0.1, 0.1, 0.1, 1))
            f.quad((x0_, ya, z0_ + 0.4 * s), (x1_, ya, z1_ + 0.4 * s), (x1_, yb, z1_ + 0.4 * s), (x0_, yb, z0_ + 0.4 * s), (0.1, 0.1, 0.1, 1))
            f.quad((x1_, ya, z1_), (x0_, ya, z0_), (x0_, yb, z0_), (x1_, yb, z1_), r)
    return "a torii gate"


def a_torii(m, o, rng):
    torii(m, 0, 0, 1.3 * o["s"]); return "a torii gate"


def a_castle(m, o, rng):
    b = 16 * o["s"]
    # sloped stone base (frustum box)
    f = m.M("flat"); hb = 6.0 * o["s"]; t = 2.0
    P0 = [(-b / 2 - t, -b / 2 - t), (b / 2 + t, -b / 2 - t), (b / 2 + t, b / 2 + t), (-b / 2 - t, b / 2 + t)]
    P1 = [(-b / 2, -b / 2), (b / 2, -b / 2), (b / 2, b / 2), (-b / 2, b / 2)]
    for k in range(4):
        j = (k + 1) % 4
        f.quad((P0[k][0], P0[k][1], 0), (P0[j][0], P0[j][1], 0), (P1[j][0], P1[j][1], hb), (P1[k][0], P1[k][1], hb), STONE)
    m.solid_box(-b / 2 - t * 0.5, -b / 2 - t * 0.5, b / 2 + t * 0.5, b / 2 + t * 0.5, 0, hb)
    z = hb
    for k, s in enumerate((1.0, 0.8, 0.6, 0.42)):
        hw = b / 2 * s; hh = 4.2 * o["s"]
        box(m, "flat", -hw, -hw, z, hw, hw, z + hh, PLASTER)
        for wx in range(int(-hw) + 1, int(hw), 2):
            box(m, "flat", wx, -hw - 0.04, z + hh * 0.45, wx + 0.8, -hw + 0.02, z + hh * 0.75, (0.16, 0.16, 0.18, 1), solid=False)
        curved_roof(m, 0, 0, hw, hw, z + hh, 2.2 * o["s"], (0.3, 0.42, 0.42, 1), over=1.8 * s, lift=0.7, top=0.6 if k < 3 else 0.2)
        z += hh + 2.2 * o["s"] * 0.55
    for sx in (-1, 1):      # golden shachihoko on the ridge
        ellipsoid(m, "flat", sx * b * 0.08, 0, z + 0.2, 0.25, 0.45, 0.6, GOLD, n=10, rings=6)
    return "a Japanese castle"


def a_shop(m, o, rng):
    w, d, h = 12 * o["s"], 10 * o["s"], 4.4
    box(m, "facade5", -w / 2, -d / 2, 0, w / 2, d / 2, h, (1, 1, 1, 1))
    box(m, "shopfront", -w / 2 - 0.04, -d / 2 - 0.04, 0, w / 2 + 0.04, -d / 2 + 0.2, 3.2, (1, 1, 1, 1), solid=False, top=False)
    stripe = rng.choice([(0.1, 0.55, 0.3, 1), (0.15, 0.35, 0.75, 1), (0.85, 0.3, 0.15, 1)])
    box(m, "flat", -w / 2 - 0.05, -d / 2 - 0.1, 3.2, w / 2 + 0.05, -d / 2 + 0.1, 3.6, stripe, solid=False)
    box(m, "flat", -w / 2 - 0.05, -d / 2 - 0.1, 3.6, w / 2 + 0.05, -d / 2 + 0.1, 3.8, (0.95, 0.95, 0.95, 1), solid=False)
    sign(m, o["title"] if o["title"] else "SHOP", 0, -d / 2 - 0.15, 3.85, min(w - 1, 1.5 + 0.75 * len(o["title"] or "SHOP")), 0.55, col=stripe, fg=(1, 1, 1, 1))
    roof_kit(m, -w / 2, -d / 2, w / 2, d / 2, h, rng)
    if o["kind"] == "konbini": return "a convenience store"
    t = (o["title"] or "").lower()
    if not t or t in ("shop", "store"): return "a shop"
    return "a " + t if re.search(r"shop|store|cafe|restaurant|bakery", t) else "a %s shop" % t


def a_lighthouse(m, o, rng):
    h = 22 * o["s"]; r0, r1 = 3.0 * o["s"], 1.9 * o["s"]; n = 6
    box(m, "flat", -4.5, -4.5, 0, 4.5, 4.5, 0.6, STONE)
    for k in range(n):
        z0, z1 = 0.6 + (h - 0.6) * k / n, 0.6 + (h - 0.6) * (k + 1) / n
        ra, rb = r0 + (r1 - r0) * k / n, r0 + (r1 - r0) * (k + 1) / n
        frustum(m, "flat", 0, 0, z0, z1, ra, rb, (0.9, 0.12, 0.1, 1) if k % 2 else (0.96, 0.96, 0.94, 1), n=24, cap=False)
    frustum(m, "flat", 0, 0, h, h + 0.3, r1 + 0.8, r1 + 0.8, (0.2, 0.2, 0.22, 1), n=24)                    # gallery
    frustum(m, "glass", 0, 0, h + 0.3, h + 2.6, r1 * 0.75, r1 * 0.75, (0.55, 0.75, 0.85, 1), n=16, solid=False, cap=False)
    dome(m, "flat", 0, 0, h + 2.6, r1 * 0.85, (0.15, 0.17, 0.2, 1), n=16, rings=5, solid=False)
    return "a lighthouse"


def a_dome(m, o, rng):
    r = 9 * o["s"]
    frustum(m, "facade3", 0, 0, 0, 6, r, r, (1, 1, 1, 1), n=28, cap=False)
    dome(m, "flat", 0, 0, 6, r, (0.82, 0.84, 0.86, 1), n=28, rings=9)
    box(m, "flat", -1.5, -r - 0.8, 0, 1.5, -r + 0.5, 3.0, (0.2, 0.2, 0.24, 1), solid=False)
    return "an observatory" if o["kind"] == "observatory" else "a domed hall"


def a_stadium(m, o, rng):
    R = 30 * o["s"]
    frustum(m, "facade2", 0, 0, 0, 14 * o["s"], R, R * 1.06, (1, 1, 1, 1), n=40, cap=False)
    f = m.M("flat")
    frustum(m, "flat", 0, 0, 14 * o["s"], 14.6 * o["s"], R * 1.1, R * 1.1, (0.9, 0.9, 0.92, 1), n=40, solid=False, cap=False)
    pts = ring_pts(0, 0, R * 0.7, 40)
    for k in range(40):
        j = (k + 1) % 40
        f.quad((pts[k][0], pts[k][1], 0.3), (pts[j][0], pts[j][1], 0.3), (0, 0, 0.3), (0, 0, 0.3), (0.2, 0.55, 0.22, 1))
    return "a stadium"


def a_pyramid(m, o, rng):
    hb = 14 * o["s"]; h = 18 * o["s"]; f = m.M("flat"); c = (0.86, 0.74, 0.52, 1)
    P = [(-hb, -hb), (hb, -hb), (hb, hb), (-hb, hb)]
    for k in range(4):
        j = (k + 1) % 4
        f.quad((P[k][0], P[k][1], 0), (P[j][0], P[j][1], 0), (0, 0, h), (0, 0, h), c)
    m.solid_pyr(0, 0, hb, hb, 0, h)
    return "a pyramid"


def a_bridge(m, o, rng):
    L, w, h = 24 * o["s"], 4.0, 4.0
    box(m, "flat", -w / 2, -L / 2, h - 0.5, w / 2, L / 2, h, (0.6, 0.6, 0.62, 1), solid=False); m.solid_box(-w / 2, -L / 2, w / 2, L / 2, 0, h)
    for sx in (-1, 1):
        box(m, "flat", sx * w / 2 - 0.1, -L / 2, h, sx * w / 2 + 0.1, L / 2, h + 1.0, (0.35, 0.36, 0.4, 1))
    for y in (-L / 4, L / 4):
        frustum(m, "flat", 0, y, 0, h - 0.5, 0.9, 0.9, STONE, n=14)
    for e in (-1, 1):       # ramps / steps at both ends
        for k in range(14):
            z = h * (k + 1) / 14
            yy0 = e * (L / 2 + (14 - k) * 0.55); yy1 = e * (L / 2 + (13 - k) * 0.55)
            box(m, "flat", -w / 2, min(yy0, yy1), 0, w / 2, max(yy0, yy1), z, (0.62, 0.62, 0.64, 1))
    return "a footbridge"


def a_stairs(m, o, rng):
    n = 14 if o["big"] else 9; w = 3.4
    for k in range(n):
        box(m, "flat", -w / 2, -n * 0.25 + k * 0.5, 0, w / 2, -n * 0.25 + (k + 1) * 0.5, 0.5 * (k + 1), (0.7, 0.7, 0.72, 1) if k % 2 else (0.64, 0.64, 0.67, 1))
    box(m, "flat", -w / 2, n * 0.25, 0, w / 2, n * 0.25 + 3.0, 0.5 * n, (0.6, 0.6, 0.63, 1))
    for sx in (-1, 1):
        box(m, "flat", sx * w / 2 - 0.06, -n * 0.25, 0.5 * n + 0.0, sx * w / 2 + 0.06, n * 0.25 + 3.0, 0.5 * n + 1.0, (0.3, 0.3, 0.34, 1), solid=False)
    return "stairs up to a %d m deck" % int(0.5 * n)


def a_statue(m, o, rng):
    s = 1.1 * (1.5 if o["big"] else 1.0) * (0.7 if o["small"] else 1.0)
    box(m, "flat", -2.4 * s, -2.4 * s, 0, 2.4 * s, 2.4 * s, 1.6 * s, STONE)
    c = (0.62, 0.66, 0.66, 1) if "bronze" not in o["text"] else (0.55, 0.4, 0.22, 1)
    if o["cat"]:
        ellipsoid(m, "flat", 0, 0.3 * s, 3.4 * s, 1.5 * s, 1.8 * s, 1.9 * s, c)             # body
        ellipsoid(m, "flat", 0, -0.9 * s, 5.6 * s, 1.15 * s, 1.0 * s, 1.0 * s, c)           # head
        for sx in (-1, 1):
            frustum(m, "flat", sx * 0.6 * s, -0.9 * s, 6.3 * s, 7.3 * s, 0.38 * s, 0.02, c, n=10, solid=False)   # ears
            ellipsoid(m, "flat", sx * 0.7 * s, -1.4 * s, 1.9 * s, 0.4 * s, 0.6 * s, 0.35 * s, c)               # paws
        f = m.M("flat")
        for k in range(8):      # tail curling round
            a0, a1 = 0.3 + k * 0.3, 0.3 + (k + 1) * 0.3
            ellipsoid(m, "flat", 1.5 * s * math.cos(a0), 1.6 * s * math.sin(a0) + 0.6 * s, 1.9 * s, 0.25 * s, 0.25 * s, 0.25 * s, c, n=8, rings=5)
        m.solid_cyl(0, 0, 1.9 * s, 1.6 * s, 7.0 * s); label = "a giant cat statue"
    else:
        ellipsoid(m, "flat", 0, 0, 3.6 * s, 0.9 * s, 0.6 * s, 1.5 * s, c)
        ellipsoid(m, "flat", 0, 0, 5.6 * s, 0.55 * s, 0.55 * s, 0.6 * s, c)
        for sx in (-1, 1):
            frustum(m, "flat", sx * 0.4 * s, 0, 1.6 * s, 2.6 * s, 0.32 * s, 0.38 * s, c, n=10, solid=False)
            ellipsoid(m, "flat", sx * 1.1 * s, 0, 4.0 * s, 0.28 * s, 0.28 * s, 1.0 * s, c, n=10, rings=6)
        m.solid_cyl(0, 0, 1.0 * s, 1.6 * s, 6.2 * s); label = "a statue"
    return label


def a_park(m, o, rng):
    n = 5 if not o["big"] else 9
    m.M("flat").quad((-9, -9, 0.06), (9, -9, 0.06), (9, 9, 0.06), (-9, 9, 0.06), (0.22, 0.45, 0.22, 1))
    for k in range(n):
        a = rng.uniform(0, 6.28); d = rng.uniform(2, 7.5)
        tree(m, math.cos(a) * d, math.sin(a) * d, rng.uniform(0.8, 1.2), pink=o["sakura"] or rng.random() < 0.25, rng=rng)
    box(m, "flat", -1.0, -8.2, 0.4, 1.0, -7.7, 0.5, (0.45, 0.3, 0.2, 1), solid=False)
    return "a little park" if not o["sakura"] else "a sakura park"


def a_tree(m, o, rng):
    tree(m, 0, 0, 1.6 if o["big"] else 1.15, pink=o["sakura"], rng=rng); return "a cherry tree" if o["sakura"] else "a tree"


def a_fountain(m, o, rng):
    frustum(m, "flat", 0, 0, 0, 0.7, 4.0, 4.0, STONE, n=28)
    frustum(m, "flat", 0, 0, 0.7, 0.72, 3.6, 3.6, (0.3, 0.5, 0.65, 1), n=28, solid=False)
    frustum(m, "flat", 0, 0, 0.7, 2.4, 0.5, 0.35, STONE, n=12)
    frustum(m, "flat", 0, 0, 2.4, 2.6, 1.5, 1.5, STONE, n=20)
    return "a fountain"


def a_wall(m, o, rng):
    L = 20 * o["s"]; box(m, "flat", -L / 2, -0.4, 0, L / 2, 0.4, 3.0 * o["s"], STONE)
    for x in range(int(-L / 2), int(L / 2), 2):
        box(m, "flat", x, -0.45, 3.0 * o["s"], x + 1, 0.45, 3.6 * o["s"], STONE)
    return "a stone wall"


def a_tower(m, o, rng):
    """a red-and-white steel lattice observation tower (Shinko Tower), or a stone watchtower for castle-ish words"""
    if re.search(r"watch|stone|castle|medieval|wizard", o["text"]):
        r = 3.2 * o["s"]; h = 16 * o["s"] * (1.6 if o["tall"] else 1.0)
        frustum(m, "flat", 0, 0, 0, h, r, r * 0.9, STONE, n=24)
        frustum(m, "flat", 0, 0, h, h + 1.2, r * 1.15, r * 1.15, (0.5, 0.49, 0.47, 1), n=24)
        frustum(m, "flat", 0, 0, h + 1.2, h + 6, r * 1.2, 0.05, (0.3, 0.2, 0.18, 1), n=24, solid=False)
        return "a stone tower"
    s = o["s"] * (1.4 if o["tall"] else 1.0); H = 48 * s; B = 9 * s
    RED, WHITE = (0.88, 0.25, 0.12, 1), (0.95, 0.95, 0.93, 1)
    def half(z): return B * (1 - z / H) ** 1.6 + 0.6 * s
    levels = 12
    for k in range(levels):
        z0, z1 = H * k / levels, H * (k + 1) / levels; c = RED if k % 2 == 0 else WHITE; h0, h1 = half(z0), half(z1)
        for sx in (-1, 1):
            for sy in (-1, 1):
                tube(m, (sx * h0, sy * h0, z0), (sx * h1, sy * h1, z1), 0.35 * s * (1 - k / 16), 0.32 * s * (1 - k / 16), c, 8)   # legs
        for (ax, ay, bx, by) in ((-1, -1, 1, -1), (1, -1, 1, 1), (1, 1, -1, 1), (-1, 1, -1, -1)):     # X bracing on all faces
            tube(m, (ax * h0, ay * h0, z0), (bx * h1, by * h1, z1), 0.12 * s, 0.12 * s, c, 6, caps=False)
            tube(m, (bx * h0, by * h0, z0), (ax * h1, ay * h1, z1), 0.12 * s, 0.12 * s, c, 6, caps=False)
            tube(m, (ax * h1, ay * h1, z1), (bx * h1, by * h1, z1), 0.14 * s, 0.14 * s, c, 6, caps=False)
    zd = H * 0.42; hd = half(zd) + 1.2 * s
    box(m, "flat", -hd, -hd, zd, hd, hd, zd + 4 * s, (0.92, 0.92, 0.9, 1), solid=False)                         # observation deck
    box(m, "flat", -hd - 0.05, -hd - 0.05, zd + 1.2 * s, hd + 0.05, hd + 0.05, zd + 3.3 * s, (0.2, 0.28, 0.36, 1), solid=False)
    frustum(m, "flat", 0, 0, H, H + 12 * s, 0.5 * s, 0.1 * s, WHITE, n=8, solid=False)                            # antenna
    for k in range(3): frustum(m, "flat", 0, 0, H + 2 * s + k * 3.5 * s, H + 3 * s + k * 3.5 * s, 0.55 * s, 0.55 * s, RED, n=8, solid=False)
    box(m, "facade5", -B - 1, -B - 1, 0, B + 1, -B + 3, 4.0, (1, 1, 1, 1), solid=False)                         # entrance hall
    sign(m, "SHINKO TOWER", 0, -B - 1.2, 4.1, 6.5, 0.9)
    for sx in (-1, 1):
        for sy in (-1, 1): m.solid_cyl(sx * (B + 0.6 * s), sy * (B + 0.6 * s), 1.2 * s, 0, 6)
    m.solid_box(-B - 1, -B - 1, B + 1, -B + 3, 0, 4.0)
    return "an observation tower"


def a_invent(m, o, rng):
    """unknown words: an invented city building - random massing from the city kit, with the word on its sign"""
    w = rng.uniform(10, 16); d = rng.uniform(9, 14); h = rng.uniform(10, 40) * (1.5 if o["tall"] else 1.0)
    fac = rng.choice(["facade1", "facade2", "facade3", "facade4", "facade6"])
    box(m, fac, -w / 2, -d / 2, 0, w / 2, d / 2, h, (1, 1, 1, 1))
    if rng.random() < 0.6:
        box(m, fac, -w / 2 + 2, -d / 2 + 2, h, w / 2 - 2, d / 2 - 2, h + rng.uniform(5, 15), (1, 1, 1, 1))
    else:
        dome(m, "flat", 0, 0, h, min(w, d) * 0.4, rng.choice([(0.4, 0.6, 0.7, 1), (0.8, 0.8, 0.82, 1), GOLD]))
    box(m, "shopfront", -w / 2 - 0.05, -d / 2 - 0.05, 0, w / 2 + 0.05, -d / 2 + 0.25, 4.0, (1, 1, 1, 1), solid=False, top=False)
    sign(m, o["title"] or "?", 0, -d / 2 - 0.3, 4.6, min(w - 1, 1.5 + 0.8 * len(o["title"] or "?")), 1.4)
    roof_kit(m, -w / 2, -d / 2, w / 2, d / 2, h, rng)
    return "a custom building (%s)" % o["title"].lower() if o["title"] else "a custom building"


KINDS = {
    "house": a_house, "home": a_house, "cottage": a_house, "hut": a_house, "cabin": a_house, "villa": a_house,
    "apartment": a_apartment, "apartments": a_apartment, "flats": a_apartment, "mansion": a_apartment, "hotel": a_apartment,
    "skyscraper": a_skyscraper, "office": a_skyscraper, "highrise": a_skyscraper, "building": a_skyscraper,
    "pagoda": a_pagoda, "temple": a_temple, "shrine": a_temple, "torii": a_torii, "gate": a_torii,
    "castle": a_castle, "palace": a_castle, "fort": a_castle,
    "shop": a_shop, "store": a_shop, "konbini": a_shop, "cafe": a_shop, "restaurant": a_shop, "ramen": a_shop, "bakery": a_shop,
    "lighthouse": a_lighthouse, "dome": a_dome, "observatory": a_dome, "planetarium": a_dome, "museum": a_dome,
    "stadium": a_stadium, "arena": a_stadium, "pyramid": a_pyramid, "bridge": a_bridge,
    "stairs": a_stairs, "staircase": a_stairs, "steps": a_stairs, "ramp": a_stairs,
    "statue": a_statue, "monument": a_statue, "cat": a_statue, "park": a_park, "garden": a_park, "forest": a_park,
    "tree": a_tree, "sakura": a_tree, "fountain": a_fountain, "wall": a_wall, "tower": a_tower, "watchtower": a_tower,
}
NAMES = {a_house: "house", a_apartment: "apartment", a_skyscraper: "skyscraper", a_pagoda: "pagoda", a_temple: "temple"}


def plan(text):
    t0 = (text or "").strip() or "house"
    t = t0.lower()
    try:
        import fs_vinebuild as V
        t = V.correct_typos(t)
    except Exception:
        pass
    words = re.findall(r"[a-z]+", t)
    fn = None; kind = None
    for w in words:                                         # exact keyword
        if w in KINDS: fn = KINDS[w]; kind = w
    if fn is None:                                          # fuzzy keyword ("pyrmid" -> pyramid)
        for w in words:
            mm = difflib.get_close_matches(w, list(KINDS), n=1, cutoff=0.78)
            if mm: fn = KINDS[mm[0]]; kind = mm[0]
    animal_ = None
    for w in words:                                         # an animal anywhere in the text -> that animal (as a statue)
        a_ = w if w in ANIMALS else (w[:-1] if w.endswith("s") and w[:-1] in ANIMALS else None)
        if a_ is None and len(w) > 3:
            mm = difflib.get_close_matches(w, list(ANIMALS), n=1, cutoff=0.8); a_ = mm[0] if mm else None
        if a_: animal_ = a_
    if animal_ and fn not in (a_park, a_shop, a_house, a_skyscraper, a_apartment): fn = a_animal; kind = animal_
    if re.search(r"\b(horse|horses|pony|stallion|mare|steed)\b", t): fn = a_horse; kind = "horse"
    o = dict(text=t, kind=kind or "invent", s=1.0, big=bool(re.search(r"\b(big|huge|giant|large|massive|enormous)\b", t)),
             small=bool(re.search(r"\b(small|tiny|little|mini)\b", t)), tall=bool(re.search(r"\b(tall|high|towering)\b", t)),
             cat="cat" in words, animal=animal_ or "cat", sakura=bool(re.search(r"sakura|cherry|pink", t)))
    if o["big"]: o["s"] = 1.35
    if o["small"]: o["s"] = 0.75
    title = " ".join(w for w in re.findall(r"[A-Za-z0-9']+", t0) if w.lower() not in ("a", "an", "the", "big", "small", "tall", "tiny", "giant", "huge", "little"))
    o["title"] = title.upper()[:18]
    return fn or a_invent, o


def generate(text, seed=None):
    fn, o = plan(text)
    rng = random.Random(seed if seed is not None else hash(text) & 0xffff)
    m = Model(); label = fn(m, o, rng)
    return m, label


# ================================================================ v1.0.4: recognisable animals, vehicles and objects
def tube(m, p0, p1, r0, r1, col, n=14, mat="flat", caps=True):
    """smooth tapered cylinder between two arbitrary points (legs, tails, fuselages, wheels)"""
    ax = [p1[i] - p0[i] for i in range(3)]; L = math.sqrt(sum(a * a for a in ax)) or 1e-6; ax = [a / L for a in ax]
    up = (0, 0, 1) if abs(ax[2]) < 0.9 else (1, 0, 0)
    u = (ax[1] * up[2] - ax[2] * up[1], ax[2] * up[0] - ax[0] * up[2], ax[0] * up[1] - ax[1] * up[0]); ul = math.sqrt(sum(a * a for a in u)); u = [a / ul for a in u]
    v = (ax[1] * u[2] - ax[2] * u[1], ax[2] * u[0] - ax[0] * u[2], ax[0] * u[1] - ax[1] * u[0])
    def ring(p, r): return [tuple(p[i] + r * (math.cos(2 * math.pi * k / n) * u[i] + math.sin(2 * math.pi * k / n) * v[i]) for i in range(3)) for k in range(n)]
    A, B = ring(p0, r0), ring(p1, r1); b = m.M(mat)
    for k in range(n):
        j = (k + 1) % n; b.quad(A[k], A[j], B[j], B[k], col)
    if caps:
        for k in range(n):
            j = (k + 1) % n
            b.quad(B[k], B[j], tuple(p1), tuple(p1), col); b.quad(A[j], A[k], tuple(p0), tuple(p0), col)


def cone(m, base, tip, r, col, n=12): tube(m, base, tip, r, 0.001, col, n)


def plinth(m, hx, hy, h=1.0, plate=None):
    box(m, "flat", -hx, -hy, 0, hx, hy, h, STONE)
    box(m, "flat", -hx - 0.15, -hy - 0.15, 0, hx + 0.15, hy + 0.15, 0.25, (0.48, 0.47, 0.45, 1), solid=False)
    if plate: sign(m, plate, 0, -hy - 0.02, h * 0.3, min(2 * hx - 0.3, 0.6 + 0.32 * len(plate)), h * 0.42, col=(0.55, 0.42, 0.2, 1), fg=(0.1, 0.08, 0.05, 1))


def eyes(m, x, y, z, sep, r, iris=(0.35, 0.65, 0.25, 1)):
    for sx in (-1, 1):
        ellipsoid(m, "flat", x + sx * sep, y, z, r, r * 0.6, r, (0.96, 0.95, 0.9, 1), n=12, rings=8)
        ellipsoid(m, "flat", x + sx * sep, y - r * 0.45, z, r * 0.62, r * 0.3, r * 0.75, iris, n=12, rings=8)
        ellipsoid(m, "flat", x + sx * sep, y - r * 0.62, z, r * 0.22, r * 0.18, r * 0.55, (0.03, 0.03, 0.03, 1), n=8, rings=6)


ANIMALS = {   # colour, accent, ear style, snout length, body length factor, tail style
    "cat": ((0.93, 0.56, 0.22, 1), (0.98, 0.93, 0.85, 1), "point", 0.0, 1.0, "curl"),
    "kitten": ((0.6, 0.6, 0.62, 1), (0.98, 0.96, 0.94, 1), "point", 0.0, 1.0, "curl"),
    "dog": ((0.62, 0.42, 0.22, 1), (0.95, 0.88, 0.75, 1), "flop", 0.55, 1.0, "up"),
    "puppy": ((0.85, 0.7, 0.45, 1), (0.98, 0.94, 0.85, 1), "flop", 0.45, 1.0, "up"),
    "fox": ((0.9, 0.45, 0.15, 1), (0.98, 0.97, 0.95, 1), "point", 0.55, 1.0, "bushy"),
    "wolf": ((0.5, 0.5, 0.52, 1), (0.85, 0.85, 0.85, 1), "point", 0.6, 1.0, "bushy"),
    "bear": ((0.36, 0.24, 0.15, 1), (0.55, 0.42, 0.3, 1), "round", 0.35, 1.1, "stub"),
    "panda": ((0.96, 0.96, 0.94, 1), (0.08, 0.08, 0.08, 1), "round", 0.25, 1.1, "stub"),
    "rabbit": ((0.92, 0.9, 0.88, 1), (0.98, 0.8, 0.82, 1), "long", 0.15, 0.9, "puff"),
    "bunny": ((0.8, 0.7, 0.6, 1), (0.98, 0.85, 0.85, 1), "long", 0.15, 0.9, "puff"),
    "pig": ((0.96, 0.7, 0.72, 1), (0.9, 0.55, 0.6, 1), "flop", 0.3, 1.2, "curl"),
    "cow": ((0.96, 0.96, 0.94, 1), (0.1, 0.1, 0.1, 1), "side", 0.55, 1.4, "rope"),
    "horse": ((0.5, 0.32, 0.18, 1), (0.15, 0.1, 0.08, 1), "point", 0.8, 1.5, "rope"),
    "lion": ((0.85, 0.65, 0.32, 1), (0.6, 0.35, 0.12, 1), "round", 0.4, 1.3, "rope"),
    "tiger": ((0.95, 0.55, 0.15, 1), (0.08, 0.08, 0.08, 1), "round", 0.4, 1.3, "rope"),
    "mouse": ((0.6, 0.6, 0.62, 1), (0.95, 0.75, 0.78, 1), "big", 0.35, 0.9, "rope"),
    "elephant": ((0.55, 0.56, 0.58, 1), (0.45, 0.46, 0.48, 1), "fan", 0.0, 1.6, "rope"),
    "giraffe": ((0.92, 0.75, 0.35, 1), (0.55, 0.32, 0.15, 1), "point", 0.6, 1.3, "rope"),
}


def animal(m, kind, s, rng, sitting=True):
    col, acc, ear, snout, blen, tail = ANIMALS[kind]
    dark = (col[0] * 0.55, col[1] * 0.5, col[2] * 0.5, 1)
    def E(x, y, z, rx, ry, rz, c=col, n=24, r=14): ellipsoid(m, "flat", x * s, y * s, z * s, rx * s, ry * s, rz * s, c, n, r)
    def T(a, b, r0, r1, c=col, n=12): tube(m, tuple(v * s for v in a), tuple(v * s for v in b), r0 * s, r1 * s, c, n)
    z0 = 1.0 / s                                    # stand on the plinth (1 m)
    if sitting and kind in ("cat", "kitten", "dog", "puppy", "fox", "wolf", "rabbit", "bunny", "mouse", "lion", "tiger"):
        E(0, 0.35, z0 + 0.9, 1.15, 1.3, 0.95)                                          # haunches
        for sx in (-1, 1): E(sx * 0.75, 0.15, z0 + 0.75, 0.42, 0.95, 0.7)              # thighs
        E(0, -0.15, z0 + 2.0, 0.85, 0.8, 1.35)                                          # chest / body upright
        E(0, -0.62, z0 + 1.9, 0.52, 0.3, 0.9, acc)                                      # bib
        for sx in (-1, 1):
            T((sx * 0.38, -0.55, z0 + 1.9), (sx * 0.4, -0.75, z0 + 0.15), 0.22, 0.2)    # front legs
            E(sx * 0.4, -0.95, z0 + 0.14, 0.27, 0.38, 0.17, acc)                       # paws
            E(sx * 0.95, -0.35, z0 + 0.14, 0.3, 0.45, 0.17, acc)                       # back feet
        hz = z0 + 3.55; hy = -0.45
    else:
        L = 1.6 * blen; leg = 1.5 if kind not in ("giraffe", "horse") else 2.2
        E(0, 0, z0 + leg + 0.5, 0.9, L, 0.85)                                           # body
        for sx in (-1, 1):
            for sy in (-1, 1):
                T((sx * 0.5, sy * L * 0.65, z0 + leg + 0.4), (sx * 0.52, sy * L * 0.68, z0 + 0.1), 0.3, 0.24)
                E(sx * 0.52, sy * L * 0.68 - 0.08, z0 + 0.1, 0.3, 0.38, 0.14, dark)      # hooves / paws
        nz = z0 + leg + (3.2 if kind == "giraffe" else 1.3)
        T((0, -L * 0.8, z0 + leg + 0.6), (0, -L * 0.95 - 0.2, nz), 0.45, 0.38)          # neck
        hz = nz + 0.35; hy = -L * 0.95 - 0.35
        if kind == "cow":
            for k in range(5): E(rng.uniform(-0.6, 0.6), rng.uniform(-L * 0.7, L * 0.7), z0 + leg + 0.6 + rng.uniform(0, 0.5), 0.45, 0.6, 0.4, acc, 10, 6)
        if kind == "tiger":
            for k in range(6): E(0, -L * 0.7 + k * L * 0.28, z0 + leg + 0.5, 0.92, 0.07, 0.87, acc, 12, 8)
        if kind == "giraffe":
            for k in range(14): E(rng.choice((-1, 1)) * 0.85, rng.uniform(-L, L), z0 + leg + rng.uniform(0.2, 0.9), 0.08, 0.3, 0.25, acc, 8, 5)
    # head + face
    E(0, hy, hz, 0.95, 0.85, 0.82)
    if kind == "lion": E(0, hy + 0.25, hz - 0.05, 1.45, 0.7, 1.35, acc, 18, 10)                       # mane
    if kind == "panda":
        for sx in (-1, 1): E(sx * 0.33, hy - 0.72, hz + 0.12, 0.22, 0.1, 0.27, acc, 10, 6)
    mz = hz - 0.28; my = hy - 0.7 - snout * 0.7
    if snout > 0.1: T((0, hy - 0.55, hz - 0.15), (0, my, mz), 0.42, 0.32, col)
    E(0, my - 0.05, mz, 0.42, 0.3, 0.3, acc if kind not in ("panda", "cow", "tiger", "horse") else col)  # muzzle
    E(0, my - 0.32, mz + 0.1, 0.15, 0.1, 0.11, (0.85, 0.45, 0.5, 1) if kind in ("cat", "kitten", "pig", "mouse", "rabbit", "bunny") else (0.08, 0.06, 0.06, 1), 10, 6)  # nose
    eyes(m, 0, (hy - 0.68) * s, (hz + 0.15) * s, 0.36 * s, 0.17 * s, (0.4, 0.75, 0.25, 1) if kind in ("cat", "kitten", "tiger", "lion", "fox") else (0.35, 0.22, 0.1, 1))
    if kind in ("cat", "kitten", "tiger", "lion", "mouse", "rabbit", "bunny", "fox"):           # whiskers
        for sx in (-1, 1):
            for dz in (-0.06, 0.06):
                T((sx * 0.25, my - 0.18, mz + dz), (sx * 1.15, my - 0.05, mz + dz * 2.5 + 0.05), 0.02, 0.01, (0.95, 0.95, 0.95, 1), 5)
    if kind == "dog" or kind == "puppy": E(0, my - 0.15, mz - 0.3, 0.16, 0.12, 0.06, (0.9, 0.35, 0.4, 1), 10, 6)   # tongue
    if kind == "elephant":
        pts = [(0, hy - 0.8, hz - 0.1), (0, hy - 1.2, hz - 0.9), (0, hy - 1.3, hz - 1.8), (0, hy - 1.6, hz - 2.3)]
        for a, b in zip(pts, pts[1:]): T(a, b, 0.32, 0.24)
        for sx in (-1, 1): T((sx * 0.35, hy - 0.6, hz - 0.5), (sx * 0.5, hy - 1.4, hz - 0.2), 0.12, 0.03, (0.96, 0.94, 0.88, 1), 8)
    if kind == "pig": E(0, my - 0.3, mz, 0.3, 0.12, 0.24, acc)
    # ears
    for sx in (-1, 1):
        ex = sx * 0.55
        if ear == "point":
            cone(m, (ex * s, (hy + 0.05) * s, (hz + 0.55) * s), (sx * 0.72 * s, (hy + 0.05) * s, (hz + 1.35) * s), 0.36 * s, col, 4)
            cone(m, (ex * s, (hy - 0.08) * s, (hz + 0.6) * s), (sx * 0.7 * s, (hy - 0.05) * s, (hz + 1.15) * s), 0.22 * s, (0.95, 0.7, 0.72, 1), 4)
        elif ear == "flop": E(sx * 0.85, hy + 0.1, hz - 0.15, 0.25, 0.4, 0.7, dark)
        elif ear == "round": E(ex, hy + 0.1, hz + 0.7, 0.3, 0.16, 0.3, acc if kind == "panda" else col)
        elif ear == "long":
            E(sx * 0.32, hy + 0.1, hz + 1.5, 0.22, 0.12, 0.85); E(sx * 0.32, hy - 0.02, hz + 1.5, 0.13, 0.06, 0.65, acc)
        elif ear == "big": E(sx * 0.75, hy + 0.1, hz + 0.75, 0.55, 0.1, 0.55, acc)
        elif ear == "side": T((sx * 0.7, hy + 0.1, hz + 0.3), (sx * 1.25, hy + 0.2, hz + 0.45), 0.18, 0.1, col, 8); cone(m, (sx * 0.4 * s, hy * s, (hz + 0.7) * s), (sx * 0.65 * s, hy * s, (hz + 1.2) * s), 0.12 * s, (0.95, 0.92, 0.82, 1), 8)
        elif ear == "fan": E(sx * 1.05, hy + 0.3, hz - 0.1, 0.12, 0.8, 0.95)
    if kind == "horse":
        for k in range(6): E(0, hy + 0.55 + k * 0.35, hz - 0.2 - k * 0.3, 0.14, 0.25, 0.4, acc, 8, 5)       # mane
    # tail
    if sitting and tail in ("curl", "bushy", "rope", "up"):
        pts = [(0.4 + 1.25 * math.cos(a), 0.6 + 1.1 * math.sin(a), z0 + 0.25 + 0.05 * k) for k, a in enumerate([1.8 - 0.42 * k for k in range(10)])]
        if tail == "up": pts = [(0, 1.2, z0 + 0.8), (0, 1.75, z0 + 1.5), (0.1, 1.9, z0 + 2.3), (0.2, 1.7, z0 + 2.9)]
    else:
        by = (1.6 * blen if not sitting else 1.2); bz = z0 + (1.5 if kind not in ("giraffe", "horse") else 2.2) + 0.7
        pts = [(0, by, bz), (0, by + 0.6, bz - 0.4), (0, by + 0.8, bz - 1.2), (0, by + 0.85, bz - 1.8)]
        if tail == "curl": pts = [(0, by, bz), (0.3, by + 0.4, bz + 0.2), (0, by + 0.5, bz + 0.5), (-0.2, by + 0.3, bz + 0.3)]
    if tail in ("stub", "puff"):
        E(0, (1.45 if sitting else 1.6 * blen + 0.1), z0 + (0.9 if sitting else 2.1), 0.35, 0.3, 0.3, acc if tail == "puff" else col, 10, 6)
    else:
        rr = 0.3 if tail != "bushy" else 0.45
        for k, (a, b) in enumerate(zip(pts, pts[1:])):
            r0 = rr * (1 - 0.5 * k / len(pts)); r1 = rr * (1 - 0.5 * (k + 1) / len(pts))
            c = (acc if (kind == "fox" and k >= len(pts) - 3) or (kind == "tiger" and k % 2) else col)
            T(a, b, r0, r1, c, 10); E(b[0], b[1], b[2], r1, r1, r1, c, 10, 6)
        if kind in ("lion", "cow"): E(pts[-1][0], pts[-1][1], pts[-1][2], 0.25, 0.25, 0.35, acc, 10, 6)


def a_animal(m, o, rng):
    kind = o["animal"]; s = 1.0 * (1.6 if o["big"] else 1.0) * (0.6 if o["small"] else 1.0)
    sitting = kind in ("cat", "kitten", "dog", "puppy", "fox", "wolf", "rabbit", "bunny", "mouse") or ("sit" in o["text"])
    hx, hy = (2.0 * s, 2.4 * s) if sitting else (1.8 * s, 3.4 * s * ANIMALS[kind][4])
    plinth(m, max(hx, 1.6), max(hy, 1.6), 1.0, kind.upper())
    animal(m, kind, s, rng, sitting)
    m.solid_box(-hx * 0.6, -hy * 0.7, hx * 0.6, hy * 0.7, 1.0, 1.0 + 4.5 * s)
    return ("a giant %s statue" if o["big"] else ("an %s statue" if kind[0] in "aeiou" else "a %s statue")) % kind


def wheel(m, x, y, z, r, w, rim=(0.75, 0.76, 0.78, 1)):
    tube(m, (x - w / 2, y, z), (x + w / 2, y, z), r, r, (0.07, 0.07, 0.08, 1), 18)
    sx = 1 if x > 0 else -1
    tube(m, (x + sx * w / 2, y, z), (x + sx * (w / 2 + 0.02), y, z), r * 0.6, r * 0.55, rim, 14)


def a_car(m, o, rng):
    s = 2.2 if o["big"] else 1.0; col = rng.choice([(0.8, 0.1, 0.1, 1), (0.1, 0.3, 0.75, 1), (0.95, 0.95, 0.95, 1), (0.15, 0.15, 0.17, 1), (0.95, 0.75, 0.1, 1)])
    for w_ in re.findall(r"red|blue|white|black|yellow|green|pink", o["text"]):
        col = {"red": (0.8, 0.1, 0.1, 1), "blue": (0.1, 0.3, 0.75, 1), "white": (0.95, 0.95, 0.95, 1), "black": (0.12, 0.12, 0.14, 1), "yellow": (0.95, 0.75, 0.1, 1), "green": (0.15, 0.55, 0.25, 1), "pink": (0.95, 0.5, 0.7, 1)}[w_]
    W, L = 0.95 * s, 2.3 * s
    box(m, "flat", -W, -L, 0.35 * s, W, L, 0.95 * s, col)                                              # lower body
    f = m.M("flat"); glass = (0.18, 0.24, 0.3, 1); z1, z2 = 0.95 * s, 1.5 * s
    P0 = [(-W * 0.98, -L * 0.45), (W * 0.98, -L * 0.45), (W * 0.98, L * 0.6), (-W * 0.98, L * 0.6)]      # cabin with sloped screens
    P1 = [(-W * 0.85, -L * 0.15), (W * 0.85, -L * 0.15), (W * 0.85, L * 0.45), (-W * 0.85, L * 0.45)]
    for k in range(4):
        j = (k + 1) % 4; f.quad((P0[k][0], P0[k][1], z1), (P0[j][0], P0[j][1], z1), (P1[j][0], P1[j][1], z2), (P1[k][0], P1[k][1], z2), glass)
    f.quad((P1[0][0], P1[0][1], z2), (P1[1][0], P1[1][1], z2), (P1[2][0], P1[2][1], z2), (P1[3][0], P1[3][1], z2), col)
    for (sx, y) in ((-1, -L * 0.65), (1, -L * 0.65), (-1, L * 0.65), (1, L * 0.65)):
        wheel(m, sx * (W - 0.12 * s), y, 0.36 * s, 0.36 * s, 0.28 * s)
    for sx in (-1, 1):
        box(m, "flat", sx * W * 0.7 - 0.18 * s, -L - 0.02, 0.7 * s, sx * W * 0.7 + 0.18 * s, -L + 0.02, 0.82 * s, (0.95, 0.95, 0.85, 1), solid=False)   # headlights
        box(m, "flat", sx * W * 0.7 - 0.18 * s, L - 0.02, 0.7 * s, sx * W * 0.7 + 0.18 * s, L + 0.02, 0.82 * s, (0.75, 0.08, 0.08, 1), solid=False)    # tail lights
    box(m, "flat", -W * 0.5, -L - 0.03, 0.42 * s, W * 0.5, -L + 0.01, 0.58 * s, (0.1, 0.1, 0.1, 1), solid=False)                                         # grille
    m.solid_box(-W, -L, W, L, 0, 1.5 * s)
    return "a giant car" if o["big"] else "a car"


def a_bus(m, o, rng):
    W, L, H = 1.25, 5.8, 3.1; col = rng.choice([(0.15, 0.55, 0.35, 1), (0.85, 0.2, 0.15, 1), (0.95, 0.75, 0.1, 1)])
    for w_ in re.findall(r"red|blue|yellow|green|pink|orange", o["text"]):
        col = {"red": (0.85, 0.15, 0.12, 1), "blue": (0.12, 0.3, 0.75, 1), "yellow": (0.95, 0.75, 0.1, 1), "green": (0.15, 0.55, 0.3, 1), "pink": (0.95, 0.5, 0.7, 1), "orange": (0.95, 0.5, 0.1, 1)}[w_]
    box(m, "flat", -W, -L, 0.45, W, L, H, (0.95, 0.95, 0.95, 1))
    box(m, "flat", -W - 0.02, -L - 0.02, 0.45, W + 0.02, L + 0.02, 1.3, col, solid=False)
    for sx in (-1, 1): box(m, "flat", sx * W - 0.03, -L + 0.4, 1.6, sx * W + 0.03, L - 0.4, 2.6, (0.15, 0.2, 0.26, 1), solid=False)
    box(m, "flat", -W * 0.9, -L - 0.04, 1.4, W * 0.9, -L + 0.02, 2.7, (0.15, 0.2, 0.26, 1), solid=False)
    sign(m, "SHINKO 01", 0, -L - 0.06, 2.75, 1.8, 0.3, col=(0.05, 0.05, 0.05, 1), fg=(1, 0.6, 0.1, 1))
    for y in (-L * 0.7, L * 0.7):
        for sx in (-1, 1): wheel(m, sx * (W - 0.15), y, 0.5, 0.5, 0.32)
    return "a bus"


def a_rocket(m, o, rng):
    s = 1.3 if o["big"] else 1.0; R = 2.2 * s; H = 26 * s
    box(m, "flat", -6, -6, 0, 6, 6, 1.2, (0.45, 0.45, 0.47, 1))                                  # launch pad
    frustum(m, "flat", 0, 0, 1.2, 3.0, R * 0.7, R, (0.2, 0.2, 0.22, 1), n=24, cap=False)           # engine skirt
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        tube(m, (math.cos(a) * R * 0.45, math.sin(a) * R * 0.45, 2.0), (math.cos(a) * R * 0.45, math.sin(a) * R * 0.45, 0.9), 0.45 * s, 0.7 * s, (0.3, 0.3, 0.32, 1), 12)   # nozzles
    for k in range(4):
        z0 = 3.0 + k * (H * 0.75 - 3.0) / 4; z1 = 3.0 + (k + 1) * (H * 0.75 - 3.0) / 4
        frustum(m, "flat", 0, 0, z0, z1, R, R, (0.96, 0.96, 0.95, 1) if k != 2 else (0.15, 0.15, 0.17, 1), n=28, cap=False)
    zt = H * 0.75; f = m.M("flat"); n = 28; prof = [(1.0, 0.0), (0.97, 0.12), (0.88, 0.3), (0.72, 0.5), (0.5, 0.7), (0.25, 0.88), (0.02, 1.0)]
    for (r0, h0), (r1, h1) in zip(prof, prof[1:]):          # ogive nose cone
        frustum(m, "flat", 0, 0, zt + h0 * H * 0.25, zt + h1 * H * 0.25, R * r0, max(R * r1, 0.01), (0.85, 0.12, 0.1, 1), n=n, cap=False, solid=False)
    m.solid_cyl(0, 0, R, 0, H)
    for k in range(4):                                       # fins
        a = k * math.pi / 2; ca, sa = math.cos(a), math.sin(a)
        p = [(R * ca, R * sa, 2.0), (R * 2.3 * ca, R * 2.3 * sa, 1.5), (R * 2.1 * ca, R * 2.1 * sa, 4.5), (R * ca, R * sa, 9.0)]
        for d in (-0.08, 0.08):
            q = [(x - sa * d, y + ca * d, z) for (x, y, z) in p]
            f.quad(*(q if d > 0 else q[::-1]), (0.85, 0.12, 0.1, 1))
    for k in range(5):                                       # window + lettering
        pass
    for side in (-1,):
        ellipsoid(m, "flat", 0, -R * 0.98, zt - 2.0, 0.6, 0.15, 0.6, (0.2, 0.35, 0.55, 1), 12, 8)
    sign(m, o["title"] or "SHINE 1", 0, -R - 0.05, H * 0.35, 1.2 + 0.5 * len(o["title"] or "SHINE 1"), 0.9, col=(0.96, 0.96, 0.95, 1), fg=(0.1, 0.1, 0.12, 1))
    box(m, "flat", R + 2.0, -1.0, 1.2, R + 3.0, 1.0, H * 0.8, (0.6, 0.15, 0.1, 1))                  # service tower
    return "a rocket"


def a_plane(m, o, rng):
    L = 16.0; R = 1.6; z = R + 1.6
    tube(m, (0, -L * 0.5, z), (0, L * 0.4, z), R, R, (0.95, 0.95, 0.96, 1), 24, caps=False)
    ellipsoid(m, "flat", 0, -L * 0.5, z, R, R * 1.8, R, (0.95, 0.95, 0.96, 1), 24, 12)
    tube(m, (0, L * 0.4, z), (0, L * 0.62, z + R * 0.6), R, 0.35, (0.95, 0.95, 0.96, 1), 24)
    f = m.M("flat"); wc = (0.8, 0.82, 0.86, 1)
    for sx in (-1, 1):
        a, b, c, d = (0, -2.5, z - 0.6), (sx * 11, 1.8, z - 0.2), (sx * 11, 3.2, z - 0.2), (0, 3.5, z - 0.6)
        f.quad(*((a, b, c, d) if sx < 0 else (d, c, b, a)), wc); f.quad(*((d, c, b, a) if sx < 0 else (a, b, c, d)), wc)
        tube(m, (sx * 4.5, -2.0, z - 1.4), (sx * 4.5, 1.2, z - 1.4), 0.75, 0.7, (0.7, 0.72, 0.76, 1), 16)         # engines
        a, b, c, d = (0, L * 0.5, z + 0.3), (sx * 4, L * 0.62, z + 0.4), (sx * 4, L * 0.66, z + 0.4), (0, L * 0.62, z + 0.5)
        f.quad(*((a, b, c, d) if sx < 0 else (d, c, b, a)), wc); f.quad(*((d, c, b, a) if sx < 0 else (a, b, c, d)), wc)
    for d in (-0.06, 0.06):
        q = [(d, L * 0.45, z + R * 0.7), (d, L * 0.62, z + R * 0.7), (d, L * 0.66, z + 5.2), (d, L * 0.58, z + 5.2)]
        f.quad(*(q if d > 0 else q[::-1]), (0.15, 0.35, 0.75, 1))
    for k in range(14):
        ellipsoid(m, "flat", -R * 0.97, -L * 0.4 + k * 1.1, z + 0.45, 0.04, 0.2, 0.25, (0.12, 0.15, 0.2, 1), 6, 4)
        ellipsoid(m, "flat", R * 0.97, -L * 0.4 + k * 1.1, z + 0.45, 0.04, 0.2, 0.25, (0.12, 0.15, 0.2, 1), 6, 4)
    for (x, y) in ((0, -L * 0.45), (-2, 1.5), (2, 1.5)):
        tube(m, (x, y, z - 0.5), (x, y, 0.5), 0.12, 0.12, (0.4, 0.4, 0.42, 1), 8); wheel(m, x, y, 0.45, 0.45, 0.3)
    m.solid_box(-R, -L * 0.6, R, L * 0.62, 0, z + R); m.solid_box(-11, -2.5, 11, 3.5, z - 1.5, z)
    return "a jet plane"


def a_boat(m, o, rng):
    L, W = 9.0, 2.6; f = m.M("flat"); hc = rng.choice([(0.85, 0.15, 0.12, 1), (0.1, 0.25, 0.55, 1), (0.95, 0.95, 0.95, 1)])
    top = [(-W, -L * 0.6), (W, -L * 0.6), (W, L), (-W, L)]; bot = [(-W * 0.4, -L * 0.45), (W * 0.4, -L * 0.45), (W * 0.5, L * 0.9), (-W * 0.5, L * 0.9)]
    for k in range(4):
        j = (k + 1) % 4; f.quad((bot[k][0], bot[k][1], 0.1), (bot[j][0], bot[j][1], 0.1), (top[j][0], top[j][1], 2.0), (top[k][0], top[k][1], 2.0), hc)
    tube(m, (-W, -L * 0.6, 2.0), (W, -L * 0.6, 2.0), 0.01, 0.01, hc, 4, caps=False)
    f.quad((-W, -L * 0.6, 2.0), (0, -L * 1.25, 2.4), (W, -L * 0.6, 2.0), (W, -L * 0.6, 2.0), hc)                        # bow deck
    f.quad((W, -L * 0.6, 2.0), (0, -L * 1.25, 2.4), (0, -L * 0.5, 0.15), (W * 0.4, -L * 0.45, 0.1), hc)
    f.quad((0, -L * 1.25, 2.4), (-W, -L * 0.6, 2.0), (-W * 0.4, -L * 0.45, 0.1), (0, -L * 0.5, 0.15), hc)
    f.quad((-W, -L * 0.6, 2.0), (W, -L * 0.6, 2.0), (W, L, 2.0), (-W, L, 2.0), (0.7, 0.55, 0.35, 1))
    box(m, "flat", -W * 0.7, -L * 0.1, 2.0, W * 0.7, L * 0.5, 4.0, (0.96, 0.96, 0.95, 1))
    box(m, "flat", -W * 0.72, -L * 0.1 - 0.05, 3.0, W * 0.72, L * 0.5 + 0.05, 3.6, (0.15, 0.2, 0.26, 1), solid=False)
    tube(m, (0, L * 0.2, 4.0), (0, L * 0.2, 7.5), 0.12, 0.08, (0.6, 0.6, 0.62, 1), 8)
    m.solid_box(-W, -L * 0.6, W, L, 0, 2.0)
    return "a boat"


def a_robot(m, o, rng):
    s = 1.6 if o["big"] else 1.0; c = (0.72, 0.75, 0.8, 1); d = (0.3, 0.32, 0.36, 1)
    def B(x0, y0, z0, x1, y1, z1, col=c): box(m, "flat", x0 * s, y0 * s, z0 * s, x1 * s, y1 * s, z1 * s, col, solid=False)
    plinth(m, 2.4 * s, 1.8 * s, 0.6)
    for sx in (-1, 1):
        B(sx * 0.9 - 0.45, -0.5, 0.6, sx * 0.9 + 0.45, 0.5, 3.6, d); B(sx * 0.9 - 0.55, -0.8, 0.6, sx * 0.9 + 0.55, 0.6, 1.1)
        B(sx * 2.0 - 0.35, -0.35, 4.0, sx * 2.0 + 0.35, 0.35, 6.8, d); B(sx * 2.0 - 0.45, -0.45, 3.5, sx * 2.0 + 0.45, 0.45, 4.1)
    B(-1.6, -0.9, 3.6, 1.6, 0.9, 7.0); B(-0.9, -0.95, 4.6, 0.9, -0.88, 6.2, (0.25, 0.55, 0.75, 1))
    B(-0.3, -0.3, 7.0, 0.3, 0.3, 7.4, d); B(-1.0, -0.8, 7.4, 1.0, 0.8, 8.9)
    for sx in (-1, 1): B(sx * 0.45 - 0.22, -0.84, 8.0, sx * 0.45 + 0.22, -0.78, 8.4, (0.95, 0.75, 0.15, 1))
    B(-0.5, -0.84, 7.65, 0.5, -0.78, 7.8, d)
    tube(m, (0, 0, 8.9 * s), (0, 0, 9.9 * s), 0.05 * s, 0.05 * s, d, 6); ellipsoid(m, "flat", 0, 0, 10.0 * s, 0.18 * s, 0.18 * s, 0.18 * s, (0.85, 0.15, 0.1, 1), 10, 6)
    m.solid_box(-2.4 * s, -1.0 * s, 2.4 * s, 1.0 * s, 0, 9 * s)
    return "a giant robot" if o["big"] else "a robot"


def a_person_statue(m, o, rng):
    s = 1.5 * (1.5 if o["big"] else 1.0); c = (0.55, 0.42, 0.24, 1) if "bronze" in o["text"] or rng.random() < 0.5 else (0.78, 0.78, 0.76, 1)
    plinth(m, 1.6 * s, 1.6 * s, 1.2, o["title"] if o["title"] not in ("STATUE", "MONUMENT") else None)
    z0 = 1.2
    def T(a, b, r0, r1): tube(m, (a[0] * s, a[1] * s, z0 + a[2] * s), (b[0] * s, b[1] * s, z0 + b[2] * s), r0 * s, r1 * s, c, 12)
    def E(x, y, z, rx, ry, rz): ellipsoid(m, "flat", x * s, y * s, z0 + z * s, rx * s, ry * s, rz * s, c, 14, 9)
    for sx in (-1, 1):
        T((sx * 0.13, 0, 0.95), (sx * 0.14, 0.02, 0.5), 0.12, 0.09); T((sx * 0.14, 0.02, 0.5), (sx * 0.14, 0.04, 0.06), 0.09, 0.06)
        E(sx * 0.14, -0.06, 0.04, 0.07, 0.14, 0.05)
    E(0, 0, 1.0, 0.24, 0.16, 0.14); T((0, 0, 1.0), (0, 0, 1.45), 0.2, 0.25); E(0, 0, 1.42, 0.27, 0.16, 0.12)
    T((-0.27, 0, 1.45), (-0.33, 0.02, 1.15), 0.07, 0.06); T((-0.33, 0.02, 1.15), (-0.34, -0.06, 0.88), 0.06, 0.05)
    T((0.27, 0, 1.45), (0.42, -0.05, 1.75), 0.07, 0.06); T((0.42, -0.05, 1.75), (0.45, -0.08, 2.05), 0.06, 0.05); E(0.45, -0.08, 2.1, 0.06, 0.05, 0.07)   # waving arm
    T((0, 0, 1.5), (0, 0, 1.6), 0.06, 0.06); E(0, -0.01, 1.72, 0.1, 0.11, 0.13)
    m.solid_box(-0.5 * s, -0.4 * s, 0.5 * s, 0.4 * s, 0, z0 + 2.2 * s)
    return "a statue"


KINDS.update({k: a_animal for k in ANIMALS})
KINDS.update({"car": a_car, "taxi": a_car, "truck": a_bus, "bus": a_bus, "van": a_bus, "train": a_bus, "rocket": a_rocket, "spaceship": a_rocket,
              "plane": a_plane, "airplane": a_plane, "jet": a_plane, "boat": a_boat, "ship": a_boat, "yacht": a_boat,
              "robot": a_robot, "mech": a_robot, "statue": a_person_statue, "monument": a_person_statue})
KINDS.pop("cat", None); KINDS["cat"] = a_animal


def a_horse(m, o, rng):
    """a life-size horse statue: ~1.6 m at the withers, long arched neck, long rectangular head, small upright ears,
    flowing dark mane and tail, long thin legs with dark hooves, chestnut coat"""
    s = 1.0 * (1.5 if o["big"] else 1.0) * (0.75 if o["small"] or "pony" in o["text"] else 1.0)
    coat = (0.46, 0.25, 0.12, 1); hair = (0.10, 0.06, 0.045, 1); hoof = (0.07, 0.06, 0.06, 1); blaze = (0.93, 0.91, 0.86, 1)
    if re.search(r"white|grey|gray", o["text"]): coat, hair = (0.9, 0.89, 0.86, 1), (0.75, 0.74, 0.72, 1)
    if re.search(r"black", o["text"]): coat, hair = (0.1, 0.09, 0.09, 1), (0.04, 0.04, 0.04, 1)
    Z = 0.8                                               # plinth height
    plinth(m, 1.0 * s + 0.4, 1.8 * s + 0.4, Z, "HORSE" if "pony" not in o["text"] else "PONY")
    def P(x, y, z): return (x * s, y * s, Z + z * s)
    def E(x, y, z, rx, ry, rz, c=coat, n=22, r=12): ellipsoid(m, "flat", x * s, y * s, Z + z * s, rx * s, ry * s, rz * s, c, n, r)
    def T(a, b, r0, r1, c=coat, n=12): tube(m, P(*a), P(*b), r0 * s, r1 * s, c, n)
    # barrel, chest and hindquarters (withers ~1.6 m)
    E(0, 0.0, 1.2, 0.4, 0.95, 0.42); E(0, -0.72, 1.25, 0.38, 0.38, 0.42); E(0, 0.72, 1.28, 0.42, 0.42, 0.42)
    # legs: forearm/gaskin, knee/hock, cannon, fetlock, dark hoof
    for sx in (-1, 1):
        for (y, back) in ((-0.75, False), (0.78, True)):
            x = sx * 0.2
            if back:
                E(x, y + 0.05, 1.05, 0.15, 0.24, 0.32)                                # thigh
                T((x, y + 0.08, 0.95), (x, y + 0.2, 0.55), 0.12, 0.07)                 # gaskin back to the hock
                T((x, y + 0.2, 0.55), (x, y + 0.12, 0.12), 0.065, 0.055)               # cannon
            else:
                T((x, y, 1.0), (x, y - 0.02, 0.55), 0.12, 0.075)                       # forearm
                T((x, y - 0.02, 0.55), (x, y - 0.02, 0.12), 0.065, 0.055)              # cannon
            fy = y + (0.12 if back else -0.02)
            E(x, fy - 0.02, 0.11, 0.07, 0.075, 0.06)                                    # fetlock
            T((x, fy - 0.03, 0.08), (x, fy - 0.05, 0.0), 0.075, 0.085, hoof, 12)        # hoof
    # long arched neck rising forward
    neck = [(0, -0.85, 1.42), (0, -1.08, 1.75), (0, -1.22, 2.05), (0, -1.3, 2.25)]
    rads = [0.27, 0.22, 0.17, 0.15]
    for (a, b), r0, r1 in zip(zip(neck, neck[1:]), rads, rads[1:]): T(a, b, r0, r1); E(b[0], b[1], b[2], r1, r1, r1)
    # long rectangular head angled down, with a broad flat muzzle
    poll = (0, -1.32, 2.33); nose = (0, -1.78, 1.88)
    E(0, -1.36, 2.28, 0.13, 0.17, 0.14)                                                  # cranium / jowl
    T((0, -1.4, 2.25), nose, 0.12, 0.095)                                                 # long face
    E(0, -1.8, 1.86, 0.105, 0.12, 0.1)                                                    # muzzle
    T((0, -1.5, 2.21), (0, -1.76, 1.95), 0.035, 0.03, blaze, 8)                            # white blaze
    for sx in (-1, 1):
        E(sx * 0.055, -1.9, 1.86, 0.025, 0.02, 0.03, hoof, 8, 5)                          # nostrils
        E(sx * 0.115, -1.42, 2.25, 0.03, 0.04, 0.03, (0.05, 0.04, 0.04, 1), 10, 6)        # eyes on the sides
        cone(m, P(sx * 0.07, -1.3, 2.4), P(sx * 0.08, -1.27, 2.58), 0.04 * s, coat, 6)    # small upright ears
    E(0, -1.62, 1.84, 0.1, 0.08, 0.05, hair, 10, 6)                                       # mouth line / chin shadow
    # flowing mane along the top of the neck + forelock
    for k in range(9):
        t = k / 8.0; y = -1.3 + 0.48 * t; z = 2.38 - 0.85 * t
        E(0.04, y + 0.06, z - 0.04, 0.05, 0.08, 0.16, hair, 10, 7)
    E(0, -1.4, 2.36, 0.05, 0.05, 0.08, hair, 8, 5)
    # long tail flowing down from the croup
    tail = [(0, 1.12, 1.48), (0, 1.3, 1.25), (0.02, 1.36, 0.9), (0.04, 1.33, 0.55), (0.05, 1.28, 0.35)]
    tr = [0.07, 0.11, 0.12, 0.1, 0.05]
    for (a, b), r0, r1 in zip(zip(tail, tail[1:]), tr, tr[1:]): T(a, b, r0, r1, hair, 10)
    m.solid_box(-0.5 * s, -2.0 * s, 0.5 * s, 1.5 * s, Z, Z + 2.5 * s)
    return "a giant horse statue" if o["big"] else ("a pony statue" if "pony" in o["text"] else "a horse statue")


KINDS["horse"] = a_horse; KINDS["pony"] = a_horse
ANIMALS.pop("horse", None)
