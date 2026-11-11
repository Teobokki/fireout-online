"""v1.0.4.1 ANA's abilities (were MIYOYAZU's in v1.0.4): BUILD (type anything -> a city-style building with real walk-on / walk-into collision, undo,
clear all) and TSUNAMI (SMALL / MEDIUM / BIG wave over HIKARI BEACH and Tokyo, STOP TSUNAMI drains it and restores
everything). Only ANA can trigger them; anyone can press STOP TSUNAMI so nobody is ever stuck in the water."""
import math, random, re, time
import numpy as np
from panda3d.core import (GeomVertexFormat, GeomVertexArrayFormat, GeomVertexData, GeomTriangles, Geom, GeomNode, InternalName,
                          Material, TransparencyAttrib, CardMaker, ColorBlendAttrib, TextNode, NodePath)
from direct.gui.DirectGui import DirectFrame, DirectEntry, DirectSlider, DGG
import fs_data as D
import fs_ui as U

VOX = 0.5                     # one build block = 0.5 m
STEP = 0.62                   # people can step up this much (so stairs / pyramids are climbable)
ORANGE = (1.0, 0.55, 0.1, 1)
ABILITY_CHAR = "ana"            # v1.0.4.1: MIYOYAZU was removed; ANA has BUILD and TSUNAMI
_FMT = None


def _fmt():
    global _FMT
    if _FMT is None:
        af = GeomVertexArrayFormat()
        af.add_column(InternalName.get_vertex(), 3, Geom.NT_float32, Geom.C_point)
        af.add_column(InternalName.get_normal(), 3, Geom.NT_float32, Geom.C_normal)
        af.add_column(InternalName.get_color(), 4, Geom.NT_float32, Geom.C_color)
        af.add_column(InternalName.get_tangent(), 4, Geom.NT_float32, Geom.C_vector)
        _FMT = GeomVertexFormat.register_format(GeomVertexFormat(af))
    return _FMT


def mesh_node(name, V, N, C, T, tris):
    """numpy arrays -> GeomNode (v3 n3 c4 t4 interleaved)"""
    n = len(V)
    vd = GeomVertexData(name, _fmt(), Geom.UH_static); vd.unclean_set_num_rows(n)
    arr = np.concatenate([V, N, C, T], 1).astype(np.float32)
    memoryview(vd.modify_array(0)).cast("B")[:] = arr.tobytes()
    tr = GeomTriangles(Geom.UH_static); tr.set_index_type(Geom.NT_uint32)
    ta = tr.modify_vertices(); ta.unclean_set_num_rows(len(tris) * 3)
    memoryview(ta).cast("B")[:] = np.asarray(tris, np.uint32).ravel().tobytes()
    g = Geom(vd); g.add_primitive(tr); gn = GeomNode(name); gn.add_geom(g); return gn


_COL = {}


def block_col(b):
    if b not in _COL:
        import fs_blocks as bl
        try:
            bk = bl.BLOCKS[b]; t = bk.tiles if isinstance(bk.tiles, str) else bk.tiles[1]
            im = bl.tex(t).astype(np.float32); a = im[..., 3:4] / 255.0
            c = (im[..., :3] * a).sum((0, 1)) / max(1e-3, a.sum()) / 255.0
            _COL[b] = tuple(float(min(1.0, (x ** 1.5) * 1.1)) for x in c)
        except Exception:
            _COL[b] = (0.6, 0.6, 0.6)
    return _COL[b]


FACES = [((1, 0, 0), [(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)]), ((-1, 0, 0), [(0, 1, 0), (0, 0, 0), (0, 0, 1), (0, 1, 1)]),
         ((0, 1, 0), [(1, 1, 0), (0, 1, 0), (0, 1, 1), (1, 1, 1)]), ((0, -1, 0), [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)]),
         ((0, 0, 1), [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]), ((0, 0, -1), [(0, 1, 0), (1, 1, 0), (1, 0, 0), (0, 0, 0)])]
SHADE = [0.86, 0.80, 0.90, 0.95, 1.0, 0.6]


