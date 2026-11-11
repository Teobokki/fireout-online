"""EX OS HACKERIA - original hacking, profiler, heat sweep, night contracts and skills for FIREOUT ONLINE.
Play as Elijer, a masked hacker, in the night city of Kagehara.
\u00a92026 EX ROMANIA/EX INC.
"""
import math, random, time
from panda3d.core import NodePath, TextNode, CardMaker, TransparencyAttrib, Vec3
from direct.gui.DirectGui import DirectFrame, DirectButton, DGG
import fs_ui as U
import fs_data as D

OS_NAME = "EX OS HACKERIA"
COPYRIGHT = "\u00a92026 EX ROMANIA/EX INC."

# skill ids -> (title, blurb, default unlocked)
SKILLS = [
    ("range", "LONG REACH", "Hack objects from further away.", True),
    ("traffic", "SIGNAL HIJACK", "Hack traffic signals. Force a scramble so chases break up.", True),
    ("bollard", "RISERS", "Raise or lower street blockers and bollards.", True),
    ("steam", "PIPE BURST", "Vent street steam to stagger nearby pursuers.", False),
    ("camera", "CAM JUMP", "Take over security cameras and jump between them.", True),
    ("barrier", "GATES", "Raise or lower road barriers and bridge gates.", False),
    ("kiosk", "YENLINK DRAIN", "Pull cash from YENLINK street kiosks.", True),
    ("profile", "PROFILER", "Scan pedestrians for a short bio and income line.", True),
    ("ghost", "SOFT TRACE", "Hacks raise less heat.", False),
    ("blackout", "CITY BLACKOUT", "Drop the district into a short blackout and slip the sweep.", False),
    ("drain", "DEEP DRAIN", "YENLINK kiosks pay more.", False),
    ("sweep", "SWEEP BREAK", "Leave a search circle faster, especially from cover.", False),
]

CONTRACTS = [
    {"id": "c_signals", "title": "SCRAMBLE THE STRIP", "giver": "SABLE",
     "line": "Hijack three traffic signals on the crossing so a courier can slip through.",
     "need": ("traffic", 3), "pay": 4000, "xp": 1},
    {"id": "c_yen", "title": "YENLINK NIGHT DROP", "giver": "SABLE",
     "line": "Drain a YENLINK kiosk and walk away before the sweep closes in.",
     "need": ("kiosk", 1), "pay": 3500, "xp": 1},
    {"id": "c_profile", "title": "NAME THE MARK", "giver": "SABLE",
     "line": "Open the profiler on eight pedestrians. Bring Sable a clean read.",
     "need": ("profile", 8), "pay": 2500, "xp": 1},
    {"id": "c_cam", "title": "EYES ON THE BLOCK", "giver": "SABLE",
     "line": "Jump through three security cameras without leaving the feed.",
     "need": ("camera", 3), "pay": 4500, "xp": 1},
    {"id": "c_site", "title": "QUIET ENTRY", "giver": "SABLE",
     "line": "Slip a guarded site, reach the data post and jack it from cover or a camera.",
     "need": ("site", 1), "pay": 7000, "xp": 2},
    {"id": "c_blackout", "title": "LIGHTS OUT", "giver": "SABLE",
     "line": "Unlock CITY BLACKOUT and drop the grid for a clean extract.",
     "need": ("blackout", 1), "pay": 8000, "xp": 2},
]

FIRST = ["Aki", "Ren", "Noa", "Sora", "Yuri", "Ken", "Mika", "Haru", "Len", "Niko",
         "Pia", "Osamu", "Chika", "Daiki", "Emi", "Fumi", "Gaku", "Hina", "Iori", "Jiro"]
LAST = ["Mori", "Kade", "Vale", "Nash", "Kuro", "Shin", "Hara", "Watt", "Sol", "Pike",
        "Reed", "Cross", "Lane", "Ash", "Quinn", "Belo", "Sato", "Ives", "March", "Cole"]
JOBS = ["Courier", "Night cook", "Clerk", "Cab driver", "Student", "Bar staff", "Dock hand",
        "Nurse", "Shop owner", "Engineer", "DJ", "Mechanic", "Teacher", "Guard", "Analyst"]
BIOS = [
    "Works late and takes the long way home.",
    "Sends most of the pay to family up the coast.",
    "Keeps a second phone just for side jobs.",
    "Still paying off a scooter from last winter.",
    "Looks for a quieter district next year.",
    "Never misses the midnight noodle window.",
    "Collects old transit cards as a hobby.",
    "Pretends not to notice the cameras.",
]


