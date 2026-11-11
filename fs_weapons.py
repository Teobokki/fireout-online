"""Weapons for ANA & DANIEL (shared): weapon wheel, melee + guns, ammo, effects, smashable street props.
Original procedural designs; non-gory (hits knock people down, no blood)."""
import math, random
from panda3d.core import NodePath, CardMaker, LineSegs, ColorBlendAttrib, TextNode, Point3
from direct.gui.DirectGui import DirectFrame, DirectButton, DGG
from direct.gui.OnscreenText import OnscreenText
from fs_geom import MB
import fs_ui as U
import fs_data as D

# id, name, kind, range, cooldown, power, ammo-per-pickup, sound, heat
WEAPONS = [
    dict(id="fists", name="FISTS", kind="melee", rng=1.6, cd=0.45, power=4.0, ammo=None, snd="swing", icon="FIST"),
    dict(id="bat", name="BASEBALL BAT", kind="melee", rng=2.1, cd=0.6, power=7.0, ammo=None, snd="swing", icon="BAT"),
    dict(id="pickaxe", name="PICKAXE", kind="melee", rng=2.3, cd=1.05, power=10.0, ammo=None, snd="swing_heavy", icon="AXE"),
    dict(id="taser", name="TASER", kind="stun", rng=9.0, cd=1.2, power=3.0, ammo=12, snd="taser", icon="ZAP"),
    dict(id="pistol", name="PISTOL", kind="gun", rng=60.0, cd=0.3, power=6.0, ammo=60, snd="pistol", icon="P"),
    dict(id="smg", name="SMG", kind="gun", rng=50.0, cd=0.09, power=4.0, ammo=150, snd="smg", icon="SMG"),
    dict(id="shotgun", name="SHOTGUN", kind="gun", rng=22.0, cd=0.9, power=9.0, ammo=24, snd="shotgun", icon="SG"),
]
W = {w["id"]: w for w in WEAPONS}
SHOP_POS = (-50.0, -94.0)


def weapon_model(wid):
    mb = MB("w_" + wid); wood = (0.45, 0.28, 0.14, 1); steel = (0.55, 0.57, 0.62, 1); black = (0.06, 0.06, 0.07, 1)
    if wid == "bat":
        mb.box(-0.03, -0.03, 0.0, 0.03, 0.03, 0.35, (0.75, 0.6, 0.38, 1)); mb.box(-0.045, -0.045, 0.35, 0.045, 0.045, 0.85, (0.82, 0.68, 0.45, 1))
    elif wid == "pickaxe":
        mb.box(-0.025, -0.025, 0.0, 0.025, 0.025, 0.85, wood)
        mb.box(-0.32, -0.035, 0.78, 0.32, 0.035, 0.86, steel); mb.box(-0.4, -0.02, 0.79, -0.32, 0.02, 0.84, steel); mb.box(0.32, -0.02, 0.8, 0.42, 0.02, 0.83, steel)
    elif wid == "taser":
        mb.box(-0.025, -0.02, 0.0, 0.025, 0.2, 0.06, (0.95, 0.8, 0.1, 1)); mb.box(-0.02, -0.04, -0.1, 0.02, 0.02, 0.0, black)
    elif wid == "pistol":
        mb.box(-0.02, -0.02, 0.0, 0.02, 0.2, 0.05, black); mb.box(-0.018, -0.02, -0.11, 0.018, 0.04, 0.0, black)
    elif wid == "smg":
        mb.box(-0.025, -0.1, 0.0, 0.025, 0.32, 0.07, black); mb.box(-0.018, 0.0, -0.18, 0.018, 0.05, 0.0, black); mb.box(-0.02, 0.1, -0.12, 0.02, 0.14, 0.0, black)
    elif wid == "shotgun":
        mb.box(-0.025, -0.25, 0.0, 0.025, 0.55, 0.05, black); mb.box(-0.03, -0.4, -0.06, 0.03, -0.12, 0.04, wood); mb.box(-0.028, 0.15, -0.04, 0.028, 0.38, 0.0, wood)
    else:
        return None
    return mb.node()


