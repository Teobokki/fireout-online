"""FIREOUT ONLINE gameplay session: open world, Elijer (a masked hacker), driving, EX OS HACKERIA, police, races, phone, FRGARAGE."""
import math
import fs_gfx, os, random, json, time
from panda3d.core import (Vec3, Point3, TextNode, CardMaker, TransparencyAttrib, ColorBlendAttrib, Texture, TextureStage,
                          NodePath, Filename, SamplerState, TransformState, KeyboardButton)
from direct.gui.DirectGui import DirectFrame, DirectButton, DirectEntry, DGG
from direct.gui.OnscreenImage import OnscreenImage
import fs_data as D
import fs_ui as U
from fs_vehicle import Car, collide_cars, TRAFFIC_KINDS, TRAFFIC_COLS
PLAYER_CARS = ["evo", "gts", "coupe", "sedan", "hatch", "kei", "suv", "van"]   # FRGARAGE car selector (original designs)
CAR_TYPES = {"evo": "Sports sedan  * RECOMMENDED *", "gts": "Supercar", "coupe": "JDM coupe", "sedan": "Sedan (4-door)", "hatch": "Hatchback", "kei": "Kei car", "suv": "SUV", "van": "Van"}
from fs_people import Person, Ped
from fs_ai import TrafficAI, RacerAI, PoliceAI, ResponderAI, graph_path, wrap

PAINTS = [("RED", (0.78, 0.04, 0.06)), ("BLUE", (0.05, 0.18, 0.75)), ("YELLOW", (0.95, 0.78, 0.05)), ("GREEN", (0.05, 0.6, 0.18)),
          ("BLACK", (0.03, 0.03, 0.035)), ("WHITE", (0.9, 0.9, 0.92)), ("ORANGE", (1.0, 0.38, 0.03)), ("PURPLE", (0.42, 0.08, 0.75)),
          ("SAKURA", (0.95, 0.35, 0.62)), ("TEAL", (0.05, 0.62, 0.66))]
NAMES = {"elijer": "ELIJER", "ana": "ANA", "daniel": "DANIEL"}
CREW = ("elijer",)
from fs_game_banter import BANTER
from fs_weapons import Arsenal, SHOP_POS, W as WEAPON
from fs_miyo import Miyo


CASH_CAP = 100_000_000_000        # total cash can never exceed ¥100,000,000,000


def fmt_cash_hud(n):
    """HUD cash: full thousands-separated up to 9,999,999,999; compact (e.g. ¥100.0B) above that."""
    n = int(n)
    if n < 10 ** 10: return "¥" + format(n, ",")
    return "¥%.1fB" % (n / 1e9) if n < 10 ** 12 else "¥" + format(n, ",")