def _box(name, boxes):
    from fs_miyo import box_mesh
    return box_mesh(name, boxes)


def _shade(np, app, gloss=0.2):
    from fs_miyo import shade
    shade(np, app, gloss)


class Hackeria:
    def __init__(self, game, save=None):
        self.g = game
        sd = save if isinstance(save, dict) else {}
        self.skills = set(sd.get("skills") or [s[0] for s in SKILLS if s[3]])
        self.points = int(sd.get("points", 1) or 0)
        self.done = set(sd.get("done") or [])
        self.active = sd.get("active")  # contract id
        self.progress = dict(sd.get("progress") or {})
        self.counts = dict(sd.get("counts") or {})
        self.profiles = {}
        self.scanned = set(sd.get("scanned") or [])
        self.target = None
        self.highlight = None
        self.cam_view = None
        self.cam_list = []
        self.blackout_t = 0.0
        self.sweep = None  # {x,y,r,t}
        self.cover = False
        self.ui = None
        self.props = []
        self.root = game.app.render.attach_new_node("hackeria")
        self._prompt = ""
        self._hud = None
        self._cool = {}
        self._build_world()
        self._hud_init()

    def save(self):
        return {"skills": sorted(self.skills), "points": self.points, "done": sorted(self.done),
                "active": self.active, "progress": dict(self.progress), "counts": dict(self.counts),
                "scanned": list(self.scanned)[-80:]}

    # ---------------- world props
    def _build_world(self):
        g = self.g
        pitch = D.PITCH
        # traffic targets use existing signal junctions
        junc = list(getattr(g.signals, "junctions", []) or [])
        for (x, y) in junc:
            self.props.append({"kind": "traffic", "skill": "traffic", "x": x, "y": y, "z": 4.2,
                               "label": "Traffic signal", "r": 18.0})
        # bollards / risers near a subset of junctions
        for i, (x, y) in enumerate(junc[::2][:24]):
            ang = (i % 4) * 90
            rad = D.ROAD_W * 0.5 + 2.2
            px = x + math.cos(math.radians(ang)) * rad
            py = y + math.sin(math.radians(ang)) * rad
            np = self._riser(px, py, down=True)
            self.props.append({"kind": "bollard", "skill": "bollard", "x": px, "y": py, "z": 0.5,
                               "label": "Street blocker", "r": 10.0, "np": np, "up": False})
        # steam pipes mid-block
        for i, (x, y) in enumerate(junc[1::3][:16]):
            px, py = x + 18, y + D.ROAD_W * 0.5 + 1.6
            np = self._pipe(px, py)
            self.props.append({"kind": "steam", "skill": "steam", "x": px, "y": py, "z": 0.8,
                               "label": "Steam pipe", "r": 10.0, "np": np})
        # cameras on building corners
        for i, (x, y) in enumerate(junc[::1][:28]):
            px = x + (D.ROAD_W * 0.5 + 6) * (1 if i % 2 == 0 else -1)
            py = y + (D.ROAD_W * 0.5 + 6) * (1 if i % 3 == 0 else -1)
            np = self._cam_prop(px, py, 7.2)
            self.props.append({"kind": "camera", "skill": "camera", "x": px, "y": py, "z": 7.2,
                               "label": "Security camera", "r": 14.0, "np": np})
        # road barriers / gates on a few arterials
        for i, (x, y, h) in enumerate(((0, 200, 90), (200, 0, 0), (-200, 0, 0), (0, -200, 90),
                                       (300, 100, 0), (-100, 300, 90))):
            np = self._gate(x, y, h, up=False)
            self.props.append({"kind": "barrier", "skill": "barrier", "x": x, "y": y, "z": 1.0,
                               "label": "Road barrier", "r": 14.0, "np": np, "up": False, "h": h})
        # YENLINK kiosks
        for i, (x, y) in enumerate(((12, 18), (-80, 12), (120, -90), (40, 140), (-150, -40),
                                    (260, 40), (-40, -160), (330, -180), (80, 260), (-220, 80))):
            np = self._kiosk(x, y)
            self.props.append({"kind": "kiosk", "skill": "kiosk", "x": x, "y": y, "z": 1.2,
                               "label": "YENLINK kiosk", "r": 8.0, "np": np})
        # two guarded sites with a data post
        sites = [((220, 220), "North relay"), ((-220, -180), "Dockside node")]
        for (sx, sy), name in sites:
            self._site(sx, sy, name)

    def _riser(self, x, y, down=True):
        h = 0.15 if down else 1.15
        boxes = [(x - 0.18, y - 0.18, 0, x + 0.18, y + 0.18, h, (0.18, 0.2, 0.22, 1))]
        n = self.root.attach_new_node(_box("riser", boxes)); _shade(n, self.g.app, 0.3)
        n.set_python_tag("h0", 0.15); n.set_python_tag("h1", 1.15)
        return n

    def _pipe(self, x, y):
        boxes = [(x - 0.25, y - 0.25, 0, x + 0.25, y + 0.25, 0.7, (0.35, 0.28, 0.18, 1)),
                 (x - 0.12, y - 0.12, 0.7, x + 0.12, y + 0.12, 1.15, (0.45, 0.35, 0.22, 1))]
        n = self.root.attach_new_node(_box("pipe", boxes)); _shade(n, self.g.app, 0.25)
        return n

    def _cam_prop(self, x, y, z):
        boxes = [(x - 0.08, y - 0.08, z - 0.08, x + 0.08, y + 0.08, z + 0.08, (0.12, 0.14, 0.16, 1)),
                 (x - 0.03, y - 0.03, z + 0.08, x + 0.03, y + 0.03, z + 1.4, (0.2, 0.2, 0.22, 1))]
        n = self.root.attach_new_node(_box("secam", boxes)); _shade(n, self.g.app, 0.4)
        return n

    def _gate(self, x, y, h, up=False):
        # a wide arm across the lane
        ca, sa = math.cos(math.radians(h)), math.sin(math.radians(h))
        w = D.ROAD_W * 0.45
        z1, z2 = (2.6, 3.0) if up else (0.05, 1.05)
        # two posts + arm
        px, py = -sa * w, ca * w
        boxes = [
            (x - px - 0.12, y - py - 0.12, 0, x - px + 0.12, y - py + 0.12, 3.0, (0.15, 0.16, 0.18, 1)),
            (x + px - 0.12, y + py - 0.12, 0, x + px + 0.12, y + py + 0.12, 3.0, (0.15, 0.16, 0.18, 1)),
            (x - px - 0.1, y - py - 0.1, z1, x + px + 0.1, y + py + 0.1, z2, (0.7, 0.15, 0.12, 1)),
        ]
        n = self.root.attach_new_node(_box("gate", boxes)); _shade(n, self.g.app, 0.25)
        n.set_python_tag("base", (x, y, h, w))
        return n

    def _kiosk(self, x, y):
        boxes = [(x - 0.35, y - 0.25, 0, x + 0.35, y + 0.25, 1.35, (0.08, 0.1, 0.12, 1)),
                 (x - 0.28, y - 0.18, 0.7, x + 0.28, y + 0.22, 1.2, (0.1, 0.55, 0.55, 1))]
        n = self.root.attach_new_node(_box("yenlink", boxes)); _shade(n, self.g.app, 0.2)
        return n

    def _site(self, x, y, name):
        # low walls around a courtyard + a data post + a camera
        s = 14.0
        boxes = [
            (x - s, y - s, 0, x + s, y - s + 0.5, 1.2, (0.2, 0.22, 0.24, 1)),
            (x - s, y + s - 0.5, 0, x + s, y + s, 1.2, (0.2, 0.22, 0.24, 1)),
            (x - s, y - s, 0, x - s + 0.5, y + s, 1.2, (0.2, 0.22, 0.24, 1)),
            (x + s - 0.5, y - s, 0, x + s, y + s, 1.2, (0.2, 0.22, 0.24, 1)),
            (x - 0.4, y - 0.4, 0, x + 0.4, y + 0.4, 1.6, (0.07, 0.25, 0.28, 1)),
        ]
        # opening on +y side
        boxes[1] = (x - s, y + s - 0.5, 0, x - 3, y + s, 1.2, (0.2, 0.22, 0.24, 1))
        n = self.root.attach_new_node(_box("site", boxes)); _shade(n, self.g.app, 0.2)
        cam = self._cam_prop(x + s - 1.5, y - s + 1.5, 6.0)
        self.props.append({"kind": "camera", "skill": "camera", "x": x + s - 1.5, "y": y - s + 1.5, "z": 6.0,
                           "label": "Site camera", "r": 14.0, "np": cam, "site": (x, y)})
        self.props.append({"kind": "site", "skill": "camera", "x": x, "y": y, "z": 1.4,
                           "label": "Data post  (%s)" % name, "r": 8.0, "np": n, "site": (x, y), "name": name})
        self.props.append({"kind": "cover", "x": x - s + 1, "y": y, "z": 0.6, "r": 2.2, "h": 1.2})
        self.props.append({"kind": "cover", "x": x + s - 1, "y": y, "z": 0.6, "r": 2.2, "h": 1.2})
        self.props.append({"kind": "zone", "x": x, "y": y, "r": s + 2, "name": name})

    # ---------------- HUD
    def _hud_init(self):
        a = self.g.app
        root = a.aspect2d.attach_new_node("hackeria-hud")
        self._hud = root
        self._prof_t = U.text(a.a2dTopRight, "", (-0.36, -0.72), 0.032, fg=(0.7, 1, 1, 1),
                              align=TextNode.A_right, font=U.FONT_PLAIN, wrap=42)
        self._os_t = U.text(a.a2dTopLeft, OS_NAME, (0.06, -0.70), 0.028, fg=(0.4, 0.95, 1, 1),
                            align=TextNode.A_left, font=U.FONT_PLAIN)
        self._os_t.setText("")

    def prompt(self):
        return self._prompt

    # ---------------- update
    def update(self, dt):
        g = self.g
        if self.blackout_t > 0:
            self.blackout_t = max(0.0, self.blackout_t - dt)
            if self.blackout_t <= 0:
                try:
                    g.update_daynight(0)
                except Exception:
                    pass
                g.toast("%s: power restored" % OS_NAME, 2.0)
        self._update_cover()
        self._update_sweep(dt)
        self._pick_target()
        self._update_profiler()
        self._update_highlight()
        self._update_cam(dt)
        if self.ui is not None:
            self._pulse_ui()

    def _player_xy(self):
        return self.g.player_pos()

    def _facing(self):
        me = self.g.me()
        if self.g.pcar:
            f = self.g.pcar.fwd
            return f[0], f[1]
        h = math.radians(me.h)
        return -math.sin(h), math.cos(h)

    def _range(self):
        return 26.0 if "range" in self.skills else 16.0

    def _pick_target(self):
        self.target = None
        self._prompt = ""
        if self.g.overlay or self.g.home or self.g.garage or self.cam_view:
            if self.cam_view:
                self._prompt = "[E] HACK FROM CAMERA    [N] NEXT CAM    [Esc] EXIT FEED"
            return
        px, py = self._player_xy()
        fx, fy = self._facing()
        best = None
        reach = self._range()
        for p in self.props:
            kind = p.get("kind")
            if kind in ("cover", "zone"):
                continue
            if p.get("skill") and p["skill"] not in self.skills and kind != "site":
                # still show locked later
                pass
            dx, dy = p["x"] - px, p["y"] - py
            d = math.hypot(dx, dy)
            if d > max(reach, p.get("r", 10) + 4):
                continue
            # prefer what we are looking toward
            if d > 0.2:
                dot = (dx * fx + dy * fy) / d
            else:
                dot = 1.0
            if d > 8 and dot < 0.15:
                continue
            score = d - dot * 8
            if best is None or score < best[0]:
                best = (score, p, d)
        if not best:
            return
        _, p, d = best
        if d > self._range() + 2:
            return
        self.target = p
        locked = p.get("skill") and p["skill"] not in self.skills and p["kind"] != "site"
        if locked:
            self._prompt = "[LOCKED] %s  -  unlock in %s (Q)" % (p["label"], OS_NAME)
        else:
            self._prompt = "[E] HACK  -  %s" % p["label"]

    def _update_highlight(self):
        # flat cyan tint on the selected prop, no bloom
        if self.highlight is not None:
            try:
                self.highlight.set_color_scale(1, 1, 1, 1)
            except Exception:
                pass
            self.highlight = None
        p = self.target
        if not p:
            self._os_t.setText("")
            return
        self._os_t.setText(OS_NAME)
        np = p.get("np")
        if np is None or np.is_empty():
            return
        np.set_color_scale(0.45, 1.0, 1.0, 1)
        self.highlight = np

    def _update_profiler(self):
        self._prof_t.setText("")
        if "profile" not in self.skills or self.g.overlay or self.g.phone or self.g.pcar:
            return
        me = self.g.me()
        fx, fy = self._facing()
        best = None
        for ped in getattr(self.g, "peds", []):
            dx, dy = ped.x - me.x, ped.y - me.y
            d = math.hypot(dx, dy)
            if d < 1.0 or d > 16:
                continue
            dot = (dx * fx + dy * fy) / d
            if dot < 0.55:
                continue
            if best is None or d < best[0]:
                best = (d, ped)
        if not best:
            return
        ped = best[1]
        info = self._profile_of(ped)
        key = info["key"]
        if key not in self.scanned:
            self.scanned.add(key)
            self._count("profile", 1)
        self._prof_t.setText("%s  -  %s\n%s\nIncome  ¥%s / mo" % (
            info["name"], info["job"], info["bio"], format(info["yen"], ",")))

    def _profile_of(self, ped):
        key = "p-%.0f-%.0f" % (round(ped.x, 0), round(ped.y, 0))
        if key in self.profiles:
            return self.profiles[key]
        rng = random.Random(hash(key) & 0xFFFFFFFF)
        name = rng.choice(FIRST) + " " + rng.choice(LAST)
        job = rng.choice(JOBS)
        bio = rng.choice(BIOS)
        yen = rng.choice((90000, 120000, 150000, 180000, 210000, 260000, 320000, 410000, 580000))
        info = {"key": key, "name": name, "job": job, "bio": bio, "yen": yen}
        self.profiles[key] = info
        return info

    def _update_cover(self):
        self.cover = False
        if self.g.pcar or self.g.home:
            return
        me = self.g.me()
        # hold G or left control near a low wall, kiosk, riser or parked car
        held = False
        try:
            mw = self.g.app.mouseWatcherNode
            from panda3d.core import KeyboardButton
            held = mw.is_button_down(KeyboardButton.ascii_key("g")) or mw.is_button_down(KeyboardButton.lcontrol())
        except Exception:
            held = False
        if not held:
            return
        px, py = me.x, me.y
        near = False
        for p in self.props:
            if p.get("kind") in ("bollard", "kiosk", "barrier", "cover", "site") and math.hypot(p["x"] - px, p["y"] - py) < 2.8:
                near = True
                break
        if not near:
            for c in self.g.cars:
                if c is self.g.pcar:
                    continue
                if math.hypot(c.x - px, c.y - py) < 3.4:
                    near = True
                    break
        self.cover = near
        if self.cover:
            me.model.set_z(-0.25)

    def _update_sweep(self, dt):
        g = self.g
        seen = any(getattr(getattr(c, "ai", None), "seen", False) for c in g.police)
        if g.heat <= 0:
            self.sweep = None
            return
        px, py = self._player_xy()
        if seen:
            self.sweep = {"x": px, "y": py, "r": 28.0 + g.heat * 8.0, "t": 0.0}
            return
        if self.sweep is None:
            self.sweep = {"x": px, "y": py, "r": 32.0 + g.heat * 8.0, "t": 0.0}
        self.sweep["t"] += dt
        # shrink slowly; leave the circle or stay in cover to break it
        if "sweep" in self.skills:
            self.sweep["r"] = max(8.0, self.sweep["r"] - dt * 3.5)
        d = math.hypot(px - self.sweep["x"], py - self.sweep["y"])
        inside = d < self.sweep["r"]
        if (not inside) or (self.cover and self.sweep["t"] > (3.0 if "sweep" in self.skills else 5.0)):
            g.escape_t = max(g.escape_t, 8.0)

    def _update_cam(self, dt):
        if not self.cam_view:
            return
        p = self.cam_view
        cam = self.g.app.camera
        cam.set_pos(p["x"], p["y"], p.get("z", 7.2))
        # look toward city centre-ish / player
        px, py = self._player_xy()
        cam.look_at(px, py, 1.2)
        self.g.app.camLens.set_fov(58)

    # ---------------- actions
    def try_hack(self):
        if self.cam_view and (self.target is None):
            # hack whatever the camera is aimed at is already picked; if none, just stay
            if self.target is None:
                self._pick_target()
        p = self.target
        if self.cam_view and p is None:
            return True  # consume E while in feed
        if p is None:
            return False
        kind = p["kind"]
        skill = p.get("skill")
        if skill and skill not in self.skills and kind != "site":
            self.g.toast("Locked  -  open %s with Q" % OS_NAME, 2.2)
            return True
        now = self.g.time
        ck = (kind, round(p["x"], 1), round(p["y"], 1))
        if now < self._cool.get(ck, 0):
            self.g.toast("Rebooting...", 1.0)
            return True
        self._cool[ck] = now + (6.0 if kind != "kiosk" else 90.0)
        fn = {
            "traffic": self._hack_traffic,
            "bollard": self._hack_bollard,
            "steam": self._hack_steam,
            "camera": self._hack_camera,
            "barrier": self._hack_barrier,
            "kiosk": self._hack_kiosk,
            "site": self._hack_site,
        }.get(kind)
        if fn:
            fn(p)
        return True

    def _heat(self, n, why):
        if n <= 0:
            return
        if "ghost" in self.skills:
            n = max(0, n - 1)
        if n:
            self.g.add_heat(n, why)

    def _hack_traffic(self, p):
        sig = self.g.signals
        if hasattr(sig, "hack_junction"):
            sig.hack_junction(p["x"], p["y"], seconds=14, phase="both")
        self.g.toast("%s: signals scrambled" % OS_NAME, 2.2)
        try:
            self.g.app.sfx("click", 0.7)
        except Exception:
            pass
        self._count("traffic", 1)
        if self.g.heat:
            self._heat(0, "")  # chase tool, no extra heat mid-chase
        else:
            self._heat(0, "")

    def _hack_bollard(self, p):
        p["up"] = not p.get("up")
        self._rebuild_riser(p)
        self.g.toast("%s: blockers %s" % (OS_NAME, "RAISED" if p["up"] else "LOWERED"), 2.0)
        self._count("bollard", 1)
        try:
            self.g.app.sfx("click", 0.6)
        except Exception:
            pass

    def _rebuild_riser(self, p):
        old = p.get("np")
        if old is not None and not old.is_empty():
            old.remove_node()
        p["np"] = self._riser(p["x"], p["y"], down=not p["up"])
        # simple collision: tall when up
        try:
            h = 1.2 if p["up"] else 0.15
            self.g.world.grid.add_circle(p["x"], p["y"], 0.4 if not p["up"] else 0.7)
        except Exception:
            pass

    def _hack_steam(self, p):
        px, py = p["x"], p["y"]
        # stagger nearby police / peds (non-graphic)
        for c in list(self.g.police):
            if math.hypot(c.x - px, c.y - py) < 16:
                c.speed = min(c.speed, 4.0)
                if getattr(c, "ai", None):
                    c.ai.seen = False
        self.g.toast("%s: pipe vented" % OS_NAME, 2.0)
        self._count("steam", 1)
        try:
            self.g.app.sfx("swing_heavy", 0.4)
        except Exception:
            pass

    def _hack_camera(self, p):
        cams = [q for q in self.props if q["kind"] == "camera"]
        self.cam_list = cams
        self.cam_view = p
        self.g.cam_pos = None
        self.g.toast("%s: camera feed" % OS_NAME, 1.6)
        self._count("camera", 1)
        try:
            self.g.app.sfx("click", 0.5)
        except Exception:
            pass

    def next_cam(self):
        if not self.cam_view:
            return False
        cams = self.cam_list or [q for q in self.props if q["kind"] == "camera"]
        if not cams:
            return True
        try:
            i = cams.index(self.cam_view)
        except ValueError:
            i = 0
        self.cam_view = cams[(i + 1) % len(cams)]
        self.g.toast("Camera %d / %d" % ((i + 1) % len(cams) + 1, len(cams)), 1.2)
        return True

    def exit_cam(self):
        if not self.cam_view:
            return False
        self.cam_view = None
        self.g.cam_pos = None
        self.g.toast("Left camera feed", 1.2)
        return True

    def handle_n(self):
        if self.cam_view:
            return self.next_cam()
        self.open_contracts()
        return True

    def _hack_barrier(self, p):
        p["up"] = not p.get("up")
        old = p.get("np")
        if old is not None and not old.is_empty():
            old.remove_node()
        p["np"] = self._gate(p["x"], p["y"], p.get("h", 0), up=p["up"])
        self.g.toast("%s: barrier %s" % (OS_NAME, "RAISED" if p["up"] else "LOWERED"), 2.0)
        self._count("barrier", 1)

    def _hack_kiosk(self, p):
        amt = 1800 if "drain" in self.skills else 900
        cap = 9999999
        try:
            import fs_game as _fg
            cap = int(getattr(_fg, "CASH_CAP", cap))
        except Exception:
            pass
        self.g.cash = min(cap, self.g.cash + amt)
        try:
            self.g.ledger.append(("YENLINK", amt, time.time()))
        except Exception:
            pass
        self.g.toast("%s: +¥%d from YENLINK" % (OS_NAME, amt), 2.2)
        self._count("kiosk", 1)
        self._heat(1, "YENLINK kiosk jacked")
        try:
            self.g.app.sfx("win", 0.35)
        except Exception:
            pass

    def _hack_site(self, p):
        self.g.cash = self.g.cash + 2500
        self.g.toast("%s: data post jacked  +¥2500" % OS_NAME, 2.5)
        self._count("site", 1)
        self._heat(1, "Secure site jacked")
        try:
            self.g.app.sfx("win", 0.45)
        except Exception:
            pass

    def blackout(self):
        if self.g.blocked() and not self.cam_view:
            return
        if "blackout" not in self.skills:
            self.g.toast("Unlock CITY BLACKOUT in %s (Q)" % OS_NAME, 2.4)
            return
        if self.blackout_t > 0:
            self.g.toast("Blackout already running", 1.4)
            return
        if self.g.time < self._cool.get("blackout", 0):
            self.g.toast("Blackout is recharging", 1.4)
            return
        self.blackout_t = 16.0
        self._cool["blackout"] = self.g.time + 90.0
        # darker night, no bloom — just a deeper fog and dimmer lights
        try:
            self.g.app.set_daylight(0.0)
            self.g.app.fogden = 0.008
        except Exception:
            pass
        for c in self.g.police:
            if getattr(c, "ai", None):
                c.ai.seen = False
        self.g.escape_t = max(self.g.escape_t, 4.0)
        self.g.toast("%s: CITY BLACKOUT" % OS_NAME, 2.6)
        self._count("blackout", 1)
        try:
            self.g.app.sfx("heat", 0.4)
        except Exception:
            pass

    def _count(self, key, n):
        self.counts[key] = self.counts.get(key, 0) + n
        if self.active:
            job = next((c for c in CONTRACTS if c["id"] == self.active), None)
            if job and job["need"][0] == key:
                have = self.progress.get(self.active, 0) + n
                self.progress[self.active] = have
                need = job["need"][1]
                if have >= need:
                    self._complete(job)
                else:
                    self.g.toast("%s  %d / %d" % (job["title"], have, need), 1.8)

    def _complete(self, job):
        self.done.add(job["id"])
        self.active = None
        self.g.cash = self.g.cash + job["pay"]
        self.points += job.get("xp", 1)
        self.g.toast("SABLE: contract done  +¥%d  +%d skill" % (job["pay"], job.get("xp", 1)), 3.5)
        try:
            self.g.app.sfx("win", 0.6)
        except Exception:
            pass

    def accept_job(self, jid):
        job = next((c for c in CONTRACTS if c["id"] == jid), None)
        if not job or jid in self.done:
            return
        self.active = jid
        self.progress[jid] = self.progress.get(jid, 0)
        self.g.toast("SABLE: %s" % job["title"], 2.5)
        self.close_ui()

    def unlock(self, sid):
        if sid in self.skills:
            return
        if self.points <= 0:
            self.g.toast("Need a skill point  -  finish a night contract")
            return
        self.skills.add(sid)
        self.points -= 1
        title = next((s[1] for s in SKILLS if s[0] == sid), sid)
        self.g.toast("%s unlocked: %s" % (OS_NAME, title), 2.2)
        self.open_skills()

    # ---------------- UI
    def close_ui(self):
        if self.ui is not None:
            ui = self.ui
            try:
                ui.destroy()
            except Exception:
                pass
            self.ui = None
            if self.g.overlay is ui:
                self.g.overlay = None
            try:
                self.g.refresh_buttons()
            except Exception:
                pass

    def _panel(self, title):
        self.close_ui()
        o = DirectFrame(parent=self.g.app.aspect2d, frameColor=(0, 0, 0, 0.78),
                        frameSize=(-4, 4, -2, 2), state=DGG.NORMAL)
        U.panel(o, -1.15, 1.15, -0.86, 0.86, col=(0.03, 0.05, 0.07, 0.94), edge=(0.25, 0.85, 0.95, 1))
        U.text(o, OS_NAME, (0, 0.78), 0.055, fg=(0.45, 0.95, 1, 1))
        U.text(o, title, (0, 0.70), 0.038, fg=(1, 1, 1, 1), font=U.FONT_PLAIN)
        U.button(o, "CLOSE", (0, -0.78), self.close_ui, w=0.2, h=0.04, scale=0.035, hint="Esc")
        self.ui = o
        self.g.overlay = o
        self.g.refresh_buttons()
        return o

    def open_skills(self):
        if self.g.phone:
            self.g.toggle_phone()
        o = self._panel("SKILL TREE")
        U.text(o, "Skill points  %d" % self.points, (0, 0.62), 0.032, fg=(0.9, 0.85, 0.3, 1), font=U.FONT_PLAIN)
        for i, (sid, title, blurb, _) in enumerate(SKILLS):
            col = i % 2
            row = i // 2
            x = -0.55 + col * 1.1
            y = 0.48 - row * 0.18
            have = sid in self.skills
            lab = ("%s  ✓" % title) if have else title
            fg = (0.4, 1, 0.7, 1) if have else (0.8, 0.95, 1, 1)
            U.text(o, lab, (x, y), 0.032, fg=fg, font=U.FONT_PLAIN)
            U.text(o, blurb, (x, y - 0.045), 0.024, fg=(0.75, 0.8, 0.85, 1), font=U.FONT_PLAIN)
            if not have:
                U.button(o, "UNLOCK", (x + 0.38, y - 0.01), lambda s=sid: self.unlock(s),
                         w=0.16, h=0.032, scale=0.028, edge=(0.3, 0.9, 1, 1))

    def open_contracts(self):
        if self.g.phone:
            self.g.toggle_phone()
        o = self._panel("NIGHT CONTRACTS  -  SABLE")
        z = 0.58
        for job in CONTRACTS:
            st = "DONE" if job["id"] in self.done else ("ACTIVE  %d/%d" % (
                self.progress.get(job["id"], 0), job["need"][1]) if self.active == job["id"] else "OPEN")
            col = (0.4, 1, 0.6, 1) if st.startswith("DONE") else ((1, 0.85, 0.3, 1) if st.startswith("ACTIVE") else (1, 1, 1, 1))
            U.text(o, "%s   ¥%d   [%s]" % (job["title"], job["pay"], st), (0, z), 0.032, fg=col, font=U.FONT_PLAIN)
            U.text(o, job["line"], (0, z - 0.04), 0.024, fg=(0.75, 0.8, 0.85, 1), font=U.FONT_PLAIN)
            if job["id"] not in self.done and self.active != job["id"]:
                U.button(o, "ACCEPT", (0.85, z), lambda j=job["id"]: self.accept_job(j),
                         w=0.14, h=0.03, scale=0.026)
            z -= 0.13

    def open_phone(self):
        # used as a phone app: close phone then show a compact OS sheet
        if self.g.phone:
            self.g.toggle_phone()
        o = self._panel("PHONE LINK")
        U.text(o, "Elijer's street OS. Highlight a device and press E to HACK.",
               (0, 0.58), 0.03, fg=(0.85, 0.9, 0.95, 1), font=U.FONT_PLAIN)
        U.button(o, "SKILL TREE", (0, 0.35), self.open_skills, w=0.32, h=0.055, scale=0.04, edge=(0.3, 0.9, 1, 1))
        U.button(o, "NIGHT CONTRACTS", (0, 0.18), self.open_contracts, w=0.32, h=0.055, scale=0.04, edge=(0.95, 0.75, 0.2, 1))
        if "blackout" in self.skills:
            U.button(o, "CITY BLACKOUT", (0, 0.01), lambda: (self.close_ui(), self.blackout()),
                     w=0.32, h=0.055, scale=0.04, edge=(0.7, 0.4, 1, 1))
        # nearby devices
        px, py = self._player_xy()
        near = [p for p in self.props if p.get("kind") not in ("cover", "zone") and math.hypot(p["x"] - px, p["y"] - py) < 40]
        U.text(o, "Nearby devices: %d" % len(near), (0, -0.22), 0.03, fg=(0.6, 0.9, 1, 1), font=U.FONT_PLAIN)
        if self.active:
            job = next((c for c in CONTRACTS if c["id"] == self.active), None)
            if job:
                U.text(o, "Active: %s  %d/%d" % (job["title"], self.progress.get(job["id"], 0), job["need"][1]),
                       (0, -0.32), 0.03, fg=(1, 0.85, 0.3, 1), font=U.FONT_PLAIN)

    def _pulse_ui(self):
        pass

    def destroy(self):
        self.close_ui()
        try:
            self.root.remove_node()
        except Exception:
            pass
        if self._hud:
            try:
                self._hud.remove_node()
            except Exception:
                pass