class Props:
    """Small smashable street props (traffic cones, crates, A-frame signs). Cars and melee/bullets knock them away."""
    def __init__(self, game):
        self.g = game; self.items = []; rnd = random.Random(7); w = game.world
        pts = [p for loop in w.ped_loops for p in loop]
        rnd.shuffle(pts)
        for (x, y) in pts[:70]:
            kind = rnd.choice(["cone", "cone", "crate", "sign"])
            mb = MB("prop")
            if kind == "cone":
                mb.box(-0.22, -0.22, 0, 0.22, 0.22, 0.05, (0.1, 0.1, 0.1, 1)); mb.box(-0.13, -0.13, 0.05, 0.13, 0.13, 0.5, (1.0, 0.35, 0.05, 1))
                mb.box(-0.1, -0.1, 0.25, 0.1, 0.1, 0.33, (0.95, 0.95, 0.95, 1)); r = 0.25
            elif kind == "crate":
                mb.box(-0.35, -0.35, 0, 0.35, 0.35, 0.6, (0.55, 0.4, 0.22, 1)); r = 0.4
            else:
                mb.box(-0.3, -0.05, 0, 0.3, 0.05, 0.9, (0.95, 0.85, 0.2, 1)); r = 0.3
            n = mb.node(); n.reparent_to(game.app.render); n.set_pos(x + rnd.uniform(-0.6, 0.6), y + rnd.uniform(-0.6, 0.6), 0.15); n.set_h(rnd.uniform(0, 360))
            n.set_light_off()
            self.items.append({"np": n, "x": n.get_x(), "y": n.get_y(), "r": r, "v": None, "t": 0.0, "kind": kind})

    def smash(self, it, dx, dy, power):
        if it["v"] is not None: return
        L = math.hypot(dx, dy) or 1; it["v"] = [dx / L * power, dy / L * power, 4.0 + power * 0.3]; it["t"] = 0.0
        self.g.app.sfx("bump", 0.5)

    def update(self, dt):
        g = self.g; c = g.pcar
        for it in self.items:
            n = it["np"]
            if it["v"] is None:
                for car in ([c] if c else []) + [o for o in g.cars_near(it["x"], it["y"], 5) if o is not c]:
                    if car.speed > 2 and math.hypot(car.x - it["x"], car.y - it["y"]) < car.spec["hl"] + it["r"]:
                        self.smash(it, car.vx, car.vy, min(14, car.speed * 0.8))
                continue
            v = it["v"]; it["t"] += dt
            n.set_pos(n.get_x() + v[0] * dt, n.get_y() + v[1] * dt, max(0.15, n.get_z() + v[2] * dt)); v[2] -= 18 * dt
            n.set_p(n.get_p() + 400 * dt); n.set_r(n.get_r() + 250 * dt)
            if it["t"] > 1.6:
                n.set_color_scale(1, 1, 1, max(0.0, 1 - (it["t"] - 1.6)))
            if it["t"] > 2.6:          # respawn quietly later
                n.hide()
            if it["t"] > 40 and not g.in_view(it["x"], it["y"]):
                it["v"] = None; n.show(); n.set_color_scale(1, 1, 1, 1); n.set_pos(it["x"], it["y"], 0.15); n.set_p(0); n.set_r(0)

    def destroy(self):
        for it in self.items: it["np"].remove_node()


