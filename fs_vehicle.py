"""Vehicles: original Blender-modelled cars (preserved look — never cel-shaded). + a carefully tuned, stable arcade driving model on a flat world
(no flipping possible, sub-stepped collision against buildings/props/cars, auto-unstick)."""
import math, os, random
from panda3d.core import (NodePath, TextNode, CardMaker, TransparencyAttrib, ColorBlendAttrib, Vec3, Filename, LODNode)
import fs_shaders

SPECS = {   # accel m/s2, vmax m/s, grip, mass, half length, half width, roof height, seat x
    "evo":    dict(acc=12.5, vmax=70.0, grip=9.2, mass=1420, hl=2.41, hw=0.95, roof=1.38, name="ENERASTIC MG EVO SEDAN"),
    "gts":    dict(acc=13.5, vmax=74.0, grip=9.5, mass=1350, hl=2.28, hw=1.0, roof=1.15, name="KAGEROU GT-S"),
    "coupe":  dict(acc=11.5, vmax=66.0, grip=8.5, mass=1300, hl=2.20, hw=0.93, roof=1.30, name="RAIJIN R9"),
    "sedan":  dict(acc=8.0, vmax=52.0, grip=7.0, mass=1450, hl=2.38, hw=0.91, roof=1.45, name="DEBAUCHE"),
    "taxi":   dict(acc=8.0, vmax=52.0, grip=7.0, mass=1450, hl=2.30, hw=0.88, roof=1.52, name="TOKO TAXI"),
    "police": dict(acc=11.0, vmax=68.0, grip=8.5, mass=1550, hl=2.43, hw=0.93, roof=1.47, name="PATROL INTERCEPTOR"),
    "hatch":  dict(acc=8.5, vmax=50.0, grip=7.5, mass=1150, hl=1.95, hw=0.87, roof=1.50, name="POCO HATCH"),
    "kei":    dict(acc=6.5, vmax=40.0, grip=7.0, mass=900, hl=1.70, hw=0.74, roof=1.85, name="CHIBI KEI"),
    "suv":    dict(acc=8.5, vmax=54.0, grip=7.0, mass=1900, hl=2.35, hw=0.98, roof=1.80, name="YAMA SUV"),
    "van":    dict(acc=6.0, vmax=42.0, grip=6.0, mass=2400, hl=2.70, hw=0.98, roof=2.35, name="HAKOBU VAN"),
    "ambulance": dict(acc=9.0, vmax=56.0, grip=7.0, mass=2400, hl=2.70, hw=0.98, roof=2.35, name="RESCUE 119"),
}
TRAFFIC_KINDS = ["sedan", "sedan", "taxi", "hatch", "kei", "suv", "van", "coupe", "hatch", "taxi", "evo", "suv", "sedan", "kei", "gts"]
TRAFFIC_COLS = [(0.85, 0.85, 0.88), (0.08, 0.08, 0.1), (0.55, 0.57, 0.6), (0.7, 0.08, 0.1), (0.12, 0.2, 0.5),
                (0.9, 0.9, 0.92), (0.15, 0.35, 0.25), (0.6, 0.5, 0.35), (0.85, 0.75, 0.2), (0.35, 0.1, 0.45),
                (0.62, 0.02, 0.04), (0.04, 0.05, 0.12), (0.4, 0.42, 0.45), (0.75, 0.73, 0.68), (0.1, 0.12, 0.1)]
_models = {}


def _load(app, name):
    if name not in _models:
        p = os.path.join(app.BASE, "assets", "models", name + ".bam")
        _models[name] = app.loader.load_model(Filename.from_os_specific(p)) if os.path.exists(p) else None
    return _models[name]


def load_model(app, kind, far=55.0):
    """v1.0.5.3: LODNode - full model (interior, detailed wheels) near, decimated car_<kind>_lod beyond `far` metres."""
    hi = _load(app, "car_%s" % kind); lo = _load(app, "car_%s_lod" % kind)
    root = NodePath("car")
    if lo is None:
        hi.copy_to(root); return root, None
    ln = LODNode("carlod"); lnp = root.attach_new_node(ln)
    hi.copy_to(lnp); lo.copy_to(lnp)
    ln.add_switch(far, 0.0); ln.add_switch(5000.0, far)
    return root, ln


