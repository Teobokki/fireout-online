"""FIREOUT ONLINE v1.0.4 - food & drink: per-item 3D props, the animated eat / drink sequence (house EAT SNACK, pause-menu
FOOD, bar drinks) shared by ANA and DANIEL."""
import math, random
from panda3d.core import TextNode
from fs_miyo import blob_mesh, box_mesh, shade

# id, Japanese, English, price (yen), health, kind (food / drink / alcohol), units of intoxication (+) / sobering (-)
FOODS = [("burger", "バーガー", "BURGER", 600, 45, "food", 0), ("onigiri", "おにぎり", "ONIGIRI", 150, 25, "food", 0),
         ("sushi", "寿司", "SUSHI", 900, 40, "food", 0), ("ramen", "カップ麺", "RAMEN CUP", 250, 35, "food", 0),
         ("takoyaki", "たこ焼き", "TAKOYAKI", 450, 30, "food", 0), ("gyoza", "餃子", "GYOZA", 400, 30, "food", 0),
         ("taiyaki", "たい焼き", "TAIYAKI", 200, 20, "food", 0), ("pocky", "ポッキー", "POCKY", 160, 15, "food", 0),
         ("melonpan", "メロンパン", "MELON PAN", 180, 20, "food", 0), ("bento", "弁当", "BENTO", 700, 50, "food", 0),
         ("water", "水", "WATER", 100, 5, "drink", -1.5), ("greentea", "緑茶", "GREEN TEA", 150, 8, "drink", -0.5)]
SNACKS = ("onigiri", "chips", "pocky")        # house fridge / cupboard
INFO = {f[0]: f for f in FOODS}
INFO["chips"] = ("chips", "ポテトチップス", "CHIPS", 0, 20, "food", 0)
for _b in (("beer", "ビール", "BEER", 600, 3, "alcohol", 1.0), ("sake", "日本酒", "SAKE", 800, 3, "alcohol", 1.4),
           ("highball", "ハイボール", "HIGHBALL", 700, 3, "alcohol", 1.2)):
    INFO[_b[0]] = _b

W = (0.96, 0.95, 0.92, 1); NORI = (0.04, 0.07, 0.05, 1); BUN = (0.80, 0.50, 0.20, 1); WOOD = (0.75, 0.6, 0.38, 1)


def _sticks(L=0.21, x=0.0):
    return [(x - 0.005, -0.006, -L + 0.03, x - 0.001, -0.002, 0.03, WOOD), (x + 0.006, -0.006, -L + 0.03, x + 0.010, -0.002, 0.03, WOOD)]