class Arsenal:
    def __init__(self, game, save):
        self.g = game; self.app = game.app
        sv = save or {}
        self.ammo = {w["id"]: (sv.get("ammo", {}).get(w["id"], w["ammo"]) if w["ammo"] else None) for w in WEAPONS}
        self.cur = "fists"          # always start unarmed; nothing is held until picked from the weapon wheel
        self.cd = 0.0; self.aiming = False; self.wheel = None; self.wheel_sel = None; self.swing = 0.0
        self.fx = game.app.render.attach_new_node("weapon-fx"); self.fx.set_light_off(); self.fx.set_depth_write(False); self.fx.set_bin("fixed", 40)
        self.fx.set_attrib(ColorBlendAttrib.make(ColorBlendAttrib.M_add, ColorBlendAttrib.O_incoming_alpha, ColorBlendAttrib.O_one))
        self.fx_items = []; self.held = None; self.held_for = None
        self.props = Props(game)
        a = game.app
        self.lbl = U.text(a.a2dBottomRight, "", (-0.3, 0.7), 0.04, fg=U.GOLD, align=TextNode.A_right)
        for ev, fn in (("mouse1", self.fire), ("mouse3", lambda: self.set_aim(True)), ("mouse3-up", lambda: self.set_aim(False)),
                       ("wheel_up", lambda: self.cycle(1)), ("wheel_down", lambda: self.cycle(-1)),
                       ("tab", self.open_wheel), ("tab-up", self.close_wheel)):
            a.accept(ev, fn)
        self.refresh_held()

    # ---------------------------------------------------------------- selection
    def cycle(self, d):
        if self.g.blocked() or self.g.phone: return
        ids = [w["id"] for w in WEAPONS]; self.equip(ids[(ids.index(self.cur) + d) % len(ids)])

    def equip(self, wid):
        if wid not in W: return
        self.cur = wid; self.app.sfx("click", 0.5); self.g.toast(W[wid]["name"], 1.2); self.refresh_held()

    def refresh_held(self):
        me = self.g.me()
        if self.held is not None and self.held_for is me and getattr(self, "_held_id", None) == self.cur and me.in_car is None: return
        if self.held is not None:
            self.held.remove_node(); self.held = None
            if getattr(self, "held_for", None) is not None:
                self.held_for.arm_pose = None
                if hasattr(self.held_for, "set_grip"): self.held_for.set_grip(False, False)
        if me.in_car is not None: return
        m = weapon_model(self.cur)
        if m is None: return
        hand = getattr(me, "handR", None)
        if hand is not None and not hand.is_empty():      # v1.0.3: the weapon sits in ANA / DANIEL's right hand
            m.reparent_to(hand); m.set_pos(me.np, hand.get_pos(me.np))
        else:
            m.reparent_to(me.np); m.set_pos(0.24, 0.12, 0.92)
        m.set_hpr(me.np, 0, 70 if W[self.cur]["kind"] == "melee" else 0, 0)
        m.set_light_off(); self.held = m; self.held_for = me; self._held_id = self.cur

    def open_wheel(self):
        g = self.g
        if self.wheel or g.blocked() or g.phone or g.ride: return
        a = self.app; o = self.wheel = DirectFrame(parent=a.aspect2d, frameColor=(0, 0, 0, 0.35), frameSize=(-3, 3, -1, 1), state=DGG.NORMAL)
        U.text(o, "WEAPONS", (0, 0.03), 0.06, fg=U.PINK); U.text(o, "click a weapon  /  release Tab", (0, -0.04), 0.028, font=U.FONT_PLAIN)
        n = len(WEAPONS)
        for k, w in enumerate(WEAPONS):
            ang = math.pi / 2 - k * 2 * math.pi / n; x, y = math.cos(ang) * 0.48, math.sin(ang) * 0.48
            am = self.ammo[w["id"]]
            b = U.button(o, w["icon"], (x, y), self.pick, w=0.12, h=0.12, scale=0.06, extra=[w["id"]],
                         edge=U.CYAN if w["id"] == self.cur else U.PINK, font=a.jpfont)
            U.text(o, w["name"] + ("" if am is None else "  %d" % am), (x, y - 0.165), 0.03, font=U.FONT_PLAIN)
            b.btn.bind(DGG.ENTER, lambda e, wid=w["id"]: setattr(self, "wheel_sel", wid))
        g.time_scale = 0.25; self.wheel_sel = None

    def pick(self, wid):
        self.equip(wid); self.close_wheel(force=True)

    def close_wheel(self, force=False):
        if not self.wheel: return
        if self.wheel_sel and not force: self.equip(self.wheel_sel)
        self.wheel.destroy(); self.wheel = None; self.g.time_scale = 1.0

    def toggle_wheel(self):
        if self.wheel: self.close_wheel(force=True)
        else: self.open_wheel()

    def set_aim(self, on):
        self.aiming = bool(on) and self.g.pcar is None and self.g.ride is None
        if on is False: self.g.vb["v_aim"] = False

    def refill(self):
        cost = 300
        if self.g.cash < cost: self.g.toast("Not enough cash (¥300)"); self.g.npc_say("shop_poor", who="店員"); return
        self.g.cash -= cost
        for w in WEAPONS:
            if w["ammo"]: self.ammo[w["id"]] = w["ammo"]
        self.app.sfx("checkpoint", 0.6); self.g.toast("KAZAN SUPPLY: ammo refilled  -¥300", 2.5); self.g.npc_say("shop", who="KAZAN SUPPLY 店員")

    # ---------------------------------------------------------------- attack
    def over_gui(self):
        mw = self.app.mouseWatcherNode
        return mw is not None and mw.get_over_region() is not None

    def fire(self, from_button=False):
        g = self.g
        if not from_button and self.over_gui(): return
        if g.blocked() or g.phone or g.pcar or g.ride or self.wheel or self.cd > 0: return
        me = g.me()
        if me.knock > 0: return
        w = W[self.cur]
        if w["ammo"] is not None:
            if self.ammo[self.cur] <= 0: self.app.sfx("empty", 0.6); g.toast("Out of ammo - refill at KAZAN SUPPLY", 1.8); self.cd = 0.3; return
            self.ammo[self.cur] -= 1
        self.cd = w["cd"]; self.app.sfx(w["snd"], 0.8)
        yaw = g.cam_yaw if self.aiming else me.h
        me.h = yaw if self.aiming else me.h
        r = math.radians(yaw); fx, fy = -math.sin(r), math.cos(r)
        ox, oy, oz = me.x + fx * 0.4, me.y + fy * 0.4, 1.3
        if w["kind"] == "melee":
            self.swing = 0.35 if w["id"] != "pickaxe" else 0.6
            self.hit_scan(me, ox, oy, fx, fy, w["rng"], w["power"], melee=True)
            return
        spread = 0.0 if w["id"] != "shotgun" else 0.12
        for k in range(1 if w["id"] != "shotgun" else 5):
            a = r + random.uniform(-spread, spread) + (random.uniform(-0.03, 0.03) if w["id"] == "smg" else 0)
            dx, dy = -math.sin(a), math.cos(a)
            end = self.hit_scan(me, ox, oy, dx, dy, w["rng"], w["power"], stun=w["kind"] == "stun")
            self.tracer((ox, oy, oz), (end[0], end[1], 1.1), (0.4, 0.8, 1.0) if w["kind"] == "stun" else (1.0, 0.85, 0.5))
        self.flash(ox + fx * 0.3, oy + fy * 0.3, oz, (0.5, 0.8, 1.0) if w["kind"] == "stun" else (1.0, 0.75, 0.35))
        # gunfire scares people and draws police attention
        if w["kind"] == "gun":
            for p in g.peds:
                if math.hypot(p.x - me.x, p.y - me.y) < 35: p.flee = 4.0; p.flee_from = (me.x, me.y)
            if any(math.hypot(c.x - me.x, c.y - me.y) < 80 for c in g.cars if c.kind == "police") and g.heat < 2:
                g.add_heat(1, "Shots fired near the police!")

    def hit_scan(self, me, ox, oy, dx, dy, rng, power, melee=False, stun=False):
        g = self.g; best = None; buddy = g.buddy()
        lim = rng
        # buildings block shots
        steps = int(rng / 2)
        for s in range(1, steps + 1):
            if g.world.grid.segment_blocked(ox, oy, ox + dx * s * 2, oy + dy * s * 2):
                lim = (s - 1) * 2 + 1; break
        def test(x, y, rad):
            t = (x - ox) * dx + (y - oy) * dy
            if t < 0 or t > lim: return None
            lat = abs((x - ox) * dy - (y - oy) * dx)
            return t if lat < rad + (0.5 if melee else 0.0) else None
        for p in g.peds:
            if p.knock > 0: continue
            t = test(p.x, p.y, 0.45)
            if t is not None and (best is None or t < best[0]): best = (t, "ped", p)
        for c in g.cars_near(ox, oy, rng + 3):
            for cx, cy, rr, _ in c.circles():
                t = test(cx, cy, rr)
                if t is not None and (best is None or t < best[0]): best = (t, "car", c)
        for it in self.props.items:
            if it["v"] is not None: continue
            t = test(it["x"], it["y"], it["r"])
            if t is not None and (best is None or t < best[0]): best = (t, "prop", it)
        if best is None:
            return (ox + dx * lim, oy + dy * lim)
        t, kind, obj = best; hx, hy = ox + dx * t, oy + dy * t
        if kind == "ped":
            obj.knock_down(dx, dy, power * (0.6 if stun else 1.0)); obj.knock = 4.5 if stun else 2.8
            obj.flee = 5.0; obj.flee_from = (me.x, me.y); self.app.sfx("hit", 0.7); g.say_line(obj, "scared")
            if any(math.hypot(c.x - me.x, c.y - me.y) < 70 for c in g.cars if c.kind == "police"): g.add_heat(1, "Assault witnessed by police!")
        elif kind == "car":
            obj.wake(); obj.vx += dx * power * 0.15; obj.vy += dy * power * 0.15; self.app.sfx("bump", 0.5)
            if obj.kind == "police": g.add_heat(1, "Attacked a police car!"); g.make_cop(obj)
            elif obj.driver == "ai" and not getattr(obj, "racer", False):
                obj.ai.speed = 22.0 if hasattr(obj.ai, "speed") else None
        elif kind == "prop":
            self.props.smash(obj, dx, dy, 4 + power * 0.8)
        self.spark(hx, hy, 1.0 if kind != "prop" else 0.4)
        return (hx, hy)

    # ---------------------------------------------------------------- effects
    def _card(self, x, y, z, s, col, life):
        cm = CardMaker("fx"); cm.set_frame(-s, s, -s, s)
        n = self.fx.attach_new_node(cm.generate()); n.set_pos(x, y, z); n.set_billboard_point_eye()
        n.set_texture(self.g.world.T("glow.png", repeat=False)); n.set_color(col[0], col[1], col[2], 1)
        self.fx_items.append([n, life, life])

    def flash(self, x, y, z, col):
        self._card(x, y, z, 0.35, col, 0.07)

    def spark(self, x, y, z):
        for _ in range(4):
            self._card(x + random.uniform(-0.2, 0.2), y + random.uniform(-0.2, 0.2), z + random.uniform(-0.2, 0.3), 0.18, (1.0, 0.8, 0.4), 0.18)

    def tracer(self, a, b, col):
        ls = LineSegs(); ls.set_thickness(2.0); ls.set_color(col[0], col[1], col[2], 1); ls.move_to(*a); ls.draw_to(*b)
        n = self.fx.attach_new_node(ls.create()); self.fx_items.append([n, 0.08, 0.08])

    def update(self, dt):
        g = self.g; self.cd = max(0.0, self.cd - dt)
        if g.vb.get("v_fire") and W[self.cur]["id"] == "smg": self.fire(from_button=True)
        mw = self.app.mouseWatcherNode
        from panda3d.core import MouseButton
        self.aiming = g.pcar is None and g.ride is None and not g.blocked() and (bool(g.vb.get("v_aim")) or (mw is not None and mw.is_button_down(MouseButton.three())))
        self.refresh_held()
        me = g.me(); k = W[self.cur]["kind"]
        in_hand = self.held is not None and self.held.get_parent().get_name() == "handR"
        # arm poses (negative pitch = raised forward): guns/taser raised two-handed when aiming, lowered in the right hand otherwise;
        # melee weapons are carried in the right hand and swung with the arm; fists punch with the right arm.
        pose = None
        if me.in_car is None:
            if self.swing > 0:
                self.swing -= dt; ph = min(1.0, 1 - self.swing / (0.35 if self.cur != "pickaxe" else 0.6)); sp = math.sin(ph * math.pi)
                pose = (-80 * sp, None, -70 + 60 * sp, None) if self.cur == "fists" else (-25 - 95 * sp, None, -30 + 20 * sp, None)
                if self.held is not None: self.held.set_hpr(me.np, 0, 70 - 160 * sp, 0)
            elif self.cur == "fists": pose = None
            elif k == "melee":
                pose = (-22, None, -45, None)
                if self.held is not None: self.held.set_hpr(me.np, 0, 70, 0)
            elif self.aiming:
                pose = (-84, -66, 0, -28)
                if self.held is not None: self.held.set_hpr(me.np, 0, 0, 0)
            else:
                pose = (-10, None, -22, None)
                if self.held is not None: self.held.set_hpr(me.np, 0, -60, 0)
        me.arm_pose = pose
        if hasattr(me, "set_grip") and me.in_car is None:     # hands close around a held weapon, a punch is a fist, otherwise relaxed open fingers
            gr = (self.held is not None or (self.cur == "fists" and self.swing > 0))
            gl = self.held is not None and self.aiming and k != "melee"
            if getattr(me, "grip", None) != (gr, gl): me.set_grip(gr, gl)
        if self.held is not None and not in_hand:
            if self.aiming: self.held.set_pos(0.22, 0.45, 1.32)
            elif k != "melee": self.held.set_pos(0.24, 0.12, 0.92)
        for it in list(self.fx_items):
            it[1] -= dt
            if it[1] <= 0: it[0].remove_node(); self.fx_items.remove(it)
            else: it[0].set_alpha_scale(it[1] / it[2])
        self.props.update(dt)
        w = W[self.cur]; am = self.ammo[self.cur]
        self.lbl.setText("" if g.pcar or g.ride or self.cur == "fists" or getattr(g, "home", None) else (w["name"] + ("" if am is None else "   %d" % am) + ("   [AIM]" if self.aiming else "")))

    def unequip(self):
        self.cur = "fists"; self.refresh_held()

    def save(self):
        return {"ammo": {k: v for k, v in self.ammo.items() if v is not None}, "weapon": self.cur}

    def destroy(self):
        for ev in ("mouse1", "mouse3", "mouse3-up", "wheel_up", "wheel_down", "tab", "tab-up"): self.app.ignore(ev)
        if self.wheel: self.wheel.destroy()
        if self.held is not None: self.held.remove_node()
        self.fx.remove_node(); self.lbl.destroy(); self.props.destroy()