class Car:
    _id = 0

    def __init__(self, game, kind, x, y, h, paint=(0.8, 0.1, 0.2), plate="", parked=False, role="traffic"):
        Car._id += 1; self.id = Car._id
        self.g = game; app = game.app; self.app = app
        self.kind = kind; self.spec = dict(SPECS[kind]); self.role = role
        self.x, self.y, self.h = x, y, h
        self.vx = self.vy = 0.0; self.w = 0.0
        self.steer = 0.0; self.throttle = 0.0; self.brake = 0.0; self.hand = False; self.nitro = False
        self.nitro_amt = 1.0; self.asleep = parked; self.sleep_t = 0.0
        self.driver = None          # "ai" | "player" | None
        self.passengers = []
        self.ai = None; self.dead = False; self.damage = 0.0; self.stuck_t = 0.0; self.contact = 0.0; self.drift = 0.0
        self.siren = kind == "police" or kind == "ambulance"; self.lights_on = False
        self.np = app.render.attach_new_node("car%d" % self.id)
        import fs_gfx
        m, self.lod = load_model(app, kind, fs_gfx.lod_far(app)); m.reparent_to(self.np); self.model = m
        A = lambda nm: list(m.find_all_matches("**/" + nm))
        self.paints = A("paint"); self.paint = self.paints[0] if self.paints else m.find("**/paint")
        self.wheels = [m.find("**/wheel_" + k) for k in ("FL", "FR", "RL", "RR")]
        self.wheels_all = [n for k in ("FL", "FR", "RL", "RR") for n in A("wheel_" + k)]
        self.set_paint(paint)
        fs_shaders.apply(m, app, gloss=0.55)
        for pn in self.paints: fs_shaders.apply(pn, app, gloss=0.85, clearcoat=1.0, tint=(paint[0], paint[1], paint[2], 1)); pn.set_two_sided(True)
        for g in A("glass"):        # v1.0.5.3: tinted see-through glass (interior visible), sorted after opaque geometry
            fs_shaders.apply(g, app, gloss=1.0, tint=(0.55, 0.55, 0.62, 1), clearcoat=0.6)
            g.set_transparency(TransparencyAttrib.M_alpha); g.set_bin("transparent", 10); g.set_depth_write(False)
        for t in A("trim"): fs_shaders.apply(t, app, gloss=0.45)
        for t in A("interior"): fs_shaders.apply(t, app, gloss=0.12)
        for nm in ("lamp_f", "lamp_r", "bar_red", "bar_blue"):
            for n in A(nm): fs_shaders.apply(n, app, gloss=0.2, emitboost=0.35, tint=(1, 1, 1, 1))
        self.lamps_r = A("lamp_r"); self.bars_r = A("bar_red"); self.bars_b = A("bar_blue")
        self.lamp_r = m.find("**/lamp_r"); self.bar_r = m.find("**/bar_red"); self.bar_b = m.find("**/bar_blue")
        for wnp in self.wheels_all: fs_shaders.apply(wnp, app, gloss=0.5)
        self.make_shadow()
        self.wheel_r = 0.34; self.wheel_rot = 0.0
        self.make_plates(plate or self.random_plate())
        self.make_glows()
        self.np.set_pos(x, y, 0); self.np.set_h(h)
        self.np.set_python_tag("car", self)

    @staticmethod
    def random_plate():
        return "%s %d-%02d" % (random.choice(["新光", "灯", "港", "桜"]), random.randint(10, 99), random.randint(10, 99))

    def set_paint(self, col):
        self.paint_col = tuple(col)
        for pn in getattr(self, "paints", [self.paint]):
            if not pn.is_empty(): pn.set_shader_input("tint", (col[0], col[1], col[2], 1))

    def set_lod_far(self, far):
        if self.lod is not None:
            self.lod.set_switch(0, far, 0.0); self.lod.set_switch(1, 5000.0, far)

    def make_shadow(self):
        """v1.0.5.4: soft contact shadow under the car (multiplicative darkening, never a glow/bloom)."""
        cm = CardMaker("shadow"); hw, hl = self.spec["hw"] + 0.55, self.spec["hl"] + 0.70
        cm.set_frame(-hw, hw, -hl, hl)
        q = self.np.attach_new_node(cm.generate()); q.set_p(-90); q.set_z(0.032)
        q.set_texture(self.g.world.T("glow.png", repeat=False)); q.set_color(0, 0, 0, 0.78)
        q.set_transparency(TransparencyAttrib.M_alpha); q.set_depth_write(False); q.set_depth_offset(2); q.set_bin("fixed", 5)
        q.set_light_off(); q.set_shader_off(1); self.shadow = q

    def make_plates(self, text):
        self.plate_text = text
        if getattr(self, "plates", None):
            for p in self.plates: p.remove_node()
        self.plates = []
        b = self.model.get_tight_bounds()
        for front in (True, False):
            y = (b[1][1] + 0.02) if front else (b[0][1] - 0.02)
            cm = CardMaker("plate"); cm.set_frame(-0.26, 0.26, -0.065, 0.065)
            p = self.model.attach_new_node(cm.generate()); p.set_pos(0, y, 0.42 if front else 0.55)   # v1.0.5.3: on the body, not the root
            p.set_h(180 if front else 0); p.set_color(0.92, 0.93, 0.9, 1); p.set_light_off(); p.set_two_sided(False); p.set_depth_offset(2); p.set_shader_off(10)   # plates use fixed-function colour (car shader made them black)
            tn = TextNode("pt"); tn.set_text(text[:10]); tn.set_align(TextNode.A_center)
            if self.app.jpfont: tn.set_font(self.app.jpfont)
            tn.set_text_color(0.05, 0.25, 0.12, 1)
            tp = p.attach_new_node(tn); tp.set_scale(0.075 if len(text) <= 8 else 0.06); tp.set_pos(0, -0.005, -0.026)
            self.plates.append(p)

    def make_glows(self):
        app = self.app
        b = self.model.get_tight_bounds()
        self.glows = self.np.attach_new_node("glows")
        tex = self.g.world.T("glow.png", repeat=False); beam = self.g.world.T("beam.png", repeat=False)
        # v1.0.5.3: no halo sprites (no glow). Lights cast onto the road instead: white headlight beam + red brake pool.
        cm = CardMaker("beam"); cm.set_frame(-3.5, 3.5, 0, 22)
        q = self.glows.attach_new_node(cm.generate()); q.set_p(-90); q.set_pos(0, b[1][1] - 0.2, 0.06); q.set_texture(beam)
        q.set_color(0.80, 0.90, 1.0, 0.55); self.beam = q          # cool white-blue LED beam on the road
        cm = CardMaker("bpool"); cm.set_frame(-1.3, 1.3, -2.6, 0)
        q = self.glows.attach_new_node(cm.generate()); q.set_p(-90); q.set_pos(0, b[0][1] + 0.1, 0.05); q.set_texture(tex)
        q.set_color(1.0, 0.08, 0.06, 0.0); self.brake_pool = q
        if self.siren:
            self.sglow = []
            for c, x in (((1, 0.1, 0.1, 1), -0.32), ((0.15, 0.35, 1, 1), 0.32)):
                cm = CardMaker("sg"); cm.set_frame(-1.4, 1.4, -1.4, 1.4)
                q = self.glows.attach_new_node(cm.generate()); q.set_p(-90); q.set_pos(x * 4, -0.15, 0.05); q.set_texture(tex)
                q.set_color(c[0], c[1], c[2], 0.5); q.set_scale(1.6); q.hide(); self.sglow.append(q)      # light cast on the road, not a halo
        self.glows.set_light_off(); self.glows.set_depth_write(False); self.glows.set_depth_offset(3); self.glows.set_bin("fixed", 20)
        self.glows.set_attrib(ColorBlendAttrib.make(ColorBlendAttrib.M_add, ColorBlendAttrib.O_incoming_alpha, ColorBlendAttrib.O_one))
        self.glows.set_shader_off(1); self.glows.set_two_sided(True)

    # ---------------------------------------------------------------- helpers
    @property
    def fwd(self):
        r = math.radians(self.h); return (-math.sin(r), math.cos(r))

    @property
    def speed(self):
        return math.hypot(self.vx, self.vy)

    def fspeed(self):
        f = self.fwd; return self.vx * f[0] + self.vy * f[1]

    def circles(self):
        f = self.fwd; o = self.spec["hl"] - self.spec["hw"]; r = self.spec["hw"]
        return [(self.x + f[0] * o, self.y + f[1] * o, r, 1), (self.x, self.y, r, 0), (self.x - f[0] * o, self.y - f[1] * o, r, -1)]

    def door_pos(self, side=1):
        """side +1 = driver (right-hand drive), -1 = passenger"""
        r = math.radians(self.h); rx, ry = math.cos(r), math.sin(r)
        d = self.spec["hw"] + 0.9
        return self.x + rx * d * side, self.y + ry * d * side

    def wake(self):
        self.asleep = False; self.sleep_t = 0.0

    # ---------------------------------------------------------------- physics
    def step(self, dt):
        if self.dead:
            return
        if self.asleep:
            return
        sp = self.spec
        surf = self.g.world.surface(self.x, self.y)
        vmax = sp["vmax"]; acc = sp["acc"]; grip = sp["grip"]
        if surf == "sand":
            vmax *= 0.55; grip *= 0.75; acc *= 0.7
        if self.nitro and self.nitro_amt > 0 and self.throttle > 0.1:
            acc *= 1.9; vmax *= 1.22; self.nitro_amt = max(0.0, self.nitro_amt - dt * 0.28)
        else:
            self.nitro_amt = min(1.0, self.nitro_amt + dt * (0.03 + 0.12 * min(1.0, self.drift)))
        f = self.fwd; rgt = (f[1], -f[0])
        vf = self.vx * f[0] + self.vy * f[1]
        vl = self.vx * rgt[0] + self.vy * rgt[1]
        thr = self.throttle
        # longitudinal
        if thr > 0:
            if vf < -0.5: vf += 20.0 * thr * dt                     # braking while reversing
            else: vf += acc * thr * max(0.0, 1.0 - (vf / vmax) ** 2) * dt
        elif thr < 0:
            if vf > 0.5: vf -= 22.0 * (-thr) * dt                   # brakes
            else: vf = max(-14.0, vf - acc * 0.6 * (-thr) * dt)       # reverse
        else:
            vf -= vf * 0.25 * dt + math.copysign(min(abs(vf), 0.8 * dt), vf)
        if self.hand:
            vf -= math.copysign(min(abs(vf), 6.0 * dt), vf)
        vf -= vf * abs(vf) * 0.0009 * dt                           # aero drag
        if vf > vmax * 1.05: vf -= (vf - vmax) * 2.0 * dt
        # steering -> yaw rate (speed sensitive), smooth response, no snap
        spd = abs(vf)
        maxrate = 2.3 * min(1.0, spd / 5.0) / (1.0 + spd / 32.0)
        if self.hand: maxrate *= 1.55
        target = -self.steer * maxrate * (1 if vf >= 0 else -1)
        self.w += (target - self.w) * min(1.0, 8.0 * dt)
        # lateral grip (handbrake -> controlled drift)
        g = grip * (0.22 if self.hand else 1.0)
        if abs(vl) > 6 and not self.hand: g *= 0.75
        vl *= math.exp(-g * dt)
        self.drift = abs(vl) if spd > 8 else 0.0
        self.h += math.degrees(self.w) * dt
        r = math.radians(self.h); f = (-math.sin(r), math.cos(r)); rgt = (f[1], -f[0])
        self.vx = f[0] * vf + rgt[0] * vl; self.vy = f[1] * vf + rgt[1] * vl
        # sub-stepped move + static collision
        n = max(1, int(math.ceil(self.speed * dt / 0.3)))
        sdt = dt / n; self.contact = max(0.0, self.contact - dt)
        for _ in range(n):
            self.x += self.vx * sdt; self.y += self.vy * sdt
            self.collide_static()
        if surf == "water" and self.role in ("player",):
            self.g.on_car_water(self)
        if self.speed < 0.15 and abs(self.throttle) < 0.05 and self.driver is None:
            self.sleep_t += dt
            if self.sleep_t > 2.0:
                self.asleep = True; self.vx = self.vy = 0.0; self.w = 0.0
        else:
            self.sleep_t = 0.0

    def collide_static(self):
        grid = self.g.world.grid
        for cx, cy, r, side in self.circles():
            px, py, nx, ny, tag = grid.push_circle(cx, cy, r)
            if tag is None:
                continue
            self.x += px; self.y += py
            vn = self.vx * nx + self.vy * ny
            if vn < 0:
                imp = -vn
                self.vx -= 1.25 * vn * nx; self.vy -= 1.25 * vn * ny
                self.vx *= 0.97; self.vy *= 0.97
                f = self.fwd
                cross = f[0] * ny - f[1] * nx
                self.w += side * cross * min(imp, 20) * 0.08
                self.w = max(-3.0, min(3.0, self.w))
                self.contact = 0.3
                if imp > 4:
                    self.g.on_impact(self, imp, None)

    def sync(self, dt):
        self.np.set_pos(self.x, self.y, 0); self.np.set_h(self.h)
        vf = self.fspeed()
        self.wheel_rot = (self.wheel_rot - math.degrees(vf * dt / self.wheel_r)) % 360
        for w in self.wheels_all:
            w.set_p(self.wheel_rot)
            if w.get_name() in ("wheel_FL", "wheel_FR"): w.set_h(-self.steer * 28)
        # body roll / pitch for motion feel (visual only).
        # v1.0.5.3 bumper-jump fix: pitch used to be set straight from the throttle key (-throttle*1.2 deg, gated on vf > 1), so every
        # key press/release, every AI throttle sign flip and every stop below 1 m/s snapped the body ~1.2 deg in ONE frame (≈5 cm at the
        # bumper, with the sign inverted: nose up under braking). The plates sat on the root node, so they did not pitch with the bumper.
        # Now: pitch/roll follow the real longitudinal/lateral acceleration through a damped spring, rate-limited -> no frame-to-frame pop.
        if dt > 0:
            ax = (vf - getattr(self, "_vf_prev", vf)) / dt
            self._vf_prev = vf
            ax = max(-14.0, min(14.0, ax))
            tp = max(-2.2, min(2.2, ax * 0.16))                          # brake (ax<0) -> nose dives, accel -> squats
            tr = max(-3.0, min(3.0, self.w * vf * 0.10))
            k = 1.0 - math.exp(-dt * 6.0)
            self._pit = getattr(self, "_pit", 0.0); self._rol = getattr(self, "_rol", 0.0)
            mx = 12.0 * dt                                                # max 12 deg/s change
            self._pit += max(-mx, min(mx, (tp - self._pit) * k)); self._rol += max(-mx, min(mx, (tr - self._rol) * k))
            self.model.set_p(-self._pit); self.model.set_r(self._rol)
        if not self.lamp_r.is_empty():
            br = 1.0 if (self.throttle < -0.1 and vf > 0.5) or self.hand else 0.35
            for n in self.lamps_r: n.set_shader_input("emitboost", br)
            if getattr(self, "brake_pool", None) is not None: self.brake_pool.set_alpha_scale(0.35 if br > 0.5 else 0.08)
        if self.siren and self.lights_on:
            t = self.g.time
            a = (math.sin(t * 18) > 0); b_ = not a
            for n in self.bars_r: n.set_shader_input("emitboost", 1.4 if a else 0.15)
            for n in self.bars_b: n.set_shader_input("emitboost", 1.4 if b_ else 0.15)
            self.sglow[0].show() if a else self.sglow[0].hide()
            self.sglow[1].show() if b_ else self.sglow[1].hide()
        elif self.siren:
            for q in self.sglow: q.hide()

    def destroy(self):
        self.np.remove_node(); self.dead = True