def stairs_canvas(text):
    import fs_vinebuild as V, fs_blocks as bl
    c = V.Canvas(); w = 3; n = 14 if re.search(r"\bbig|tall|huge|long", text) else 9
    mat = bl.STONE_BRICKS if not re.search(r"wood", text) else bl.PLANKS
    for k in range(n):
        for x in range(-w, w + 1):
            for z in range(0, k + 1): c.put(x, -n // 2 + k, z, mat)
    for x in range(-w, w + 1):
        for y in range(n // 2, n // 2 + 6):
            for z in range(0, n): c.put(x, y, z, mat)
    return c, "stairs up to a %d m deck" % int(n * VOX)


class Builds:
    def __init__(self, game):
        self.g = game; self.items = []; self.root = game.app.render.attach_new_node("miyo-builds")
        mt = Material("build"); mt.set_base_color((1, 1, 1, 1)); mt.set_roughness(0.8); self.root.set_material(mt, 1)
        self.anim = None

    # ---------------------------------------------------------------- generation
    def make(self, text):
        """v1.0.4: builds are made like the city (fs_citybuild): real-scale solid meshes with the city's facade textures"""
        import fs_citybuild as CB
        t = (text or "").strip() or "house"
        m, label = CB.generate(t, seed=len(self.items) * 7919 + sum(map(ord, t)))
        label = re.sub(r"(?i)steam", "brass", label)
        return m, label

    def _mesh(self, m):
        """per-material city-style nodes (same textures, day/night swap and unlit vertex shading as the Tokyo blocks)"""
        w = self.g.world; root = NodePath("build")
        texmap = {"shopfront": "shopfront.png"}
        day = bool(getattr(w, "_dayfac", False))
        facs = []
        for mat, mb in m.mb.items():
            if not len(mb): continue
            np_ = mb.node(); np_.reparent_to(root)
            if mat.startswith("facade"):
                np_.set_texture(w.T(mat + ("_day" if day else "") + ".png", repeat=True), 1); facs.append((np_, mat))
            elif mat in texmap:
                np_.set_texture(w.T(texmap[mat], repeat=True), 1)
        for (text, x, y, z, hh, face, fg) in m.signs:          # painted sign lettering (plain, no glow)
            tn = TextNode("buildsign"); tn.set_text(text); tn.set_align(TextNode.A_center); tn.set_text_color(*fg)
            if U.FONT is not None: tn.set_font(U.FONT)
            sn = root.attach_new_node(tn); sn.set_pos(x, y - 0.01 * face, z - hh * 0.36); sn.set_scale(hh)
            sn.set_h(0 if face < 0 else 180); sn.set_depth_offset(1)
        root.set_light_off()
        return root, facs

    def place(self, text, me):
        m, label = self.make(text)
        if not m.solids: return None
        lx0, ly0, lx1, ly1 = m.bounds()
        # face the build's front (-y) toward the builder, snapped to 90 deg so collision stays an axis-aligned column grid
        q = int(round(me.h / 90.0)) % 4; h = q * 90.0
        fx, fy = -math.sin(math.radians(h)), math.cos(math.radians(h))
        dist = -ly0 + 2.5
        cx, cy = round((me.x + fx * dist) / VOX) * VOX, round((me.y + fy * dist) / VOX) * VOX
        ca, sa = math.cos(math.radians(h)), math.sin(math.radians(h))
        corners = [(cx + x * ca - y * sa, cy + x * sa + y * ca) for x in (lx0, lx1) for y in (ly0, ly1)]
        wx0, wx1 = min(c[0] for c in corners), max(c[0] for c in corners)
        wy0, wy1 = min(c[1] for c in corners), max(c[1] for c in corners)
        # collision: rasterise the solid volumes into the 0.5 m column grid (stand height / overhead / top)
        colinfo = {}
        for i in range(int(math.floor(wx0 / VOX)), int(math.floor(wx1 / VOX)) + 1):
            for j in range(int(math.floor(wy0 / VOX)), int(math.floor(wy1 / VOX)) + 1):
                px, py = (i + 0.5) * VOX - cx, (j + 0.5) * VOX - cy
                lx, ly = px * ca + py * sa, -px * sa + py * ca
                iv = sorted(m.intervals(lx, ly))
                if not iv: continue
                merged = []
                for a0, a1 in iv:
                    if merged and a0 <= merged[-1][1] + 0.05: merged[-1][1] = max(merged[-1][1], a1)
                    else: merged.append([a0, a1])
                if merged[0][0] <= 0.3:
                    stand = merged[0][1]; above = merged[1][0] if len(merged) > 1 else None
                else:
                    stand = 0.0; above = merged[0][0]
                colinfo[(i, j)] = (stand, above, merged[-1][1])
        npth, facs = self._mesh(m)
        w = self.g.world
        npth.reparent_to(getattr(w, "static", None) or self.root)
        npth.set_pos(cx, cy, 0.0); npth.set_h(h)
        w.fac_nodes = list(getattr(w, "fac_nodes", [])) + facs
        # the structure rises out of the ground while ANA builds it
        npth.set_sz(0.02)
        bbox = (wx0 - 0.5, wy0 - 0.5, wx1 + 0.5, wy1 + 0.5)
        it = dict(np=npth, cols=colinfo, bbox=bbox, label=label, text=text, rise=0.0, n=len(m.solids), center=(cx, cy), facs=facs)
        self.items.append(it)
        if len(self.items) > 16: self.remove(self.items[0])
        self.clear_cars(it)
        return it

    def clear_cars(self, it):
        """nudge parked / traffic cars out of a new build's footprint so nothing ends up inside a wall"""
        b = it["bbox"]
        for c in self.g.cars:
            if b[0] - 1 < c.x < b[2] + 1 and b[1] - 1 < c.y < b[3] + 1 and c is not self.g.pcar:
                c.x = b[0] - 4 if abs(c.x - b[0]) < abs(c.x - b[2]) else b[2] + 4; c.vx = c.vy = 0

    def remove(self, it):
        if it in self.items: self.items.remove(it)
        w = self.g.world
        if it.get("facs") and getattr(w, "fac_nodes", None) is not None:
            drop = set(id(f[0]) for f in it["facs"]); w.fac_nodes = [f for f in w.fac_nodes if id(f[0]) not in drop]
        it["np"].remove_node()

    def undo(self):
        if not self.items: return None
        it = self.items[-1]; self.remove(it); return it

    def clear(self):
        n = len(self.items)
        for it in list(self.items): self.remove(it)
        return n

    # ---------------------------------------------------------------- collision
    def resolve(self, x, y, z, rad=0.33):
        """push a walker out of columns too tall to step onto; returns (x, y, standing_height or None)"""
        stand = None
        for it in self.items:
            b = it["bbox"]
            if not (b[0] - rad < x < b[2] + rad and b[1] - rad < y < b[3] + rad): continue
            if it["rise"] < 0.98: continue
            cols = it["cols"]
            for _ in range(2):
                i0, i1 = int(math.floor((x - rad) / VOX)), int(math.floor((x + rad) / VOX))
                j0, j1 = int(math.floor((y - rad) / VOX)), int(math.floor((y + rad) / VOX))
                for i in range(i0, i1 + 1):
                    for j in range(j0, j1 + 1):
                        ci = cols.get((i, j))
                        if ci is None: continue
                        if ci[0] <= z + STEP: continue              # low enough to step onto (stairs, ledges)
                        x0, y0 = i * VOX, j * VOX; x1, y1 = x0 + VOX, y0 + VOX
                        cx = min(max(x, x0), x1); cy = min(max(y, y0), y1); dx, dy = x - cx, y - cy; d2 = dx * dx + dy * dy
                        if d2 >= rad * rad: continue
                        if d2 > 1e-8:
                            d = math.sqrt(d2); pen = rad - d; x += dx / d * pen; y += dy / d * pen
                        else:
                            cand = [(x - x0, -1, 0), (x1 - x, 1, 0), (y - y0, 0, -1), (y1 - y, 0, 1)]
                            m = min(cand); x += m[1] * (m[0] + rad); y += m[2] * (m[0] + rad)
            ci = cols.get((int(math.floor(x / VOX)), int(math.floor(y / VOX))))
            if ci is not None and ci[0] <= z + STEP:
                stand = ci[0] if stand is None else max(stand, ci[0])
        return x, y, stand

    def update(self, dt):
        for it in self.items:
            if it["rise"] < 1.0:
                it["rise"] = min(1.0, it["rise"] + dt / 1.6); k = it["rise"]; k = 1 - (1 - k) ** 3
                it["np"].set_sz(max(0.02, k))


class Tsunami:
    LEVELS = {"small": (0.75, 455.0, 22.0), "medium": (1.9, 120.0, 28.0), "big": (3.8, -430.0, 36.0)}   # water m, inland reach x, speed

    def __init__(self, game, sev):
        self.g = game; a = game.app; self.sev = sev
        if isinstance(sev, (int, float)):           # slider 0..1 -> blend SMALL..BIG
            t = max(0.0, min(1.0, float(sev)))
            lo, hi = self.LEVELS["small"], self.LEVELS["big"]
            self.L, self.reach, self.speed = (lo[0] + (hi[0] - lo[0]) * t, lo[1] + (hi[1] - lo[1]) * t, lo[2] + (hi[2] - lo[2]) * t)
            self.name = "SMALL" if t < 0.34 else ("MEDIUM" if t < 0.67 else "BIG")
        else:
            self.L, self.reach, self.speed = self.LEVELS[sev]; self.name = sev.upper()
        self.front = D.SEA_X + 60.0; self.level = 0.0; self.phase = "warn"; self.t = 0.0; self.drain = False; self.k = 1.0
        self.root = a.render.attach_new_node("tsunami"); W = D.WORLD
        self.y0, self.y1 = W[1] - 60, W[3] + 60
        # flood water (one big sheet that follows the front and rises)
        cm = CardMaker("flood"); cm.set_frame(0, 1, self.y0, self.y1)
        self.sheet = self.root.attach_new_node(cm.generate()); self.sheet.set_p(-90)
        try:
            self.wtex = game.world.T("flood_water.png", repeat=True); self.sheet.set_texture(self.wtex, 1); self.sheet.set_color(1, 1, 1, 0.93)
        except Exception:
            self.wtex = None; self.sheet.set_color(0.06, 0.28, 0.36, 0.92)
        self.sheet.set_transparency(TransparencyAttrib.M_alpha)
        self.sheet.set_light_off(); self.sheet.set_shader_off(); self.sheet.set_bin("transparent", 5); self.sheet.set_depth_write(False)
        self.sheet.set_two_sided(True)
        # wave crest: a curling wall along the whole coast, white foam on top
        self.crest = self.root.attach_new_node(self._crest_geom()); self.crest.set_light_off(); self.crest.set_shader_off()
        self.crest.set_transparency(TransparencyAttrib.M_alpha); self.crest.set_two_sided(True); self.crest.set_bin("transparent", 6)
        self.crest.set_depth_write(False)
        self.fx = a.render.attach_new_node("tsunami-fx"); self.fx.set_light_off(); self.fx.set_shader_off(); self.fx.set_depth_write(False)
        self.fx.set_bin("fixed", 41); self.fx.set_transparency(TransparencyAttrib.M_alpha)
        self.splashes = []; self.spl_t = 0.0
        self.hud = DirectFrame(parent=a.a2dTopCenter, frameColor=(0, 0, 0, 0), pos=(0, 0, -0.30))
        self.hud_bg = DirectFrame(parent=self.hud, frameColor=(0.55, 0.0, 0.0, 0.78), frameSize=(-0.78, 0.78, -0.105, 0.075))
        self.warn1 = U.text(self.hud, "", (0, 0.0), 0.058, fg=(1, 0.95, 0.2, 1))
        self.warn2 = U.text(self.hud, "", (0, -0.075), 0.034, fg=(1, 1, 1, 1), font=a.jpfont)
        game.app.sfx("siren", 0.9); game.app.sfx("heat", 0.8)
        self.saved_peds = []

    def _crest_geom(self):
        prof = [(-26, 0.0, (0.10, 0.36, 0.46, 0.85)), (-8, 0.55, (0.12, 0.42, 0.52, 0.9)), (-2, 0.95, (0.30, 0.62, 0.70, 0.95)),
                (0, 1.12, (0.85, 0.95, 0.97, 1.0)), (1.8, 1.0, (0.95, 0.98, 1.0, 0.95)), (2.6, 0.62, (0.8, 0.9, 0.95, 0.6)),
                (2.2, 0.25, (0.6, 0.8, 0.9, 0.25))]                                 # (dx toward land is negative x, height, colour)
        ny = 120; V, N, C, T, tris = [], [], [], [], []
        for j in range(ny + 1):
            y = self.y0 + (self.y1 - self.y0) * j / ny; wob = 0.08 * math.sin(j * 0.9) + 0.05 * math.sin(j * 2.3)
            for (dx, h, c) in prof:
                V.append((-dx * (1 + wob), y, h * (1 + wob))); N.append((1, 0, 0)); C.append(c); T.append((0, 1, 0, 1))
        m = len(prof)
        for j in range(ny):
            for i in range(m - 1):
                a = j * m + i; b = a + m
                tris.append((a, b, b + 1)); tris.append((a, b + 1, a + 1))
        return mesh_node("crest", np.array(V, np.float32), np.array(N, np.float32), np.array(C, np.float32), np.array(T, np.float32), tris)

    # water surface height at a point (0 = dry)
    def level_at(self, x, y):
        if x < self.front: return 0.0
        ramp = min(1.0, (x - self.front) / 30.0 + 0.35)
        return self.level * ramp

    def stop(self):
        if not self.drain:
            self.drain = True; self.phase = "drain"; self.g.toast("STOP TSUNAMI - the water is draining away")

    def update(self, dt):
        g = self.g; self.t += dt
        if self.phase == "warn":
            if self.t > 2.2: self.phase = "surge"
        elif self.phase == "surge":
            self.front = max(self.reach, self.front - self.speed * dt)
            self.level = min(self.L, self.level + dt * self.L / 3.0)
            if self.front <= self.reach + 0.1 and self.level >= self.L - 0.01: self.phase = "hold"
        elif self.phase == "hold":
            self.level = self.L * (1.0 + 0.03 * math.sin(self.t * 1.3))
        if self.drain:
            self.k = max(0.0, self.k - dt / 3.5); self.level = min(self.level, self.L * self.k)
            self.front = min(D.SEA_X + 140.0, self.front + dt * 60.0 * (1.2 - self.k))
        # visuals
        lv = max(0.02, self.level)
        sx = max(1.0, D.SEA_X + 400 - self.front)
        self.sheet.set_pos(self.front, 0, lv - 0.05 + 0.04 * math.sin(self.t * 2)); self.sheet.set_sx(sx)
        if self.wtex is not None:                 # ripples ~14 m across, drifting inland with the flow
            from panda3d.core import TextureStage
            ts = TextureStage.get_default(); self.sheet.set_tex_scale(ts, sx / 14.0, (self.y1 - self.y0) / 14.0)
            self.sheet.set_tex_offset(ts, (self.t * 0.09 + self.front / 14.0) % 1.0, (self.t * 0.013) % 1.0)
        crest_h = 0.0 if self.phase == "warn" else (lv * 1.7 + 1.0 if self.phase == "surge" else lv * 0.9) * (self.k if self.drain else 1.0)
        self.crest.set_pos(self.front, 0, -0.1); self.crest.set_sz(max(0.01, crest_h)); self.crest.set_sx(1.0 + 0.6 * (self.phase == "surge"))
        fl = 0.5 + 0.5 * math.sin(self.t * 7)
        self.hud_bg["frameColor"] = (0.55 + 0.35 * fl, 0.0, 0.0, 0.8)
        if self.drain:
            self.warn1.setText("TSUNAMI ENDING  -  WATER DRAINING"); self.warn2.setText("津波警報 解除  -  water %.1f m" % self.level)
        else:
            self.warn1.setText("! TSUNAMI WARNING  -  %s WAVE !" % self.name)
            self.warn2.setText("津波警報  -  GET TO HIGH GROUND  -  water %.1f m   -   N: STOP TSUNAMI" % self.level)
        # splashes along the front near the player + on cars hit
        px, py = g.player_pos(); self.spl_t -= dt
        if self.phase in ("surge", "hold") and not self.drain and self.spl_t <= 0:
            self.spl_t = 0.05 if self.phase == "surge" else 0.18
            for _ in range(3 if self.phase == "surge" else 1):
                self.splash(self.front + random.uniform(-1, 3), py + random.uniform(-60, 60), lv + random.uniform(0.2, 1.2) * (crest_h * 0.5 + 0.5), 1.2 + lv * 0.5)
        for s in list(self.splashes):
            s[1] -= dt; n = s[0]; s[3] -= 9.8 * dt; n.set_z(n.get_z() + s[3] * dt); n.set_scale(n.get_sx() * (1 + dt * 0.8))
            n.set_alpha_scale(max(0.0, s[1] / s[2]))
            if s[1] <= 0: n.remove_node(); self.splashes.remove(s)
        # cars pushed inland / floating, peds swept
        push = self.L * (2.6 if self.phase == "surge" else 0.6) * (0 if self.drain else 1)
        for c in g.cars:
            w = self.level_at(c.x, c.y)
            if w <= 0.15: continue
            if push > 0 and getattr(c, "asleep", False): c.wake()
            if c is not g.pcar or c.speed < 6: c.vx -= push * dt * 1.6; c.vy += math.sin(self.t + c.x) * dt * push * 0.2
            if w > 0.9:
                fz = w - 0.85 + 0.12 * math.sin(self.t * 2.2 + c.y)
                c.np.set_z(fz); c.model.set_r(6 * math.sin(self.t * 1.7 + c.x)); c.model.set_p(4 * math.sin(self.t * 1.3 + c.y))
            if self.phase == "surge" and random.random() < dt * 2 and abs(c.x - self.front) < 6 and abs(c.y - py) < 90:
                self.splash(c.x, c.y, w + 1.0, 2.0)
        for p in g.peds:
            w = self.level_at(p.x, p.y)
            if w > 0.3 and push > 0:
                p.x -= push * 0.6 * dt; p.flee = max(p.flee, 0.5); p.flee_from = (p.x + 20, p.y)
        for p in g.chars.values():
            if getattr(p, "benched", False) or p.in_car is not None: continue
            w = self.level_at(p.x, p.y)
            if w > 1.0 and push > 0: p.x -= push * 0.35 * dt
        if self.drain and self.k <= 0.0: return False
        return True

    def splash(self, x, y, z, s):
        cm = CardMaker("spl"); cm.set_frame(-1, 1, -1, 1)
        n = self.fx.attach_new_node(cm.generate()); n.set_billboard_point_eye(); n.set_texture(self.g.world.T("glow.png", repeat=False))
        n.set_pos(x, y, z); n.set_scale(s * random.uniform(0.6, 1.3)); n.set_color(0.85, 0.95, 1.0, 0.9)
        life = random.uniform(0.5, 1.0); self.splashes.append([n, life, life, random.uniform(2.5, 6.0)])

    def destroy(self):
        for s in self.splashes: s[0].remove_node()
        self.splashes = []; self.root.remove_node(); self.fx.remove_node(); self.hud.destroy()
        for c in self.g.cars:
            c.model.set_r(0); c.model.set_p(0)


class Miyo:
    """ANA's BUILD / TSUNAMI ability controller (owned by the Game)."""
    def __init__(self, game):
        self.g = game; self.builds = Builds(game); self.tsu = None; self.ui = None; self.anim = 0.0; self.pending = None
        game.builds = self.builds
        try: self.ramen = RamenStall(game)
        except Exception as e: self.ramen = None; game.app.log_error(e)
        try:
            from fs_food import BeachBar
            self.bar = game.bar = BeachBar(game)
        except Exception as e: self.bar = game.bar = None; game.app.log_error(e)

    def is_miyo(self): return self.g.active == ABILITY_CHAR and not getattr(self.g, "guest", False)       # v1.0.4.1: ANA has BUILD + TSUNAMI

    # ---------------------------------------------------------------- BUILD
    def open_build(self):
        g = self.g
        if not self.is_miyo(): g.toast("Only ANA can BUILD  -  press Q to switch to her"); return
        if g.pcar or g.blocked() or g.phone: return
        if hasattr(g, "arsenal"): g.arsenal.unequip()
        a = g.app; o = g.overlay = DirectFrame(parent=a.aspect2d, frameColor=(0, 0, 0, 0.45), frameSize=(-4, 4, -2, 2), state=DGG.NORMAL)
        U.panel(o, -0.95, 0.95, -0.55, 0.55, edge=ORANGE)
        U.text(o, "ANA  -  BUILD", (0, 0.43), 0.068, fg=ORANGE)
        U.text(o, "Type anything: house, pagoda, skyscraper, tower, bridge, stairs, castle, horse, cat, car, rocket...", (0, 0.335), 0.03,
               fg=(0.85, 0.85, 0.9, 1), font=U.FONT_PLAIN)
        ent = DirectEntry(parent=o, initialText=getattr(self, "last_text", ""), width=24, numLines=1, scale=0.06, pos=(-0.72, 0, 0.19),
                          frameColor=(0.1, 0.08, 0.15, 1), text_fg=(1, 1, 1, 1), entryFont=U.FONT_PLAIN, focus=1, command=lambda t: go())
        msg = U.text(o, "Built so far: %d" % len(self.builds.items), (0, 0.06), 0.034, fg=(1, 1, 1, 1), font=U.FONT_PLAIN, wrap=48)
        o.ent = ent; o.msg = msg
        def go():
            t = ent.get().strip() or "house"; self.close_ui(); self.start_build(t)
        def quick(t): ent.enterText(t)
        for k, t in enumerate(("house", "tower", "bridge", "stairs", "pyramid", "castle")):
            U.button(o, t.upper(), (-0.70 + k * 0.28, -0.07), lambda t=t: quick(t), w=0.12, h=0.04, scale=0.03, edge=U.CYAN)
        U.button(o, "BUILD", (0.55, -0.24), go, w=0.17, h=0.055, scale=0.045, edge=ORANGE, hint="Enter")
        U.button(o, "UNDO", (0.0, -0.24), lambda: (self.undo(), msg.setText("Built so far: %d" % len(self.builds.items))), w=0.14, h=0.05, scale=0.038)
        U.button(o, "CLEAR ALL", (-0.5, -0.24), lambda: (self.clear(), msg.setText("Built so far: 0")), w=0.17, h=0.05, scale=0.038, edge=(1, 0.4, 0.3, 1))
        U.button(o, "CLOSE", (0, -0.44), self.close_ui, w=0.2, h=0.045, scale=0.04, hint="Esc")
        self.ui = o; g.refresh_buttons()

    def close_ui(self):
        g = self.g
        if g.overlay is not None and g.overlay is self.ui: g.close_overlay()
        self.ui = None

    def start_build(self, text):
        g = self.g; me = g.me(); self.last_text = text
        it = self.builds.place(text, me)
        if it is None: g.toast("Nothing to build for \"%s\"" % text); return
        self.anim = 1.7; me.set_grip(True, False)
        g.toast("ANA builds: %s" % it["label"], 3.5); g.app.sfx("swing_heavy", 0.7)
        cx, cy = it["center"]; g.cam_yaw = math.degrees(math.atan2(-(cx - me.x), (cy - me.y))); g.cam_pos = None

    def undo(self):
        it = self.builds.undo()
        self.g.toast("Undo: removed %s" % it["label"] if it else "Nothing to undo"); self.g.app.sfx("click", 0.6)

    def clear(self):
        n = self.builds.clear(); self.g.toast("Cleared %d build%s" % (n, "" if n == 1 else "s")); self.g.app.sfx("bump", 0.6)

    # ---------------------------------------------------------------- TSUNAMI
    def key_tsunami(self):
        g = self.g
        if self.tsu is not None: self.tsu.stop(); g.refresh_buttons(); return
        self.open_tsunami()

    def open_tsunami(self):
        g = self.g
        if not self.is_miyo(): g.toast("Only ANA can summon a TSUNAMI  -  press Q to switch to her"); return
        if g.blocked() or g.phone or g.activity: return
        a = g.app; o = g.overlay = DirectFrame(parent=a.aspect2d, frameColor=(0, 0, 0, 0.45), frameSize=(-4, 4, -2, 2), state=DGG.NORMAL)
        U.panel(o, -0.85, 0.85, -0.55, 0.55, edge=(0.3, 0.75, 1.0, 1))
        U.text(o, "TSUNAMI", (0, 0.43), 0.075, fg=(0.4, 0.8, 1.0, 1)); U.text(o, "津波", (0, 0.35), 0.045, fg=(0.4, 0.8, 1.0, 1), font=a.jpfont)
        U.text(o, "A wave rolls in from the sea over HIKARI BEACH and Tokyo. STOP TSUNAMI drains it any time.", (0, 0.27), 0.029,
               fg=(0.85, 0.85, 0.9, 1), font=U.FONT_PLAIN, wrap=52)
        for k, (sv, desc) in enumerate((("small", "knee-deep, beach + coast road"), ("medium", "2 m, floods the beach districts"),
                                        ("big", "4 m, rolls deep into Tokyo"))):
            x = -0.55 + k * 0.55
            U.button(o, sv.upper(), (x, 0.09), lambda sv=sv: self.start_tsunami(sv), w=0.2, h=0.065, scale=0.05,
                     edge=((0.4, 1, 0.5, 1), (1, 0.8, 0.2, 1), (1, 0.3, 0.3, 1))[k], hint=str(k + 1))
            U.text(o, desc, (x, -0.03), 0.026, fg=(0.85, 0.85, 0.9, 1), font=U.FONT_PLAIN)
        U.text(o, "or set the severity:", (-0.36, -0.15), 0.03, fg=(0.85, 0.85, 0.9, 1), font=U.FONT_PLAIN)
        sl = DirectSlider(parent=o, range=(0, 1), value=0.5, pageSize=0.1, scale=0.32, pos=(0.18, 0, -0.14), frameColor=(0.2, 0.3, 0.5, 1),
                          thumb_frameColor=(0.4, 0.8, 1.0, 1))
        U.button(o, "SURGE AT THIS SEVERITY", (0, -0.29), lambda: self.start_tsunami(float(sl["value"])), w=0.32, h=0.05, scale=0.036,
                 edge=(0.4, 0.8, 1.0, 1))
        U.button(o, "CANCEL", (0, -0.45), self.close_ui, w=0.2, h=0.045, scale=0.04, hint="Esc")
        o.sl = sl; self.ui = o
        o.kind = "tsunami"

    def start_tsunami(self, sev):
        g = self.g; self.close_ui()
        if self.tsu is not None: self.tsu.destroy()
        self.tsu = Tsunami(g, sev); g.tsunami = self.tsu
        if hasattr(g, "news"): g.news.append(("tsunami", sev, time.time()))
        px, py = g.player_pos(); near = [p for p in g.peds if math.hypot(p.x - px, p.y - py) < 30]
        if near: g.npc_say("tsunami", random.choice(near))
        g.toast("ANA summons a %s TSUNAMI!" % self.tsu.name, 3.0); g.refresh_buttons()

    def stop_tsunami(self):
        if self.tsu is not None: self.tsu.stop(); self.g.refresh_buttons()

    # ---------------------------------------------------------------- per frame
    def update(self, dt):
        g = self.g; self.builds.update(dt)
        if self.ramen is not None: self.ramen.update(dt)
        if self.bar is not None: self.bar.update(dt)
        if self.anim > 0:
            self.anim -= dt; me = g.me(); t = 1.7 - self.anim
            hm = math.sin(t * 13.0)                       # hammering strokes with the right arm, left arm steadies
            me.arm_pose = (-70 - 35 * hm, -35, -60 + 25 * hm, -40)
            if self.anim <= 0: me.arm_pose = None; me.set_grip(False, False); g.app.sfx("checkpoint", 0.5)
            elif int(t * 13.0 / math.pi) != int((t - dt) * 13.0 / math.pi) and hm > 0: g.app.sfx("hit", 0.25)
        if self.tsu is not None:
            if not self.tsu.update(dt):
                self.tsu.destroy(); self.tsu = None; g.tsunami = None; g.toast("TSUNAMI over  -  everything is back to normal"); g.refresh_buttons()

    def state(self):
        return (self.is_miyo(), self.tsu is not None and not self.tsu.drain)

    def destroy(self):
        if self.tsu: self.tsu.destroy(); self.tsu = None
        self.builds.root.remove_node()
        if self.ramen is not None: self.ramen.root.remove_node()
        if self.bar is not None: self.bar.root.remove_node()


# ================================================================ v1.0.4 shared small-mesh helpers (props, moustache)
def blob_mesh(name, blobs, col, seg=10, ring=7):
    """union-look mesh of ellipsoids: blobs = [(cx, cy, cz, rx, ry, rz)] -> GeomNode with vertex colours"""
    V, N, C, T, tris = [], [], [], [], []
    for (cx, cy, cz, rx, ry, rz) in blobs:
        base = len(V)
        for i in range(ring + 1):
            th = math.pi * i / ring
            for j in range(seg + 1):
                ph = 2 * math.pi * j / seg
                nx, ny, nz = math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th)
                V.append((cx + rx * nx, cy + ry * ny, cz + rz * nz))
                n = (nx / rx, ny / ry, nz / rz); L = math.sqrt(sum(a * a for a in n)) or 1; N.append(tuple(a / L for a in n))
                C.append(col); T.append((1, 0, 0, 1))
        for i in range(ring):
            for j in range(seg):
                a = base + i * (seg + 1) + j; b = a + seg + 1
                tris.append((a, b, b + 1)); tris.append((a, b + 1, a + 1))
    return mesh_node(name, np.array(V, np.float32), np.array(N, np.float32), np.array(C, np.float32), np.array(T, np.float32), tris)


def box_mesh(name, boxes):
    """boxes = [(x0, y0, z0, x1, y1, z1, (r, g, b, a))] -> GeomNode"""
    V, N, C, T, tris = [], [], [], [], []
    for (x0, y0, z0, x1, y1, z1, col) in boxes:
        for nrm, cs in FACES:
            base = len(V)
            for (ox, oy, oz) in cs:
                V.append((x0 + (x1 - x0) * ox, y0 + (y1 - y0) * oy, z0 + (z1 - z0) * oz)); N.append(nrm); C.append(col); T.append((1, 0, 0, 1))
            tris.append((base, base + 1, base + 2)); tris.append((base, base + 2, base + 3))
    return mesh_node(name, np.array(V, np.float32), np.array(N, np.float32), np.array(C, np.float32), np.array(T, np.float32), tris)


def shade(np_, app, gloss=0.2, sheen=0.0):
    import fs_shaders
    fs_shaders.apply(np_, app, gloss=gloss, sheen=sheen)
    mt = Material("prop"); mt.set_base_color((1, 1, 1, 1)); mt.set_roughness(0.7); np_.set_material(mt, 1)
    return np_


# ================================================================ v1.0.4 JP TAXI driver (adult Indian man)
DAN_HEAD_O = (0.0, -0.030, 1.578)
DAN_HEAD_R = ((0.955854594707489, -0.2752596139907837, -0.10283010452985764), (0.2674517035484314, 0.9599443078041077, -0.08352530002593994),
              (0.12170232087373734, 0.0523359552025795, 0.9911858439445496))


def head_to_model(q):
    R = DAN_HEAD_R; o = DAN_HEAD_O
    return tuple(o[i] + R[i][0] * q[0] + R[i][1] * q[1] + R[i][2] * q[2] for i in range(3))


def drop_hidden_tris(np_, inside, ref=None):
    """remove triangles whose three vertices all satisfy inside(x, y, z) (coords relative to ref) - skin under clothes"""
    from panda3d.core import GeomVertexReader
    ref = ref or np_
    for gnp in [np_] + list(np_.find_all_matches("**/+GeomNode")):
        if gnp.is_empty() or gnp.node().get_type().get_name() != "GeomNode": continue
        gn = gnp.node(); mat = gnp.get_mat(ref)
        for i in range(gn.get_num_geoms()):
            g = gn.modify_geom(i); r = GeomVertexReader(g.get_vertex_data(), "vertex"); ins = []
            while not r.is_at_end():
                v = mat.xform_point(r.get_data3()); ins.append(bool(inside(v[0], v[1], v[2])))
            for pi in range(g.get_num_primitives()):
                pr = g.get_primitive(pi).decompose(); keep = GeomTriangles(Geom.UH_static); keep.set_index_type(Geom.NT_uint32); n = 0
                for t in range(pr.get_num_primitives()):
                    a, b, c = pr.get_vertex(pr.get_primitive_start(t)), pr.get_vertex(pr.get_primitive_start(t) + 1), pr.get_vertex(pr.get_primitive_start(t) + 2)
                    if ins[a] and ins[b] and ins[c]: continue
                    keep.add_vertices(a, b, c); n += 1
                g.set_primitive(pi, keep)


def shrinkwrap_shirt(m, col, z0=0.96, z1=1.43, nz=26, na=40, off=0.014):
    sk = m.find("**/skin")
    if sk.is_empty(): return None
    from panda3d.core import GeomVertexReader
    P = []
    for gnp in [sk] + list(sk.find_all_matches("**/+GeomNode")):
        if gnp.node().get_type().get_name() != "GeomNode": continue
        mat = gnp.get_mat(m)
        for i in range(gnp.node().get_num_geoms()):
            r = GeomVertexReader(gnp.node().get_geom(i).get_vertex_data(), "vertex")
            while not r.is_at_end():
                v = mat.xform_point(r.get_data3()); P.append((v[0], v[1], v[2]))
    P = np.array(P, float)
    if len(P) == 0: return None
    cx = float(np.median(P[(P[:, 2] > z0) & (P[:, 2] < z1)][:, 0])); cy = float(np.median(P[(P[:, 2] > z0) & (P[:, 2] < z1)][:, 1]))
    zs = np.linspace(z0, z1, nz); R = np.zeros((nz, na))
    for k, z in enumerate(zs):
        S = P[np.abs(P[:, 2] - z) < (z1 - z0) / nz]
        if len(S) == 0: continue
        dx, dy = S[:, 0] - cx, S[:, 1] - cy; ang = (np.arctan2(dy, dx) % (2 * np.pi)) / (2 * np.pi) * na; rad = np.hypot(dx, dy)
        for j in range(na):
            sel = rad[(ang >= j) & (ang < j + 1)]
            R[k, j] = sel.max() if len(sel) else 0.0
    for k in range(nz):                                   # fill empty bins from neighbours
        for j in range(na):
            if R[k, j] == 0.0: R[k, j] = max(R[k, (j - 1) % na], R[k, (j + 1) % na], R[max(k - 1, 0), j])
    R += off; R0 = R.copy()
    th = (np.arange(na) + 0.5) / na * 2 * np.pi
    back = np.clip(np.sin(th), 0, 1)                      # +y = his back
    for _ in range(3):                                    # smooth across the back (height) and around the body
        Rz = R.copy(); Rz[1:-1] = (R[:-2] + R[1:-1] * 2 + R[2:]) / 4.0; R = R + (Rz - R) * (0.4 + 0.6 * back)[None, :]
        Ra = (np.roll(R, 1, 1) + R * 2 + np.roll(R, -1, 1)) / 4.0; R = np.maximum(R * 0.5 + Ra * 0.5, R - 0.004)
    R = np.maximum(R, R0)                                 # never inside the body
    # collar: two more rings that slope in from the shoulders to the neck
    Sn = P[np.abs(P[:, 2] - (z1 + 0.05)) < 0.012]
    rn = np.full(na, 0.065)
    if len(Sn):
        dx, dy = Sn[:, 0] - cx, Sn[:, 1] - cy; ang = (np.arctan2(dy, dx) % (2 * np.pi)) / (2 * np.pi) * na; rad = np.hypot(dx, dy)
        for j in range(na):
            sel = rad[(ang >= j) & (ang < j + 1)]
            if len(sel): rn[j] = sel.max()
    rn = np.minimum(rn + 0.004, R[-1])                     # collar hugs the neck: no gap to see into
    def skin_r(zq, tol=0.01):
        out = np.zeros(na); Sq = P[np.abs(P[:, 2] - zq) < tol]
        if len(Sq):
            dx, dy = Sq[:, 0] - cx, Sq[:, 1] - cy; ang = (np.arctan2(dy, dx) % (2 * np.pi)) / (2 * np.pi) * na; rad = np.hypot(dx, dy)
            for j in range(na):
                sel = rad[(ang >= j) & (ang < j + 1)]
                if len(sel): out[j] = sel.max()
        return out
    c1 = np.maximum(R[-1] * 0.45 + rn * 0.55, skin_r(z1 + 0.022) + 0.006)      # collar never under the trapezius skin
    rn = np.maximum(rn, skin_r(z1 + 0.042, 0.006) + 0.004)
    R = np.vstack([R, c1[None, :], rn[None, :], (rn - 0.006)[None, :]])
    zs = np.concatenate([zs, [z1 + 0.022, z1 + 0.042, z1 + 0.030]]); nz += 3      # last ring folds the collar inward
    V, N, C, T, tris = [], [], [], [], []
    for k, z in enumerate(zs):
        for j in range(na + 1):
            a = th[j % na]; r = R[k, j % na]
            V.append((cx + r * math.cos(a), cy + r * math.sin(a), z)); N.append((math.cos(a), math.sin(a), 0)); C.append(col); T.append((1, 0, 0, 1))
    W = na + 1
    for k in range(nz - 1):
        for j in range(na):
            a_, b_, c_, d_ = k * W + j, k * W + j + 1, (k + 1) * W + j + 1, (k + 1) * W + j
            tris.append((a_, b_, c_)); tris.append((a_, c_, d_))
    node = m.attach_new_node(mesh_node("tshirt", np.array(V, np.float32), np.array(N, np.float32), np.array(C, np.float32), np.array(T, np.float32), tris))
    return node


def make_taxi_driver(game):
    """a respectful, realistic taxi driver: warm brown skin (same skin material as the crew, toned), short dark hair, a
    thick full dark moustache (3D mesh, clean-shaven chin), plain white short-sleeve T-shirt (arms showing), navy trousers, no hat."""
    from fs_people import Person
    p = Person(game, "daniel", 0, 0, 0, ped=False)
    if p.outfit != "default": p.set_outfit("default")
    p.npc = True; p.benched = False
    m = p.model; app = game.app
    tone = p.skin_tint = (0.60, 0.45, 0.36, 1)
    for n in [m.find("**/skin")] + list(m.find_all_matches("**/arm*")) + list(m.find_all_matches("**/fore*")):
        if not n.is_empty(): n.set_shader_input("tint", tone)
    for arm in list(m.find_all_matches("**/arm*")) + list(m.find_all_matches("**/fore*")):   # the arm skin geoms carry their
        for gnp in arm.find_all_matches("**/+GeomNode"):                                      # own tint - same tone as face
            nm_ = gnp.get_name()
            if "fingers" in nm_ or "fist" in nm_ or "tank" in nm_ or "shoulder" in nm_: continue
            gnp.set_shader_input("tint", tone)
    for n in list(m.find_all_matches("**/fingers*")) + list(m.find_all_matches("**/fist*")):
        n.set_shader_input("tint", (0.82, 0.68, 0.62, 1))
    for n in [m.find("**/tank")] + list(m.find_all_matches("**/sleeve*")):            # plain white short-sleeve T-shirt, matte
        if n.is_empty(): continue
        n.set_texture_off(1); shade(n, app, 0.05, 0.0); n.set_shader_input("tint", (0.76, 0.76, 0.75, 1)); n.set_shader_input("emitboost", 0.0)
        n.set_shader_input("use_tex", 0.0)
    for sl in m.find_all_matches("**/sleeve*"):      # snug T-shirt sleeves
        sl.set_scale(0.96, 0.96, 0.92)
    # v1.0.4: a proper men's T-shirt torso. The loose-shirt sculpt had rounded bulges over the shoulder blades, so it is
    # replaced by a shirt shrink-wrapped around his own body: a ring of radii per height, taken from the skin, pushed 1.4 cm
    # out (no skin can poke through) and smoothed hard across the back so it hangs flat and natural.
    old = m.find("**/tank")
    if not old.is_empty(): old.hide()
    from panda3d.core import GeomVertexRewriter
    sk = m.find("**/skin")
    for gnp in [sk] + list(sk.find_all_matches("**/+GeomNode")):
        if gnp.is_empty() or gnp.node().get_type().get_name() != "GeomNode": continue
        gn = gnp.node()
        for i in range(gn.get_num_geoms()):
            vd = gn.modify_geom(i).modify_vertex_data(); rw = GeomVertexRewriter(vd, "vertex")
            rn = GeomVertexRewriter(vd, "normal") if vd.has_column("normal") else None
            while not rw.is_at_end():
                x, y, z = rw.get_data3(); nx_, ny_, nz_ = rn.get_data3() if rn is not None else (0, 0, 1)
                if y > 0.0 and 1.0 < z < 1.47:
                    w = min(1.0, (z - 1.0) / 0.1, (1.47 - z) / 0.08); sc = 1.0 - 0.55 * w
                    y = y * sc; ny_ = ny_ / sc; L = math.sqrt(nx_ * nx_ + ny_ * ny_ + nz_ * nz_) or 1.0; nx_, ny_, nz_ = nx_ / L, ny_ / L, nz_ / L
                rw.set_data3(x, y, z)
                if rn is not None: rn.set_data3(nx_, ny_, nz_)
    shirt = shrinkwrap_shirt(m, (0.80, 0.80, 0.78, 1))
    # nothing under the shirt can poke through: drop torso skin inside the shirt and upper-arm skin inside the sleeves
    if shirt is not None: drop_hidden_tris(sk, lambda x, y, z: 0.975 < z < 1.40, m)
    for arm in (m.find("**/armL"), m.find("**/armR")):
        if arm.is_empty(): continue
        for gnp in arm.find_all_matches("**/+GeomNode"):
            if gnp.get_name().startswith("skin") and gnp.get_parent() == arm: drop_hidden_tris(gnp, lambda x, y, z: z > -0.11, arm)
    if shirt is not None: shade(shirt, app, 0.05, 0.0); shirt.set_shader_input("emitboost", 0.0); shirt.set_two_sided(True)
    for sl in m.find_all_matches("**/sleeve*"):      # T-shirt sleeves, a touch roomier so the arm never shows through
        sl.set_scale(1.1, 1.1, 1.0)
    for arm in (m.find("**/armL"), m.find("**/armR")):  # shoulder caps in shirt fabric that move with the arm
        if arm.is_empty(): continue
        cap = arm.attach_new_node(blob_mesh("shoulder_cap", [(0, 0, -0.035, 0.074, 0.078, 0.09)], (0.80, 0.80, 0.78, 1), 16, 12))
        shade(cap, app, 0.05, 0.0); cap.set_shader_input("emitboost", 0.0)
    for n in [m.find("**/skin")] + list(m.find_all_matches("**/arm*")) + list(m.find_all_matches("**/fore*")):
        if not n.is_empty(): n.set_shader_input("sheen", 0.25); n.set_shader_input("gloss", 0.15)   # no shiny pale patches
    tr = m.find("**/trousers")
    if not tr.is_empty(): tr.set_shader_input("tint", (0.55, 0.55, 0.7, 1))
    hr = m.find("**/hair")
    if not hr.is_empty(): hr.set_shader_input("tint", (0.45, 0.4, 0.38, 1))
    # thick, full moustache along the upper lip (3D) - ends drooping slightly, bushy layered lumps
    rng = random.Random(7); blobs = []
    for k in range(13):
        t = -1 + 2 * k / 12.0
        q = (0.036 * t, -0.0505 + 0.007 * t * t, -0.0565 - 0.010 * t * t)
        c = head_to_model(q); blobs.append((c[0], c[1], c[2], 0.0125, 0.0092, 0.0095 - 0.0022 * abs(t)))
    for k in range(10):
        t = rng.uniform(-0.9, 0.9); q = (0.033 * t, -0.0535 + 0.006 * t * t, -0.0585 - 0.009 * t * t + rng.uniform(-0.002, 0.002))
        c = head_to_model(q); blobs.append((c[0], c[1], c[2], 0.0095, 0.0065, 0.0068))
    mo = m.attach_new_node(blob_mesh("moustache", blobs, (0.035, 0.024, 0.02, 1))); shade(mo, app, 0.12, 0.3)
    p.moustache = mo
    p.wheel_pose = ((-20, 5), (-20, 5), (-72, 8), (-72, 8))     # elbows down, upper arms low: shoulders stay smooth
    return p


def beam_mesh(name, beams):
    """beams = [((x0, y0, z0), (x1, y1, z1), thick_x, thick_z, (r, g, b, a))] -> GeomNode of oriented boxes"""
    V, N, C, T, tris = [], [], [], [], []
    for (p0, p1, tx, tz, col) in beams:
        p0 = np.array(p0, float); p1 = np.array(p1, float); ax = p1 - p0; ax /= (np.linalg.norm(ax) or 1)
        up = np.array((0, 0, 1.0)) if abs(ax[2]) < 0.9 else np.array((1.0, 0, 0))
        u = np.cross(ax, up); u /= np.linalg.norm(u); v = np.cross(u, ax)
        cs = [p + su * u * tx / 2 + sv * v * tz / 2 for p in (p0, p1) for (su, sv) in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        for q in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
            a_, b_, c_ = cs[q[0]], cs[q[1]], cs[q[2]]; nrm = np.cross(b_ - a_, c_ - a_); nrm /= (np.linalg.norm(nrm) or 1)
            base = len(V)
            for k in q: V.append(cs[k]); N.append(nrm); C.append(col); T.append((1, 0, 0, 1))
            tris.append((base, base + 1, base + 2)); tris.append((base, base + 2, base + 3))
    return mesh_node(name, np.array(V, np.float32), np.array(N, np.float32), np.array(C, np.float32), np.array(T, np.float32), tris)


def taxi_glass(car, app):
    """v1.0.4 see-through JP TAXI cabin, done cleanly: the body paint stays fully opaque (no blending, own bin), only the
    glass is alpha-blended (inset a touch so it never z-fights the body), and a proper black window frame - rubber
    belt-line seals, A / B / C pillars, windscreen + rear-screen surrounds - covers the raw edge where the body mesh meets
    the glass, plus door cards / seats / dashboard inside so nothing looks hollow from the back seat."""
    m = car.model
    for nm in ("paint", "trim", "lamp_f", "lamp_r"):
        n = m.find("**/" + nm)
        if not n.is_empty():
            n.set_transparency(TransparencyAttrib.M_none, 2); n.set_depth_write(True, 2); n.set_bin("opaque", 0, 2)
    g = m.find("**/glass")
    if not g.is_empty():
        g.set_transparency(TransparencyAttrib.M_alpha); g.set_shader_input("tint", (0.55, 0.68, 0.75, 1)); g.set_alpha_scale(0.26)
        g.set_depth_write(False); g.set_bin("transparent", 30); g.set_two_sided(True)
        g.set_pos(0, -0.71, 1.24); g.set_scale(0.975, 0.985, 0.975); g.set_pos(g, 0, 0.71 / 0.985, -1.24 / 0.975)   # inset about the cabin centre
    blk = (0.035, 0.035, 0.04, 1); body = tuple(list(getattr(car, "paint_col", (0.9, 0.75, 0.2))) + [1])
    W = 0.79
    frame = []
    for sx in (-1, 1):
        x = sx * W
        frame += [((x, -1.40, 1.0), (x, 0.92, 1.0), 0.09, 0.14, blk),                     # belt-line seal along each side
                  ((x, 0.90, 1.0), (sx * 0.74, 0.50, 1.46), 0.07, 0.06, blk),           # A pillar
                  ((x, -0.24, 1.0), (sx * 0.765, -0.24, 1.49), 0.09, 0.06, blk),         # B pillar
                  ((x, -1.36, 1.02), (sx * 0.765, -0.98, 1.47), 0.08, 0.06, blk),        # C pillar
                  ((sx * 0.765, 0.50, 1.48), (sx * 0.765, -0.98, 1.50), 0.05, 0.05, blk)]  # roof rail / door top
    frame += [((-W, 0.90, 1.01), (W, 0.90, 1.01), 0.24, 0.2, blk),                         # windscreen base (scuttle)
              ((-0.74, 0.50, 1.47), (0.74, 0.50, 1.47), 0.08, 0.07, blk),                 # windscreen header
              ((-W, -1.40, 1.02), (W, -1.40, 1.02), 0.14, 0.12, blk),                     # rear-screen base
              ((-0.765, -0.98, 1.48), (0.765, -0.98, 1.48), 0.08, 0.07, blk)]             # rear-screen header
    fn = car.np.attach_new_node(beam_mesh("window_frame", frame)); shade(fn, app, 0.35)
    sp = car.spec; hw = sp["hw"] - 0.12; z = 0.05
    seat = (0.16, 0.14, 0.16, 1); dash = (0.08, 0.08, 0.09, 1); card = (0.12, 0.11, 0.12, 1)
    cab = box_mesh("cabin", [(-hw, -0.55, z + 0.15, -0.08, 0.05, z + 0.32, seat), (0.08, -0.55, z + 0.15, hw, 0.05, z + 0.32, seat),
                             (-hw, -0.65, z + 0.32, -0.08, -0.52, z + 0.72, seat), (0.08, -0.65, z + 0.32, hw, -0.52, z + 0.72, seat),
                             (-hw + 0.12, -0.63, z + 0.76, -0.2, -0.55, z + 0.9, seat), (0.2, -0.63, z + 0.76, hw - 0.12, -0.55, z + 0.9, seat),
                             (-hw, -1.55, z + 0.15, hw, -0.95, z + 0.32, seat), (-hw, -1.62, z + 0.32, hw, -1.5, z + 0.95, seat),
                             (-hw, 0.55, z + 0.55, hw, 0.95, z + 0.82, dash),
                             (-0.80, -1.5, 0.3, -0.74, 0.95, 0.97, card), (0.74, -1.5, 0.3, 0.80, 0.95, 0.97, card),   # door cards
                             (-0.8, -1.7, 0.3, 0.8, -1.62, 1.0, card), (-0.8, 0.95, 0.3, 0.8, 1.05, 0.95, card),       # parcel shelf / firewall
                             (-0.8, -1.5, 0.12, 0.8, 0.95, 0.16, card)])                                                # floor
    n = car.np.attach_new_node(cab); shade(n, app, 0.1)
    return n


# ================================================================ v1.0.4 AKARI-CHO ramen stall (yatai) with staff
class RamenStall:
    def __init__(self, game, near=(-250.0, 250.0)):
        from fs_people import Person
        self.g = game; app = game.app; w = game.world
        best = None
        for loop in w.ped_loops:
            for k, a in enumerate(loop):
                b = loop[(k + 1) % len(loop)]; d = math.hypot(a[0] - near[0], a[1] - near[1])
                if best is None or d < best[0]: best = (d, a, b)
        _, a, b = best; L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        self.x, self.y = a[0] + ux * min(8.0, L * 0.5), a[1] + uy * min(8.0, L * 0.5)
        self.h = math.degrees(math.atan2(-ux, uy)) + 90
        root = self.root = app.render.attach_new_node("ramen-stall"); root.set_pos(self.x, self.y, 0.15); root.set_h(self.h)
        wood = (0.42, 0.26, 0.14, 1); dark = (0.2, 0.12, 0.07, 1); red = (0.75, 0.08, 0.06, 1)
        n = root.attach_new_node(box_mesh("yatai", [(-1.3, -0.45, 0.0, 1.3, 0.45, 0.95, wood), (-1.4, -0.6, 0.95, 1.4, 0.55, 1.02, dark),
                                                   (-1.3, 0.35, 0.0, -1.22, 0.45, 2.25, dark), (1.22, 0.35, 0.0, 1.3, 0.45, 2.25, dark),
                                                   (-1.3, -0.45, 0.0, -1.22, -0.37, 2.25, dark), (1.22, -0.45, 0.0, 1.3, -0.37, 2.25, dark),
                                                   (-1.55, -0.85, 2.25, 1.55, 0.75, 2.36, red),
                                                   (-0.9, -0.3, 1.02, -0.6, 0.0, 1.12, (0.9, 0.9, 0.88, 1)), (0.5, -0.3, 1.02, 0.8, 0.0, 1.12, (0.9, 0.9, 0.88, 1))]))
        shade(n, app, 0.15)
        # noren curtain with the shop name + a red paper lantern
        tn = TextNode("noren"); tn.set_text("ラーメン  灯町"); tn.set_align(TextNode.A_center); tn.set_text_color(1, 1, 1, 1)
        if app.jpfont: tn.set_font(app.jpfont)
        tn.set_card_color(0.55, 0.05, 0.05, 1); tn.set_card_as_margin(0.6, 0.6, 0.5, 0.6)
        for sgn in (-1, 1):
            t = root.attach_new_node(tn.generate()); t.set_pos(0, sgn * 0.86 if sgn < 0 else 0.8, 1.95); t.set_scale(0.22); t.set_light_off()
            if sgn > 0: t.set_h(180)
            t.set_two_sided(True)
        lan = root.attach_new_node(blob_mesh("lantern", [(1.45, -0.7, 1.85, 0.16, 0.16, 0.22)], (1.0, 0.25, 0.12, 1))); lan.set_light_off()
        # staff behind the counter (white top, dark apron colours), same realistic skin as everyone
        st = self.staff = Person(game, "ana", 0, 0, 0, ped=True); st.np.reparent_to(root); st.np.set_pos(0, 0.7, -0.15); st.np.set_h(180)
        st.x, st.y = self.x, self.y
        for nm, c in (("tank", (3.8, 3.8, 3.8, 1)), ("straps", (3.8, 3.8, 3.8, 1)), ("trousers", (0.25, 0.25, 0.3, 1))):
            x = st.model.find("**/" + nm)
            if not x.is_empty(): x.set_shader_input("tint", c)
        for lg in (st.legL, st.legR):
            if not lg.is_empty(): lg.set_shader_input("tint", (0.25, 0.25, 0.3, 1))
        band = st.model.attach_new_node(blob_mesh("hachimaki", [(0, -0.01, 1.66, 0.098, 0.108, 0.018)], (0.95, 0.95, 0.95, 1))); shade(band, app, 0.1)
        st.set_arms((-30, 6), (-30, 6), (-50, 0), (-50, 0))
        w.grid.add_circle(self.x, self.y, 1.1, "p")
        self.cd = 1.0

    def update(self, dt):
        g = self.g; self.cd -= dt
        if g.pcar is not None or g.home: return
        px, py = g.player_pos(); d = math.hypot(px - self.x, py - self.y)
        if d < 7.0 and self.cd <= 0:
            self.staff.np.set_pos(0, 0.7, -0.15); g.npc_say("ramen", self.staff); self.cd = random.uniform(8, 13)
        t = g.time; self.staff.set_arms((-30 + 6 * math.sin(t * 2.0), 6), (-30 - 6 * math.sin(t * 2.0), 6), (-50, 0), (-50, 0))