def build_prop(fid, app):
    """returns (root, eaten_part): a NodePath whose origin is the grip point; eaten_part shrinks bite by bite."""
    from panda3d.core import NodePath
    root = NodePath("food-" + fid); eat = root.attach_new_node("eat"); extra = root.attach_new_node("keep")
    def add(parent, node, gloss=0.2): n = parent.attach_new_node(node); shade(n, app, gloss); return n
    if fid == "burger":
        add(eat, blob_mesh("bun0", [(0, 0, 0.0, 0.055, 0.055, 0.016)], BUN))
        add(eat, blob_mesh("patty", [(0, 0, 0.018, 0.058, 0.058, 0.012)], (0.28, 0.13, 0.06, 1)))
        add(eat, box_mesh("cheese", [(-0.05, -0.05, 0.028, 0.05, 0.05, 0.033, (1.0, 0.75, 0.1, 1))]))
        add(eat, blob_mesh("lettuce", [(0, 0, 0.036, 0.062, 0.062, 0.006)], (0.35, 0.7, 0.15, 1)))
        add(eat, blob_mesh("top", [(0, 0, 0.042, 0.057, 0.057, 0.034), ], BUN), 0.4)
        eat.set_hpr(0, 90, 0)                                          # held upright, top bun towards the face
    elif fid in ("onigiri",):
        k = 1.45
        add(eat, blob_mesh("rice", [(x * k, y * k, z * k, rx * k, ry * k, rz * k) for x, y, z, rx, ry, rz in
                                    [(0, 0, 0.040, 0.020, 0.018, 0.016), (-0.026, 0, 0.005, 0.020, 0.018, 0.016), (0.026, 0, 0.005, 0.020, 0.018, 0.016),
                                     (0, 0, 0.012, 0.034, 0.019, 0.026)]], W))
        add(eat, box_mesh("nori", [(-0.032, -0.029, -0.017, 0.032, 0.029, 0.034, NORI)]))
        eat.set_hpr(0, 90, 0)
    elif fid == "sushi":
        add(extra, box_mesh("sticks", _sticks()))
        add(eat, blob_mesh("rice", [(0, -0.003, 0.05, 0.017, 0.014, 0.028)], W))
        add(eat, box_mesh("salmon", [(-0.02, -0.02, 0.018, 0.0, -0.008, 0.084, (1.0, 0.45, 0.22, 1))]), 0.6)
        tray = add(extra, box_mesh("tray", [(-0.06, 0.02, -0.05, 0.06, 0.10, -0.04, (0.1, 0.1, 0.1, 1)), (-0.045, 0.04, -0.04, -0.015, 0.08, -0.02, W),
                                             (-0.045, 0.04, -0.02, -0.015, 0.08, -0.012, (1.0, 0.45, 0.22, 1)),
                                             (0.015, 0.04, -0.04, 0.045, 0.08, -0.02, W), (0.015, 0.04, -0.02, 0.045, 0.08, -0.012, (0.85, 0.15, 0.15, 1))]))
        tray.hide(); root.set_python_tag("tray", tray)
    elif fid == "ramen":
        add(extra, box_mesh("cup", [(-0.04, -0.04, -0.04, 0.04, 0.04, 0.05, W), (-0.041, -0.041, 0.0, 0.041, 0.041, 0.02, (0.85, 0.1, 0.1, 1))]))
        add(eat, blob_mesh("noodles", [(0, 0, 0.05, 0.036, 0.036, 0.008)], (0.95, 0.82, 0.45, 1)))
        add(extra, box_mesh("sticks", [(0.01, -0.004, 0.02, 0.014, 0.0, 0.22, WOOD), (0.02, -0.004, 0.02, 0.024, 0.0, 0.22, WOOD)]))
    elif fid == "takoyaki":
        add(extra, box_mesh("boat", [(-0.05, -0.035, -0.02, 0.05, 0.035, -0.012, (0.85, 0.75, 0.55, 1))]))
        add(eat, blob_mesh("balls", [(x, y, 0.004, 0.017, 0.017, 0.015) for x in (-0.025, 0.0, 0.025) for y in (-0.014, 0.014)], (0.68, 0.38, 0.12, 1)))
        add(eat, box_mesh("sauce", [(-0.04, -0.03, 0.016, 0.04, 0.03, 0.02, (0.25, 0.1, 0.05, 1))]))
        add(extra, box_mesh("pick", [(0.024, 0.012, 0.0, 0.027, 0.015, 0.09, WOOD)]))
    elif fid == "gyoza":
        add(extra, box_mesh("sticks", _sticks()))
        add(eat, blob_mesh("gyoza", [(0.004 + 0.014 * k, -0.003, 0.05, 0.015, 0.012, 0.015) for k in (-1, 0, 1)] + [(0.004, -0.003, 0.062, 0.036, 0.011, 0.007)], (0.93, 0.83, 0.6, 1)))
    elif fid == "taiyaki":
        add(eat, blob_mesh("fish", [(0, 0, 0.03, 0.035, 0.012, 0.04), (0, 0, 0.0, 0.03, 0.011, 0.03)], (0.78, 0.48, 0.16, 1)))
        add(eat, box_mesh("tail", [(-0.025, -0.008, -0.06, 0.025, 0.008, -0.025, (0.72, 0.42, 0.13, 1))]))
    elif fid == "pocky":
        add(extra, box_mesh("box", [(-0.03, -0.008, -0.07, 0.03, 0.008, 0.02, (0.85, 0.08, 0.1, 1))]))
        add(eat, box_mesh("sticks", [(x - 0.002, -0.002, 0.02, x + 0.002, 0.002, 0.10, (0.35, 0.15, 0.06, 1)) for x in (-0.012, -0.004, 0.004, 0.012)]))
    elif fid == "melonpan":
        add(eat, blob_mesh("melonpan", [(0, 0, 0.0, 0.055, 0.055, 0.03)], (0.92, 0.78, 0.35, 1)))
        add(eat, blob_mesh("crust", [(0, 0, 0.012, 0.052, 0.052, 0.022)], (0.95, 0.86, 0.45, 1)))
        eat.set_hpr(0, 90, 0)
    elif fid == "bento":
        add(extra, box_mesh("box", [(-0.08, -0.06, -0.03, 0.08, 0.06, 0.0, (0.1, 0.1, 0.1, 1)), (-0.083, -0.063, -0.03, 0.083, 0.063, -0.022, (0.7, 0.1, 0.1, 1))]))
        add(eat, box_mesh("food", [(-0.07, -0.05, 0.0, -0.005, 0.05, 0.012, W), (0.0, -0.05, 0.0, 0.07, 0.0, 0.016, (0.85, 0.5, 0.2, 1)),
                                   (0.0, 0.005, 0.0, 0.07, 0.05, 0.014, (0.4, 0.7, 0.2, 1)), (-0.045, -0.01, 0.012, -0.03, 0.005, 0.018, (0.85, 0.1, 0.12, 1))]))
        add(extra, box_mesh("sticks", [(0.03, -0.004, 0.02, 0.034, 0.0, 0.2, WOOD), (0.04, -0.004, 0.02, 0.044, 0.0, 0.2, WOOD)]))
    elif fid == "chips":
        add(extra, box_mesh("bag", [(-0.05, -0.016, -0.06, 0.05, 0.016, 0.07, (0.95, 0.75, 0.1, 1)), (-0.03, -0.017, -0.01, 0.03, 0.017, 0.03, (0.85, 0.1, 0.1, 1))]))
        add(eat, blob_mesh("chip", [(0, 0, 0.09, 0.02, 0.004, 0.016)], (0.95, 0.8, 0.35, 1)))
    elif fid in ("water", "greentea", "beer", "sake", "highball"):
        if fid in ("water", "greentea"):
            body = (0.75, 0.88, 1.0, 0.55) if fid == "water" else (0.35, 0.65, 0.25, 0.75)
            n = add(extra, blob_mesh("bottle", [(0, 0, 0.04, 0.032, 0.032, 0.09)], body), 0.8)
            add(extra, box_mesh("cap", [(-0.012, -0.012, 0.125, 0.012, 0.012, 0.145, (1, 1, 1, 1) if fid == "water" else (0.1, 0.4, 0.1, 1))]))
            add(extra, box_mesh("label", [(-0.033, -0.033, 0.02, 0.033, 0.033, 0.06, (0.2, 0.45, 0.9, 1) if fid == "water" else (0.9, 0.9, 0.85, 1))]))
            liq = (0.8, 0.9, 1.0, 0.6) if fid == "water" else (0.55, 0.75, 0.2, 0.8)
            add(eat, blob_mesh("liquid", [(0, 0, 0.02, 0.028, 0.028, 0.06)], liq))
        else:
            liq = {"beer": (0.95, 0.65, 0.1, 0.85), "sake": (0.95, 0.95, 0.85, 0.6), "highball": (0.95, 0.8, 0.45, 0.7)}[fid]
            r, hgt = {"beer": (0.04, 0.15), "sake": (0.025, 0.05), "highball": (0.035, 0.14)}[fid]
            n = add(extra, box_mesh("glass", [(-r, -r, -0.02, r, r, hgt - 0.02, (0.85, 0.92, 1.0, 0.25))]), 0.9)
            add(eat, box_mesh("liquid", [(-r + 0.004, -r + 0.004, -0.016, r - 0.004, r - 0.004, hgt - 0.05, liq)]))
            if fid == "beer": add(eat, box_mesh("foam", [(-r + 0.004, -r + 0.004, hgt - 0.05, r - 0.004, r - 0.004, hgt - 0.03, (1, 0.97, 0.9, 1))]))
            if fid == "beer": add(extra, box_mesh("handle", [(r, -0.005, 0.01, r + 0.03, 0.005, 0.10, (0.85, 0.92, 1.0, 0.3))]))
        from panda3d.core import TransparencyAttrib
        root.set_transparency(TransparencyAttrib.M_alpha); root.set_depth_write(False); root.set_bin("transparent", 40)
    else:
        add(eat, blob_mesh("food", [(0, 0, 0, 0.04, 0.04, 0.04)], W))
    return root, eat