def collide_cars(cars, game):
    """pairwise circle collisions between awake/nearby cars (impulse based, mass weighted)."""
    n = len(cars)
    bucket = {}
    for c in cars:
        bucket.setdefault((int(c.x // 12), int(c.y // 12)), []).append(c)
    done = set()
    for c in cars:
        kx, ky = int(c.x // 12), int(c.y // 12)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for o in bucket.get((kx + dx, ky + dy), ()):
                    if o is c or (o.id, c.id) in done or (c.asleep and o.asleep):
                        continue
                    done.add((c.id, o.id))
                    _pair(c, o, game)


def _pair(a, b, game):
    if (a.x - b.x) ** 2 + (a.y - b.y) ** 2 > 49:
        return
    for ax, ay, ar, _ in a.circles():
        for bx, by, br, _ in b.circles():
            dx, dy = ax - bx, ay - by; d2 = dx * dx + dy * dy; rr = ar + br
            if d2 < rr * rr:
                d = math.sqrt(d2) or 1e-3; nx, ny = dx / d, dy / d; pen = rr - d
                ma, mb = a.spec["mass"], b.spec["mass"]
                if a.asleep: a.wake()
                if b.asleep: b.wake()
                wa = mb / (ma + mb); wb = ma / (ma + mb)
                a.x += nx * pen * wa; a.y += ny * pen * wa; b.x -= nx * pen * wb; b.y -= ny * pen * wb
                rv = (a.vx - b.vx) * nx + (a.vy - b.vy) * ny
                if rv < 0:
                    j = -(1.3) * rv / (1 / ma + 1 / mb)
                    a.vx += j / ma * nx; a.vy += j / ma * ny; b.vx -= j / mb * nx; b.vy -= j / mb * ny
                    a.w += random.uniform(-0.3, 0.3) * min(1, -rv / 10); b.w += random.uniform(-0.3, 0.3) * min(1, -rv / 10)
                    if -rv > 3:
                        game.on_impact(a, -rv, b)
                return