class Game:
    def __init__(self, app, save, start=None):
        self.app = app; self.world = app.world; self.time = 0.0
        sd = save or {}
        try: self.cash = max(0, min(CASH_CAP, int(sd.get("cash", 2500))))
        except (TypeError, ValueError): self.cash = 2500
        self.tokens = set(tuple(t) for t in sd.get("tokens", []))
        self.best = dict(sd.get("best", {})); self.cars_cfg = dict(sd.get("cars", {})); self.cam_cams = dict(sd.get("speedcams", {}))
        self.active = sd.get("active", "elijer") if sd.get("active") in CREW else "elijer"
        self.mate = None
        self.tsunami = None; self.builds = None; self.eating = None; self.drunk = float(sd.get("drunk", 0.0) or 0.0)
        self.photos = [p for p in sd.get("photos", []) if isinstance(p, str)]; self.ledger = [tuple(x) for x in sd.get("ledger", [])][-30:]
        self.owned = sd.get("owned") if isinstance(sd.get("owned"), dict) else {}; self.news = [tuple(x) for x in sd.get("news", [])][-10:]
        self.misto = sd.get("misto") if isinstance(sd.get("misto"), dict) else {}
        self.cars = []; self.peds = []; self.police = []; self.paused = False; self.overlay = None; self.phone = None
        self.heat = 0; self.heat_t = 0.0; self.escape_t = 0.0; self.bust_t = 0.0; self.activity = None; self.cam_mode = 0
        self.vb = {}; self.cam_yaw = D.SPAWN[2] - 90; self.cam_pos = None; self.shake = 0.0; self.district = None
        self.sub_t = 0.0; self.talk_cd = 4.0; self.banter_cd = 45.0; self.taxi = None; self.medic = None; self.ride = None
        self.waypoint = None; self.stuck_t = 0.0; self.pop_t = 0.0; self.health_regen = 0.0; self.cinematic = 0.0
        self.garage = None; self.cp_np = None; self._cam_cd = 0.0; self.lb_on = False; self.lb_k = 0.0
        self.outfit = sd.get("outfit", "default") if sd.get("outfit") in ("default", "crop", "bikini", "police") else "default"
        so = sd.get("outfits") if isinstance(sd.get("outfits"), dict) else {}
        self.outfits = {"elijer": so.get("elijer", "default") if isinstance(so.get("elijer"), str) else "default"}
        self.home = None
        self.camapp = None          # v1.0.3: phone CAMERA app state (selfie / rear)
        self.player_kind = sd.get("car", "evo") if sd.get("car") in PLAYER_CARS else "evo"
        self.evo_given = bool(sd.get("evo_v1053"))
        if not self.evo_given:          # v1.0.5.3: the ENERASTIC SEDAN EVO becomes the default / recommended car once (old cars stay in FRGARAGE)
            self.player_kind = "evo"; self.evo_given = True; self._evo_news = True
        x, y, h = D.SPAWN
        self.chars = {"elijer": Person(self, "elijer", x, y - 4.0, 180)}
        for k, p in self.chars.items(): self.bench(p, k != self.active)
        self.miyo = Miyo(self)
        from fs_signals import Signals
        self.signals = Signals(self)
        import fs_hack
        self.hackeria = fs_hack.Hackeria(self, sd.get("hackeria"))
        from fs_laptop import Laptop
        self.laptop = Laptop(self)
        self.pcar = None
        self.own = self.spawn_car(self.player_kind, x, y, h, role="player", parked=True); self.own.owned = True
        self.time_scale = 1.0; self.tod = 23.0
        self.markers = []; self.spawn_markers(); self.build_pois(); self.build_hud(); self.bind_keys()
        try:                                    # v1.0.5.3 seasonal events + live feed
            from fs_events import Events
            self.events = Events(self, sd.get("events"))
            if getattr(self, "_evo_news", False): self.events.notify("New car unlocked", "ENERASTIC MG EVO SEDAN - now your car (FRGARAGE)", small=False)
        except Exception as e:
            self.app.log_error(e); self.events = None
        self.arsenal = Arsenal(self, sd); self.btn_state = None
        # v1.0.5 FIREOUT ONLINE + SFC 27
        self.match = None; self.guest = False; self._save = sd
        import fs_online, fs_sfc
        self.online = fs_online.Online(self); self.online_app = self.online.open
        try: fs_sfc.add_signs(self)
        except Exception as e: self.app.log_error(e)
        app.task_mgr.add(self.update, "game-update", sort=10)
        self.letterbox(True); self.intro_t = 5.0
        self.caption(NAMES["elijer"], "%s  -  %s" % (D.TITLE_JP, D.DISTRICT_EN), 4.5)
        if start:
            self.intro_t = 0.6
            app.do_method_later(0.8, lambda t: self.start_activity(start) or t.done, "auto-start")

    # ================================================================ spawning
    def spawn_car(self, kind, x, y, h, role="traffic", parked=False, paint=None, plate=""):
        cfg = self.cars_cfg.get(kind, {}) if role == "player" else {}
        paint = cfg.get("paint", paint or (((0.62, 0.02, 0.04) if kind == "evo" else (0.20, 0.22, 0.28)) if role == "player" else random.choice(TRAFFIC_COLS)))
        if kind == "police": paint = (0.92, 0.92, 0.94)
        if kind == "ambulance": paint = (0.95, 0.95, 0.95)
        if kind == "taxi" and role != "player": paint = (0.95, 0.75, 0.1)
        c = Car(self, kind, x, y, h, paint, cfg.get("plate", plate), parked, role)
        self.cars.append(c)
        if kind == "taxi" and role == "taxi":          # v1.0.4: see-through taxi glass + the JP TAXI driver at the wheel
            try:
                from fs_miyo import taxi_glass, make_taxi_driver
                taxi_glass(c, self.app); d = make_taxi_driver(self); d.seat(c, 1); c.taxi_driver = d
            except Exception as e: self.app.log_error(e)
        return c

    def remove_car(self, c):
        if c in self.cars: self.cars.remove(c)
        if c in self.police: self.police.remove(c)
        for p in self.chars.values():
            if p.in_car is c: p.unseat(c.x + 3, c.y, c.h)
        c.destroy()

    def cars_near(self, x, y, r):
        r2 = r * r
        return [c for c in self.cars if (c.x - x) ** 2 + (c.y - y) ** 2 < r2]

    def walkers(self):
        out = list(self.peds)
        for p in self.chars.values():
            if p.in_car is None and not getattr(p, "benched", False): out.append(p)
        return out

    def me(self):
        return self.chars[self.active]

    def buddy(self):
        m = getattr(self, "mate", None)
        if not m or m == self.active or m not in self.chars:
            return None
        return self.chars[m]

    def bench(self, p, on):
        """the crew member not in the active pair is parked off-screen (hidden, not simulated)"""
        p.benched = on
        if on:
            if p.in_car is not None: p.unseat(p.in_car.x, p.in_car.y, 0)
            p.np.hide(); p.np.set_pos(0, 0, -50)
        else: p.np.show()

    def player_pos(self):
        if self.pcar: return self.pcar.x, self.pcar.y
        if self.ride: return self.ride["car"].x, self.ride["car"].y
        p = self.me(); return p.x, p.y

    def player_target(self):
        if self.pcar: return self.pcar.x, self.pcar.y, self.pcar.vx, self.pcar.vy
        x, y = self.player_pos(); return x, y, 0.0, 0.0

    def in_view(self, x, y):
        p = self.app.cam.get_relative_point(self.app.render, Point3(x, y, 1))
        return p.y > 0 and abs(p.x) < p.y * 1.1

    def offscreen_road_point(self, min_d=110, max_d=220):
        px, py = self.player_pos(); best = None
        for _ in range(40):
            a = random.uniform(0, 2 * math.pi); d = random.uniform(min_d, max_d)
            x, y, h = self.world.nearest_road_point(px + math.cos(a) * d, py + math.sin(a) * d)
            dd = math.hypot(x - px, y - py)
            if dd < min_d * 0.7: continue
            best = (x, y, h)
            if not self.in_view(x, y): return x, y, h
        return best or self.world.nearest_road_point(px + min_d, py)

    def populate(self):
        px, py = self.player_pos(); w = self.world
        keep = {self.own, self.pcar, self.taxi, self.medic}
        for c in list(self.cars):
            if c in keep or c in self.police or getattr(c, "racer", False) or getattr(c, "friend", False): continue
            if math.hypot(c.x - px, c.y - py) > 175: self.remove_car(c)
        for p in list(self.peds):
            if math.hypot(p.x - px, p.y - py) > 140: p.destroy(); self.peds.remove(p)
        q = self.app.settings.get("quality", 2)
        # v1.0.4 TRAFFIC DENSITY (LOW / NORMAL / HIGH, default HIGH): a busy city - spawned around you out of view, despawned far away
        dens = {"low": 1.0, "normal": 2.0, "high": 4.0}.get(self.app.settings.get("traffic", "high"), 4.0)
        want = int({0: 12, 1: 20, 2: 26}.get(q, 20) * dens * fs_gfx.traffic_scale(self.app))
        traffic = [c for c in self.cars if isinstance(c.ai, TrafficAI)]
        nodes_ = [n for n, (x_, y_) in w.nodes.items() if abs(x_ - px) < 140 and abs(y_ - py) < 140] or list(w.nodes)
        seed = len(traffic) < want * 0.4      # first fill (load / teleport / taxi skip): fill the streets straight away
        for _ in range(40 if seed else (12 if dens > 1.5 else 4)):
            if len(traffic) >= want: break
            node = random.choice(nodes_); nx_, ny_ = w.nodes[node]
            d = math.hypot(nx_ - px, ny_ - py)
            if d > 140 or (not seed and (d < 40 or (self.in_view(nx_, ny_) and d < 95))) or (seed and d < 20): continue
            nb = random.choice(w.adj[node]); bx, by = w.nodes[nb]
            dx, dy = bx - nx_, by - ny_; L = math.hypot(dx, dy); dx /= L; dy /= L
            x, y = nx_ + dx * 14 - dy * 3.0, ny_ + dy * 14 + dx * 3.0
            if self.cars_near(x, y, 9): continue
            c = self.spawn_car(random.choice(TRAFFIC_KINDS), x, y, math.degrees(math.atan2(-dx, dy)))
            c.ai = TrafficAI(self, c, nb, node); c.driver = "ai"; c.asleep = False; c.vx, c.vy = dx * 8, dy * 8
            traffic.append(c)
        parked = sum(1 for c in self.cars if c.ai is None and c.driver is None and c not in keep)
        if parked < {0: 10, 1: 20, 2: 30}.get(q, 20):
            for (x, y, h) in random.sample(w.parking, min(40, len(w.parking))):
                d = math.hypot(x - px, y - py)
                if 50 < d < 190 and not self.cars_near(x, y, 5) and not self.in_view(x, y):
                    self.spawn_car(random.choice(TRAFFIC_KINDS), x, y, h, parked=True); break
        wantp = {0: 6, 1: 12, 2: 18}.get(q, 12)
        for _ in range(6):
            if len(self.peds) >= wantp: break
            loop = random.choice(w.ped_loops)
            cx = sum(p[0] for p in loop) / len(loop); cy = sum(p[1] for p in loop) / len(loop)
            if math.hypot(cx - px, cy - py) > 120: continue
            p = Ped(self, loop, random.randrange(len(loop)))
            dd = math.hypot(p.x - px, p.y - py)
            if dd < 20 or (self.in_view(p.x, p.y) and dd < 50):
                p.destroy(); continue
            self.peds.append(p)

    # ================================================================ input
    KEYS = ("f", "e", "c", "r", "h", "m", "t", "escape", "q", "f2", "arrow_up", "enter", "j", "space", "1", "2", "3", "b", "n", "l")

    def bind_keys(self):
        a = self.app
        for k, f in zip(self.KEYS, (self.key_f, self.key_e, self.key_c, self.key_r, self.key_h, self.toggle_map, self.toggle_phone,
                                    self.key_esc, self.switch_char, self.switch_char, self.key_up, self.key_enter, self.repair_car, self.key_space,
                                    lambda: self.key_num(0), lambda: self.key_num(1), lambda: self.key_num(2), self.key_b, self.key_n, self.key_l)):
            a.accept(k, self._key_guard(k, f))

    def _key_guard(self, k, f):
        def h():
            m = getattr(self, "match", None)
            if m is not None and m.key(k): return
            if m is not None and k != "escape": return
            if k == "escape" and self.online.ui is not None and self.overlay is self.online.ui:
                v = self.online.view
                if v in ("main",): self.online.close()
                else: self.online.goto("main")
                return
            f()
        return h

    def start_match(self, **kw):
        """v1.0.5 SFC 27: kick off at the stadium (VS AI, or ONLINE when the session has friends)"""
        import fs_sfc
        if self.match is not None: return
        if self.ride: self.leave_taxi()
        if self.pcar: self.exit_car(force=True)
        if self.home: self.leave_home()
        if hasattr(self, "arsenal"): self.arsenal.unequip()
        self.close_overlay()
        self.match = fs_sfc.Match(self, **kw); self.btn_state = None; self.refresh_buttons()

    def start_match_view(self, setup):
        import fs_sfc
        if self.match is not None: return
        if self.ride: self.leave_taxi()
        if self.pcar: self.exit_car(force=True)
        if self.home: self.leave_home()
        self.close_overlay()
        try:
            self.match = fs_sfc.Match(self, mode="view", setup=setup, online=self.online); self.btn_state = None; self.refresh_buttons()
        except Exception as e:
            self.app.log_error(e); self.match = None

    def unbind(self):
        for k in self.KEYS: self.app.ignore(k)

    def down(self, *keys):
        mw = self.app.mouseWatcherNode
        for k in keys:
            if self.vb.get(k): return True
            if k.startswith("v_") or mw is None: continue
            if k == "shift": b = KeyboardButton.shift()
            elif k == "space": b = KeyboardButton.space()
            elif k == "arrow_up": b = KeyboardButton.up()
            elif k == "arrow_down": b = KeyboardButton.down()
            elif k == "arrow_left": b = KeyboardButton.left()
            elif k == "arrow_right": b = KeyboardButton.right()
            else: b = KeyboardButton.ascii_key(k)
            if mw.is_button_down(b): return True
        return False

    def blocked(self):
        return self.paused or self.overlay is not None or self.intro_t > 0 or self.garage is not None or self.home is not None or self.camapp is not None

    def key_up(self):
        if self.pcar is None and self.ride is None and not self.blocked() and self.phone is None: self.toggle_phone()

    def key_b(self):
        if getattr(self, "hackeria", None):
            self.hackeria.blackout(); return
        if self.miyo.ui is not None and self.overlay is self.miyo.ui: return
        self.miyo.open_build()

    def key_n(self):
        if getattr(self, "hackeria", None) and self.hackeria.handle_n():
            return
        if self.miyo.ui is not None and self.overlay is self.miyo.ui and getattr(self.miyo.ui, "kind", "") == "tsunami": self.miyo.close_ui(); return
        if self.overlay is not None and self.tsunami is None: return
        self.miyo.key_tsunami()

    def key_num(self, k):
        if self.miyo.ui is not None and self.overlay is self.miyo.ui and getattr(self.miyo.ui, "kind", "") == "tsunami":
            self.miyo.start_tsunami(("small", "medium", "big")[k]); return
        if self.camapp and self.camapp.get("picker"): self.cam_set_expr(("smile", "neutral", "frown")[k])

    def key_space(self):
        if self.camapp: self.cam_shutter()

    def key_enter(self):
        if self.camapp: self.cam_shutter(); return
        if self.home and self.home.get("mode") == "wardrobe": self.close_wardrobe(True); return
        if self.home_roam(): self.home_use(); return
        if self.ride and self.ride.get("mode") == "riding": self.skip_ride()

    def repair_car(self):
        """instantly repair the current car (paint + plate from FRGARAGE stay as they are)"""
        c = self.pcar
        if self.typing(): return
        if c is None: self.toast("Get in a car to repair it"); return
        c.damage = 0.0; c.dead = False; c.stuck_t = 0.0
        if hasattr(c, "health"): c.health = 100.0
        cfg = self.cars_cfg.get(c.kind)
        if cfg:
            try: c.set_paint(tuple(cfg.get("paint", c.paint_col))); c.make_plates(cfg.get("plate", c.plate_text))
            except Exception: pass
        from panda3d.core import CardMaker
        cm = CardMaker("spark"); cm.set_frame(-1, 1, -1, 1); root = self.app.render.attach_new_node("repair_fx")
        for k in range(14):
            s_ = root.attach_new_node(cm.generate()); s_.set_billboard_point_eye(); s_.set_texture(self.world.T("glow.png", repeat=False))
            s_.set_pos(c.x + random.uniform(-2, 2), c.y + random.uniform(-2, 2), random.uniform(0.3, 1.8)); s_.set_scale(random.uniform(0.25, 0.6))
            s_.set_color(0.5, 1.0, 0.6, 1)
        root.set_light_off(); root.set_depth_write(False); root.set_bin("fixed", 40)
        root.set_attrib(ColorBlendAttrib.make(ColorBlendAttrib.M_add, ColorBlendAttrib.O_incoming_alpha, ColorBlendAttrib.O_one))
        self.app.task_mgr.do_method_later(0.9, lambda t: root.remove_node(), "fs-repairfx")
        self.app.sfx("checkpoint", 0.6); self.app.sfx("door", 0.3); self.toast("Car repaired  -  good as new")

    def key_l(self):
        if self.typing(): return
        self.laptop.toggle()

    def typing(self):
        """the BUILD text box has focus: letter keys type, they don't honk / switch camera / repair"""
        if getattr(self, "laptop", None) is not None and self.laptop.ui is not None: return True
        if self.overlay is not None and getattr(self.overlay, "is_misto", False): return True
        if self.overlay is not None and getattr(self.overlay, "is_online", False): return True
        if self.camapp and self.camapp.get("misto"): return True
        m = getattr(self, "miyo", None)
        return m is not None and m.ui is not None and self.overlay is m.ui and hasattr(m.ui, "ent")

    def key_c(self):
        if self.typing(): return
        if self.ride: self.ride_cam_toggle(); return
        self.cam_mode = (self.cam_mode + 1) % 3

    def key_h(self):
        if self.typing(): return
        self.app.sfx("horn", 0.7)
        if self.pcar:
            for p in self.peds:
                if math.hypot(p.x - self.pcar.x, p.y - self.pcar.y) < 15: p.flee = 2.0; p.flee_from = (self.pcar.x, self.pcar.y)

    def key_esc(self):
        if getattr(self, "hackeria", None) and (self.hackeria.cam_view or self.hackeria.ui is not None):
            if self.hackeria.ui is not None:
                self.hackeria.close_ui(); return
            if self.hackeria.exit_cam():
                return
        if self.laptop.ui is not None or self.laptop.phase is not None:
            if getattr(self.laptop, "dlg", None): self.laptop.dlg.destroy(); self.laptop.dlg = None; return
            self.laptop.close(); return
        if self.camapp: self.close_camera(); return
        if self.phone: self.toggle_phone(); return
        if self.home:
            if self.home.get("mode") == "shower": self.end_shower()
            elif self.home.get("mode") == "wardrobe": self.close_wardrobe(False)
            else: self.leave_home()
            return
        if self.garage: self.close_garage(); return
        if self.overlay:
            if self.ride and self.ride.get("mode") == "menu": self.leave_taxi(); return
            self.close_overlay(); return
        if self.intro_t > 0: self.intro_t = 0.01; return
        self.app.show_pause()

    def key_r(self):
        if self.camapp: self.cam_flip(); return
        c = self.pcar
        if c is None: return
        x, y, h = self.world.nearest_road_point(c.x, c.y)
        for _ in range(6):
            if len([o for o in self.cars_near(x, y, 4.5) if o is not c]) == 0: break
            f = (-math.sin(math.radians(h)), math.cos(math.radians(h))); x += f[0] * 6; y += f[1] * 6
        c.x, c.y, c.h = x, y, h; c.vx = c.vy = c.w = 0.0; c.wake(); self.cam_pos = None; self.toast("Vehicle reset")

    def key_f(self):
        if self.blocked() or (self.ride is not None): return
        if self.pcar: self.exit_car(); return
        me = self.me()
        if self.taxi and self.taxi_ai_arrived() and math.hypot(self.taxi.x - me.x, self.taxi.y - me.y) < 8:
            self.board_taxi(); return
        best = None
        for c in self.cars_near(me.x, me.y, 7):
            if c is self.taxi or c is self.medic or getattr(c, "racer", False): continue
            d = math.hypot(c.x - me.x, c.y - me.y)
            if d < c.spec["hl"] + 2.3 and (best is None or d < best[0]): best = (d, c)
        if best: self.enter_car(best[1])

    def key_e(self):
        if self.camapp: return
        if self.home and self.home.get("mode") == "shower": self.end_shower(); return
        if self.home:
            if self.home.get("mode") == "room": self.home_use()
            return
        if self.blocked(): return
        if getattr(self, "hackeria", None) and self.hackeria.has_hack_target():
            # hold-to-hack is driven from Hackeria.update; tapping E only locks the target
            return
        if getattr(self, "hackeria", None) and self.hackeria.target is not None:
            # locked device: still swallow E so we don't trigger a nearby marker
            self.hackeria.try_hack()
            return
        m = self.near_marker()
        if m: self.start_activity(m["id"]); return
        if getattr(self, "bar", None) is not None and self.bar.near(): self.bar.open_menu()

    # ================================================================ car enter / exit / jack / switch
    def enter_car(self, c):
        if c.ai is not None and c.driver == "ai":     # carjack: the driver is ejected and runs off
            ex, ey = c.door_pos(1)
            p = Ped(self, random.choice(self.world.ped_loops), 0); p.x, p.y = ex, ey; p.flee = 4.0; p.flee_from = (c.x, c.y)
            self.peds.append(p); self.say_line(p, "jacked")
            if c.kind == "police": self.add_heat(2, "Stole a police car!")
            elif any(math.hypot(pc.x - c.x, pc.y - c.y) < 60 for pc in self.police): self.add_heat(1, "Carjacking witnessed!")
            if c in self.police: self.police.remove(c)
        if getattr(c, "taxi_driver", None) is not None: c.taxi_driver.destroy(); c.taxi_driver = None
        c.ai = None; c.driver = "player"; c.role = "player"; c.wake(); c.lights_on = False
        self.pcar = c; self.cam_pos = None
        self.me().seat(c, 1)
        bd = self.buddy()
        if bd: bd.seat(c, -1)
        self.app.sfx("door", 0.6); self.refresh_buttons()

    def exit_car(self, force=False):
        c = self.pcar
        if c.speed > 7 and not force: self.toast("Slow down to get out"); return
        if hasattr(self, "arsenal"): self.arsenal.unequip()
        def free(side):
            x, y = c.door_pos(side)
            px, py, nx, ny, tag = self.world.grid.push_circle(x, y, 0.4)
            return x + px, y + py
        x1, y1 = free(1); x2, y2 = free(-1)
        self.me().unseat(x1, y1, c.h - 90)
        bd = self.buddy()
        if bd: bd.unseat(x2, y2, c.h + 90)
        c.driver = None; c.throttle = 0; c.steer = 0; c.hand = True; c.nitro = False
        self.pcar = None; self.cam_yaw = c.h; self.cam_pos = None
        self.app.sfx("door", 0.6); self.refresh_buttons()

    def switch_char(self):
        if len(CREW) <= 1:
            if getattr(self, "hackeria", None):
                self.hackeria.open_skills()
            return
        if self.camapp: return
        if getattr(self, "guest", False):
            if not self.blocked(): self.toast("You're a guest in a FIREOUT ONLINE session - leave it to play as ELIJER")
            return
        if hasattr(self, "arsenal"): self.arsenal.unequip()
        at_home = self.home is not None and self.home.get("mode") == "room"
        if (self.blocked() and not at_home) or self.ride: return
        self.select_char(CREW[(CREW.index(self.active) + 1) % len(CREW)], _checked=True)

    def select_char(self, who, _checked=False):
        if getattr(self, "guest", False): return
        """v1.0.4.1 crew of two (ANA + DANIEL). Switching to the follower swaps who leads; switching to the benched one brings them in
        exactly where the current character stands (that character steps out and waits off-screen)."""
        if not _checked:
            if self.camapp or who == self.active: return
            if hasattr(self, "arsenal"): self.arsenal.unequip()
            at_home = self.home is not None and self.home.get("mode") == "room"
            if (self.blocked() and not at_home) or self.ride: return
        old = self.me()
        if who == self.mate:
            self.mate = self.active; self.active = who
        else:
            new = self.chars[who]; self.bench(new, False)
            new.x, new.y, new.h = old.x, old.y, old.h
            if self.home is not None: new.sync()
            self.bench(old, True); self.active = who; new.sync()
            if self.camapp is None and getattr(new, "expression", "neutral") != "neutral": new.set_expression("neutral")
        if self.pcar:
            self.me().seat(self.pcar, 1)
            bd = self.buddy()
            if bd: bd.seat(self.pcar, -1)
        else:
            self.cam_yaw = self.me().h; self.cam_pos = None
        self.cinematic = 0.8
        self.toast("Now playing as %s" % NAMES[self.active]); self.app.sfx("switch", 0.7)
        if self.miyo.ui is not None and self.overlay is self.miyo.ui: self.miyo.close_ui()
        self.update_portraits()
        if self.phone: self.phone_screen(getattr(self.phone, "which", "home"))     # the phone swaps with the character

    # ================================================================ markers / activities
    def spawn_markers(self):
        self.markers = []
        def add(id_, x, y, name, col, kind):
            self.markers.append({"id": id_, "x": x, "y": y, "name": name, "col": col, "kind": kind})
        for r in D.RACES: add(r["id"], r["start"][0], r["start"][1], r["name"], (1.0, 0.3, 0.7), "race")
        add("tt", D.TIME_TRIAL["start"][0], D.TIME_TRIAL["start"][1], D.TIME_TRIAL["name"], (0.3, 0.9, 1.0), "tt")
        add("chase", D.CHASE_MISSION["start"][0], D.CHASE_MISSION["start"][1], D.CHASE_MISSION["name"], (0.35, 0.45, 1.0), "chase")
        add("drift", D.DRIFT_ZONE["start"][0], D.DRIFT_ZONE["start"][1], D.DRIFT_ZONE["name"], (1.0, 0.6, 0.1), "drift")
        add("garage", D.GARAGE_POS[0], D.GARAGE_POS[1], "FRGARAGE", (0.2, 1.0, 0.9), "garage")
        add("shop", SHOP_POS[0], SHOP_POS[1], "KAZAN SUPPLY", (1.0, 0.85, 0.2), "shop")
        add("home", D.HOME_POS[0], D.HOME_POS[1], "ELIJER'S LOFT", (0.3, 0.9, 1.0), "home")
        add("sfc", D.STADIUM_GATE[0], D.STADIUM_GATE[1], "SFC 27", (0.3, 1.0, 0.45), "football")
        self.mk_np = self.app.render.attach_new_node("markers")
        tex = self.world.T("glow.png", repeat=False); beam = self.world.T("beam.png", repeat=False)
        for m in self.markers:
            n = self.mk_np.attach_new_node("m"); n.set_pos(m["x"], m["y"], 0)
            cm = CardMaker("col"); cm.set_frame(-2.2, 2.2, -26, 0)
            for a in (0, 60, 120):
                c = n.attach_new_node(cm.generate()); c.set_h(a); c.set_texture(beam); c.set_z(0)
                c.set_r(0); c.set_p(0); c.set_color(m["col"][0], m["col"][1], m["col"][2], 0.5); c.set_sz(-1)
            cm2 = CardMaker("ring"); cm2.set_frame(-6, 6, -6, 6)
            r = n.attach_new_node(cm2.generate()); r.set_p(-90); r.set_z(0.1); r.set_texture(tex); r.set_color(m["col"][0], m["col"][1], m["col"][2], 0.9)
            tn = TextNode("lbl"); tn.set_text(m["name"]); tn.set_align(TextNode.A_center)
            if U.FONT: tn.set_font(U.FONT)
            tn.set_text_color(m["col"][0], m["col"][1], m["col"][2], 1)
            t = n.attach_new_node(tn); t.set_z(6.5); t.set_scale(1.5); t.set_billboard_point_eye()
            m["np"] = n
        gx, gy, gz = self.world.garage_sign
        cm = CardMaker("frg"); cm.set_frame(-12, 12, -3, 3)
        s = self.app.render.attach_new_node(cm.generate()); s.set_pos(gx, gy + 0.1, gz + 0.8); s.set_h(180)
        s.set_texture(self.world.T("frgarage.png", repeat=False)); s.set_two_sided(True); s.set_color_scale(1.6, 1.6, 1.6, 1); s.set_light_off()
        self.garage_sign = s
        self.mk_np.set_light_off(); self.mk_np.set_depth_write(False); self.mk_np.set_bin("fixed", 30); self.mk_np.set_two_sided(True)
        self.mk_np.set_attrib(ColorBlendAttrib.make(ColorBlendAttrib.M_add, ColorBlendAttrib.O_incoming_alpha, ColorBlendAttrib.O_one))
        self.tok_np = self.app.render.attach_new_node("tokens")
        for t in D.TOKENS:
            if tuple(t) in self.tokens: continue
            cm = CardMaker("tok"); cm.set_frame(-1.2, 1.2, -1.2, 1.2)
            n = self.tok_np.attach_new_node(cm.generate()); n.set_pos(t[0], t[1], 1.6); n.set_billboard_point_eye(); n.set_texture(tex)
            n.set_color(1.0, 0.85, 0.2, 1); n.set_python_tag("tok", tuple(t))
        self.tok_np.set_light_off(); self.tok_np.set_depth_write(False); self.tok_np.set_bin("fixed", 31)
        self.tok_np.set_attrib(ColorBlendAttrib.make(ColorBlendAttrib.M_add, ColorBlendAttrib.O_incoming_alpha, ColorBlendAttrib.O_one))

    ICON = {"race": "R", "tt": "T", "chase": "P", "drift": "D", "garage": "G", "shop": "$", "home": "H",
            "hospital": "+", "tower": "A", "beach": "~", "speedcam": "S", "football": "F"}
    LEGEND = [("H", "ELIJER'S LOFT (home)"), ("G", "FRGARAGE (paint & plates)"), ("R", "Street race"), ("T", "Time trial"),
              ("D", "Drift zone"), ("P", D.GET_WANTED + " (police chase)"), ("S", "Speed camera"), ("$", "KAZAN SUPPLY (ammo)"), ("+", "Hospital"),
              ("A", "Shinko Tower (landmark)"), ("~", "HIKARI BEACH"), ("F", "SFC 27 STADIUM (football)"), ("*", "Neon token"), ("X", "Waypoint")]

    def build_pois(self):
        """non-interactive places shown on the map + minimap"""
        from fs_world import block_rect
        x0, y0, x1, y1 = block_rect(*D.TOWER_BLOCK)
        self.pois = [{"x": D.HOSPITAL_POS[0], "y": D.HOSPITAL_POS[1], "kind": "hospital", "name": "HOSPITAL", "col": (1.0, 0.35, 0.35)},
                     {"x": (x0 + x1) / 2, "y": (y0 + y1) / 2, "kind": "tower", "name": "SHINKO TOWER", "col": (1.0, 0.5, 0.2)},
                     {"x": 540.0, "y": -60.0, "kind": "beach", "name": "HIKARI BEACH", "col": (0.4, 0.9, 1.0)}]
        for (sx, sy, nm) in D.SPEED_CAMS:
            self.pois.append({"x": sx, "y": sy, "kind": "speedcam", "name": "SPEED CAM", "col": (0.9, 0.9, 0.3)})

    def near_marker(self):
        if self.activity: return None
        px, py = self.player_pos()
        for m in self.markers:
            if math.hypot(m["x"] - px, m["y"] - py) < 8: return m
        return None

    def ensure_in_car(self, x, y, h):
        c = self.pcar
        if c is None:
            c = self.own
            if c is None or c.dead or c not in self.cars:
                c = self.own = self.spawn_car(self.player_kind, x, y, h, role="player"); c.owned = True
            self.enter_car(c)
        for o in self.cars_near(x, y, 7):
            if o is not c and not getattr(o, "racer", False) and o not in (self.taxi, self.medic): self.remove_car(o)
        c.x, c.y, c.h = x, y, h; c.vx = c.vy = c.w = 0.0; c.wake(); self.cam_pos = None; self.cam_yaw = h
        return c

    def start_activity(self, aid):
        if self.activity: return
        if self.ride: return
        if self.phone: self.toggle_phone()
        self.close_overlay()
        if aid == "garage": self.open_garage(); return
        if aid == "shop": self.arsenal.refill(); return
        if aid == "home": self.enter_home(); return
        if aid == "sfc": self.online.open("football"); return
        if aid == "chase":
            sx, sy, sh = D.CHASE_MISSION["start"]; self.ensure_in_car(sx, sy, sh)
            self.activity = {"kind": "chase", "t": 0.0, "name": D.GET_WANTED}
            self.add_heat(3, "")
            self.caption(D.GET_WANTED, "Lose the police - break their line of sight!", 3.0); return
        if aid == "drift":
            sx, sy, sh = D.DRIFT_ZONE["start"]; self.ensure_in_car(sx, sy, sh)
            self.activity = {"kind": "drift", "t": D.DRIFT_ZONE["time"], "score": 0.0, "name": D.DRIFT_ZONE["name"], "count": 3.5}
            self.caption("BEACH DRIFT ZONE", "Hold SPACE / HANDBRAKE to drift inside the neon lot", 3.0); return
        race = next((r for r in D.RACES if r["id"] == aid), None); tt = aid == "tt"
        if race is None and not tt: return
        spec = D.TIME_TRIAL if tt else race
        sx, sy, sh = spec["start"]
        c = self.ensure_in_car(sx, sy, sh)
        cps = [tuple(p) for p in spec["cps"]]; laps = 1 if tt else race["laps"]
        w = self.world; nodes = []; prev = w.nearest_node(sx, sy)
        for cp in cps:
            n = w.nearest_node(*cp); seg = graph_path(w, prev, n); nodes += seg if not nodes else seg[1:]; prev = n
        pts = [w.nodes[n] for n in nodes]
        act = {"kind": "tt" if tt else "race", "id": aid, "name": spec["name"], "cps": cps, "laps": laps, "cp": 0, "lap": 1,
               "t": 0.0, "count": 3.5, "racers": [], "limit": spec.get("time")}
        if not tt:
            f = (-math.sin(math.radians(sh)), math.cos(math.radians(sh))); r_ = (f[1], -f[0])
            for k, (kind, col, nm) in enumerate((("coupe", (0.95, 0.85, 0.1), "RAIJIN"), ("gts", (0.1, 0.3, 0.9), "AOI"), ("coupe", (0.9, 0.3, 0.05), "KITSUNE"))):
                ob = 9.0 + 8.0 * ((k + 1) // 2); os_ = 3.5 if k % 2 == 0 else -3.5
                rx, ry = sx - f[0] * ob + r_[0] * os_, sy - f[1] * ob + r_[1] * os_
                if k == 0: rx, ry = sx + r_[0] * 3.5 * -1 - f[0] * 0.0, sy + r_[1] * -3.5
                for o in self.cars_near(rx, ry, 6):
                    if o is not c and o not in self.police and o not in (self.taxi, self.medic): self.remove_car(o)
                rc = self.spawn_car(kind, rx, ry, sh, paint=col, role="racer")
                rc.racer = True; rc.driver = "ai"; rc.asleep = False
                rc.ai = RacerAI(self, rc, pts * laps, skill=0.86 + 0.06 * k)
                rc.race = {"cp": 0, "lap": 1, "done": None, "name": nm}
                act["racers"].append(rc)
            if act["racers"]: self.npc_say("rival", random.choice(act["racers"]))     # rival trash talk (Japanese + English)
        self.activity = act
        self.cp_np = self.app.render.attach_new_node("cp")
        cm = CardMaker("cp"); cm.set_frame(-8, 8, -16, 0)
        for a in (0, 90):
            q = self.cp_np.attach_new_node(cm.generate()); q.set_h(a); q.set_texture(self.world.T("beam.png", repeat=False)); q.set_sz(-1)
        self.cp_np.set_color(1, 0.3, 0.8, 0.8); self.cp_np.set_light_off(); self.cp_np.set_two_sided(True); self.cp_np.set_depth_write(False)
        self.cp_np.set_bin("fixed", 32)
        self.cp_np.set_attrib(ColorBlendAttrib.make(ColorBlendAttrib.M_add, ColorBlendAttrib.O_incoming_alpha, ColorBlendAttrib.O_one))
        self.place_cp()
        self.caption(spec["name"], "%d checkpoints  -  %d lap%s" % (len(cps), laps, "s" if laps > 1 else ""), 3.0)

    def place_cp(self):
        a = self.activity
        if a and a["kind"] in ("race", "tt") and a["cp"] < len(a["cps"]) and self.cp_np:
            x, y = a["cps"][a["cp"]]; self.cp_np.set_pos(x, y, 0)

    def end_activity(self, title, sub, reward=0, win=True):
        a = self.activity; self.activity = None; self.big.setText("")
        if self.cp_np: self.cp_np.remove_node(); self.cp_np = None
        if a and a.get("racers"):
            for rc in a["racers"]:
                rc.racer = False; self.remove_car(rc)
        if reward: self.add_cash(reward)
        self.app.sfx("win" if win else "busted", 0.8)
        self.caption(title, sub + ("   +¥%s" % format(reward, ",") if reward else ""), 4.5)
        self.save()

    def quit_activity(self):
        if self.activity:
            if self.activity["kind"] == "chase": self.heat = 0
            self.end_activity("ACTIVITY ENDED", "", 0, False)

    def update_activity(self, dt):
        a = self.activity
        if not a: return
        if a["kind"] in ("race", "tt", "drift") and a.get("count", 0) > 0:
            prev = math.ceil(a["count"]); a["count"] -= dt
            if self.pcar: self.pcar.vx = self.pcar.vy = 0; self.pcar.w = 0
            for rc in a.get("racers", []): rc.vx = rc.vy = 0; rc.w = 0
            if math.ceil(a["count"]) != prev and prev <= 3: self.app.sfx("go" if a["count"] <= 0 else "beep", 0.8)
            self.big.setText(str(max(1, math.ceil(a["count"]))) if a["count"] > 0 and a["count"] <= 3 else "")
            return
        if a["kind"] in ("race", "tt"):
            a["t"] += dt
            self.big.setText("GO!" if a["t"] < 1.0 else "")
            c = self.pcar
            if c is None:
                self.end_activity("RACE ABANDONED", "You left the car", 0, False); return
            cx, cy = a["cps"][a["cp"]]
            if math.hypot(c.x - cx, c.y - cy) < 14:
                a["cp"] += 1; self.app.sfx("checkpoint", 0.7)
                if a["cp"] >= len(a["cps"]):
                    if a["lap"] >= a["laps"]:
                        if a["kind"] == "tt":
                            ok = a["t"] <= a["limit"]; best = self.best.get("tt")
                            if ok and (best is None or a["t"] < best): self.best["tt"] = a["t"]
                            self.end_activity("TIME TRIAL " + ("CLEAR!" if ok else "FAILED"), "Time %s" % self.fmt(a["t"]), 3000 if ok else 0, ok)
                        else:
                            pos = self.race_position(finished=True)
                            rew = {1: 8000, 2: 4000, 3: 2000}.get(pos, 500)
                            best = self.best.get(a["id"])
                            if pos == 1 and (best is None or a["t"] < best): self.best[a["id"]] = a["t"]
                            self.end_activity("FINISHED %s" % self.ordinal(pos), "%s  -  %s" % (a["name"], self.fmt(a["t"])), rew, pos == 1)
                        return
                    a["lap"] += 1; a["cp"] = 0
                self.place_cp()
            for rc in a["racers"]:
                r = rc.race
                if r["done"]: continue
                rx, ry = a["cps"][r["cp"]]
                if math.hypot(rc.x - rx, rc.y - ry) < 16:
                    r["cp"] += 1
                    if r["cp"] >= len(a["cps"]):
                        if r["lap"] >= a["laps"]: r["done"] = a["t"]; r["cp"] = len(a["cps"]) - 1
                        else: r["lap"] += 1; r["cp"] = 0
            if a["kind"] == "tt" and a["t"] > a["limit"]:
                self.end_activity("TIME TRIAL FAILED", "Out of time", 0, False)
        elif a["kind"] == "chase":
            a["t"] += dt
            if self.heat == 0: self.end_activity("ESCAPED!", "You lost the police in %s" % self.fmt(a["t"]), 6000, True)
        elif a["kind"] == "drift":
            a["t"] -= dt; c = self.pcar; self.big.setText("")
            if c and self.world.in_lot(c.x, c.y) and c.drift > 2.5 and c.speed > 7:
                a["score"] += c.drift * c.speed * dt * 2
            if a["t"] <= 0 or c is None:
                s = int(a["score"]); best = self.best.get("drift", 0)
                if s > best: self.best["drift"] = s
                self.end_activity("DRIFT ZONE COMPLETE", "Score %d  (best %d)" % (s, max(s, best)), s // 4, True)

    def race_position(self, finished=False):
        a = self.activity
        if not a or a["kind"] != "race" or not self.pcar: return 1
        def prog(lap, cp, x, y):
            cx, cy = a["cps"][min(cp, len(a["cps"]) - 1)]
            return lap * 1000 + cp * 10 - math.hypot(cx - x, cy - y) / 1000
        me = 1e9 if finished else prog(a["lap"], a["cp"], self.pcar.x, self.pcar.y)
        pos = 1
        for rc in a["racers"]:
            r = rc.race
            if r["done"] is not None or prog(r["lap"], r["cp"], rc.x, rc.y) > me: pos += 1
        return pos

    def rubber_band(self, ai):
        a = self.activity
        if not a or not self.pcar or not hasattr(ai.car, "race"): return 1.0
        r = ai.car.race
        d = math.hypot(ai.car.x - self.pcar.x, ai.car.y - self.pcar.y)
        ahead = r["lap"] * 100 + r["cp"] > a["lap"] * 100 + a["cp"]
        return 0.84 if ahead and d > 50 else (1.1 if not ahead and d > 50 else 1.0)

    @staticmethod
    def fmt(t):
        return "%d:%05.2f" % (int(t // 60), t % 60)

    @staticmethod
    def ordinal(n):
        return {1: "1ST", 2: "2ND", 3: "3RD"}.get(n, "%dTH" % n)

    # ================================================================ police / heat
    def add_heat(self, n, why=""):
        if n > 0 and self.active == "ana" and self.outfit == "police" and random.random() < 0.3:
            n -= 1                       # TOKYO NEON PD uniform: the police are a little slower to suspect you
            if n <= 0: return
        old = self.heat; self.heat = min(5, self.heat + n); self.escape_t = 0.0
        if self.heat > old:
            self.app.sfx("heat", 0.6)
            if why: self.toast(why)
            if self.heat >= 2:          # v1.0.4: NEON TOKYO NEWS covers your police chases (IX NAVI browser)
                if self.news and self.news[-1][0] == "wanted" and time.time() - self.news[-1][2] < 300: self.news[-1] = ("wanted", self.heat, self.news[-1][2])
                else: self.news.append(("wanted", self.heat, time.time()))

    def make_cop(self, c):
        if c not in self.police: self.police.append(c)
        c.ai = PoliceAI(self, c); c.lights_on = True; c.driver = "ai"; c.asleep = False

    def update_police(self, dt):
        px, py = self.player_pos()
        if self.heat > 0:
            want = min(6, 1 + self.heat)
            self.heat_t -= dt
            if len(self.police) < want and self.heat_t <= 0:
                self.heat_t = 3.0
                x, y, h = self.offscreen_road_point(90, 170)
                c = self.spawn_car("police", x, y, h, role="police"); self.make_cop(c)
            seen = any(isinstance(c.ai, PoliceAI) and c.ai.seen for c in self.police)
            if seen: self.escape_t = max(0.0, self.escape_t - dt * 2)
            else:
                self.escape_t += dt
                if self.escape_t > 5.0 + self.heat * 2.0:
                    self.heat = 0; self.escape_t = 0; self.toast("You lost them!"); self.app.sfx("win", 0.5)
            self._cop_cd = getattr(self, "_cop_cd", 2.0) - dt
            if self._cop_cd <= 0:
                near = [c for c in self.police if c is not self.pcar and math.hypot(c.x - px, c.y - py) < 40]
                if near: self.npc_say("police", min(near, key=lambda c: math.hypot(c.x - px, c.y - py))); self._cop_cd = random.uniform(6, 10)
            close = any(math.hypot(c.x - px, c.y - py) < 7.5 for c in self.police if c is not self.pcar)
            sp = self.pcar.speed if self.pcar else 0.0
            if close and sp < 2.5: self.bust_t += dt
            else: self.bust_t = max(0.0, self.bust_t - dt)
            if self.bust_t > 2.5: self.busted()
        else:
            self.bust_t = 0.0
            for c in list(self.police):
                if c is self.pcar: self.police.remove(c); continue
                c.lights_on = False
                if isinstance(c.ai, PoliceAI):
                    n = self.world.nearest_node(c.x, c.y); c.ai = TrafficAI(self, c, n)
                if math.hypot(c.x - px, c.y - py) > 150: self.remove_car(c)
            if self.pcar:
                for c in self.cars_near(px, py, 22):
                    if c.kind == "police" and c is not self.pcar and self.pcar.speed > 33 and c.driver == "ai":
                        self.add_heat(1, "Speeding past the police!"); self.make_cop(c); break

    def death_screen(self, word, sub):
        """full-screen slow-motion, washed-out grey screen with a big title (BUSTED / CAPITULATED), then respawn."""
        from direct.gui.OnscreenText import OnscreenText
        a = self.app
        if getattr(self, "_ds", None): self._ds_end()
        cm = CardMaker("ds"); cm.set_frame(-3, 3, -1.2, 1.2)
        n = a.aspect2d.attach_new_node(cm.generate()); n.set_color(0.35, 0.35, 0.37, 0.55); n.set_transparency(TransparencyAttrib.M_alpha); n.set_bin("fixed", 0)
        col = (0.95, 0.25, 0.25, 1) if word == "CAPITULATED" else (0.35, 0.65, 1.0, 1)
        t = OnscreenText(parent=a.aspect2d, text=word, pos=(0, 0.02), scale=0.2, fg=col, shadow=(0, 0, 0, 1), font=U.FONT)
        t2 = OnscreenText(parent=a.aspect2d, text=sub, pos=(0, -0.12), scale=0.05, fg=(1, 1, 1, 1), shadow=(0, 0, 0, 1), font=U.FONT_PLAIN)
        self._ds = [n, t, t2]; self.time_scale = 0.35
        a.task_mgr.do_method_later(2.6, lambda task: self._ds_end(), "fs-ds")

    def _ds_end(self):
        for x in getattr(self, "_ds", None) or []:
            try: x.destroy()
            except Exception:
                try: x.remove_node()
                except Exception: pass
        self._ds = None; self.time_scale = 1.0

    def busted(self):
        self.arsenal.unequip()
        self.bust_t = 0; self.heat = 0
        fine = min(self.cash, 1500); self.cash -= fine
        if self.activity: self.activity = None; self.big.setText("")
        if self.cp_np: self.cp_np.remove_node(); self.cp_np = None
        self.death_screen("BUSTED", "Fine ¥%s  -  released at home" % format(fine, ",")); self.app.sfx("busted", 0.8)
        self.npc_say("busted", who="警察官")
        if self.pcar: self.exit_car(force=True)
        hx, hy = D.HOME_POS[0] + 1.0, D.HOME_POS[1] - 2.0      # released: back home
        self.me().x, self.me().y = hx, hy
        bd = self.buddy()
        if bd: bd.x, bd.y = hx + 1.5, hy
        self.cam_pos = None
        for c in list(self.police): self.remove_car(c)
        self.fade(1.0)

    def on_impact(self, car, imp, other):
        if car is self.pcar or other is self.pcar:
            self.shake = min(1.0, self.shake + imp / 25.0)
            self.app.sfx("crash" if imp > 9 else "bump", min(1.0, imp / 18.0))
            if other is not None and imp > 5:
                for c in (car, other):
                    if c is not self.pcar and c.kind == "police" and c.driver == "ai":
                        self.add_heat(1, "Hit a police car!"); self.make_cop(c)
            if other is not None and isinstance(getattr(other, "ai", None), TrafficAI) and imp > 6:
                other.ai.speed = max(6.0, other.ai.speed * 0.7)

    def on_car_water(self, car):
        if car is self.pcar:
            self.toast("Splash! Car recovered to the coast road.")
            car.x, car.y, car.h = D.BEACH_ROAD_X - 3, max(-380, min(380, car.y)), 0; car.vx = car.vy = car.w = 0; self.cam_pos = None

    # ================================================================ people & companion
    def update_people(self, dt):
        threats = [c for c in self.cars if c.speed > 4]
        for p in list(self.peds):
            thr = None
            for c in threats:
                d = math.hypot(p.x - c.x, p.y - c.y)
                if d < 10 and (c is self.pcar or c in self.police): thr = (c.x, c.y)
                if p.knock <= 0 and any(math.hypot(p.x - cx, p.y - cy) < r + 0.4 for cx, cy, r, _ in c.circles()):
                    sp = c.speed; p.knock_down(c.vx / sp, c.vy / sp, min(sp * 0.5, 9))
                    if c is self.pcar:
                        self.app.sfx("bump", 0.6); self.say_line(p, "scared")
                        if any(math.hypot(pc.x - p.x, pc.y - p.y) < 50 for pc in self.police): self.add_heat(1, "Hit a pedestrian!")
            p.update(dt, thr)
        me = self.me(); bud = self.buddy()
        if self.pcar is None and me.in_car is None:
            for c in threats:
                if me.knock <= 0 and any(math.hypot(me.x - cx, me.y - cy) < r + 0.4 for cx, cy, r, _ in c.circles()):
                    sp = c.speed; me.knock_down(c.vx / sp, c.vy / sp, min(sp * 0.5, 9)); me.health -= sp * 2.0
                    self.app.sfx("bump", 0.8); self.shake = 0.6
                    if me.health <= 0: self.knocked_out()
            if not me.update_knock(dt): self.move_on_foot(me, dt)
            else: me.sync()
            if bud is not None and bud.in_car is None: self.follow(bud, me, dt)
        self.health_regen += dt
        if self.health_regen > 1.0:
            self.health_regen = 0
            for p in self.chars.values(): p.health = min(100.0, p.health + 0.4)

    def knocked_out(self):
        self.arsenal.unequip()
        me = self.me(); me.health = 60.0
        fee = min(self.cash, 800); self.cash -= fee
        self.death_screen("CAPITULATED", "Hospital bill ¥%d  -  patched up, sent home" % fee); self.app.sfx("busted", 0.7)
        hx, hy = D.HOME_POS[0] + 1.0, D.HOME_POS[1] - 2.0      # patched up, sent home
        me.x, me.y = hx, hy; me.sync()
        bd = self.buddy()
        if bd:
            bd.x, bd.y = hx + 1.5, hy; bd.sync()
        self.heat = 0; self.fade(1.0)

    def move_on_foot(self, me, dt):
        f = (1 if self.down("w", "arrow_up", "v_up") else 0) - (1 if self.down("s", "arrow_down", "v_down") else 0)
        s = (1 if self.down("d", "arrow_right", "v_right") else 0) - (1 if self.down("a", "arrow_left", "v_left") else 0)
        run = self.down("shift", "v_nitro"); sp = 0.0
        if getattr(self, "eating", None) is not None and me is self.me(): f = s = 0; run = False      # v1.0.4: stand still while eating
        if self.arsenal.aiming and not self.blocked():
            self.cam_yaw -= s * 110 * dt
            mw = self.app.mouseWatcherNode
            if mw is not None and mw.has_mouse(): self.cam_yaw -= mw.get_mouse_x() * 90 * dt
            me.h = self.cam_yaw; s = 0
        roam = self.home_roam(); blk = (self.blocked() and not roam) or self.camapp is not None
        if (f or s) and not blk and self.phone is None:
            yaw = math.radians(self.cam_yaw)
            fx, fy = -math.sin(yaw), math.cos(yaw); rx, ry = fy, -fx
            dx, dy = fx * f + rx * s, fy * f + ry * s; L = math.hypot(dx, dy) or 1; dx /= L; dy /= L
            sp = 5.8 if run else 2.1
            me.x += dx * sp * dt; me.y += dy * sp * dt
            th = math.degrees(math.atan2(-dx, dy))
            if not self.arsenal.aiming: me.h += wrap(th - me.h) * min(1, dt * 10)
            if f > 0 and not s: self.cam_yaw += wrap(me.h - self.cam_yaw) * min(1, dt * 1.2)
            elif s and not f: self.cam_yaw += wrap(me.h - self.cam_yaw) * min(1, dt * 0.6)
        if roam:                                   # v1.0.3: free roam inside the house - walls + furniture collide
            for _ in range(2):
                px, py, nx, ny, tag = self.world.home_grid.push_circle(me.x, me.y, 0.32); me.x += px; me.y += py
            b = self.world.home_bounds; me.x = max(b[0], min(b[2], me.x)); me.y = max(b[1], min(b[3], me.y))
            me.walk_anim(dt, sp); me.sync(); return
        px, py, nx, ny, tag = self.world.grid.push_circle(me.x, me.y, 0.35); me.x += px; me.y += py
        for c in self.cars_near(me.x, me.y, 5):
            for cx, cy, r, _ in c.circles():
                dx, dy = me.x - cx, me.y - cy; d = math.hypot(dx, dy)
                if 1e-3 < d < r + 0.35:
                    me.x += dx / d * (r + 0.35 - d); me.y += dy / d * (r + 0.35 - d)
        me.x = min(me.x, D.SEA_X - 0.5) if not self.world.on_pier(me.x, me.y) else me.x
        W = D.WORLD; me.x = max(W[0] + 1, min(W[2] - 1, me.x)); me.y = max(W[1] + 1, min(W[3] - 1, me.y))
        me.walk_anim(dt, sp); me.sync()

    def follow(self, bud, me, dt):
        if bud.update_knock(dt): bud.sync(); return
        r = math.radians(me.h); tx = me.x + math.cos(r) * 1.5 + math.sin(r) * 1.2; ty = me.y + math.sin(r) * 1.5 - math.cos(r) * 1.2
        if self.camapp:                            # camera app: step behind (photobomb the selfie, out of the rear camera's view)
            tx = me.x + math.cos(r) * 0.9 + math.sin(r) * 1.5; ty = me.y + math.sin(r) * 0.9 - math.cos(r) * 1.5
        elif self.home:                            # indoors: walk beside, slightly ahead, so they don't block the camera
            tx = me.x + math.cos(r) * 1.2 - math.sin(r) * 0.5; ty = me.y + math.sin(r) * 1.2 + math.cos(r) * 0.5
        dx, dy = tx - bud.x, ty - bud.y; d = math.hypot(dx, dy)
        if d > 25:
            bud.x, bud.y = tx, ty; d = 0
        sp = 0.0
        if d > 0.7:
            sp = min(6.2, max(1.8, d * 1.5)); bud.x += dx / d * sp * dt; bud.y += dy / d * sp * dt
            th = math.degrees(math.atan2(-dx, dy)); bud.h += wrap(th - bud.h) * min(1, dt * 8)
        else:
            bud.h += wrap(me.h - bud.h) * min(1, dt * 3)
        if self.home:
            for _ in range(2):
                px, py, nx, ny, tag = self.world.home_grid.push_circle(bud.x, bud.y, 0.32); bud.x += px; bud.y += py
            b = self.world.home_bounds; bud.x = max(b[0], min(b[2], bud.x)); bud.y = max(b[1], min(b[3], bud.y))
        else:
            px, py, nx, ny, tag = self.world.grid.push_circle(bud.x, bud.y, 0.35); bud.x += px; bud.y += py
        dme = math.hypot(bud.x - me.x, bud.y - me.y)
        if 1e-3 < dme < 0.75: bud.x += (bud.x - me.x) / dme * (0.75 - dme); bud.y += (bud.y - me.y) / dme * (0.75 - dme)
        if not self.home: bud.x = min(bud.x, D.SEA_X - 0.5) if not self.world.on_pier(bud.x, bud.y) else bud.x
        bud.walk_anim(dt, sp); bud.sync()

    # ================================================================ chatter / subtitles
    def say_line(self, p, group=None):
        """v1.0.4: most pedestrians speak Japanese (English translation underneath); a few tourists stay English-only."""
        if not self.app.settings.get("chatter", True): return
        idx = self.app.voice_index
        if not idx: return
        dist = D.district_at(p.x, p.y)
        from fs_lines import TOURIST
        if group is None:
            ja = [("ja", e) for e in idx.get("ja", []) if e["district"] in ("*", dist)]
            en = [("ambient", e) for e in idx.get("ambient", []) if e["district"] in ("*", dist)
                  and int(e["file"].split("_")[1].split(".")[0]) in TOURIST]
            pool = en if (en and random.random() < 0.12) else ja
        else:
            if idx.get("ja_" + group) and random.random() < 0.85: return self.npc_say(group, p)
            pool = [(group, e) for e in idx.get(group, [])]
        if not pool: return
        g, e = random.choice(pool)
        px, py = self.player_pos(); d = math.hypot(p.x - px, p.y - py)
        self.app.voice(e["file"], max(0.25, 1.0 - d / 25.0))
        self.bubble(p, e["text"], e.get("en") if g == "ja" else None)

    def npc_say(self, group, p=None, who=None, vol=0.9):
        """Japanese NPC line (+ English underneath): a speech bubble over p, or a two-line subtitle with a speaker name"""
        e = random.choice(self.app.voice_index.get("ja_" + group) or [None])
        if e is None: return
        if self.app.settings.get("chatter", True): self.app.voice(e["file"], vol)
        if p is not None: self.bubble(p, e["text"], e["en"])
        else: self.subtitle(("%s：" % who if who else "") + e["text"], 4.0, en=e["en"])

    def bubble(self, p, txt, en=None):
        """speech bubble: Japanese line on top, the English translation underneath in smaller text"""
        if not self.app.settings.get("subtitles", True): return
        from panda3d.core import TextPropertiesManager, TextProperties
        tpm = TextPropertiesManager.get_global_ptr()
        if not tpm.has_properties("en"):
            tp = TextProperties(); tp.set_text_scale(0.72); tp.set_text_color(0.85, 0.92, 1.0, 1)
            if U.FONT_PLAIN: tp.set_font(U.FONT_PLAIN)
            tpm.set_properties("en", tp)
        tn = TextNode("bub"); tn.set_align(TextNode.A_center)          # wrapped by hand: kinsoku rules for Japanese
        f = self.app.jpfont if en is not None else U.FONT_PLAIN
        if f: tn.set_font(f)
        import textwrap
        body = U.jwrap(txt, 15.0) if en is not None else "\n".join(textwrap.wrap(txt, 26))
        tn.set_text(body + (("\n\1en\1" + "\n".join(textwrap.wrap(en, 34)) + "\2") if en else ""))
        tn.set_card_color(0.05, 0.03, 0.1, 0.78); tn.set_card_as_margin(0.4, 0.4, 0.25, 0.2); tn.set_text_color(1, 1, 1, 1)
        if getattr(p, "bub", None) and not p.bub.is_empty(): p.bub.remove_node()
        b = p.np.attach_new_node(tn); b.set_z(2.35); b.set_scale(0.2); b.set_billboard_point_eye(); b.set_light_off(); b.set_bin("fixed", 50)
        b.set_depth_test(False); b.set_depth_write(False)
        p.bub = b
        self.app.do_method_later(4.5, lambda t, b=b: (b.remove_node() if not b.is_empty() else None) or t.done, "bub")

    def update_chatter(self, dt):
        self.talk_cd -= dt; self.banter_cd -= dt
        px, py = self.player_pos()
        if self.talk_cd <= 0 and self.pcar is None:
            near = [p for p in self.peds if math.hypot(p.x - px, p.y - py) < 7 and p.knock <= 0]
            if near: self.say_line(random.choice(near)); self.talk_cd = random.uniform(9, 16)
        if self.banter_cd <= 0 and self.pcar and not self.activity:
            self.banter_cd = random.uniform(60, 100)
            k = random.randrange(len(BANTER)); who, line = BANTER[k]
            self.app.voice("banter_%02d.wav" % k, 0.8)
            self.subtitle("%s: %s" % (NAMES[who], line), 4.0)

    def subtitle(self, txt, dur=3.5, en=None):
        """two-line subtitle: Japanese on top, English translation underneath (smaller); plain English lines use one line"""
        if not self.app.settings.get("subtitles", True): return
        self.sub.setText(U.jwrap(txt, 30.0) if en else txt); self.sub_t = dur
        self.sub["font"] = self.app.jpfont if en else U.FONT_PLAIN
        self.sub_en.setText(en or "")

    # ================================================================ phone (EX IX G9)
    def accent(self):
        return {"elijer": (0.25, 0.9, 1.0, 1), "ana": (0.2, 0.55, 1.0, 1)}.get(self.active, (0.25, 0.9, 1.0, 1))

    def toggle_phone(self):
        if self.phone:
            self.phone.destroy(); self.phone = None; self.app.sfx("click", 0.5); self.refresh_buttons(); return
        if (self.blocked() and not self.home_roam()) or self.ride: return
        self.phone_screen("home"); self.app.sfx("click", 0.6)

    def phone_screen(self, which):
        """EX IX G9 phone: ANA's blue one with the cracked screen, DANIEL's apple-green one. Anchored bottom-right in
        aspect2d (scales with window height), so it looks the same at 1024x576, 1280x720 and 1920x1080."""
        if self.phone: self.phone.destroy()
        acc = self.accent(); who = self.active if self.active in CREW else "elijer"
        T = lambda n: Filename.from_os_specific(os.path.join(self.app.BASE, "assets", "tex", n)).get_fullpath()
        PH = 1.22; k = PH / 1170.0; PW = 585 * k                 # phone art is 585x1170 px, screen at (43,43) 479x1054
        sx0, sy1 = (43 - 292.5) * k, (585 - 43) * k; sw, sh = 479 * k, 1054 * k
        cx = sx0 + sw / 2; top = sy1
        drv = self.pcar is not None       # while driving, sit left of the speedometer + driving buttons so they stay visible
        root = DirectFrame(parent=self.app.a2dBottomRight, frameColor=(0, 0, 0, 0), pos=((-0.86 if drv else -0.06) - PW / 2, 0, PH / 2 + 0.04))
        root.set_bin("gui-popup", 60); self.phone = root; root.which = which; root.driving = drv
        pn = "phone_%s.png" % who
        if not os.path.exists(os.path.join(self.app.BASE, "assets", "tex", pn)): pn = "phone_elijer.png"
        img = OnscreenImage(parent=root, image=T(pn), scale=(PW / 2, 1, PH / 2)); img.set_transparency(TransparencyAttrib.M_alpha)
        W = lambda t, y, sc, fg=(1, 1, 1, 1), font=None, wrap=None: U.text(root, t, (cx, top - y), sc, fg=fg, font=font or U.FONT_PLAIN, wrap=wrap)
        W(time.strftime("%H:%M"), 0.16, 0.085)
        W("EX IX G9  -  Hi, %s" % NAMES[who], 0.215, 0.03, fg=acc)
        items = []
        def btn(lbl, fn, y, w=0.2):
            U.button(root, lbl, (cx, top - y), fn, w=w, h=0.042, scale=0.032, edge=acc); items.append((lbl, fn))
        if which == "home":
            import fs_misto
            apps = [("phone_icon_hackeria.png", "EX OS HACKERIA", lambda: (self.toggle_phone(), self.hackeria.open_phone())),
                    ("phone_icon_contacts.png", "Contacts", lambda: self.phone_screen("contacts")), ("phone_icon_taxi.png", "JP TAXI", lambda: self.phone_screen("taxi")),
                    ("phone_icon_camera.png", "CAMERA", self.open_camera), ("ix_icon_misto2.png", "MISTO 2", lambda: fs_misto.open_app(self))]
            if hasattr(self, "online_app"): apps.append(("ix_icon_online.png", "ONLINE", self.online_app))
            if getattr(self, "events", None) is not None: apps.append(("ix_icon_festival.png", "FESTIVAL", lambda: self.phone_screen("festival")))
            for n, (ic, lbl, fn) in enumerate(apps):
                x = cx + ((n % 3) - 1) * 0.15; yo = (n // 3) * 0.17
                b = DirectButton(parent=root, image=T(ic), image_scale=0.062 if ic.startswith("phone") else 0.05, relief=None, pos=(x, 0, top - 0.42 - yo), command=fn)
                b.set_transparency(TransparencyAttrib.M_alpha)
                U.text(root, lbl, (x, top - 0.52 - yo), 0.027, font=U.FONT_PLAIN); items.append((lbl, fn))
            btn("MAP", lambda: (self.toggle_phone(), self.toggle_map()), 0.76)
            btn("CLOSE", self.toggle_phone, 0.86)
        elif which == "festival" and getattr(self, "events", None) is not None:
            self.events.page(root, cx, top, btn, W)
            btn("BACK", lambda: self.phone_screen("home"), 0.86)
        elif which == "contacts":
            W("CONTACTS", 0.30, 0.045, fg=acc, font=U.FONT)
            btn("Emergency Services  119", self.call_emergency, 0.42, w=0.23)
            btn("JP Taxi", lambda: self.phone_screen("taxi"), 0.53, w=0.23)
            btn("BACK", lambda: self.phone_screen("home"), 0.81)
        elif which == "taxi":
            W("JP TAXI", 0.30, 0.055, fg=(1.0, 0.8, 0.15, 1), font=U.FONT)
            if self.taxi:
                st = "Driver arriving" if not self.taxi_ai_arrived() else "Your taxi is here - press F"
                W(st, 0.40, 0.03, wrap=14)
                btn("CANCEL TAXI", self.cancel_taxi, 0.55)
            else:
                W("Base fare \u00a5500 + distance", 0.40, 0.028)
                btn("REQUEST TAXI", self.request_taxi, 0.55)
            btn("BACK", lambda: self.phone_screen("home"), 0.81)
        if who == "ana":       # cracked glass drawn over everything, thin and translucent so the app text stays readable
            cr = OnscreenImage(parent=root, image=T("phone_ana_crack.png"), scale=(PW / 2, 1, PH / 2)); cr.set_transparency(TransparencyAttrib.M_alpha)
            cr.set_color_scale(1, 1, 1, 0.95); cr.set_bin("gui-popup", 80)
        self.phone.items = items; self.phone.sel = 0
        self.refresh_buttons()

    # ================================================================ CAMERA app (v1.0.3): selfie + rear camera, saves PNGs
    def pictures_dir(self):
        """%USERPROFILE%\\Pictures\\FIREOUT ONLINE (or ~/Pictures/FIREOUT ONLINE); falls back to the save folder"""
        cands = []
        if os.name == "nt":
            try:
                import ctypes
                from ctypes import wintypes
                class GUID(ctypes.Structure):
                    _fields_ = [("a", wintypes.DWORD), ("b", wintypes.WORD), ("c", wintypes.WORD), ("d", ctypes.c_ubyte * 8)]
                g = GUID(0x33E28130, 0x4E1E, 0x4676, (ctypes.c_ubyte * 8)(0x83, 0x5A, 0x98, 0x39, 0x5C, 0x3B, 0xC3, 0xBB))  # FOLDERID_Pictures
                pp = ctypes.c_wchar_p()
                if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(g), 0, None, ctypes.byref(pp)) == 0:
                    cands.append(pp.value); ctypes.windll.ole32.CoTaskMemFree(pp)
            except Exception: pass
            if os.environ.get("USERPROFILE"): cands.append(os.path.join(os.environ["USERPROFILE"], "Pictures"))
        cands.append(os.path.join(os.path.expanduser("~"), "Pictures"))
        for c in cands:
            try:
                d = os.path.join(c, "FIREOUT ONLINE"); os.makedirs(d, exist_ok=True)
                if os.access(d, os.W_OK): return d
            except Exception: continue
        d = os.path.join(os.path.dirname(self.app.save_path()), "Pictures"); os.makedirs(d, exist_ok=True); return d

    # ---- v1.0.4: the photos the game itself saved (PHOTOS app, KIRAKIRA feed, DELETE)
    def add_photo(self, path):
        path = os.path.abspath(path)
        if path not in self.photos: self.photos.append(path)
        self.save()

    def photo_list(self):
        return [p for p in self.photos if os.path.exists(p)]

    def delete_photo(self, path):
        """delete one selfie - only a PNG this game saved itself into Pictures/FIREOUT ONLINE, nothing else"""
        path = os.path.abspath(path)
        if path not in self.photos: return False
        try:
            ok_dir = os.path.normcase(os.path.dirname(path)) == os.path.normcase(os.path.abspath(self.pictures_dir()))
            if ok_dir and path.lower().endswith(".png") and os.path.isfile(path): os.remove(path)
        except Exception as e: self.app.log_error(e)
        self.photos = [p for p in self.photos if p != path]
        m = getattr(self, "misto", None)
        if isinstance(m, dict): m["stories"] = [p for p in m.get("stories", []) if p != path]
        self.save(); self.app.sfx("click", 0.6)
        return not os.path.exists(path)

    def open_camera(self, misto=False):
        if self.phone: self.phone.destroy(); self.phone = None
        if self.ride or (self.blocked() and not self.home_roam()): return
        if hasattr(self, "arsenal"): self.arsenal.unequip()
        me = self.me()
        self.camapp = {"mode": "rear" if self.pcar else "selfie", "t": 0.0, "ang": 0.0, "pitch": 0.0, "flash": 0.0, "expr": "neutral", "misto": misto, "lens": "none"}
        me.set_expression("neutral")
        if self.home: self.home_prompt_off()
        self.cam_prop(); self.cam_ui(); self.app.sfx("click", 0.6); self.refresh_buttons()
        if self.pcar: self.toast("In a car: REAR camera only - selfies work on foot", 3.0)

    def cam_prop(self):
        """the EX IX G9 in ANA / DANIEL's right hand (selfie)"""
        ca = self.camapp; me = self.me()
        if ca.get("prop"): ca["prop"].remove_node(); ca["prop"] = None
        if ca["mode"] != "selfie" or me.in_car is not None: return
        hand = getattr(me, "handR", None)
        if hand is None or hand.is_empty(): return
        from fs_geom import MB
        b = MB("phone_prop"); col = {"ana": (0.12, 0.35, 0.95, 1)}.get(me.who, (0.45, 0.85, 0.25, 1))
        b.box(-0.036, -0.005, -0.075, 0.036, 0.005, 0.075, col)
        b.box(-0.032, 0.0052, -0.07, 0.032, 0.0062, 0.07, (0.3, 0.55, 1.2, 1))           # screen (faces the character)
        b.box(0.014, -0.0065, 0.045, 0.028, -0.005, 0.064, (0.05, 0.05, 0.06, 1))         # lens
        n = b.node(); n.reparent_to(hand); n.set_pos(0, 0, -0.045); ca["prop"] = n

    def cam_ui(self):
        ca = self.camapp
        if ca.get("ui"): ca["ui"].destroy()
        a = self.app; o = ca["ui"] = DirectFrame(parent=a.aspect2d, frameColor=(0, 0, 0, 0)); o.set_bin("gui-popup", 50)
        acc = self.accent(); ar = a.getAspectRatio()
        for sx in (-1, 1):                                  # viewfinder corner brackets
            for sy in (-1, 1):
                x, y = sx * (ar - 0.12), sy * 0.86
                DirectFrame(parent=o, frameColor=(1, 1, 1, 0.85), frameSize=(min(0, -sx * 0.14), max(0, -sx * 0.14), -0.004, 0.004), pos=(x, 0, y))
                DirectFrame(parent=o, frameColor=(1, 1, 1, 0.85), frameSize=(-0.004, 0.004, min(0, -sy * 0.14), max(0, -sy * 0.14)), pos=(x, 0, y))
        for k in (-1, 1):                                   # faint rule-of-thirds grid
            DirectFrame(parent=o, frameColor=(1, 1, 1, 0.12), frameSize=(-ar, ar, -0.002, 0.002), pos=(0, 0, k * 0.333))
            DirectFrame(parent=o, frameColor=(1, 1, 1, 0.12), frameSize=(-0.002, 0.002, -1, 1), pos=(k * ar / 3, 0, 0))
        sel = ca["mode"] == "selfie"
        if ca.get("misto"):
            import fs_misto; fs_misto.cam_extras(self, o)
        else: U.text(o, "CAMERA", (0, 0.88), 0.05, fg=acc)
        U.text(o, ("SELFIE" if sel else "PHOTO") + "   -   EX IX G9", (0, 0.82), 0.032, font=U.FONT_PLAIN, shadow=(0, 0, 0, 0.8))
        T = lambda n: Filename.from_os_specific(os.path.join(self.app.BASE, "assets", "tex", n)).get_fullpath()
        # big round camera-style shutter, centred at the bottom; click it or press Space / Enter
        sh = ca["shutter"] = DirectButton(parent=o, relief=None, pos=(0, 0, -0.74), command=self.cam_shutter,
                                          image=(T("cam_shutter.png"), T("cam_shutter_down.png"), T("cam_shutter_hover.png"), T("cam_shutter.png")),
                                          image_scale=0.115, frameSize=(-0.115, 0.115, -0.115, 0.115), rolloverSound=None, clickSound=None)
        sh.set_transparency(TransparencyAttrib.M_alpha)
        U.text(o, "SNAP" if ca.get("misto") else "TAKE PHOTO", (0, -0.905), 0.045, fg=(1, 1, 1, 1), shadow=(0, 0, 0, 0.9))
        U.text(o, "Space / Enter", (0, -0.955), 0.026, font=U.FONT_PLAIN, fg=(1, 1, 1, 0.8), shadow=(0, 0, 0, 0.9))
        U.button(o, "BACK", (-0.78, -0.76), self.close_camera, w=0.13, h=0.05, scale=0.036, hint="Esc")
        U.button(o, "FLIP", (-0.40, -0.76), self.cam_flip, w=0.13, h=0.05, scale=0.036, edge=acc, hint="R")
        sm = ca["selm_btn"] = DirectButton(parent=o, relief=None, pos=(0.40, 0, -0.73), command=self.cam_selmotes,
                                           image=T("cam_selmotes.png"), image_scale=0.06, frameSize=(-0.065, 0.065, -0.065, 0.065),
                                           rolloverSound=None, clickSound=None)
        sm.set_transparency(TransparencyAttrib.M_alpha)
        U.text(o, "SELMOTES", (0.40, -0.83), 0.036, fg=(1.0, 0.85, 0.25, 1), shadow=(0, 0, 0, 0.9))
        U.text(o, NAMES[self.active] + ": " + {"smile": "SMILE", "neutral": "NEUTRAL", "frown": "GOOFY FROWN"}[ca.get("expr", "neutral")],
               (0.40, -0.875), 0.024, font=U.FONT_PLAIN, fg=(1, 1, 1, 0.85), shadow=(0, 0, 0, 0.9))
        U.text(o, "A / D  angle      W / S  tilt", (0, 0.77), 0.026, font=U.FONT_PLAIN, fg=(1, 1, 1, 0.75), shadow=(0, 0, 0, 0.8))
        if ca.get("picker"): self.cam_selmotes(force=True)

    def cam_selmotes(self, force=False):
        """SELMOTES picker: three facial expressions for the active character (kept on for the photo)"""
        ca = self.camapp
        if not ca: return
        if ca.get("picker_np"): ca["picker_np"].destroy(); ca["picker_np"] = None
        if not force:
            ca["picker"] = not ca.get("picker")
            self.app.sfx("click", 0.5)
        if not ca.get("picker"): return
        pk = ca["picker_np"] = DirectFrame(parent=ca["ui"], frameColor=(0.06, 0.04, 0.12, 0.88), frameSize=(-0.2, 0.2, -0.2, 0.2),
                                          pos=(0.40, 0, -0.38))
        U.text(pk, "SELMOTES", (0, 0.145), 0.038, fg=(1.0, 0.85, 0.25, 1))
        cur = ca.get("expr", "neutral")
        for k, (eid, nm) in enumerate((("smile", "SMILE"), ("neutral", "NEUTRAL"), ("frown", "GOOFY FROWN"))):
            U.button(pk, nm, (0, 0.06 - k * 0.095), self.cam_set_expr, w=0.17, h=0.038, scale=0.03, extra=[eid],
                     edge=(1.0, 0.85, 0.25, 1) if eid == cur else (0.5, 0.5, 0.6, 1), hint=str(k + 1))

    def cam_set_expr(self, eid):
        ca = self.camapp
        if not ca: return
        ca["expr"] = eid; self.me().set_expression(eid); self.app.sfx("click", 0.5)
        self.toast("%s: %s" % (NAMES[self.active], {"smile": "SMILE", "neutral": "NEUTRAL", "frown": "GOOFY FROWN"}[eid]), 1.5)
        self.cam_ui()

    def cam_flip(self):
        ca = self.camapp
        if not ca: return
        if ca["mode"] == "rear" and self.pcar is not None:
            self.toast("Selfie mode is off in a car - get out first"); return
        ca["mode"] = "rear" if ca["mode"] == "selfie" else "selfie"; ca["ang"] = 0.0; ca["pitch"] = 0.0
        self.cam_prop(); self.cam_ui(); self.app.sfx("click", 0.5)

    def close_camera(self):
        ca = self.camapp
        if not ca: return
        for k in ("prop",):
            if ca.get(k): ca[k].remove_node()
        for k in ("ui", "flash_np", "lens_np"):
            if ca.get(k): ca[k].destroy()
        me = self.me(); me.arm_pose = None; me.set_grip(False, False); me.np.show(); me.set_expression("neutral")
        self.camapp = None; self.cam_pos = None; self.app.camLens.set_fov(65)
        if self.home: self.home_panel()
        self.app.sfx("click", 0.5); self.refresh_buttons()

    def cam_shutter(self):
        ca = self.camapp
        if not ca or ca.get("busy"): return
        ca["busy"] = True; a = self.app
        nm = "%s_%s.png" % ("selfie" if ca["mode"] == "selfie" else "photo", time.strftime("%Y%m%d_%H%M%S"))
        path = None
        try:
            if ca.get("misto"):
                import fs_misto; d = fs_misto.snap_dir(self); nm = "snap_" + time.strftime("%Y%m%d_%H%M%S") + ".png"
            else: d = self.pictures_dir()
            path = os.path.join(d, nm)
            k = 1
            while os.path.exists(path): path = os.path.join(d, nm[:-4] + "_%d.png" % k); k += 1
            a.render2d.hide()                               # no HUD / viewfinder in the picture
            a.graphicsEngine.render_frame(); a.graphicsEngine.render_frame()
            ok = a.win.save_screenshot(Filename.from_os_specific(path))
            if ok and getattr(self, "events", None) is not None: self.events.photo_taken()
        except Exception as e:
            ok = False; print("camera save failed", e)
        finally:
            a.render2d.show(); ca["busy"] = False
        if ca.get("flash_np"): ca["flash_np"].destroy()
        ca["flash_np"] = DirectFrame(parent=a.render2d, frameColor=(1, 1, 1, 1), frameSize=(-1, 1, -1, 1)); ca["flash_np"].set_bin("gui-popup", 90)
        ca["flash_np"].set_transparency(TransparencyAttrib.M_alpha); ca["flash"] = 0.35
        ca["last"] = path if ok else None
        self.app.sfx("click", 0.9)
        if ok and ca.get("misto"):
            if ca.get("flash_np"): ca["flash_np"].destroy(); ca["flash_np"] = None
            import fs_misto; fs_misto.after_shot(self, path); return
        if ok: self.add_photo(path)
        self.toast(("Saved  -  Pictures/FIREOUT ONLINE/%s" % os.path.basename(path)) if ok else "Couldn't save the photo", 3.0)

    def update_camapp(self, dt):
        ca = self.camapp
        if not ca: return
        self._update_camapp(dt)
        if self.camapp and self.camapp.get("misto"):
            import fs_misto; fs_misto.track_lens(self)      # after the selfie camera has moved this frame

    def _update_camapp(self, dt):
        ca = self.camapp
        ca["t"] += dt; t = ca["t"]; me = self.me(); cam = self.app.camera; lens = self.app.camLens
        if ca.get("flash_np"):
            ca["flash"] -= dt; f = max(0.0, ca["flash"] / 0.35)
            ca["flash_np"]["frameColor"] = (1, 1, 1, f * 0.9)
            if f <= 0: ca["flash_np"].destroy(); ca["flash_np"] = None
        s = (1 if self.down("d", "arrow_right", "v_right") else 0) - (1 if self.down("a", "arrow_left", "v_left") else 0)
        v = (1 if self.down("w", "arrow_up", "v_up") else 0) - (1 if self.down("s", "arrow_down", "v_down") else 0)
        if self.pcar is not None:
            if ca["mode"] == "selfie": ca["mode"] = "rear"; self.cam_prop(); self.cam_ui()
            c = self.pcar; ca["ang"] = max(-70, min(70, ca["ang"] - s * 60 * dt)); ca["pitch"] = max(-25, min(25, ca["pitch"] + v * 40 * dt))
            r = math.radians(c.h + ca["ang"]); fx, fy = -math.sin(r), math.cos(r)
            cam.set_pos(c.x + c.fwd[0] * 0.2, c.y + c.fwd[1] * 0.2, c.spec["roof"] + 0.1); cam.set_hpr(c.h + ca["ang"], ca["pitch"], 0)
            lens.set_fov(66); self.cam_h = c.h; return
        fx0, fy0 = -math.sin(math.radians(me.h)), math.cos(math.radians(me.h))
        face = 1.56
        if ca["mode"] == "selfie":
            ca["ang"] = max(-55, min(55, ca["ang"] + s * 50 * dt)); ca["pitch"] = max(-0.25, min(0.35, ca["pitch"] + v * 0.4 * dt))
            r = math.radians(me.h + 14 + ca["ang"]); fx, fy = -math.sin(r), math.cos(r)
            d = 0.92 if me.who == "ana" else 1.0; cz = face + 0.16 + ca["pitch"]
            cam.set_pos(me.x + fx * d, me.y + fy * d, cz); cam.look_at(me.x + fx0 * 0.05, me.y + fy0 * 0.05, face - 0.12 if not ca.get("misto") else face + 0.02); lens.set_fov(64)
            # pose: right arm out towards the lens holding the phone, left hand waves beside the face
            wv = math.sin(t * 7.0)
            me.set_arms((-78, 14), (-46 + 3 * wv, 30), (-14, 0), (-128 + 14 * wv, 4)); me.set_grip(True, False)
            me.model.set_r(math.sin(t * 1.4) * 1.5)
            pr = ca.get("prop")
            if pr: pr.look_at(self.app.render, Point3(me.x + fx0 * 0.1, me.y + fy0 * 0.1, face)); pr.set_h(pr, 180)
        else:
            me.h = (me.h - s * 70 * dt) % 360; me.sync(); ca["pitch"] = max(-30, min(30, ca["pitch"] + v * 40 * dt))
            me.set_arms((-70, 6), (-70, 6), (-35, 12), (-35, 12)); me.set_grip(True, True)
            fx, fy = fx0, fy0
            cam.set_pos(me.x + fx * 0.42, me.y + fy * 0.42, 1.42); cam.set_hpr(me.h, ca["pitch"], 0); lens.set_fov(66)
        self.cam_h = me.h

    def phone_nav(self, d):
        if not self.phone: return
        self.phone.sel = (self.phone.sel + d) % len(self.phone.items)
        self.toast(self.phone.items[self.phone.sel][0], 1.2)

    def phone_ok(self):
        if self.phone: self.phone.items[self.phone.sel][1]()

    def call_emergency(self):
        self.toggle_phone(); self.app.sfx("dial", 0.7)
        if self.medic: self.toast("An ambulance is already on its way"); return
        me = self.me()
        self.npc_say("op119", who="119番")
        x, y, h = self.offscreen_road_point(70, 140)
        c = self.spawn_car("ambulance", x, y, h, role="medic"); c.lights_on = True; c.driver = "ai"; c.asleep = False
        c.ai = ResponderAI(self, c, (me.x, me.y)); c.t0 = self.time
        self.medic = c

    def update_responders(self, dt):
        px, py = self.player_pos()
        for kind in ("medic", "taxi"):
            c = getattr(self, kind)
            if c is None: continue
            if c.dead or c not in self.cars: setattr(self, kind, None); continue
            if self.ride and c is self.ride["car"]: continue
            ai = c.ai
            if not isinstance(ai, ResponderAI): continue
            el = self.time - getattr(c, "t0", self.time)
            d = math.hypot(c.x - px, c.y - py)
            if not ai.arrived:
                if (el > 9 and d > 70 and not self.in_view(c.x, c.y)) or el > 22:      # guarantee a fast arrival
                    x, y, h = self.offscreen_road_point(35, 60)
                    if el > 22: x, y, h = self.world.nearest_road_point(px + 6, py + 6)
                    c.x, c.y, c.h = x, y, h; c.vx = c.vy = 0; ai.route(); c.t0 = self.time - 12
                if abs(ai.dest[0] - px) + abs(ai.dest[1] - py) > 25: ai.dest = (px, py); ai.route()
            elif kind == "medic" and not getattr(c, "done", False) and d < 14:
                c.done = True; me = self.me()
                if me.health < 99:
                    me.health = 100.0
                    bd = self.buddy()
                    if bd: bd.health = 100.0
                    self.npc_say("paramedic", who="救急隊員")
                else:
                    self.npc_say("paramedic_fine", who="救急隊員")
                self.app.do_method_later(6.0, lambda t: self.release_medic() or t.done, "medic-leave")
            elif kind == "medic" and not getattr(c, "done", False) and ai.arrived and d >= 14:
                ai.arrived = False; ai.dest = (px, py); ai.route()

    def release_medic(self):
        c = self.medic; self.medic = None
        if c and not c.dead:
            c.lights_on = False; c.ai = TrafficAI(self, c, self.world.nearest_node(c.x, c.y)); c.role = "traffic"

    def taxi_ai_arrived(self):
        return self.taxi is not None and isinstance(self.taxi.ai, ResponderAI) and self.taxi.ai.arrived

    def request_taxi(self):
        if self.pcar: self.toast("Get out of the car first"); return
        self.app.sfx("dial", 0.7)
        me = self.me(); x, y, h = self.offscreen_road_point(80, 140)
        c = self.spawn_car("taxi", x, y, h, role="taxi"); c.driver = "ai"; c.asleep = False
        c.ai = ResponderAI(self, c, (me.x, me.y)); c.t0 = self.time
        self.taxi = c; self.toast("JP TAXI: a driver is on the way (about 15 s)", 3.0)
        self.phone_screen("taxi")

    def cancel_taxi(self):
        c = self.taxi; self.taxi = None
        if c and not c.dead: c.ai = TrafficAI(self, c, self.world.nearest_node(c.x, c.y)); c.role = "traffic"
        self.toast("Taxi cancelled"); self.phone_screen("taxi") if self.phone else None

    def board_taxi(self):
        c = self.taxi
        if self.phone: self.toggle_phone()
        self.me().seat(c, -1)
        bd = self.buddy()
        if bd: bd.seat(c, 1)
        for p_, sx in ((self.me(), -0.36),) + (((bd, 0.36),) if bd else ()):
            p_.np.set_x(sx); p_.np.set_y(-1.2); p_.set_arms((-14, 4), (-14, 4), (-60, 6), (-60, 6)); p_.set_grip(False, False)
        self.ride = {"car": c, "mode": "menu", "fare": 0, "cam": "fp", "cam_k": 1.0, "t": 0.0}
        self.app.sfx("door", 0.6); self.driver_say("hello", turn=True)
        self.taxi_menu()

    def taxi_menu(self):
        dests = []
        if self.waypoint: dests.append(("MAP WAYPOINT", self.waypoint))
        dests.append(("HOME  ELIJER'S LOFT", (D.HOME_POS[0] + 8, D.HOME_POS[1] - 8)))
        dests.append(("FRGARAGE", (D.GARAGE_POS[0], D.GARAGE_POS[1] + 6)))
        dests.append(("FIREOUT ONLINE SFC 27 FOOTBALL PITCH", (D.BEACH_ROAD_X + 4.0, D.STADIUM_GATE[1])))
        for did, nm, jp, col in D.DISTRICTS:
            dests.append(("%s  %s" % (nm, jp), {"crossing": (0, 0), "akari": (-250, 250), "kurogane": (-250, -250),
                                                "tower": (250, 250), "sakura": (250, -250), "beach": (460, 0)}[did]))
        self.taxi_dests = [d[0] for d in dests]
        self.overlay = DirectFrame(parent=self.app.aspect2d, frameColor=(0, 0, 0, 0), pos=(-0.78, 0, 0.08))     # left: the driver stays in view
        U.panel(self.overlay, -0.6, 0.6, -0.78, 0.62, edge=(1.0, 0.8, 0.15, 1))
        U.text(self.overlay, "JP TAXI  -  WHERE TO?", (0, 0.52), 0.06, fg=(1.0, 0.8, 0.15, 1))
        for k, (nm, p) in enumerate(dests):
            U.button(self.overlay, nm, (0, 0.4 - k * 0.1), self.taxi_go, w=0.5, h=0.045, scale=0.034, extra=[p, nm],
                     font=self.app.jpfont, edge=(1.0, 0.8, 0.15, 1))
        U.button(self.overlay, "GET OUT", (0, 0.4 - len(dests) * 0.1), self.leave_taxi, w=0.5, h=0.045, scale=0.034, hint="Esc")
        self.refresh_buttons()

    def taxi_go(self, p, name):
        self.close_overlay(); c = self.ride["car"]
        d = math.hypot(p[0] - c.x, p[1] - c.y)
        fare = int(500 + 2.5 * d); self.ride.update(mode="riding", dest=p, fare=fare, t=0.0, dest_name=name)
        c.ai = ResponderAI(self, c, p, fast=False); c.ai.arrived = False; c.ai.mul = 1.4      # v1.0.4: a bit too fast...
        self.ride["bump_t"] = random.uniform(5.0, 11.0)
        self.toast("Heading to %s - fare ¥%s  (ENTER to skip trip,  C: first person / rear view)" % (name.split("  ")[0], format(fare, ",")), 3.5)
        self.driver_say("go"); self.ride["cam"] = "rear"          # v1.0.4: off we go - the camera eases out behind the taxi
        self.refresh_buttons()

    # ---- v1.0.4 taxi: the driver speaks British English (pre-rendered offline with Piper), first-person back seat camera
    def driver_say(self, key, extra=None, turn=False):
        c = (self.ride or {}).get("car") or self.taxi; d = getattr(c, "taxi_driver", None) if c is not None else None
        e = random.choice(self.app.voice_index.get("taxi_en_" + key) or [None])
        if e is None: return
        self.app.voice(e["file"], 1.0)
        dur = 1.6
        try:
            import wave
            with wave.open(os.path.join(self.app.BASE, "assets", "voice", e["file"])) as w: dur = w.getnframes() / float(w.getframerate())
        except Exception: pass
        self.subtitle("Driver: " + e["text"] + (("  " + extra) if extra else ""), max(3.0, dur + 1.5))
        self._drv_talk = {"d": d, "t": 0.0, "dur": dur, "turn": turn}

    def update_taxi_fx(self, dt):
        """driver mouth + head turn while talking; first-person / rear ride camera"""
        tk = getattr(self, "_drv_talk", None)
        if tk is not None and tk["d"] is not None and not tk["d"].np.is_empty():
            tk["t"] += dt; t = tk["t"]; d = tk["d"]
            talking = t < tk["dur"]
            d.set_chew(abs(math.sin(t * 11.0)) if talking else 0.0)
            if tk["turn"]:
                k = min(1.0, t / 0.4) if t < tk["dur"] + 0.4 else max(0.0, 1.0 - (t - tk["dur"] - 0.4) / 0.5)
                d.np.set_h(25.0 * k * k * (3 - 2 * k))
            if t > tk["dur"] + 1.0: d.set_chew(0.0); d.np.set_h(0); self._drv_talk = None
        r = self.ride
        if not r or r.get("car") is None: return
        c = r["car"]; cam = self.app.camera
        want = 1.0 if r.get("cam", "fp") == "fp" else 0.0
        r["cam_k"] = r.get("cam_k", want) + (want - r.get("cam_k", want)) * min(1.0, dt * 2.5)
        k = r["cam_k"]; e = k * k * (3 - 2 * k)
        from panda3d.core import Point3
        fp_pos = Point3(-0.3, -1.15, 1.06); fp_look = Point3(0.55, 3.0, 0.8)
        rr_pos = Point3(0.9, -7.0, 2.7); rr_look = Point3(0.0, 0.2, 0.9)
        pos = rr_pos + (fp_pos - rr_pos) * e; look = rr_look + (fp_look - rr_look) * e
        cam.set_pos(self.app.render.get_relative_point(c.np, pos)); cam.look_at(self.app.render.get_relative_point(c.np, look))
        self.app.camLens.set_fov(72 if e > 0.5 else 62)
        me = self.me()
        if e > 0.6: me.np.hide()          # the camera is in your own head: hide your body in first person
        else: me.np.show()

    def taxi_bump(self, c):
        """comedic bump: the taxi clips the nearest car (or a kerb / bollard), the other car spins and honks, sparks + shake,
        and the driver is back to full speed within a second, completely unbothered"""
        f = c.fwd; best = None
        for o in self.cars_near(c.x, c.y, 30):
            if o is c or o is self.pcar: continue
            dx, dy = o.x - c.x, o.y - c.y; fw = dx * f[0] + dy * f[1]
            if fw > -4 and (best is None or math.hypot(dx, dy) < best[0]): best = (math.hypot(dx, dy), o)
        side = random.choice((-1, 1))
        c.h += side * random.uniform(5, 9); c.vx += f[1] * side * 2.5; c.vy -= f[0] * side * 2.5      # jolt, but no stopping
        c.damage = min(getattr(c, "damage", 0.0) + 3.0, 40.0)
        if best is not None:
            o = best[1]
            if getattr(o, "asleep", False): o.wake()
            o.h += random.choice((-1, 1)) * random.uniform(35, 70); o.vx += f[0] * 4 - f[1] * side * 3; o.vy += f[1] * 4 + f[0] * side * 3
            o.damage = min(getattr(o, "damage", 0.0) + 8.0, 60.0)
            if hasattr(o, "ai") and o.ai is not None and hasattr(o.ai, "wait"): o.ai.wait = 2.5
            near_ped = min(self.peds, key=lambda p: math.hypot(p.x - o.x, p.y - o.y)) if self.peds else None
            if near_ped is not None and math.hypot(near_ped.x - o.x, near_ped.y - o.y) < 25: self.npc_say("crash_shout", near_ped)
            else: self.npc_say("crash_shout", who="運転手（相手）")
            x, y = (c.x + o.x) / 2, (c.y + o.y) / 2
        else:
            x, y = c.x + f[0] * 2.2 - f[1] * side * 0.9, c.y + f[1] * 2.2 + f[0] * side * 0.9
        self.app.sfx("bump", 0.9); self.app.do_method_later(0.35, lambda t: self.app.sfx("horn", 0.8) or t.done, "bump-horn")
        self.shake = max(self.shake, 0.7); self.bump_fx(x, y)
        self.ride["bumped"] = self.ride.get("bumped", 0) + 1
        if random.random() < 0.75:
            self.app.do_method_later(0.6, lambda t: (self.driver_say("oops") if self.ride else None) or t.done, "taxi-oops")

    def bump_fx(self, x, y):
        """a quick burst of sparks + a puff at the point of contact"""
        from panda3d.core import CardMaker
        cm = CardMaker("spark"); cm.set_frame(-0.06, 0.06, -0.06, 0.06)
        root = self.app.render.attach_new_node("bumpfx"); root.set_light_off(); root.set_bin("fixed", 30); root.set_depth_write(False)
        sp = []
        for k in range(22):
            n = root.attach_new_node(cm.generate()); n.set_pos(x, y, 0.6); n.set_billboard_point_eye()
            n.set_color(1.0, random.uniform(0.6, 0.95), 0.2, 1); sp.append((n, random.uniform(-6, 6), random.uniform(-6, 6), random.uniform(2, 6)))
        st = {"t": 0.0}
        def tick(task):
            dt = globalClock.get_dt(); st["t"] += dt
            for i, (n, vx, vy, vz) in enumerate(sp):
                vz -= 12 * dt; sp[i] = (n, vx, vy, vz); n.set_pos(n.get_x() + vx * dt, n.get_y() + vy * dt, max(0.05, n.get_z() + vz * dt))
            if st["t"] > 0.7: root.remove_node(); return task.done
            return task.cont
        self.app.task_mgr.add(tick, "bumpfx"); self.last_bump_fx = (root, sp)

    def ride_cam_toggle(self):
        if self.ride: self.ride["cam"] = "rear" if self.ride.get("cam", "fp") == "fp" else "fp"

    def skip_ride(self):
        r = self.ride
        if not r or r.get("mode") != "riding": return
        self.fade(0.8); c = r["car"]
        x, y, h = self.world.nearest_road_point(*r["dest"])
        for o in self.cars_near(x, y, 7):
            if o is not c: self.remove_car(o)
        c.x, c.y, c.h = x, y, h; c.vx = c.vy = 0; c.ai.arrived = True; self.cam_pos = None

    def update_ride(self, dt):
        r = self.ride
        if not r or r.get("mode") != "riding": return
        r["t"] += dt; c = r["car"]
        # v1.0.4 slapstick: every so often he clips a car or a street prop, jolts, and just carries on as if nothing happened
        r["bump_t"] = r.get("bump_t", 8.0) - dt
        if r["bump_t"] <= 0 and not c.ai.arrived and c.speed > 7.0:
            self.taxi_bump(c); r["bump_t"] = random.uniform(9.0, 18.0)
        # never stuck: if the taxi is boxed in by traffic for a while, clear the way, then hop it along the route
        r["slow"] = r.get("slow", 0.0) + dt if (c.speed < 1.5 and not c.ai.arrived) else 0.0
        if r["slow"] > 4.0 and not r.get("cleared"):
            f = c.fwd; r["cleared"] = True
            for o in list(self.cars_near(c.x, c.y, 12)):
                if o is c or not isinstance(o.ai, TrafficAI): continue
                dx, dy = o.x - c.x, o.y - c.y
                if dx * f[0] + dy * f[1] > -1 and not self.in_view(o.x, o.y): self.remove_car(o)
        if r["slow"] > 8.0:
            pf = c.ai.pf; i = min(pf.i + 1, len(pf.pts) - 1); x, y = pf.pts[i]
            nx_, ny_ = pf.pts[min(i + 1, len(pf.pts) - 1)]
            c.x, c.y = x, y; c.vx = c.vy = 0.0
            if (nx_, ny_) != (x, y): c.h = math.degrees(math.atan2(-(nx_ - x), ny_ - y))
            pf.i = i; r["slow"] = 0.0; r["cleared"] = False
        if c.ai.arrived and c.speed < 1.0:
            fare = min(self.cash, r["fare"]); self.cash -= fare
            self.toast("Arrived. Fare paid: ¥%s" % format(fare, ","), 3.0); self.app.sfx("checkpoint", 0.6)
            self.driver_say("arrive", extra="That'll be ¥%s. Cheers, have a good one!" % format(fare, ","), turn=True)
            self.leave_taxi()

    def leave_taxi(self):
        r = self.ride; self.close_overlay()
        if not r: return
        c = r["car"]; self.ride = None; self.taxi = None; self.me().np.show()
        x1, y1 = c.door_pos(-1)
        px, py, nx, ny, tag = self.world.grid.push_circle(x1, y1, 0.4)
        self.me().unseat(x1 + px, y1 + py, c.h + 90)
        bd = self.buddy()
        if bd: bd.unseat(x1 + px + 1.0, y1 + py + 0.5, c.h + 90)
        if "SFC 27" in str(r.get("dest_name", "")) and r.get("mode") == "riding" and c.ai is not None and getattr(c.ai, "arrived", False):
            gx, gy = D.STADIUM_GATE                   # v1.0.5: dropped right at the stadium entrance
            me = self.me(); me.x, me.y, me.h = gx - 1.5, gy, -90.0; me.sync()
            b = self.buddy()
            if b:
                b.x, b.y, b.h = gx - 2.5, gy + 1.2, -90.0; b.sync()
            self.fade(0.6)
            self.toast("SFC 27 STADIUM  -  press [E] at the gate to play", 3.5)
            c.ai = TrafficAI(self, c, self.world.nearest_node(c.x, c.y)); c.role = "traffic"
            self.cam_yaw = -90.0; self.cam_pos = None; self.app.sfx("door", 0.6); self.refresh_buttons(); return
        c.ai = TrafficAI(self, c, self.world.nearest_node(c.x, c.y)); c.role = "traffic"
        self.cam_yaw = c.h; self.cam_pos = None; self.app.sfx("door", 0.6); self.refresh_buttons()

    # ================================================================ FRGARAGE
    # ================================================================ ANA & DANIEL'S HOUSE
    def enter_home(self):
        self.arsenal.unequip()
        if self.phone: self.toggle_phone()
        if self.pcar: self.exit_car(force=True)
        if self.heat > 0: self.toast("Lose the police first!"); return
        self.cap_k = 0.0; self.cap1.setText(""); self.cap2.setText(""); self.big.setText("")
        X, Y = D.HOME_INT
        self.home = {"mode": "room", "ret": self.player_pos(), "a": 0.0, "spot": None}
        self.world.home_int.show()
        me, bd = self.me(), self.buddy()
        pair = [(me, (4.0, -3.5, 0))]
        if bd: pair.append((bd, (4.9, -3.0, 20)))
        for p, (dx, dy, h) in pair:
            p.x, p.y, p.h = X + dx, Y + dy, h; p.sync(); p.np.show(); p.walk_anim(0.016, 0.0)
        self.cam_yaw = 0.0; self.cam_pos = None
        self.home_cam(); self.home_panel(); self.app.sfx("door", 0.5); self.refresh_buttons(); self.fade(0.6)

    def home_roam(self):
        return self.home is not None and self.home.get("mode") == "room"

    def home_cam_clear(self, tx, ty, x, y):
        """keep the house camera inside the room and in front of walls / tall furniture (no clipping)"""
        rs = self.world.home_cam_rects; b = self.world.home_bounds; m = 0.22
        def bad(px, py):
            if not (b[0] - 0.05 < px < b[2] + 0.05 and b[1] - 0.05 < py < b[3] + 0.05): return True
            return any(r[0] - m < px < r[2] + m and r[1] - m < py < r[3] + m for r in rs)
        n = 24; last = (tx, ty)
        for k in range(1, n + 1):
            f = k / n; px, py = tx + (x - tx) * f, ty + (y - ty) * f
            if bad(px, py): return last
            last = (px, py)
        return last

    def home_cam(self):
        X, Y = D.HOME_INT; cam = self.app.camera; self.app.camLens.set_fov(62)
        if self.home and self.home.get("mode") == "wardrobe":
            a = self.me(); cam.set_pos(a.x + 0.5, a.y + 2.9, 1.5); cam.look_at(a.x - 0.35, a.y, 0.95)
        else:                                       # v1.0.3: third-person follow camera, same feel as outside
            me = self.me(); dt = getattr(self, "_home_dt", 0.016)
            r = math.radians(self.cam_yaw); fx, fy = -math.sin(r), math.cos(r); dist, hgt = 3.1, 1.95
            if self.cinematic > 0: self.cinematic -= dt
            x, y = self.home_cam_clear(me.x, me.y, me.x - fx * dist + fy * 0.35, me.y - fy * dist - fx * 0.35)
            if self.cam_pos is None: self.cam_pos = [x, y]
            k = min(1, dt * 8); self.cam_pos[0] += (x - self.cam_pos[0]) * k; self.cam_pos[1] += (y - self.cam_pos[1]) * k
            self.cam_pos[0], self.cam_pos[1] = self.home_cam_clear(me.x, me.y, self.cam_pos[0], self.cam_pos[1])
            d = math.hypot(self.cam_pos[0] - me.x, self.cam_pos[1] - me.y)
            cam.set_pos(self.cam_pos[0], self.cam_pos[1], min(2.75, hgt + max(0.0, 1.6 - d) * 0.35))
            cam.look_at(me.x + fx * 1.5 + fy * 0.35, me.y + fy * 1.5 - fx * 0.35, 1.25); self.app.camLens.set_fov(68); self.cam_h = self.cam_yaw

    def home_spot(self):
        me = self.me(); best = None
        for sp in self.world.home_spots:
            d = math.hypot(me.x - sp[2], me.y - sp[3])
            if d < sp[4] and (best is None or d < best[0]): best = (d, sp)
        return best[1] if best else None

    def home_use(self, sid=None):
        if not self.home_roam(): return
        if sid is None:
            sp = self.home_spot()
            if sp is None: return
            sid = sp[0]
        me = self.me()
        if sid == "shower": self.start_shower()
        elif sid == "wardrobe": self.open_wardrobe()
        elif sid == "sleep": self.home_sleep()
        elif sid == "save": self.save(); self.toast("Game saved"); self.app.sfx("click", 0.5)
        elif sid == "tv":
            self.toast("NEON CITY NEWS: police chase on the coast road...  %s relaxes" % NAMES[self.active])
            me.health = min(100.0, me.health + 10.0); self.app.sfx("click", 0.5)
        elif sid == "eat": self.house_snack()
        elif sid == "laptop": self.laptop.toggle(desk=True)
        elif sid == "leave": self.leave_home()

    # ---- v1.0.4: animated eating (house EAT SNACK + pause-menu FOOD) ----------------------------------------------
    def fridge_door(self):
        d = getattr(self, "_fridge", None)
        if d is not None and not d.is_empty(): return d
        from fs_miyo import box_mesh, shade
        X, Y = D.HOME_INT; parent = NodePath(self.world.home_int)
        inner = parent.attach_new_node(box_mesh("fridge_in", [(X + 5.295, Y + 1.36, 0.1, X + 5.31, Y + 2.24, 2.0, (0.98, 0.98, 1.0, 1)),
                                                               (X + 5.27, Y + 1.36, 0.75, X + 5.3, Y + 2.24, 0.78, (0.75, 0.85, 0.95, 1)),
                                                               (X + 5.27, Y + 1.36, 1.35, X + 5.3, Y + 2.24, 1.38, (0.75, 0.85, 0.95, 1)),
                                                               (X + 5.27, Y + 1.5, 0.78, X + 5.3, Y + 1.7, 0.9, (0.95, 0.85, 0.2, 1)),
                                                               (X + 5.27, Y + 1.9, 0.78, X + 5.3, Y + 2.1, 0.95, (0.2, 0.55, 0.9, 1)),
                                                               (X + 5.27, Y + 1.55, 1.38, X + 5.3, Y + 1.95, 1.5, (0.9, 0.3, 0.3, 1))]))
        inner.set_light_off(1)
        d = self._fridge = parent.attach_new_node("fridge_hinge"); d.set_pos(X + 5.30, Y + 2.28, 0)
        n = d.attach_new_node(box_mesh("fridge_door", [(-0.06, -0.96, 0.04, 0.0, 0.0, 2.06, (0.74, 0.76, 0.79, 1)),
                                                       (-0.10, -0.86, 0.9, -0.06, -0.82, 1.5, (0.3, 0.3, 0.32, 1))]))
        shade(n, self.app, 0.5)
        return d

    def house_snack(self):
        if self.eating is not None: return
        from fs_food import EatAnim, SNACKS, INFO
        X, Y = D.HOME_INT; me = self.me()
        me.x, me.y, me.h = X + 4.55, Y + 1.8, -90; me.speed = 0; me.sync(); me.walk_anim(0.016, 0.0)
        fid = random.choice(SNACKS); self.home["mode"] = "eat"; self.home_prompt_off()
        def done():
            me.health = 100.0; self.home["mode"] = "room"
            self.toast("%s ate %s  -  health full" % (NAMES[self.active], INFO[fid][2].lower()))
        self.eating = EatAnim(self, me, fid, fridge=self.fridge_door(), on_done=done); self.app.sfx("click", 0.5)

    def food_block(self):
        if self.pcar is not None or self.ride: return "Pull over to eat"
        if self.eating is not None: return "Still eating..."
        if self.home and self.home.get("mode") != "room": return "Not right now"
        if self.camapp: return "Close the camera first"
        if self.me().in_car is not None or getattr(self.me(), "swim", False): return "Not right now"
        return None

    def eat_food(self, fid):
        """pause-menu FOOD: pay, then the animated eat / drink; health up, water / tea sober you up after the bar"""
        from fs_food import EatAnim, INFO
        f = INFO[fid]; b = self.food_block()
        if b: self.toast(b); return False
        if self.cash < f[3]: self.toast("Not enough cash (¥%d)" % f[3]); return False
        self.cash -= f[3]; me = self.me(); me.speed = 0; self.ledger.append(("FOOD: %s" % f[2], -f[3]))
        if hasattr(self, "arsenal"): self.arsenal.unequip()
        def done():
            me.health = min(100.0, me.health + f[4])
            if f[6]: self.drunk = max(0.0, getattr(self, "drunk", 0.0) + f[6])
            self.toast("%s finished the %s  +%d health" % (NAMES[self.active], f[2].lower(), f[4])); self.save()
        self.eating = EatAnim(self, me, fid, on_done=done); self.app.sfx("cash", 0.5)
        return True

    def home_prompt(self):
        """contextual [E] button for the closest thing in the house (clickable too)"""
        sp = self.home_spot() if self.home_roam() else None
        sid = sp[0] if sp else None
        if self.home is None or sid == self.home.get("spot"): return
        self.home["spot"] = sid
        if getattr(self, "home_btn", None): self.home_btn.destroy(); self.home_btn = None
        if sp is None: return
        o = self.home_btn = DirectFrame(parent=self.app.a2dBottomCenter, frameColor=(0, 0, 0, 0), pos=(0, 0, 0.22))
        U.button(o, "[E]  " + sp[1], (0, 0), self.home_use, w=0.3, h=0.06, scale=0.045, edge=(1.0, 0.55, 0.85, 1), extra=[sp[0]])

    def home_prompt_off(self):
        for k in ("home_btn", "home_info"):
            n = getattr(self, k, None)
            if n: n.destroy(); setattr(self, k, None)
        if self.home: self.home["spot"] = None

    def home_panel(self):
        if self.overlay: self.overlay.destroy()
        self.overlay = None                        # v1.0.3: no button menu any more - walk around, every spot has its own [E] button
        if getattr(self, "home_btn", None): self.home_btn.destroy(); self.home_btn = None
        if self.home: self.home["spot"] = None
        if getattr(self, "home_info", None): self.home_info.destroy()
        pk = (1.0, 0.55, 0.85, 1)
        o = self.home_info = DirectFrame(parent=self.app.a2dTopLeft, frameColor=(0, 0, 0, 0), pos=(0.05, 0, -0.08))
        h = int(self.tod); mi = int((self.tod - h) * 60)
        U.text(o, "HOME  %02d:%02d" % (h, mi), (0.0, 0), 0.055, fg=pk, align=TextNode.A_left, shadow=(0, 0, 0, 0.8))
        U.text(o, "WASD walk  -  Shift run  -  walk up to things and press E  -  Q switch  -  Esc leave", (0.0, -0.07), 0.04,
               font=U.FONT_PLAIN, fg=(1, 1, 1, 0.95), align=TextNode.A_left, shadow=(0, 0, 0, 0.9))

    def home_sleep(self):
        self.tod = 8.0 if (self.tod >= 17.0 or self.tod < 6.0) else 20.0
        self._tod_t = 0; self.me().health = 100.0; self.fade(1.2); self.save()
        self.toast("Slept until %02d:00  -  game saved" % int(self.tod)); self.home_panel()

    def start_shower(self):
        """open-ended shower: swimsuit on, water + steam loop, slow wide camera, health refills; EXIT SHOWER / E / Esc to leave"""
        if not self.home or self.home.get("mode") != "room": return
        from panda3d.core import CardMaker
        me = self.me(); sx, sy = self.world.shower_pos
        self.home["mode"] = "shower"; self.home["prev"] = me.outfit; self.home["t"] = 0.0
        me.set_outfit({"ana": "bikini", "daniel": "swim"}.get(me.who, me.outfit)); me.x, me.y, me.h = sx, sy, 90; me.sync(); me.walk_anim(0.016, 0.0)
        bd = self.buddy(); X, Y = D.HOME_INT
        if bd:
            bd.x, bd.y, bd.h = X + 1.2, Y + 2.3, 180; bd.sync()
        fx = self.home["fx"] = self.world.home_int.attach_new_node("shower_fx"); drops = []
        cm = CardMaker("drop"); cm.set_frame(-0.006, 0.006, -0.16, 0.16)
        for k in range(70):
            d = fx.attach_new_node(cm.generate()); d.set_billboard_axis(); d.set_color(0.75, 0.88, 1.0, 0.55)
            d.set_pos(sx + random.uniform(-0.3, 0.3), sy + random.uniform(-0.3, 0.3), random.uniform(0.1, 2.3)); drops.append(d)
        cm2 = CardMaker("steam"); cm2.set_frame(-0.9, 0.9, -0.9, 0.9); steam = []
        for k in range(8):
            s_ = fx.attach_new_node(cm2.generate()); s_.set_billboard_point_eye(); s_.set_texture(self.world.T("glow.png", repeat=False))
            s_.set_pos(sx + random.uniform(-0.4, 0.4), sy + random.uniform(-0.5, 0.5), random.uniform(0.6, 2.4)); steam.append([s_, random.uniform(0, 6.28)])
        fx.set_transparency(TransparencyAttrib.M_alpha); fx.set_depth_write(False); fx.set_light_off(); fx.set_bin("transparent", 30)
        self.home["drops"] = drops; self.home["steam"] = steam; self.home_prompt_off()
        if self.overlay: self.overlay.destroy()
        o = self.overlay = DirectFrame(parent=self.app.a2dBottomCenter, frameColor=(0, 0, 0, 0), pos=(0, 0, 0.16))
        U.button(o, "EXIT SHOWER", (0, 0), self.end_shower, w=0.26, h=0.055, scale=0.042, edge=U.CYAN, hint="E")
        self.fade(0.6); self.app.sfx("door", 0.4)

    def end_shower(self):
        self.arsenal.unequip()
        if not self.home or self.home.get("mode") != "shower": return
        me = self.me(); me.set_outfit(self.home.get("prev", "default")); me.health = 100.0; me.stop_scrub()
        if self.home.get("fx"): self.home["fx"].remove_node()
        for k in ("fx", "drops", "steam"): self.home.pop(k, None)
        X, Y = D.HOME_INT; me.x, me.y, me.h = X - 6.1, Y + 3.5, 0; me.sync(); self.cam_yaw = 180.0; self.cam_pos = None
        bd = self.buddy()
        if bd:
            bd.x, bd.y, bd.h = X - 4.6, Y + 3.9, 120; bd.sync()
        self.home["mode"] = "room"; self.fade(0.8); self.save(); self.toast("Fresh!  Health restored  -  game saved"); self.home_panel()

    def update_home(self, dt):
        X, Y = D.HOME_INT
        if self.home.get("mode") == "shower":
            h = self.home; h["t"] += dt; me = self.me(); me.health = min(100.0, me.health + dt * 15)
            me.scrub(dt)                       # v1.0.3: ANA / DANIEL actively scrub (hair, shoulders, arms), hands alternating
            sx, sy = self.world.shower_pos
            for d in h["drops"]:
                z = d.get_z() - dt * 5.5
                if z < 0.08: z = 2.3; d.set_x(sx + random.uniform(-0.3, 0.3)); d.set_y(sy + random.uniform(-0.3, 0.3))
                d.set_z(z)
            for s_ in h["steam"]:
                n, ph = s_; z = n.get_z() + dt * 0.25
                if z > 2.8: z = 0.6
                n.set_z(z); n.set_alpha_scale(0.10 + 0.06 * math.sin(h["t"] * 0.8 + ph)); n.set_color(1, 1, 1, 1)
            a = math.radians(35 * math.sin(h["t"] * 0.12)); cam = self.app.camera
            cam.set_pos(sx + math.cos(a) * 4.2, sy + math.sin(a) * 2.4 - 0.6, 2.0); cam.look_at(sx, sy, 1.15); self.app.camLens.set_fov(60)
            return
        X, Y = D.HOME_INT; self._home_dt = dt
        if self.home.get("mode") == "wardrobe":
            a = self.me(); a.h = (a.h + dt * 40) % 360; a.sync()
        elif self.home.get("mode") == "room":
            self.move_on_foot(self.me(), dt)
            bd = self.buddy()
            if bd: self.follow(bd, self.me(), dt)
            self.home_prompt()
        self.home_cam()

    def open_wardrobe(self):
        if not self.home: return
        from fs_people import OUTFITS
        X, Y = D.HOME_INT
        a = self.me(); a.x, a.y, a.h = X - 3.1, Y - 3.3, 0; a.sync()
        self.home["mode"] = "wardrobe"; self.home["orig"] = self.outfit; self.home["pick"] = self.outfit; self.home_prompt_off()
        if self.overlay: self.overlay.destroy()
        o = self.overlay = DirectFrame(parent=self.app.a2dLeftCenter, frameColor=(0, 0, 0, 0), pos=(0.45, 0, 0))
        pk = (0.3, 0.9, 1.0, 1)
        U.panel(o, -0.4, 0.4, -0.7, 0.7, edge=pk)
        U.text(o, "WARDROBE", (0, 0.58), 0.07, fg=pk)
        U.text(o, "ELIJER", (0, 0.51), 0.032, font=U.FONT_PLAIN)
        self._wd_lbl = U.text(o, "", (0, -0.36), 0.026, font=U.FONT_PLAIN, wrap=22)
        for k, (oid, nm, desc) in enumerate(self.outfit_list(self.active)):
            U.button(o, nm, (0, 0.38 - k * 0.13), self.wardrobe_pick, w=0.3, h=0.05, scale=0.038, extra=[oid], edge=pk if oid == self.outfit else (0.5, 0.5, 0.6, 1))
        U.button(o, "EQUIP", (0, -0.5), lambda: self.close_wardrobe(True), w=0.3, h=0.055, scale=0.042, edge=U.CYAN, hint="Enter")
        U.button(o, "BACK", (0, -0.61), lambda: self.close_wardrobe(False), w=0.3, h=0.045, scale=0.034, hint="Esc")
        self.wardrobe_pick(self.outfit)

    def wardrobe_pick(self, oid):
        from fs_people import OUTFITS
        self.home["pick"] = oid; a = self.me(); a.set_outfit(oid); a.sync(); a.walk_anim(0.016, 0.0)
        d = dict((i, (n, t)) for i, n, t in self.outfit_list(self.active))[oid]
        try: self._wd_lbl.setText("%s\n%s" % d)
        except Exception: pass
        self.app.sfx("click", 0.5)

    def close_wardrobe(self, equip):
        if not self.home: return
        a = self.me()
        if equip:
            self.apply_outfit(self.active, self.home["pick"])
        else:
            a.set_outfit(self.home.get("orig", self.outfit))
        X, Y = D.HOME_INT; a.x, a.y, a.h = X - 3.1, Y - 3.5, 0; a.sync(); self.cam_yaw = 180.0; self.cam_pos = None
        self.home["mode"] = "room"; self.home_panel()

    # ---- v1.0.4: shared outfit logic (house WARDROBE + pause-menu CLOTHING)
    def outfit_list(self, who=None):
        from fs_people import outfits_for
        return outfits_for(self.app.BASE, who or self.active)

    def outfit_block(self):
        """why clothes can't be changed right now (None = OK)"""
        if self.pcar is not None or self.ride: return "Exit the vehicle first"
        if self.home and self.home.get("mode") == "shower": return "Finish your shower first"
        if self.home and self.home.get("mode") == "wardrobe": return "Close the wardrobe first"
        if self.camapp: return "Close the camera first"
        return None

    def apply_outfit(self, who, oid):
        """put an outfit on and save it - same result from the wardrobe or the pause menu"""
        ok = [o[0] for o in self.outfit_list(who)]
        if oid not in ok: return False
        self.outfits[who] = oid
        if who == self.active: self.outfit = oid
        p = self.chars[who]
        if p.outfit != oid: p.set_outfit(oid)
        if not getattr(p, "benched", False): p.sync(); p.walk_anim(0.016, 0.0)
        nm = dict((i, n) for i, n, _ in self.outfit_list(who))[oid]
        self.save(); self.toast("%s is now wearing: %s" % (NAMES[who], nm))
        return True

    def leave_home(self):
        self.arsenal.unequip()
        if not self.home: return
        if self.home.get("mode") == "wardrobe": self.close_wardrobe(False)
        self.home_prompt_off(); self.world.home_int.hide(); self.home = None
        if self.overlay: self.overlay.destroy(); self.overlay = None
        hx, hy = D.HOME_POS
        self.me().x, self.me().y, self.me().h = hx + 1.5, hy - 2.5, -90; self.me().sync()
        bd = self.buddy()
        if bd:
            bd.x, bd.y = hx + 1.5, hy - 4.0; bd.sync()
        self.cam_pos = None; self.cam_yaw = -180
        self.app.camLens.set_fov(70); self.fade(0.6); self.refresh_buttons(); self.app.sfx("door", 0.5)

    def open_garage(self):
        if self.phone: self.toggle_phone()
        self.cap_k = 0.0; self.cap1.setText(""); self.cap2.setText(""); self.big.setText("")
        gx, gy = D.GARAGE_POS
        c = self.ensure_in_car(gx, gy - 2, 90)
        c.vx = c.vy = 0
        self.me().unseat(gx - 3.6, gy - 0.5, 200)
        bd = self.buddy()
        if bd: bd.unseat(gx - 4.6, gy - 2.6, 230)
        self.pcar_saved = c; self.pcar = None
        cfg = self.cars_cfg.setdefault(c.kind, {})
        self.garage = {"car": c, "a": 0.0, "paint": tuple(cfg.get("paint", c.paint_col)), "plate": cfg.get("plate", c.plate_text)}
        o = self.overlay = DirectFrame(parent=self.app.a2dLeftCenter, frameColor=(0, 0, 0, 0), pos=(0.5, 0, 0))
        U.panel(o, -0.44, 0.44, -0.8, 0.8, edge=U.CYAN)
        U.text(o, "FRGARAGE", (0, 0.68), 0.085, fg=U.CYAN)
        U.text(o, "%s  -  %s" % (c.spec["name"], NAMES.get(self.active, "ELIJER")), (0, 0.6), 0.032, font=U.FONT_PLAIN)
        U.text(o, "PAINT", (-0.38, 0.5), 0.04, fg=U.PINK, align=TextNode.A_left)
        ev_p = [(p_[0], tuple(p_[1])) for p_ in (self.events.paints if getattr(self, "events", None) is not None else [])]
        for k, (nm, col) in enumerate(PAINTS + ev_p):
            x = -0.3 + (k % 5) * 0.15; y = 0.4 - (k // 5) * 0.16
            DirectButton(parent=o, frameColor=col + (1,), frameSize=(-0.055, 0.055, -0.055, 0.055), pos=(x, 0, y), relief=DGG.FLAT,
                         command=self.garage_paint, extraArgs=[col], pressEffect=1)
            U.text(o, nm, (x, y - 0.085), 0.022, font=U.FONT_PLAIN)
        U.text(o, "PLATE (max 8)", (-0.38, 0.1), 0.04, fg=U.PINK, align=TextNode.A_left)
        self.plate_entry = DirectEntry(parent=o, initialText=self.garage["plate"], width=8, numLines=1, scale=0.07, pos=(-0.3, 0, -0.0),
                                       frameColor=(0.1, 0.08, 0.15, 1), text_fg=(1, 1, 1, 1), entryFont=U.FONT_PLAIN,
                                       command=self.garage_plate, focus=0)
        self.plate_entry["width"] = 8
        U.button(o, "APPLY PLATE", (0, -0.18), lambda: self.garage_plate(self.plate_entry.get()), w=0.3, h=0.05, scale=0.036)
        U.button(o, "SAVE & EXIT", (0, -0.66), self.close_garage, w=0.3, h=0.06, scale=0.042, edge=U.CYAN, hint="Esc")
        U.text(o, "CAR", (-0.38, -0.27), 0.04, fg=U.PINK, align=TextNode.A_left)
        U.button(o, "< PREV", (-0.27, -0.35), lambda: self.garage_swap(-1), w=0.1, h=0.04, scale=0.03)
        U.button(o, "NEXT >", (0.27, -0.35), lambda: self.garage_swap(1), w=0.1, h=0.04, scale=0.03)
        self._g_name = U.text(o, "", (0, -0.36), 0.032, fg=U.CYAN)
        self._g_stats = U.text(o, "", (0, -0.415), 0.022, font=U.FONT_PLAIN)
        self._g_sel = U.button(o, "SELECT THIS CAR", (0, -0.54), self.garage_select, w=0.22, h=0.04, scale=0.03, edge=U.GOLD)
        self.garage_info()
        self.letterbox(False); self.refresh_buttons(); self.app.sfx("door", 0.5)

    def garage_info(self):
        g = self.garage; c = g["car"]; s = c.spec
        bar = lambda v: "|" * max(1, int(round(v * 10))) + "." * max(0, 10 - int(round(v * 10)))
        self._g_name.setText(s["name"])
        self._g_stats.setText("Type: %s   (%d/%d)\nSPEED %s   ACCEL %s   HANDLING %s%s" % (CAR_TYPES.get(c.kind, ""), PLAYER_CARS.index(c.kind) + 1 if c.kind in PLAYER_CARS else 0, len(PLAYER_CARS), bar(s["vmax"] / 74.0), bar(s["acc"] / 13.5), bar(s["grip"] / 9.5),
                                                                       "\n(your car)" if c.kind == self.player_kind else ""))

    def garage_swap(self, d):
        g = self.garage
        if not g: return
        old = g["car"]; cfg = self.cars_cfg.get(old.kind, {}); cfg.update({"paint": list(g["paint"]), "plate": g["plate"]}); self.cars_cfg[old.kind] = cfg
        kinds = PLAYER_CARS; k = kinds[(kinds.index(old.kind) + d) % len(kinds)] if old.kind in kinds else kinds[0]
        x, y, h = old.x, old.y, old.h
        was_own = old is self.own; self.remove_car(old)
        c = self.spawn_car(k, x, y, h, role="player"); c.owned = True; c.vx = c.vy = 0
        if was_own: self.own = c
        self.pcar_saved = c
        cf = self.cars_cfg.get(k, {}); g["car"] = c; g["paint"] = tuple(cf.get("paint", c.paint_col)); g["plate"] = cf.get("plate", c.plate_text)
        try: self.plate_entry.enterText(g["plate"])
        except Exception: pass
        self.garage_info(); self.app.sfx("click", 0.6)

    def garage_select(self):
        g = self.garage
        if not g: return
        self.player_kind = g["car"].kind; self.own = g["car"]; self.save(); self.garage_info()
        self.toast("%s is now your car" % g["car"].spec["name"]); self.app.sfx("checkpoint", 0.5)

    def garage_paint(self, col):
        g = self.garage
        if not g: return
        g["paint"] = tuple(col); g["car"].set_paint(col); self.app.sfx("click", 0.6)

    def garage_plate(self, txt):
        g = self.garage
        if not g: return
        t = "".join(ch for ch in txt.upper() if ch.isalnum() or ch in " -")[:8].strip() or g["plate"]
        g["plate"] = t; g["car"].make_plates(t); self.plate_entry.enterText(t); self.toast("Plate: %s" % t)

    def close_garage(self):
        g = self.garage
        if not g: return
        try: self.garage_plate(self.plate_entry.get())
        except Exception: pass
        c = g["car"]; self.cars_cfg[c.kind] = {"paint": list(g["paint"]), "plate": g["plate"]}
        self.garage = None; self.close_overlay(); self.pcar_saved = None
        self.enter_car(c); self.save(); self.toast("FRGARAGE: saved for %s" % c.spec["name"])

    def close_overlay(self):
        if self.overlay:
            if hasattr(self, "online") and self.overlay is self.online.ui:
                self.online.ui = None; self.online._drop_preview()
            self.overlay.destroy(); self.overlay = None
        if getattr(self, "map_np", None): self.map_np = None
        self.refresh_buttons()

    # ================================================================ full map
    def toggle_map(self):
        if self.overlay and getattr(self, "map_np", None): self.close_overlay(); return
        if self.blocked(): return
        o = self.overlay = DirectFrame(parent=self.app.aspect2d, frameColor=(0, 0, 0, 0.75), frameSize=(-3, 3, -1, 1),
                                       state=DGG.NORMAL)
        o.bind(DGG.B1PRESS, self.map_click)
        S = 0.9; self.map_np = S
        OnscreenImage(parent=o, image=self.map_tex, pos=(0, 0, 0), scale=(S, 1, S))
        xmin, ymin, span = -470.0, -590.0, 1180.0
        def mp(x, y): return ((x - xmin) / span * 2 - 1) * S, ((y - ymin) / span * 2 - 1) * S
        for did, nm, jp, col in D.DISTRICTS:
            c = {"crossing": (0, 0), "akari": (-280, 280), "kurogane": (-280, -280), "tower": (280, 280), "sakura": (280, -280),
                 "beach": (540, 0)}[did]
            x, y = mp(*c)
            U.text(o, nm, (x, y), 0.032, fg=col + (1,))
            U.text(o, jp, (x, y - 0.045), 0.032, fg=col + (0.9,), font=self.app.jpfont)
        for m in self.markers + self.pois:
            x, y = mp(m["x"], m["y"])
            DirectFrame(parent=o, frameColor=(0, 0, 0, 0.75), frameSize=(-0.024, 0.024, -0.024, 0.024), pos=(x, 0, y))
            U.text(o, self.ICON[m["kind"]], (x, y - 0.013), 0.038, fg=m["col"] + (1,))
            U.text(o, m["name"], (x, y - 0.05), 0.022, fg=m["col"] + (0.95,), font=U.FONT_PLAIN)
        lg = DirectFrame(parent=o, frameColor=(0.04, 0.03, 0.08, 0.9), frameSize=(-0.02, 0.52, -0.06 - 0.052 * len(self.LEGEND), 0.06), pos=(0.98, 0, 0.62))
        U.text(lg, "LEGEND", (0.25, 0.0), 0.04, fg=U.CYAN)
        for i, (ic, txt) in enumerate(self.LEGEND):
            U.text(lg, ic, (0.03, -0.06 - i * 0.052), 0.036, fg=U.GOLD)
            U.text(lg, txt, (0.08, -0.06 - i * 0.052), 0.026, fg=(1, 1, 1, 0.9), font=U.FONT_PLAIN, align=TextNode.A_left)
        for t in D.TOKENS:
            if tuple(t) not in self.tokens:
                x, y = mp(*t); U.text(o, "*", (x, y - 0.02), 0.04, fg=U.GOLD)
        if self.waypoint:
            x, y = mp(*self.waypoint); U.text(o, "X", (x, y - 0.015), 0.05, fg=(0.3, 1, 0.4, 1))
        px, py = self.player_pos(); x, y = mp(px, py); U.text(o, "●", (x, y - 0.015), 0.05, fg=(1, 1, 1, 1), font=self.app.jpfont)
        U.text(o, "MAP  -  click to set a waypoint   [M / Esc to close]", (0, -0.96), 0.035, font=U.FONT_PLAIN)
        U.button(o, "CLOSE", (1.15, 0.85), self.close_overlay, w=0.14, h=0.045, scale=0.034, hint="M")
        self.refresh_buttons()

    def map_click(self, ev):
        mw = self.app.mouseWatcherNode
        if mw is None or not mw.has_mouse(): return
        p = self.app.aspect2d.get_relative_point(self.app.render2d, Point3(mw.get_mouse()[0], 0, mw.get_mouse()[1]))
        S = 0.9; xmin, ymin, span = -470.0, -590.0, 1180.0
        if abs(p.x) > S or abs(p.z) > S: return
        x = xmin + (p.x / S + 1) / 2 * span; y = ymin + (p.z / S + 1) / 2 * span
        self.waypoint = (x, y); self.toast("Waypoint set"); self.app.sfx("click", 0.6)
        self.close_overlay(); self.toggle_map()

    # ================================================================ HUD
    def build_hud(self):
        a = self.app
        self.hud = a.aspect2d.attach_new_node("hud")
        img, (xmin, ymin, s) = self.world.map_image(1024)
        t = Texture("map"); t.load(img); t.set_wrap_u(SamplerState.WM_border_color); t.set_wrap_v(SamplerState.WM_border_color)
        t.set_border_color((0.02, 0.02, 0.05, 1)); t.set_minfilter(SamplerState.FT_linear); self.map_tex = t
        # minimap (top right)
        self.mm_root = a.a2dTopRight.attach_new_node("mm"); self.mm_root.set_pos(-0.33, 0, -0.36); M = 0.27; self.mm_M = M
        U.panel(DirectFrame(parent=self.mm_root, frameColor=(0, 0, 0, 0)), -M, M, -M, M, col=(0, 0, 0, 0), edge=U.CYAN, ew=0.008)
        cm = CardMaker("mm"); cm.set_frame(-M, M, -M, M); cm.set_uv_range((0, 0), (1, 1))
        self.mm = self.mm_root.attach_new_node(cm.generate()); self.mm.set_texture(t)
        self.mm_dots = []
        for _ in range(48):
            d = DirectFrame(parent=self.mm_root, frameColor=(1, 1, 1, 1), frameSize=(-0.01, 0.01, -0.01, 0.01)); d.hide(); self.mm_dots.append(d)
        self.mm_icons = [U.text(self.mm_root, self.ICON[m["kind"]], (0, 0), 0.034, fg=m["col"] + (1,)) for m in self.markers + self.pois]
        for ic in self.mm_icons: ic.setShadow((0, 0, 0, 1))
        U.text(self.mm_root, "▲", (0, -0.016), 0.045, fg=(1, 1, 1, 1), font=a.jpfont)
        self.dist_lbl = U.text(self.mm_root, "", (0, -M - 0.05), 0.034, fg=U.CYAN)
        self.dist_lbl_jp = U.text(self.mm_root, "", (0, -M - 0.095), 0.03, fg=U.CYAN, font=a.jpfont)
        # circular speedometer (ring gauge around the speed number) + nitro + health
        br = a.a2dBottomRight
        # v1.0.5.5: sit in the BR corner below the driving-button stack (never overlaps RESET CAR DAMAGE)
        self.speedo_root = DirectFrame(parent=br, frameColor=(0, 0, 0, 0), pos=(-0.28, 0, 0.26))
        self.speedo_track = self.speedo_root.attach_new_node("speedo-track")
        self.speedo_fill = self.speedo_root.attach_new_node("speedo-fill")
        self.speedo_vmax = 280.0          # ring tops out around typical top speed (km/h)
        self.speedo_bucket = -1
        self._build_speedo_track()
        self.speed_t = U.text(self.speedo_root, "0", (0, 0.018), 0.095, fg=(1, 1, 1, 1))
        self.kmh_t = U.text(self.speedo_root, "km/h", (0, -0.055), 0.028, fg=U.CYAN, font=U.FONT_PLAIN)
        self.nitro_bar = U.bar(self.speedo_root, (-0.16, -0.145), 0.32, 0.009, 1.0, col=U.CYAN)
        self.hp_bar = U.bar(a.a2dTopLeft, (0.06, -0.47), 0.4, 0.01, 1.0, col=(0.3, 1, 0.45, 1))
        # top-left status
        tl = a.a2dTopLeft
        self.cash_t = U.text(tl, "", (0.06, -0.54), 0.05, fg=U.GOLD, align=TextNode.A_left)
        self.cash_pop = U.text(tl, "", (0.06, -0.54), 0.045, fg=(0.3, 1.0, 0.45, 1), align=TextNode.A_left); self.cash_pop_k = 0.0
        self.stars_t = U.text(tl, "", (0.06, -0.61), 0.06, fg=(1, 0.85, 0.2, 1), align=TextNode.A_left, font=a.jpfont)
        self.race_t = U.text(a.a2dTopCenter, "", (0, -0.1), 0.05, fg=(1, 1, 1, 1))
        self.big = U.text(a.aspect2d, "", (0, 0.15), 0.22, fg=U.PINK)
        self.prompt = U.text(a.aspect2d, "", (0, -0.55), 0.045, fg=(1, 1, 1, 1))
        self.sub = U.text(a.a2dBottomCenter, "", (0, 0.36), 0.044, fg=(1, 1, 1, 1), font=U.FONT_PLAIN, wrap=34, shadow=(0, 0, 0, 1))
        self.sub_en = U.text(a.a2dBottomCenter, "", (0, 0.305), 0.032, fg=(0.8, 0.9, 1.0, 1), font=U.FONT_PLAIN, wrap=46, shadow=(0, 0, 0, 1))
        self.toast_t = U.text(a.aspect2d, "", (0, 0.62), 0.045, fg=U.CYAN); self.toast_k = 0.0
        self.cap1 = U.text(a.aspect2d, "", (0, 0.05), 0.11, fg=(1, 1, 1, 1)); self.cap2 = U.text(a.aspect2d, "", (0, -0.05), 0.045, fg=U.CYAN, font=a.jpfont)
        self.cap_k = 0.0
        self.pop1 = U.text(a.a2dTopCenter, "", (0, -0.26), 0.07, fg=(1, 1, 1, 1)); self.pop2 = U.text(a.a2dTopCenter, "", (0, -0.33), 0.05, fg=(1, 1, 1, 1), font=a.jpfont)
        self.pop_k = 0.0
        cmb = CardMaker("lb"); cmb.set_frame(-3, 3, 0, 0.16)
        self.lb_top = a.aspect2d.attach_new_node(cmb.generate()); self.lb_top.set_color(0, 0, 0, 1); self.lb_top.set_z(1.0)
        self.lb_bot = a.aspect2d.attach_new_node(cmb.generate()); self.lb_bot.set_color(0, 0, 0, 1); self.lb_bot.set_r(180); self.lb_bot.set_z(-1.0)
        cmf = CardMaker("fade"); cmf.set_frame(-3, 3, -1, 1)
        self.fade_np = a.aspect2d.attach_new_node(cmf.generate()); self.fade_np.set_color(0, 0, 0, 0); self.fade_np.set_transparency(TransparencyAttrib.M_alpha)
        self.fade_np.set_bin("fixed", 100); self.fade_k = 0.0
        self.btn_root = None; self.btn_state = None
        self.refresh_buttons()


    def _speedo_arc(self, parent, r0, r1, a0, a1, segs, col, alpha=0.92):
        """Flat arc ring segment in aspect2d space. No glow — solid colour only."""
        import math
        from panda3d.core import (GeomVertexFormat, GeomVertexData, GeomVertexWriter,
                                  GeomTriangles, Geom, GeomNode, TransparencyAttrib)
        vd = GeomVertexData("sa", GeomVertexFormat.get_v3c4(), Geom.UH_static)
        vw = GeomVertexWriter(vd, "vertex"); cw = GeomVertexWriter(vd, "color")
        tri = GeomTriangles(Geom.UH_static)
        for k in range(segs + 1):
            a = a0 + (a1 - a0) * (k / segs)
            c, s = math.cos(a), math.sin(a)
            for rr in (r0, r1):
                vw.add_data3(c * rr, 0, s * rr)
                cw.add_data4(col[0], col[1], col[2], alpha)
            if k < segs:
                i = k * 2
                tri.add_vertices(i, i + 1, i + 3); tri.add_vertices(i, i + 3, i + 2)
        gm = Geom(vd); gm.add_primitive(tri); gn = GeomNode("arc"); n = parent.attach_new_node(gn); gn.add_geom(gm)
        n.set_transparency(TransparencyAttrib.M_alpha); n.set_bin("fixed", 50); n.set_depth_test(False); n.set_depth_write(False)
        return n

    def _build_speedo_track(self):
        """Static dark track + soft ticks. Sweep is an open ring (bottom gap), modern racing HUD."""
        import math
        for ch in self.speedo_track.get_children(): ch.remove_node()
        # open ring: about 270 deg, gap at the bottom
        a0, a1 = math.radians(-210), math.radians(30)
        self._speedo_a0, self._speedo_a1 = a0, a1
        self._speedo_arc(self.speedo_track, 0.175, 0.205, a0, a1, 48, (0.08, 0.08, 0.12), 0.85)
        self._speedo_arc(self.speedo_track, 0.168, 0.175, a0, a1, 48, (0.25, 0.9, 1.0), 0.35)   # thin inner accent, no bloom
        # tick marks every 40 km/h
        ticks = self.speedo_track.attach_new_node("ticks")
        for i in range(8):
            frac = i / 7.0
            a = a0 + (a1 - a0) * frac
            self._speedo_arc(ticks, 0.205, 0.218, a - 0.012, a + 0.012, 2, (0.7, 0.75, 0.85), 0.7)

    def _set_speedo_fill(self, frac):
        import math
        for ch in self.speedo_fill.get_children(): ch.remove_node()
        frac = max(0.0, min(1.0, frac))
        if frac <= 0.001: return
        a0, a1 = self._speedo_a0, self._speedo_a1
        a = a0 + (a1 - a0) * frac
        # colour shifts cool cyan -> warm pink as speed climbs (still flat, no glow)
        t = frac
        col = (0.25 + 0.75 * t, 0.90 - 0.55 * t, 1.0 - 0.40 * t)
        segs = max(3, int(48 * frac))
        self._speedo_arc(self.speedo_fill, 0.175, 0.205, a0, a, segs, col, 0.95)
        # leading tip
        self._speedo_arc(self.speedo_fill, 0.168, 0.218, a - 0.02, a + 0.02, 3, (1.0, 1.0, 1.0), 0.95)

    def portrait(self, who):
        return Filename.from_os_specific(os.path.join(self.app.BASE, "assets", "tex", "portrait_%s.png" % who)).get_fullpath()

    def update_portraits(self):
        self.btn_state = None; self.refresh_buttons()

    def hold(self, key):
        return (lambda: self.vb.__setitem__(key, True)), (lambda: self.vb.__setitem__(key, False))

    def refresh_buttons(self):
        if self.phone is not None and getattr(self.phone, "driving", None) is not None and self.phone.driving != (self.pcar is not None):
            self.phone_screen(self.phone.which); return
        hack = bool(getattr(self, "hackeria", None) and (self.hackeria.has_hack_target() or self.hackeria.cam_view))
        st = (self.pcar is not None, self.ride is not None and self.ride.get("mode"), self.phone is not None, self.overlay is not None,
              self.garage is not None or self.home is not None or self.camapp is not None, self.active, self.app.settings.get("buttons", True), bool(self.near_marker()) if hasattr(self, "markers") else False,
              self.miyo.state() if hasattr(self, "miyo") else None, self.miyo_spot() if hasattr(self, "miyo") else None, getattr(self, "match", None) is not None, hack)
        if st == self.btn_state: return
        self.btn_state = st
        for n in getattr(self, "btn_nodes", []): n.destroy()
        self.btn_nodes = []
        if self.btn_root: self.btn_root.destroy()
        self.vb.clear()
        a = self.app; root = self.btn_root = DirectFrame(parent=a.aspect2d, frameColor=(0, 0, 0, 0))
        if not a.settings.get("buttons", True) or self.garage or self.home or self.camapp or getattr(self, "match", None) is not None: return
        tl = DirectFrame(parent=a.a2dTopLeft, frameColor=(0, 0, 0, 0)); self.btn_nodes.append(tl)
        self.btn_tl = tl; root.tl = tl
        sm = dict(w=0.105, h=0.04, scale=0.03)
        U.button(tl, "MENU", (0.13, -0.07), self.key_esc, hint="Esc", **sm)
        U.button(tl, "MAP", (0.36, -0.07), self.toggle_map, hint="M", **sm)
        U.button(tl, "PHONE", (0.59, -0.07), self.toggle_phone, hint="T", edge=self.accent(), **sm)
        U.button(tl, "LAPTOP", (0.82, -0.07), lambda: self.laptop.toggle(), hint="L", edge=(0.35, 0.85, 1.0, 1), **sm)
        sw = U.button(tl, "", (0.25, -0.28), self.switch_char, w=0.21, h=0.15, scale=0.03, hint="Q", edge=self.accent())
        for k, who in enumerate(CREW):
            x = -0.1 + k * 0.2; on = who == self.active
            DirectFrame(parent=sw, frameColor=(0.3, 1.0, 1.0, 1) if on else (0.35, 0.35, 0.42, 1),
                        frameSize=(-0.092, 0.092, -0.092, 0.092), pos=(x, 0, 0.025), relief=DGG.FLAT)
            try:
                im = OnscreenImage(parent=sw, image=self.portrait(who), pos=(x, 0, 0.025), scale=0.085)
                if not on: im.set_color_scale(0.6, 0.6, 0.65, 1)
            except Exception: pass
            U.text(sw, NAMES[who], (x, -0.125), 0.032 if len(NAMES[who]) < 7 else 0.025, fg=(0.3, 1.0, 1.0, 1) if on else (0.8, 0.8, 0.85, 1))
            hot = DirectButton(parent=sw, frameColor=(0, 0, 0, 0), frameSize=(-0.092, 0.092, -0.14, 0.12), pos=(x, 0, 0.0), relief=DGG.FLAT,
                               command=lambda w=who: self.select_char(w), pressEffect=0)
        if self.ride:
            br = DirectFrame(parent=a.a2dBottomRight, frameColor=(0, 0, 0, 0)); self.btn_nodes.append(br)
            if self.ride.get("mode") == "riding":
                U.button(br, "SKIP TRIP", (-0.25, 0.4), self.skip_ride, w=0.18, h=0.05, scale=0.034, hint="Enter")
            U.button(br, "GET OUT", (-0.25, 0.27), self.leave_taxi, w=0.18, h=0.05, scale=0.034, hint="Esc")
            return
        if self.phone and not self.pcar:
            br = DirectFrame(parent=a.a2dBottomLeft, frameColor=(0, 0, 0, 0)); self.btn_nodes.append(br)
            return
        # right-hand action cluster (context sensitive)
        br = DirectFrame(parent=a.a2dBottomRight, frameColor=(0, 0, 0, 0)); self.btn_nodes.append(br)
        bw = dict(w=0.115, h=0.045, scale=0.028)
        # on foot: low cluster. driving: lift above the circular speedo (ring top ~0.48) so RESET CAR DAMAGE never overlaps it
        col1, col2 = -0.42, -0.16
        rows = [0.58, 0.70, 0.82, 0.94, 1.06] if self.pcar else [0.08, 0.2, 0.32, 0.44, 0.56]
        if self.pcar:
            p, r = self.hold("v_nitro"); U.button(br, "NITRO", (col2, rows[0]), None, hint="Shift", press=p, release=r, edge=U.CYAN, **bw)
            p, r = self.hold("v_hand"); U.button(br, "HANDBRAKE", (col1, rows[0]), None, hint="Space", press=p, release=r, **bw)
            U.button(br, "EXIT CAR", (col2, rows[1]), self.key_f, hint="F", **bw)
            U.button(br, "CAMERA", (col1, rows[1]), self.key_c, hint="C", **bw)
            U.button(br, "RESET", (col2, rows[2]), self.key_r, hint="R", **bw)
            U.button(br, "HORN", (col1, rows[2]), self.key_h, hint="H", **bw)
            U.button(br, "RESET CAR DAMAGE", (col2 - 0.13, rows[4]), self.repair_car, hint="J", edge=(0.4, 1.0, 0.5, 1), **dict(bw, w=0.25))
        else:
            U.button(br, "ENTER CAR", (col2, rows[0]), self.key_f, hint="F", **bw)
            p, r = self.hold("v_nitro"); U.button(br, "RUN", (col1, rows[0]), None, hint="Shift", press=p, release=r, **bw)
            U.button(br, "CAMERA", (col1, rows[1]), self.key_c, hint="C", **bw)
            fp = lambda: (self.vb.__setitem__("v_fire", True), self.arsenal.fire(from_button=True)); fr = lambda: self.vb.__setitem__("v_fire", False)
            U.button(br, "FIRE", (col2, rows[2]), None, hint="LMB", press=fp, release=fr, edge=(1, 0.4, 0.3, 1), **bw)
            p, r = self.hold("v_aim"); U.button(br, "AIM", (col1, rows[2]), None, hint="RMB", press=p, release=r, **bw)
            U.button(br, "WEAPONS", (col1, rows[3]), lambda: self.arsenal.toggle_wheel(), hint="Tab", edge=U.GOLD, **bw)
        # v1.0.4.1: ANA's abilities (were MIYOYAZU's) (contextual-button style, with key hints) + STOP TSUNAMI for anyone
        if self.active == "ana" and not self.pcar:
            U.button(br, "BUILD", (col2, rows[3]), self.key_b, hint="B", edge=(1.0, 0.55, 0.1, 1), **bw)
            if self.tsunami is None:
                U.button(br, "TSUNAMI", (col2, rows[4]), self.key_n, hint="N", edge=(0.3, 0.75, 1.0, 1), **bw)
        if self.tsunami is not None and not self.tsunami.drain:
            U.button(br, "STOP TSUNAMI", (col1 - 0.02, rows[4] if not self.pcar else rows[3]), self.miyo.stop_tsunami, hint="N", edge=(1, 0.3, 0.3, 1), **dict(bw, w=0.15))
        sp = self.miyo_spot()
        if sp:
            ctx = DirectFrame(parent=a.a2dBottomCenter, frameColor=(0, 0, 0, 0), pos=(0, 0, 0.30)); self.btn_nodes.append(ctx)
            U.button(ctx, sp[0], (0, 0), sp[1], hint=sp[2], w=0.3, h=0.05, scale=0.036, edge=sp[3])
        m = self.near_marker()
        if getattr(self, "hackeria", None) and self.hackeria.has_hack_target():
            p, r = self.hold("v_hack")
            U.button(br, "HACK", (col2, rows[3] if self.pcar else rows[1]), None, hint="E", press=p, release=r,
                     edge=(0.3, 0.95, 1, 1), **bw)
        elif m:
            U.button(br, {"garage": "GARAGE", "shop": "REFILL", "home": "ENTER HOME"}.get(m["kind"], "START"), (col2, rows[3] if self.pcar else rows[1]), self.key_e, hint="E",
                     edge=U.GOLD, **bw)
        if self.activity:
            U.button(br, "QUIT EVENT", (col1, rows[3]), self.quit_activity, hint="", **bw)
        # left movement pad
        bl = DirectFrame(parent=a.a2dBottomLeft, frameColor=(0, 0, 0, 0)); self.btn_nodes.append(bl)
        pd = dict(w=0.065, h=0.065, scale=0.045, font=a.jpfont)
        for key, lbl, pos, hint in (("v_up", "▲", (0.25, 0.37), "W"), ("v_down", "▼", (0.25, 0.1), "S"),
                                    ("v_left", "◀", (0.11, 0.1), "A"), ("v_right", "▶", (0.39, 0.1), "D")):
            p, r = self.hold(key); U.button(bl, lbl, pos, None, hint=hint, press=p, release=r, **pd)

    def miyo_spot(self):
        """contextual prompt: ANA standing on HIKARI BEACH can call the TSUNAMI from right there"""
        if self.active != "ana" or self.pcar or self.tsunami is not None or self.home or self.garage: return None
        me = self.me()
        if D.SAND[0] - 2 < me.x < D.SEA_X + 2: return ("SUMMON TSUNAMI", self.key_n, "N", (0.3, 0.75, 1.0, 1))
        return None

    def add_cash(self, amount):
        """Add cash (int), clamped so the total never exceeds CASH_CAP. Returns the amount actually added."""
        amount = int(amount)
        if amount <= 0: return 0
        add = max(0, min(amount, CASH_CAP - self.cash))
        if add > 0:
            self.cash += add; self.app.sfx("cash", 0.8)
            self.cash_pop.setText("+" + fmt_cash_hud(add) if add >= 10 ** 10 else "+¥" + format(add, ",")); self.cash_pop_k = 2.6
            self.save()
        return add

    def add_cash_text(self, text):
        """Validate typed input for the ADD MONEY panel. Returns (ok, message)."""
        t = (text or "").replace(",", "").replace(" ", "").replace("¥", "").replace("_", "").strip()
        if not t: return False, "Type an amount first."
        if t.startswith("-"): return False, "Amount must be more than zero."
        if not t.isdigit() or not t.isascii(): return False, "Numbers only, please."
        n = int(t)
        if n <= 0: return False, "Amount must be more than zero."
        if self.cash >= CASH_CAP: self.app.sfx("empty", 0.6); return False, "Cash limit reached: %s" % format(CASH_CAP, ",")
        add = self.add_cash(n)
        if self.cash >= CASH_CAP:
            return True, "Added ¥%s.  Cash limit reached: %s" % (format(add, ","), format(CASH_CAP, ","))
        return True, "Added ¥%s" % format(add, ",")

    def toast(self, txt, dur=2.5):
        self.toast_t.setText(txt); self.toast_k = dur

    def caption(self, a, b, dur=3.0):
        self.cap1.setText(a); self.cap2.setText(b); self.cap_k = dur

    def letterbox(self, on):
        self.lb_on = on

    def fade(self, dur=1.0):
        self.fade_k = dur; self.fade_dur = dur

    def update_hud(self, dt):
        a = self.app; px, py = self.player_pos()
        # timers
        self.toast_k -= dt; self.cap_k -= dt; self.pop_k -= dt; self.sub_t -= dt
        if self.toast_k <= 0: self.toast_t.setText("")
        if self.cap_k <= 0: self.cap1.setText(""); self.cap2.setText("")
        if self.sub_t <= 0: self.sub.setText(""); self.sub_en.setText("")
        if self.pop_k <= 0: self.pop1.setText(""); self.pop2.setText("")
        else:
            al = min(1.0, self.pop_k); self.pop1.setFg(self.pop_col + (al,)); self.pop2.setFg(self.pop_col + (al,))
        self.lb_k += ((1.0 if (self.lb_on or self.intro_t > 0 or self.ride) else 0.0) - self.lb_k) * min(1, dt * 3)
        self.lb_top.set_z(1.0 - 0.16 * self.lb_k); self.lb_bot.set_z(-1.0 + 0.16 * self.lb_k)
        if self.fade_k > 0:
            self.fade_k -= dt; k = self.fade_k / self.fade_dur; al = 1.0 - abs(k * 2 - 1)
            self.fade_np.set_color(0, 0, 0, max(0, min(1, al * 1.6)))
        else: self.fade_np.set_color(0, 0, 0, 0)
        # district popup
        d = D.district_at(px, py) if self.home is None else self.district
        if d != self.district:
            self.district = d; dd = D.DISTRICT[d]
            self.dist_lbl.setText(dd[1]); self.dist_lbl_jp.setText(dd[2]); self.dist_lbl.setFg(dd[3] + (1,)); self.dist_lbl_jp.setFg(dd[3] + (1,))
            if self.time > 1.0:
                self.pop_col = dd[3]; self.pop1.setText(dd[1]); self.pop2.setText(dd[2]); self.pop_k = 3.0
        # minimap
        yaw = self.cam_yaw if self.pcar is None else (self.pcar.h if self.cam_mode != 2 else self.pcar.h)
        if self.cam_h is not None: yaw = self.cam_h
        span = 1180.0; z = 0.16; xmin, ymin = -470.0, -590.0
        cu, cv = (px - xmin) / span, (py - ymin) / span
        ts = TransformState.make_pos2d((cu, cv)).compose(TransformState.make_rotate2d(yaw)).compose(
            TransformState.make_scale2d(z)).compose(TransformState.make_pos2d((-0.5, -0.5)))
        self.mm.set_tex_transform(TextureStage.get_default(), ts)
        M = self.mm_M; r = math.radians(yaw); cs, sn = math.cos(r), math.sin(r); k = 0
        def dot(x, y, col, sz=0.012):
            nonlocal k
            if k >= len(self.mm_dots): return
            dx, dy = x - px, y - py
            u = (dx * cs + dy * sn) / (span * z); v = (-dx * sn + dy * cs) / (span * z)
            X, Y = u * 2 * M, v * 2 * M
            if abs(X) > M - 0.012 or abs(Y) > M - 0.012:
                if col[3] < 0.99: return
                X = max(-M + 0.012, min(M - 0.012, X)); Y = max(-M + 0.012, min(M - 0.012, Y))
            dd_ = self.mm_dots[k]; k += 1
            dd_.show(); dd_.set_pos(X, 0, Y); dd_["frameColor"] = col; dd_["frameSize"] = (-sz, sz, -sz, sz)
        for c in self.police: dot(c.x, c.y, (0.3, 0.45, 1.0, 1) if int(self.time * 4) % 2 else (1, 0.2, 0.2, 1))
        if self.activity and self.activity["kind"] in ("race", "tt"):
            cx, cy = self.activity["cps"][self.activity["cp"]]; dot(cx, cy, (1, 0.9, 0.2, 1), 0.016)
            for rc in self.activity.get("racers", []): dot(rc.x, rc.y, (1, 0.3, 0.7, 0.95))
        if self.taxi: dot(self.taxi.x, self.taxi.y, (1, 0.8, 0.15, 1), 0.014)
        if self.medic: dot(self.medic.x, self.medic.y, (1, 1, 1, 1), 0.014)
        if self.waypoint: dot(self.waypoint[0], self.waypoint[1], (0.3, 1, 0.4, 1), 0.016)
        if getattr(self, "events", None) is not None:
            for (ex, ey, ec, _) in self.events.map_points(): dot(ex, ey, ec, 0.015)
        if self.pcar is None and self.own and not self.own.dead: dot(self.own.x, self.own.y, (0.2, 1, 0.9, 0.9), 0.012)
        for i in range(k, len(self.mm_dots)): self.mm_dots[i].hide()
        for (m, ic) in zip(self.markers + self.pois, self.mm_icons):
            dx, dy = m["x"] - px, m["y"] - py
            u = (dx * cs + dy * sn) / (span * z); v = (-dx * sn + dy * cs) / (span * z)
            X, Y = u * 2 * M, v * 2 * M; lim = M - 0.022
            edge = abs(X) > lim or abs(Y) > lim
            if edge:
                s_ = lim / max(abs(X), abs(Y)); X *= s_; Y *= s_
            ic.setPos(X, Y - 0.011); ic.setFg(m["col"] + ((0.75 if edge else 1.0),)); ic.setScale(0.026 if edge else 0.034)
        # status + circular speedometer
        c = self.pcar
        sp = c.speed * 3.6 if c else 0.0
        hud_on = self.garage is None and self.home is None and self.camapp is None
        if c and hud_on:
            self.speedo_root.show()
            self.speed_t.setText("%d" % int(sp)); self.kmh_t.setText("km/h")
            bucket = int(sp) // 2
            if bucket != self.speedo_bucket:
                self.speedo_bucket = bucket
                self._set_speedo_fill(sp / self.speedo_vmax)
            self.nitro_bar[0].show(); self.nitro_bar[1].set_sx(max(0.001, c.nitro_amt))
        else:
            self.speedo_root.hide(); self.speed_t.setText(""); self.kmh_t.setText("")
            self.nitro_bar[0].hide(); self.speedo_bucket = -1
        for n in (self.cash_t, self.stars_t, self.hp_bar[0], self.mm_root):
            n.show() if hud_on else n.hide()
        me = self.me(); self.hp_bar[1].set_sx(max(0.001, me.health / 100.0))
        self.cash_t.setText(fmt_cash_hud(self.cash))
        if self.cash_pop_k > 0:      # classic "+¥..." that rises and fades under the cash, cash flashes green
            self.cash_pop_k -= dt; f = max(0.0, self.cash_pop_k / 2.6)
            self.cash_pop.set_z(-0.075 + 0.03 * (1 - f)); self.cash_pop["fg"] = (0.3, 1.0, 0.45, min(1.0, f * 2.5))
            self.cash_t["fg"] = (0.3 + 0.7 * (1 - f), 1.0, 0.45 * f + 0.2 * (1 - f), 1) if f > 0.6 else U.GOLD
            if self.cash_pop_k <= 0: self.cash_pop.setText(""); self.cash_t["fg"] = U.GOLD
        self.cash_pop.show() if hud_on else self.cash_pop.hide()
        self.stars_t.setText("★" * self.heat + "☆" * (5 - self.heat) if self.heat else "")
        act = self.activity
        if act and act["kind"] == "race" and act.get("count", 0) <= 0:
            self.race_t.setText("POS %d/%d   LAP %d/%d   CP %d/%d   %s" % (self.race_position(), 1 + len(act["racers"]), act["lap"], act["laps"],
                                                                         act["cp"], len(act["cps"]), self.fmt(act["t"])))
        elif act and act["kind"] == "tt" and act.get("count", 0) <= 0:
            self.race_t.setText("TIME TRIAL   CP %d/%d   %s / %s" % (act["cp"], len(act["cps"]), self.fmt(act["t"]), self.fmt(act["limit"])))
        elif act and act["kind"] == "chase":
            self.race_t.setText(D.GET_WANTED + "  -  break line of sight   %s" % self.fmt(act["t"]))
        elif act and act["kind"] == "drift" and act.get("count", 0) <= 0:
            self.race_t.setText("DRIFT SCORE %d   %ds" % (act["score"], max(0, act["t"])))
        elif self.heat:
            self.race_t.setText("WANTED  -  lose the police" + ("   BUSTING..." if self.bust_t > 0.5 else ""))
        else:
            self.race_t.setText("")
        m = self.near_marker()
        if self.garage or self.overlay or self.phone: self.prompt.setText("")
        elif m: self.prompt.setText("[E] %s" % ("ENTER FRGARAGE" if m["kind"] == "garage" else "ENTER HOME" if m["kind"] == "home" else ("REFILL AMMO (¥300)" if m["kind"] == "shop" else ("PLAY SFC 27" if m["kind"] == "football" else "START " + m["name"]))))
        elif self.miyo_spot(): self.prompt.setText("[N] SUMMON TSUNAMI")
        elif getattr(self, "bar", None) is not None and self.bar.near(): self.prompt.setText("[E] ORDER A DRINK  -  HIKARI BEACH BAR")
        elif self.pcar is None and self.ride is None and self.taxi_ai_arrived() and math.hypot(self.taxi.x - me.x, self.taxi.y - me.y) < 8:
            self.prompt.setText("[F] RIDE JP TAXI")
        elif self.pcar is None and self.ride is None and any(math.hypot(o.x - me.x, o.y - me.y) < o.spec["hl"] + 2.3 for o in self.cars_near(me.x, me.y, 7)
                                                             if o not in (self.taxi, self.medic) and not getattr(o, "racer", False)):
            self.prompt.setText("[F] ENTER VEHICLE")
        else: self.prompt.setText("")
        if (not self.garage and not self.overlay and not self.phone
                and getattr(self, "hackeria", None) and self.hackeria.prompt()):
            hp = self.hackeria.prompt()
            if (not m) or hp.startswith("[E] HACK") or hp.startswith("[LOCKED]") or "CAMERA" in hp:
                self.prompt.setText(hp)
        self.refresh_buttons()

    # ================================================================ camera
    cam_h = None

    def cam_clear(self, tx, ty, x, y, z):
        """pull the camera in front of buildings so it never clips inside geometry."""
        g = self.world.grid
        if not g.segment_blocked(tx, ty, x, y): return x, y
        for f in (0.8, 0.6, 0.45, 0.3, 0.18):
            nx_, ny_ = tx + (x - tx) * f, ty + (y - ty) * f
            if not g.segment_blocked(tx, ty, nx_, ny_): return nx_, ny_
        return tx + (x - tx) * 0.12, ty + (y - ty) * 0.12

    def update_camera(self, dt):
        cam = self.app.camera; lens = self.app.camLens
        self.shake = max(0.0, self.shake - dt * 2.0)
        sh = (random.uniform(-1, 1) * self.shake * 0.25, random.uniform(-1, 1) * self.shake * 0.25)
        fov = 70.0
        if self.garage:
            g = self.garage; c = g["car"]; g["a"] += dt * 14
            r = math.radians(g["a"]); d = 9.5
            x, y = c.x + math.cos(r) * d, c.y + math.sin(r) * d
            cam.set_pos(x, y, 2.4); cam.look_at(c.x, c.y, 0.8); lens.set_fov(50)
            cam.set_h(cam, 14); self.cam_h = cam.get_h(); return
        if self.intro_t > 0:
            me = self.me(); r = math.radians(self.time * 18 + 200); d = 7.0 + self.intro_t * 1.4
            cam.set_pos(me.x + math.cos(r) * d, me.y + math.sin(r) * d, 1.6 + self.intro_t * 0.9)
            cam.look_at(me.x, me.y, 1.4); lens.set_fov(55); self.cam_h = cam.get_h(); return
        if self.ride:
            c = self.ride["car"]; t = self.time
            r = math.radians(c.h + 150 + math.sin(t * 0.15) * 40); d = 10.0
            x, y = self.cam_clear(c.x, c.y, c.x + math.cos(r) * d, c.y + math.sin(r) * d, 3)
            cam.set_pos(x, y, 2.4 + math.sin(t * 0.2) * 0.8); cam.look_at(c.x, c.y, 1.0); lens.set_fov(50); self.cam_h = c.h; return
        if self.pcar:
            c = self.pcar; f = c.fwd; sp = c.speed
            if self.cam_mode == 2:
                cam.set_pos(c.x + f[0] * 0.2, c.y + f[1] * 0.2, c.spec["roof"] + 0.1); cam.set_hpr(c.h, -3, 0)
                lens.set_fov(min(95, 72 + sp * 0.3)); self.cam_h = c.h; return
            dist, hgt = (6.8, 2.3) if self.cam_mode == 0 else (11.0, 3.8)
            dist += min(sp, 70) * 0.03
            # heading follows velocity a bit (drift look)
            vh = math.degrees(math.atan2(-c.vx, c.vy)) if sp > 5 and c.fspeed() > 0 else c.h
            want = c.h + wrap(vh - c.h) * 0.35
            if self.cam_pos is None: self.cam_yaw = want
            self.cam_yaw += wrap(want - self.cam_yaw) * min(1, dt * 4.5)
            r = math.radians(self.cam_yaw); fx, fy = -math.sin(r), math.cos(r)
            x, y = c.x - fx * dist, c.y - fy * dist
            x, y = self.cam_clear(c.x, c.y, x, y, hgt)
            if self.cam_pos is None: self.cam_pos = [x, y]
            k = min(1, dt * 10)
            self.cam_pos[0] += (x - self.cam_pos[0]) * k; self.cam_pos[1] += (y - self.cam_pos[1]) * k
            cam.set_pos(self.cam_pos[0] + sh[0], self.cam_pos[1] + sh[1], hgt + sh[0] * 0.5)
            cam.look_at(c.x + fx * 4, c.y + fy * 4, 0.9)
            fov = 68 + min(28, sp * 0.42) + (6 if c.nitro and c.nitro_amt > 0 else 0)
            self.cur_fov = getattr(self, "cur_fov", fov) + (fov - getattr(self, "cur_fov", fov)) * min(1, dt * 3)
            lens.set_fov(self.cur_fov); self.cam_h = self.cam_yaw; return
        me = self.me()
        dist, hgt = ((4.2, 1.9), (7.0, 3.2), (2.6, 1.7))[self.cam_mode]
        if self.arsenal.aiming:
            dist, hgt = 2.1, 1.75
        if self.cinematic > 0:
            self.cinematic -= dt; dist += self.cinematic * 3; hgt += self.cinematic * 1.5
        r = math.radians(self.cam_yaw); fx, fy = -math.sin(r), math.cos(r)
        x, y = me.x - fx * dist + fy * 0.5, me.y - fy * dist - fx * 0.5
        x, y = self.cam_clear(me.x, me.y, x, y, hgt)
        if self.cam_pos is None: self.cam_pos = [x, y]
        k = min(1, dt * 8)
        self.cam_pos[0] += (x - self.cam_pos[0]) * k; self.cam_pos[1] += (y - self.cam_pos[1]) * k
        cam.set_pos(self.cam_pos[0] + sh[0], self.cam_pos[1] + sh[1], hgt)
        cam.look_at(me.x + fx * 2 + fy * 0.5, me.y + fy * 2 - fx * 0.5, 1.4)
        lens.set_fov(50 if self.arsenal.aiming else 65); self.cam_h = self.cam_yaw

    # ================================================================ main loop
    def control_player(self, dt):
        c = self.pcar
        if c is None: return
        if self.blocked() or self.phone:
            c.throttle = 0; c.steer = 0; c.hand = True; c.nitro = False; return
        up = self.down("w", "arrow_up", "v_up"); dn = self.down("s", "arrow_down", "v_down")
        lf = self.down("a", "arrow_left", "v_left"); rt = self.down("d", "arrow_right", "v_right")
        pad = getattr(self.app, "pad", None)
        # v1.0.5.3 fix: A / left arrow / stick left = steer LEFT, D / right arrow / stick right = steer RIGHT.
        # The car model turns right for steer > 0 (heading decreases, front wheels set_h(-28)), but the input used +1 for A,
        # so A steered right and D left (and the gamepad stick was inverted the same way).
        thr = (1.0 if up else 0.0) - (1.0 if dn else 0.0); st = (1.0 if rt else 0.0) - (1.0 if lf else 0.0)
        if pad:
            try:
                thr += pad.get("rt", 0) - pad.get("lt", 0); st += pad.get("lx", 0)
            except Exception: pass
        c.throttle = max(-1.0, min(1.0, thr))
        tgt = max(-1.0, min(1.0, st))
        c.steer += (tgt - c.steer) * min(1, dt * (6 if tgt else 9))
        c.hand = self.down("space", "v_hand"); c.nitro = self.down("shift", "v_nitro")
        if c.asleep and (thr or st): c.wake()
        # automatic unstick: pushing against a wall without moving -> reset
        if c.contact > 0 and abs(c.throttle) > 0.5 and c.speed < 1.0:
            self.stuck_t += dt
            if self.stuck_t > 2.5: self.stuck_t = 0; self.key_r()
        else: self.stuck_t = max(0.0, self.stuck_t - dt)

    def update(self, task):
        # v1.0.3: real-time sub-stepping. Frames slower than 20 fps used to be clamped to a 0.05 s step, so on a busy
        # scene (beach / dense sidewalks) ANA & DANIEL walked in slow motion; now up to 4 sub-steps keep normal speed.
        raw = max(0.0, min(0.2, self.app.clock.get_dt()))
        if self.paused:
            try: self.online.update(1e-4)          # v1.0.5: the session keeps talking while the menu is open
            except Exception as e: self.app.log_error(e)
            return task.cont
        n = max(1, int(math.ceil(raw / 0.05))); dt = raw / n * self.time_scale
        try:
            for _ in range(n): self.step(dt)
        except Exception as e:
            self.app.log_error(e)
        return task.cont

    def _apply_blackout_light(self):
        """Near-total dark: dense black fog, neon almost out. Headlight beams and phone HUD stay visible."""
        app = self.app
        try:
            app.set_daylight(0.0, 0.0)
        except Exception:
            pass
        try:
            app.fog.set_color(0.002, 0.003, 0.006)
            app.set_background_color(0, 0, 0, 1)
            app.fog.set_exp_density(0.048)
            app.render.set_shader_input("dayk", 0.0)
        except Exception:
            pass
        w = self.world
        try:
            if w is not None:
                if getattr(w, "static", None):
                    w.static.set_color_scale(0.10, 0.11, 0.12, 1)
                for np_ in getattr(w, "emit_nodes", []) or []:
                    np_.set_color_scale(0.04, 0.045, 0.05, 1)
                if getattr(w, "ground_np", None) is not None:
                    w.ground_np.set_color_scale(0.12, 0.12, 0.13, 1)
                if getattr(w, "sky_day", None) is not None:
                    w.sky_day.hide()
        except Exception:
            pass
        # keep road headlight beams visible
        for c in self.cars:
            try:
                if getattr(c, "beam", None) is not None and not c.beam.is_empty():
                    c.beam.set_color(0.85, 0.92, 1.0, 0.85)
                    c.beam.show()
            except Exception:
                pass

    def update_daynight(self, dt):
        """24 real minutes = 24 h in game. Settings can lock day or night."""
        if getattr(self, "hackeria", None) and self.hackeria.blackout_t > 0:
            self._apply_blackout_light()
            self._blackout_beams = True
            return
        mode = self.app.settings.get("tod", "cycle")
        if getattr(self, "_blackout_beams", False):
            self._blackout_beams = False
            for c in self.cars:
                try:
                    if getattr(c, "beam", None) is not None and not c.beam.is_empty():
                        c.beam.set_color(0.80, 0.90, 1.0, 0.55)
                except Exception:
                    pass
        if mode == "day": self.tod = 13.0
        elif mode == "night": self.tod = 23.0
        else: self.tod = (self.tod + dt / 60.0) % 24.0
        self._tod_t = getattr(self, "_tod_t", 0) - dt
        if self._tod_t > 0 and mode == getattr(self, "_tod_mode", None): return
        self._tod_t = 0.5; self._tod_mode = mode
        a = (self.tod - 6.0) / 12.0 * math.pi                  # sunrise 06:00, sunset 18:00
        elev = math.sin(a)
        k = max(0.0, min(1.0, (elev + 0.08) / 0.30)); k = k * k * (3 - 2 * k)
        warm = max(0.0, min(1.0, 1.0 - abs(elev - 0.08) / 0.25)) * (1 if k > 0 else 0)
        az = a
        sun = (math.cos(az) * 0.8, -0.45, max(0.15, elev) + 0.1)
        self.app.set_daylight(k, warm, sun)

    def step(self, dt):
        self.time += dt
        self.update_daynight(dt)
        self.online.update(dt)
        if self.match is not None:             # v1.0.5 SFC 27: the match owns the player, ball and camera
            self.match.step(dt); self.world.update(dt, self.time); self.update_hud(dt); self.app.update_audio(self, dt)
            self.prompt.setText("")
            return
        if self.home:
            self.update_home(dt); self.update_camapp(dt); self.update_hud(dt); self.app.update_audio(self, dt)
            if self.eating is not None and self.eating.update(dt): self.eating = None
            self.laptop.update(dt)
            return
        if self.intro_t > 0:
            self.intro_t -= dt
            if self.intro_t <= 0: self.letterbox(False); self.cam_pos = None
        self.control_player(dt)
        px, py = self.player_pos()
        for c in self.cars:
            if c.ai is not None and not c.dead:
                if math.hypot(c.x - px, c.y - py) < 320: c.ai.update(dt)
                else: c.throttle = 0
        for c in list(self.cars): c.step(dt)
        collide_cars(self.cars, self)
        for c in self.cars: c.sync(dt)
        self.update_people(dt)
        self.update_police(dt)
        self.update_activity(dt)
        self.update_responders(dt)
        self.update_ride(dt)
        self.update_chatter(dt)
        self.update_pickups(dt)
        if getattr(self, "events", None) is not None:
            try: self.events.update(dt)
            except Exception as e: self.app.log_error(e); self.events = None
        self.arsenal.update(dt)
        self.pop_t -= dt
        if self.pop_t <= 0: self.pop_t = 0.5; self.populate()
        self.world.update(dt, self.time)
        for m in self.markers:
            if "np" in m: m["np"].set_h(self.time * 30)
        self.miyo.update(dt); self.signals.update(dt); self.laptop.update(dt)
        if self.eating is not None and self.eating.update(dt): self.eating = None
        self.update_camera(dt); self.update_taxi_fx(dt)
        if getattr(self, "hackeria", None):
            try: self.hackeria.update(dt)
            except Exception as e: self.app.log_error(e)
        if self.drunk > 0:                       # v1.0.4: tipsy from the bar - a gentle camera sway, wears off slowly
            self.drunk = max(0.0, self.drunk - dt * 0.006); dk = min(1.0, self.drunk / 4.0)
            self.app.camera.set_r(self.app.camera.get_r() + math.sin(self.time * 0.9) * 3.0 * dk)
        self.update_camapp(dt)
        self.update_hud(dt)
        self.app.update_audio(self, dt)

    def update_pickups(self, dt):
        px, py = self.player_pos()
        for n in self.tok_np.get_children():
            t = n.get_python_tag("tok")
            n.set_z(1.6 + math.sin(self.time * 3 + t[0]) * 0.25)
            if math.hypot(t[0] - px, t[1] - py) < 3.0:
                self.tokens.add(t); n.remove_node(); self.add_cash(500); self.app.sfx("checkpoint", 0.6)
                self.toast("Neon token %d/%d  +¥500" % (len(self.tokens), len(D.TOKENS)))
        self._cam_cd -= dt
        if self.pcar and self._cam_cd <= 0:
            for x, y, nm in D.SPEED_CAMS:
                if math.hypot(x - px, y - py) < 12:
                    v = int(self.pcar.speed * 3.6); best = self.cam_cams.get(nm, 0)
                    self._cam_cd = 3.0
                    if v > best:
                        self.cam_cams[nm] = v; self.toast("SPEED CAMERA %s: %d km/h  (new best!)" % (nm, v)); self.app.sfx("checkpoint", 0.5)
                    else:
                        self.toast("SPEED CAMERA %s: %d km/h  (best %d)" % (nm, v, best))

    # ================================================================ persistence
    def save(self):
        d = {"cash": self.cash, "tokens": [list(t) for t in self.tokens], "best": self.best, "cars": self.cars_cfg,
             "speedcams": self.cam_cams, "active": self.active, "mate": self.mate, "outfit": self.outfit, "outfits": dict(self.outfits),
             "hackeria": self.hackeria.save() if getattr(self, "hackeria", None) else {}, "photos": list(getattr(self, "photos", [])), "ledger": [list(x) for x in getattr(self, "ledger", [])][-30:],
             "owned": getattr(self, "owned", {}), "news": [list(x) for x in getattr(self, "news", [])][-10:], "misto": getattr(self, "misto", {}), "drunk": getattr(self, "drunk", 0.0), "car": self.player_kind, "evo_v1053": True, "events": self.events.save() if getattr(self, "events", None) is not None else {}, **(self.arsenal.save() if hasattr(self, "arsenal") else {}), "names": self.real_names(), "online": self.online.save() if hasattr(self, "online") else {}, "version": self.app.VERSION}
        if getattr(self, "guest", False) and d.get("active") not in CREW: d["active"] = "elijer"
        try: self.app.write_save(d)
        except Exception as e: self.app.log_error(e)

    def real_names(self):
        n = {"elijer": NAMES["elijer"], "ana": NAMES.get("ana", "ANA"), "daniel": NAMES.get("daniel", "DANIEL")}
        o = getattr(self, "online", None)
        if o is not None and o.guest and o._real: n[o._real[0]] = o._real[1]
        return [n.get(self.active, NAMES["elijer"])]

    def destroy(self):
        if getattr(self, "events", None) is not None:
            try: self.events.destroy()
            except Exception as e: self.app.log_error(e)
        if getattr(self, "match", None) is not None:
            try: self.match.quit()
            except Exception as e: self.app.log_error(e)
        if hasattr(self, "online"):
            try: self.online.destroy()
            except Exception as e: self.app.log_error(e)
        if getattr(self, "sfc_signs", None) is not None: self.sfc_signs.remove_node()
        self.app.task_mgr.remove("fs-ds"); self._ds_end()
        self.save()
        self.app.task_mgr.remove("game-update"); self.unbind(); self.arsenal.destroy(); self.miyo.destroy(); self.signals.destroy()
        for c in list(self.cars): c.destroy()
        for p in self.peds: p.destroy()
        for p in self.chars.values(): p.destroy()
        for n in (self.mk_np, self.tok_np, self.garage_sign, self.hud, self.mm_root, self.lb_top, self.lb_bot, self.fade_np):
            n.remove_node()
        if self.cp_np: self.cp_np.remove_node()
        for o in (self.btn_root, self.overlay, self.phone): 
            if o: o.destroy()
        for t in (self.speed_t, self.kmh_t, self.cash_t, self.stars_t, self.race_t, self.big, self.prompt, self.sub, self.sub_en, self.toast_t, self.cap1, self.cap2,
                  self.pop1, self.pop2, self.dist_lbl, self.dist_lbl_jp):
            t.destroy()
        self.nitro_bar[0].destroy(); self.hp_bar[0].destroy()
        try: self.speedo_root.destroy()
        except Exception: pass
        for n in getattr(self, "btn_nodes", []): n.destroy()