# arm keyframe poses: (armR pitch, armR roll, foreR pitch, foreR roll, body pitch)
REST = (-4, 4, -10, 0, 0)
REACH = (-72, 8, -12, 0, 2)
HOLD = (-32, -8, -105, -28, 0)
MOUTH = (-58, -15, -124, -40, 3)
DRINK = (-64, -14, -128, -40, -7)


def _ease(t): t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)


class EatAnim:
    """one smooth, keyframed eat / drink sequence (no popping): optional fridge reach -> item in the hand -> to the mouth,
    3 bites (the item shrinks, head nods, jaw chews) or 3 sips (the liquid goes down) -> finish -> put away / bin it."""
    def __init__(self, game, person, fid, fridge=None, on_done=None, two_hand=False, glass_put=None):
        self.g = game; self.p = person; self.fid = fid; self.fridge = fridge; self.done_cb = on_done; self.t = 0.0
        self.drink = INFO[fid][5] in ("drink", "alcohol"); self.finished = False; self.glass_put = glass_put
        self.prop, self.eat = build_prop(fid, game.app); self.prop.set_scale(0.001)
        self.two = two_hand or fid in ("burger", "melonpan", "bento", "ramen", "takoyaki")
        hand = person.handR if not person.handR.is_empty() else person.np
        self.prop.reparent_to(hand); self.prop.set_light_off(1)
        self.pre = 0.9 if fridge is not None else (0.6 if glass_put is not None else 0.0)
        self.T = self.pre + 4.4
        person.anim_lock = True; person.set_grip(True, self.two)
        k = self.pre; bt = [k + 1.05, k + 1.95, k + 2.85]
        P = DRINK if self.drink else MOUTH
        self.keys = ([(0.0, REST), (0.45, REACH), (0.9, HOLD)] if fridge is not None else
                     ([(0.0, REST), (0.6, REACH)] if glass_put is not None else [(0.0, REST)])) + \
            [(k + 0.45, HOLD), (k + 0.9, P), (k + 1.25, P), (k + 1.5, HOLD if not self.drink else P), (k + 1.8, P), (k + 2.15, P),
             (k + 2.45, HOLD if not self.drink else P), (k + 2.7, P), (k + 3.05, P), (k + 3.4, HOLD), (k + 3.8, REACH), (k + 4.4, REST)]
        self.bites = bt
        if fridge is not None: fridge.set_h(0)
        if INFO[fid][0] in ("sushi", "gyoza", "ramen"): pass

    def pose_at(self, t):
        ks = self.keys
        for (t0, a), (t1, b) in zip(ks, ks[1:]):
            if t <= t1:
                u = _ease((t - t0) / max(1e-6, t1 - t0)); return tuple(x + (y - x) * u for x, y in zip(a, b))
        return ks[-1][1]

    def update(self, dt):
        if self.finished: return True
        self.t += dt; t = self.t; p = self.p; k = self.pre
        ar, rr, fr, fro, bp = self.pose_at(t)
        # bites: a little forward nod of the head/upper body + chewing (jaw) for a moment after each bite
        nod = 0.0; chew = 0.0; left = 1.0
        for b in self.bites:
            if t > b: left -= 1 / 3.0
            d = t - b
            if -0.15 < d < 0.15: nod += (1 - abs(d) / 0.15) * (3.5 if not self.drink else -2.0)
            if 0.1 < d < 0.75 and not self.drink: chew = abs(math.sin((d - 0.1) * 14.0))
        if not self.drink: left = max(0.0, left)
        lft = (fr if self.two else -14, fro)
        p.set_arms((ar, rr), ((ar if self.two else -4), (rr if self.two else 4)), (fr, fro), (fr if self.two else -10, fro if self.two else 0))
        p.model.set_p(-(bp + nod)); p.model.set_r(0)
        if hasattr(p, "set_chew"): p.set_chew(chew)
        # prop: grows in when picked up, shrinks bite by bite, wrapper / empty is binned at the end
        if t < k: s = 0.001 if self.fridge is not None and t < 0.45 else min(1.0, (t - (0.45 if self.fridge is not None else 0.0)) / 0.25)
        else: s = 1.0
        if self.glass_put is not None and t < k: s = 0.001
        if t > k + 3.6: s = max(0.001, 1.0 - (t - (k + 3.6)) / 0.35)
        self.prop.set_scale(max(0.001, s))
        if self.drink: self.eat.set_scale(1, 1, max(0.02, left + 0.02))
        else:
            e = max(0.001, left); self.eat.set_scale(0.35 + 0.65 * e, 1, e) if self.fid != "takoyaki" else self.eat.set_scale(e)
        if self.fid == "pocky" or self.fid == "chips": self.eat.set_scale(1, 1, max(0.001, left))
        if self.fridge is not None:                         # fridge door: opens, then swings shut
            o = _ease(t / 0.4) if t < 0.95 else 1.0 - _ease((t - 0.95) / 0.45)
            self.fridge.set_h(-105 * o)
        if self.glass_put is not None: self.glass_put(t, k)
        if t >= self.T:
            self.finish(); return True
        return False

    def finish(self):
        if self.finished: return
        self.finished = True; p = self.p
        if not self.prop.is_empty(): self.prop.remove_node()
        p.anim_lock = False; p.set_grip(False, False); p.model.set_p(0)
        if hasattr(p, "set_chew"): p.set_chew(0.0)
        if self.fridge is not None: self.fridge.set_h(0)
        if self.done_cb: self.done_cb()


# ================================================================ HIKARI BEACH BAR (bartender, drinks, animated drinking)
BAR_DRINKS = ("beer", "sake", "highball", "water", "greentea")


class BeachBar:
    def __init__(self, game, x=489.5, y=-20.0):
        from fs_people import Person
        from fs_miyo import box_mesh
        self.g = game; app = game.app; self.x, self.y = x, y
        r = self.root = app.render.attach_new_node("beach-bar"); r.set_pos(x, y, 0.0)
        wood = (0.55, 0.36, 0.2, 1); dark = (0.25, 0.15, 0.08, 1); straw = (0.85, 0.72, 0.4, 1)
        n = r.attach_new_node(box_mesh("bar", [(0.0, -2.0, 0.0, 0.6, 2.0, 1.05, wood), (-0.12, -2.1, 1.05, 0.7, 2.1, 1.12, dark),
                                               (1.9, -2.0, 0.0, 2.1, 2.0, 1.6, dark), (1.85, -1.9, 1.6, 2.1, 1.9, 1.64, wood),
                                               (-0.3, -2.3, 0.0, -0.18, -2.18, 2.6, dark), (-0.3, 2.18, 0.0, -0.18, 2.3, 2.6, dark),
                                               (2.1, -2.3, 0.0, 2.22, -2.18, 2.6, dark), (2.1, 2.18, 0.0, 2.22, 2.3, 2.6, dark),
                                               (-0.7, -2.6, 2.6, 2.6, 2.6, 2.75, straw)] +
                                     [(1.92, -1.6 + k * 0.4, 1.12, 2.02, -1.5 + k * 0.4, 1.4, c) for k, c in
                                      enumerate([(0.2, 0.5, 0.2, 1), (0.6, 0.3, 0.1, 1), (0.85, 0.85, 0.8, 1), (0.3, 0.2, 0.5, 1), (0.7, 0.6, 0.1, 1), (0.2, 0.5, 0.2, 1), (0.6, 0.1, 0.1, 1), (0.85, 0.85, 0.8, 1)])]))
        shade(n, app, 0.3)
        tn = TextNode("barsign"); tn.set_text("光ビーチ・バー  HIKARI BEACH BAR"); tn.set_align(TextNode.A_center); tn.set_text_color(1, 0.9, 0.6, 1)
        if app.jpfont: tn.set_font(app.jpfont)
        tn.set_card_color(0.15, 0.08, 0.04, 1); tn.set_card_as_margin(0.4, 0.4, 0.3, 0.3)
        sg = r.attach_new_node(tn.generate()); sg.set_pos(-0.72, 0, 2.3); sg.set_h(90); sg.set_scale(0.22); sg.set_light_off(); sg.set_two_sided(True)
        bt = self.tender = Person(game, "daniel", 0, 0, 0, ped=True); bt.np.reparent_to(r); bt.np.set_pos(1.25, 0, 0); bt.np.set_h(90)
        for nm, c in (("tank", (3.6, 3.6, 3.6, 1)), ("trousers", (0.2, 0.2, 0.25, 1))):
            x_ = bt.model.find("**/" + nm)
            if not x_.is_empty(): x_.set_shader_input("tint", c)
        bt.set_arms((-20, 6), (-20, 6), (-60, 0), (-60, 0))
        for k in range(3):
            st = r.attach_new_node(box_mesh("stool", [(-0.75, -1.2 + k * 1.2 - 0.17, 0.0, -0.45, -1.2 + k * 1.2 + 0.17, 0.72, dark)])); shade(st, app, 0.3)
        game.world.grid.add_rect((x - 0.3, y - 2.3, x + 2.3, y + 2.3), "b") if hasattr(game.world.grid, "add_rect") else None
        self.cd = 2.0; self.ui = None; self.glass = None

    def near(self):
        g = self.g
        if g.pcar is not None or g.home or g.eating is not None: return False
        px, py = g.player_pos(); return abs(px - (self.x - 1.1)) < 1.6 and abs(py - self.y) < 2.4

    def update(self, dt):
        g = self.g; self.cd -= dt
        if self.near() and self.cd <= 0 and g.overlay is None:
            g.npc_say("bar", self.tender); self.cd = random.uniform(10, 16)
        t = g.time; self.tender.set_arms((-22 + 5 * math.sin(t * 1.7), 6), (-22 - 5 * math.sin(t * 1.7), 6), (-60, 0), (-60, 0))

    def open_menu(self):
        g = self.g
        if self.ui is not None or g.overlay is not None: return
        from direct.gui.DirectGui import DirectFrame
        import fs_ui as U
        o = self.ui = DirectFrame(parent=g.app.aspect2d, frameColor=(0, 0, 0, 0.3), frameSize=(-4, 4, -2, 2)); g.overlay = o
        U.panel(o, -0.62, 0.62, -0.55, 0.55, edge=(1.0, 0.75, 0.35, 1))
        U.text(o, "HIKARI BEACH BAR", (0, 0.43), 0.06, fg=(1.0, 0.75, 0.35, 1)); U.text(o, "光ビーチ・バー", (0, 0.36), 0.04, fg=U.CYAN, font=g.app.jpfont)
        for k, fid in enumerate(BAR_DRINKS):
            f = INFO[fid]; y = 0.22 - k * 0.12
            U.button(o, "%s  %s   ¥%d" % (f[1], f[2], f[3]), (0, y), self.order, w=0.42, h=0.045, scale=0.034, extra=[fid], font=g.app.jpfont,
                     edge=(1.0, 0.75, 0.35, 1) if f[5] == "alcohol" else U.CYAN)
        U.text(o, "Tipsy: %.1f   (water / green tea sober you up)" % getattr(g, "drunk", 0.0), (0, -0.4), 0.028, font=U.FONT_PLAIN)
        U.button(o, "LEAVE", (0, -0.48), self.close, w=0.14, h=0.035, scale=0.03, hint="Esc")
        g.app.accept("escape", self.close)
        g.refresh_buttons()

    def close(self):
        g = self.g
        if self.ui is not None: self.ui.destroy(); self.ui = None
        if g.overlay is not None and g.overlay.is_empty(): g.overlay = None
        g.overlay = None; g.app.accept("escape", g.key_esc); g.refresh_buttons()

    def order(self, fid):
        """the bartender puts the glass on the counter, the character grips it, sips 3 times (the drink goes down), sets it
        back and the empty glass is cleared away"""
        g = self.g; f = INFO[fid]
        if g.cash < f[3]: g.toast("Not enough cash (¥%d)" % f[3]); return
        self.close(); g.cash -= f[3]; g.ledger.append(("BAR: %s" % f[2], -f[3]))
        me = g.me(); me.x, me.y, me.h = self.x - 0.95, self.y, -90; me.speed = 0; me.sync()
        gl, _ = build_prop(fid, g.app); gl.reparent_to(self.root); gl.set_pos(0.3, 0.0, 1.13); gl.set_scale(0.001); self.glass = gl
        def put(t, k):
            if gl.is_empty(): return
            if t < k: gl.set_scale(max(0.001, min(1.0, t / 0.3))); gl.set_x(0.6 - 0.3 * min(1.0, t / 0.4))
            elif t < k + 0.05: gl.hide()
            if t > k + 3.6 and t < k + 3.95: gl.show(); gl.set_scale(1)       # set back on the counter (empty)...
            if t >= k + 3.95: gl.remove_node()                                  # ...and cleared away by the bartender
        def done():
            me.health = min(100.0, me.health + f[4])
            g.drunk = max(0.0, getattr(g, "drunk", 0.0) + f[6])
            g.toast("%s  -  %s" % (f[2], ("tipsy level %.1f" % g.drunk) if f[5] == "alcohol" else ("sobering up: tipsy %.1f" % g.drunk)))
        if fid in ("beer", "sake", "highball"): g.npc_say("bar_serve", self.tender)
        g.eating = EatAnim(g, me, fid, on_done=done, glass_put=put); g.app.sfx("cash", 0.5)
