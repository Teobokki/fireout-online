"""v1.0.5 FIREOUT ONLINE app (phone, IX LAPTOPOS G9 laptop, pause menu).

Host / join a session with a SHINE-XXXX-XXXX code, play together across the internet (see fs_net), chat, kick, ping,
friends as NEW characters (8 presets + customiser), BRING THEM IN AI friends, and the SHINE SFC 27 football button."""
import math, random, time, os
from direct.gui.DirectGui import DirectFrame, DirectEntry, DGG
from panda3d.core import TextNode
import fs_ui as U
import fs_data as D
import fs_avatar as A

PINK = (0.95, 0.35, 0.62, 1); VIOLET = (0.55, 0.3, 0.95, 1); CY_ = (0.3, 0.9, 1.0, 1)


class Remote:
    """another player in the open world (avatar + optional car proxy), smoothed toward the latest state"""
    def __init__(self, game, key, name, cfg=None, who=None):
        self.g = game; self.key = key; self.name = name; self.cfg = cfg; self.who = who; self.car = None; self.car_kind = None
        if who in ("ana", "daniel"):
            from fs_people import Person
            self.p = Person(game, who, 0, 0, 0, ped=True)
        else:
            self.p = A.Avatar(game, cfg or A.preset(0))
        tn = TextNode("tag"); tn.set_text(name); tn.set_align(TextNode.A_center); tn.set_text_color(1, 1, 1, 1)
        if U.FONT: tn.set_font(U.FONT)
        self.tag = self.p.np.attach_new_node(tn); self.tag.set_z(2.15); self.tag.set_scale(0.28); self.tag.set_billboard_point_eye()
        self.tag.set_light_off(); self.tag.set_shader_off(); self.tag.set_depth_offset(1)
        self.s = None; self.first = True

    def set_state(self, s): self.s = s

    def update(self, dt, hidden=False):
        s = self.s
        if s is None or hidden or s.get("m"):
            self.p.np.hide()
            if self.car is not None: self.car.np.hide()
            return
        self.p.np.show(); p = self.p
        car = s.get("car")
        if car:
            kind, cx, cy, ch = car[0], car[1], car[2], car[3]
            if self.car is None or self.car_kind != kind:
                self._drop_car()
                from fs_vehicle import Car
                paint = tuple(car[4]) if len(car) > 4 else (0.6, 0.6, 0.65)
                from fs_vehicle import SPECS
                if kind not in SPECS: kind = "sedan"
                self.car = Car(self.g, kind, cx, cy, ch, paint, "", True, "remote"); self.car_kind = car[0]
                p.seat(self.car, 1)
            c = self.car; c.np.show(); k = min(1.0, dt * 10)
            c.x += (cx - c.x) * k; c.y += (cy - c.y) * k; c.h += ((ch - c.h + 180) % 360 - 180) * k
            c.vx = c.vy = 0.0; c.sync(dt)
            return
        if self.car is not None:
            p.unseat(self.car.x, self.car.y, self.car.h); self._drop_car()
        if self.first: p.x, p.y, p.h = s["x"], s["y"], s["h"]; self.first = False
        k = min(1.0, dt * 10)
        if math.hypot(s["x"] - p.x, s["y"] - p.y) > 12: p.x, p.y = s["x"], s["y"]
        p.x += (s["x"] - p.x) * k; p.y += (s["y"] - p.y) * k; p.h += ((s["h"] - p.h + 180) % 360 - 180) * k
        p.walk_anim(dt, s.get("sp", 0.0)); p.sync()

    def _drop_car(self):
        if self.car is not None:
            if self.p.in_car is self.car: self.p.unseat(self.car.x, self.car.y, self.car.h)
            self.car.destroy(); self.car = None; self.car_kind = None

    def destroy(self):
        self._drop_car(); self.p.destroy()


class Friend:
    """BRING THEM IN: an AI friend from the avatar pool - follows you, roams, drives its own car, plays football"""
    def __init__(self, game, cfg, slot):
        self.g = game; self.cfg = cfg; self.slot = slot; me = game.me()
        r = math.radians(me.h + 180 + (slot - 1) * 35)
        self.p = A.Avatar(game, cfg, me.x - math.sin(r) * 3.0, me.y + math.cos(r) * 3.0, me.h)
        self.p.sync(); self.car = None; self.roam = None; self.idle = 0.0; self.re_t = 0.0

    def update(self, dt):
        g = self.g; me = g.me(); p = self.p
        if g.home is not None:
            p.np.hide(); return
        p.np.show()
        if g.pcar is not None or g.ride is not None:
            self._drive(dt); return
        if self.car is not None: self._park()
        if p.update_knock(dt): p.sync(); return
        moving = math.hypot(me.vx, me.vy) > 0.3 if hasattr(me, "vx") else True
        self.idle = 0.0 if getattr(g, "_me_moved", True) else self.idle + dt
        if self.idle > 8.0:              # you stopped: they wander around nearby, then come back
            if self.roam is None or math.hypot(self.roam[0] - p.x, self.roam[1] - p.y) < 0.8:
                a = random.uniform(0, 6.28); d = random.uniform(3, 9)
                self.roam = (me.x + math.cos(a) * d, me.y + math.sin(a) * d)
            tx, ty = self.roam; spmax = 1.4
        else:
            self.roam = None
            r = math.radians(me.h); side = (-1.6, 1.6, 0.0, -3.2)[self.slot % 4]; back = (1.8, 1.8, 3.4, 3.4)[self.slot % 4]
            fx, fy = -math.sin(r), math.cos(r)
            tx = me.x - fx * back + fy * side; ty = me.y - fy * back - fx * side; spmax = 6.4
        dx, dy = tx - p.x, ty - p.y; d = math.hypot(dx, dy)
        if d > 30: p.x, p.y = tx, ty; d = 0
        sp = 0.0
        if d > 0.6:
            sp = min(spmax, max(1.3, d * 1.4)); p.x += dx / d * sp * dt; p.y += dy / d * sp * dt
            th = math.degrees(math.atan2(-dx, dy)); p.h += ((th - p.h + 180) % 360 - 180) * min(1, dt * 8)
        px_, py_, nx, ny, tag = g.world.grid.push_circle(p.x, p.y, 0.35); p.x += px_; p.y += py_
        for o in [g.me(), g.buddy()] + [f.p for f in g.online.ai_friends if f is not self]:
            dd = math.hypot(p.x - o.x, p.y - o.y)
            if 1e-3 < dd < 0.8: p.x += (p.x - o.x) / dd * (0.8 - dd) * 0.5; p.y += (p.y - o.y) / dd * (0.8 - dd) * 0.5
        p.walk_anim(dt, sp); p.sync()

    def _behind(self, lead, d):
        r = math.radians(lead.h); fx, fy = -math.sin(r), math.cos(r)
        x, y, h = self.g.world.nearest_road_point(lead.x - fx * d, lead.y - fy * d)
        if math.hypot(x - lead.x, y - lead.y) > d + 25: x, y, h = lead.x - fx * d, lead.y - fy * d, lead.h
        return x, y, h

    def _drive(self, dt):
        g = self.g; lead = g.pcar or (g.ride["car"] if g.ride else None)
        if lead is None: return
        from fs_ai import ResponderAI
        if self.car is None:
            x, y, h = self._behind(lead, 9.0 * (self.slot + 1))
            for _ in range(6):
                if not g.cars_near(x, y, 4.5): break
                x, y, h = self._behind(lead, 9.0 * (self.slot + 1) + 7 * (_ + 1))
            c = self.car = g.spawn_car(random.choice(["sedan", "hatch", "coupe", "kei", "suv"]), x, y, h)
            c.driver = "ai"; c.asleep = False; c.friend = True
            self.p.seat(c, 1); c.ai = ResponderAI(g, c, (lead.x, lead.y), fast=True); c.ai.arrived = True
            self.dest = (lead.x, lead.y); self.re_t = 0.5
        c = self.car; self.re_t -= dt
        d = math.hypot(lead.x - c.x, lead.y - c.y)
        if d > 160:                       # lost in traffic: catch up behind you
            x, y, h = self._behind(lead, 14.0 + 8 * self.slot); c.x, c.y, c.h = x, y, h; c.vx = c.vy = 0.0; c.w = 0.0
            c.ai = ResponderAI(g, c, (lead.x, lead.y), fast=True); c.ai.arrived = True; self.dest = (lead.x, lead.y); return
        if self.re_t <= 0:
            self.re_t = 1.0
            moved = math.hypot(lead.x - self.dest[0], lead.y - self.dest[1])
            if d < 14 + 5 * self.slot: c.ai.arrived = True                  # close enough: wait behind you
            elif c.ai.arrived or moved > 35:                                # set off / re-plan only when you've really moved
                c.ai = ResponderAI(g, c, (lead.x, lead.y), fast=True); self.dest = (lead.x, lead.y)

    def _park(self):
        c = self.car; g = self.g
        if self.p.in_car is c: self.p.unseat(c.x + 2.5, c.y, c.h)
        g.remove_car(c); self.car = None
        me = g.me(); self.p.x, self.p.y = me.x + random.uniform(-3, 3), me.y + random.uniform(-3, 3); self.p.sync()

    def destroy(self):
        if self.car is not None:
            if self.p.in_car is self.car: self.p.unseat(0, 0, 0)
            self.g.remove_car(self.car); self.car = None
        self.p.destroy()


class Online:
    def __init__(self, game):
        self.g = game; self.app = game.app; self.sess = None; self.remotes = {}; self.ai_friends = []; self.ui = None
        sd = getattr(game, "_save", {}) or {}
        prof = sd.get("online") or {}
        self.profile = A.clean(prof.get("avatar") or A.preset(0))
        self.password = ""; self.lan = None; self.view = "main"; self.guest = False; self.fb_seq = 0; self._fb_t = 0.0; self._fb_last = {}
        self._real = None; self.hud = None; self.preview = None; self.last_event = ""; self.chat_log = []

    def save(self):
        return {"avatar": dict(self.profile)}

    # ----------------------------------------------------------------- session control
    def host(self, password=""):
        import fs_net as N
        self.leave(quiet=True)
        self.sess = N.Session("host", self.profile["name"], self.profile, password=password)
        self._handlers(); self.g.toast("FIREOUT ONLINE: opening a session...", 2.5); self.refresh()

    def join(self, code, password="", addr=None):
        import fs_net as N
        if N.parse_code(code) is None:
            self.g.toast("That code looks wrong - it should look like SHINE-XXXX-XXXX", 3.0); return False
        self.leave(quiet=True)
        self.sess = N.Session("join", self.profile["name"], self.profile, password=password)
        self.sess.join(code, addr); self._handlers(); self.refresh(); return True

    def _handlers(self):
        s = self.sess
        s.on("fbi", self._on_fb_input); s.on("fb_start", self._on_fb_start); s.on("fb", self._on_fb_snap); s.on("fb_end", self._on_fb_end); s.on("fb_leave", self._on_fb_leave)

    def leave(self, quiet=False):
        if self.sess is not None:
            self.sess.close(); self.sess = None
            if not quiet: self.g.toast("Left the FIREOUT ONLINE session", 2.0)
        for r in self.remotes.values(): r.destroy()
        self.remotes = {}
        self.set_guest(False)
        if getattr(self.g, "match", None) is not None and self.g.match.mode == "view": self.g.match.quit()
        self.refresh()

    def kick(self, pid):
        if self.sess and self.sess.role == "host": self.sess.kick(pid); self.refresh()

    # joiner: play as your own FIREOUT ONLINE character (the crew is not used while you're a guest)
    def set_guest(self, on):
        g = self.g; me = g.me()
        if on and not self.guest:
            from fs_game import NAMES
            self._real = (g.active, NAMES[g.active]); NAMES[g.active] = self.profile["name"]
            me.model.remove_node(); me.cfg = dict(self.profile); A.Avatar.build_model(me)
            me.set_outfit = lambda o: None; me.set_expression = lambda e="neutral": None; me.set_chew = lambda k: None
            b = g.buddy(); b.np.hide(); b.guest_hidden = True
            self.guest = True; g.guest = True; me.sync()
        elif not on and self.guest:
            from fs_game import NAMES
            act, nm = self._real; NAMES[act] = nm
            p = g.chars[act]
            for k in ("set_outfit", "set_expression", "set_chew"):
                if k in p.__dict__: del p.__dict__[k]
            if hasattr(p, "cfg"): del p.cfg
            p.model.remove_node(); p._chew_np = None; p.build_model(); p.sync()
            b = g.buddy(); b.np.show(); b.guest_hidden = False
            self.guest = False; g.guest = False

    # ----------------------------------------------------------------- AI friends
    def bring_them_in(self, n=3):
        if self.ai_friends: return
        used = {self.profile.get("name")}
        idx = [i for i in range(len(A.PRESETS)) if A.PRESETS[i]["name"] not in used]
        random.shuffle(idx)
        for k, i in enumerate(idx[:n]): self.ai_friends.append(Friend(self.g, A.preset(i), k))
        self.g.toast("BRING THEM IN: %s joined you" % ", ".join(f.cfg["name"] for f in self.ai_friends), 3.0); self.refresh()

    def send_home(self):
        for f in self.ai_friends: f.destroy()
        self.ai_friends = []; self.g.toast("Your AI friends went home", 2.0); self.refresh()

    def hide_all(self, on):
        for f in self.ai_friends:
            if on: f.p.np.hide()
            else: f.p.np.show()
        self._hidden = on

    def after_match(self, me):
        for k, f in enumerate(self.ai_friends):
            f.p.x, f.p.y = me.x - 1.5 - k, me.y - 1.5; f.p.sync()

    # ----------------------------------------------------------------- per-frame
    def my_state(self):
        g = self.g; me = g.me(); m = getattr(g, "match", None)
        st = {"x": round(me.x, 2), "y": round(me.y, 2), "h": int(me.h), "sp": round(getattr(me, "_spd", 0.0), 2), "m": 1 if m else 0}
        if self.sess and self.sess.role == "host": st["who"] = g.active
        c = g.pcar or (g.ride["car"] if g.ride else None)
        if c is not None: st["car"] = [c.kind, round(c.x, 2), round(c.y, 2), int(c.h), [round(v, 2) for v in getattr(c, "paint", (0.6, 0.6, 0.65))[:3]]]
        if self.sess and self.sess.role == "host" and self.ai_friends and not m:
            st["ai"] = [[round(f.p.x, 2), round(f.p.y, 2), int(f.p.h), f.cfg["name"]] + ([f.car.kind, round(f.car.x, 2), round(f.car.y, 2), int(f.car.h)] if f.car else [])
                        for f in self.ai_friends]
        return st

    def update(self, dt):
        g = self.g; me = g.me()
        lp = getattr(self, "_lp", (me.x, me.y)); mv = math.hypot(me.x - lp[0], me.y - lp[1]); self._lp = (me.x, me.y)
        me._spd = mv / max(dt, 1e-3); g._me_moved = mv > 0.02 or g.pcar is not None
        if getattr(g, "match", None) is None:
            for f in list(self.ai_friends): f.update(dt)
        s = self.sess
        if s is None:
            self._hud(); return
        s.poll(my_state=self.my_state())
        for ev, data in s.events:
            if ev == "chat":
                self.chat_log.append(data); self.chat_log = self.chat_log[-30:]; g.toast("ONLINE  " + data, 3.0)
            elif ev == "joined":
                self.set_guest(True); g.toast("Connected - you are %s in this session" % self.profile["name"], 3.0)
            elif ev == "code":
                g.toast("SESSION OPEN  -  code %s" % data, 5.0)
            elif ev in ("kicked", "ended"):
                g.toast(s.status, 4.0)
            self.last_event = ev
            if self.ui is not None: self._ui_dirty = True
        s.events = []
        if s.state in ("ended", "error") and s.role == "join":
            msg = s.status; self.leave(quiet=True); g.toast(msg, 5.0); return
        # remote players
        want = {}
        if s.role == "host":
            for pid, p in s.peers.items():
                if p.get("state") is not None: want[pid] = (p["name"], p.get("cfg"), None, p["state"])
        else:
            ros = {e.get("id"): e for e in getattr(s, "roster", [])}
            for pid, st in s.remote_states.items():
                e = ros.get(pid, {})
                want[pid] = (e.get("name", "FRIEND"), e.get("cfg"), st.get("who") if pid == 0 else None, st)
                for k, a in enumerate(st.get("ai") or []) if pid == 0 else []:
                    ai_st = {"x": a[0], "y": a[1], "h": a[2], "sp": 2.0, "m": st.get("m", 0)}
                    if len(a) > 4: ai_st["car"] = [a[4], a[5], a[6], a[7]]
                    nm = a[3]; cfg = next((dict(p) for p in A.PRESETS if p["name"] == nm), A.preset(k))
                    want["ai%d" % k] = (nm + " (AI)", cfg, None, ai_st)
        for k in list(self.remotes):
            if k not in want: self.remotes.pop(k).destroy()
        for k, (nm, cfg, who, st) in want.items():
            r = self.remotes.get(k)
            if r is not None and (r.who != who or (who is None and A.clean(cfg) != r.cfg)):
                r.destroy(); r = None
            if r is None:
                r = self.remotes[k] = Remote(g, k, nm, A.clean(cfg) if who is None else None, who)
            r.set_state(st); r.update(dt, hidden=g.home is not None or getattr(g, "match", None) is not None)
        if self.ui is not None and getattr(self, "_ui_dirty", False): self._ui_dirty = False; self.refresh()
        self._hud()

    def _hud(self):
        g = self.g; s = self.sess
        if s is None and not self.ai_friends:
            if self.hud is not None: self.hud.destroy(); self.hud = None
            return
        if self.hud is None:
            self.hud = U.text(self.app.a2dTopRight, "", (-0.05, -0.82), 0.028, fg=(1, 0.75, 0.9, 1), align=TextNode.A_right, font=U.FONT_PLAIN, shadow=(0, 0, 0, 1))
        if s is None: t = "AI FRIENDS: %d" % len(self.ai_friends)
        elif s.role == "host":
            pings = [p["ping"] for p in s.peers.values() if p.get("ping") is not None]
            t = "FIREOUT ONLINE HOST  %s\n%d PLAYER%s%s" % (s.code or "...", len(s.peers) + 1, "" if not s.peers else "S",
                                                         ("   PING %d ms" % max(pings)) if pings else "")
        else:
            t = "FIREOUT ONLINE  %s\n%s%s" % (s.code or "", s.status, ("   PING %d ms" % s.ping_ms) if s.ping_ms is not None else "")
        if self.ai_friends and s is not None: t += "\nAI FRIENDS: %d" % len(self.ai_friends)
        self.hud.setText(t)

    # ----------------------------------------------------------------- football glue
    def start_football(self, versus=False, minutes=0.0, home=0, away=1):
        g = self.g; s = self.sess
        if s is not None and s.role == "join":
            g.toast("Only the host can start an online match - ask them to press ONLINE MATCH", 3.0); return
        self.close()
        g.start_match(home_club=home, away_club=away, minutes_real=minutes, online=self if (s is not None and s.peers) else None, versus=versus)
        m = g.match
        if m is not None and m.online is not None:
            for f in m.fps:
                if isinstance(f.human, int):
                    p = s.peers.get(f.human)
                    if p:
                        setup = {"slots": m.slots(), "clubs": [list(c) for c in m.clubs], "secs": m.secs, "you": f.human}
                        for _ in range(3): s.send(p["addr"], {"t": "fb_start", "setup": setup})

    def fb_tick(self, m, dt):
        self._fb_t -= dt
        if self._fb_t <= 0 and self.sess is not None:
            self._fb_t = 1.0 / 15.0; self.sess.broadcast({"t": "fb", "s": m.snapshot()})

    def fb_leave(self):
        s = self.sess
        if s is not None and s.role == "join":
            for _ in range(3): s.to_host({"t": "fb_leave"})

    def _on_fb_leave(self, pid, msg):
        m = getattr(self.g, "match", None)
        if m is None or m.mode != "sim": return
        for f in m.fps:
            if f.human == pid:
                f.human = None; f.inp = {"mv": (0, 0), "sp": False}; f.acts = []; m.banner("%s LEFT - AI TAKES OVER" % f.name, 2.0)

    def fb_end(self, m):
        if self.sess is not None:
            for _ in range(3): self.sess.broadcast({"t": "fb_end"})

    def _on_fb_input(self, pid, msg):
        m = getattr(self.g, "match", None)
        if m is None or m.mode != "sim": return
        for f in m.fps:
            if f.human == pid:
                mv = msg.get("mv") or [0, 0]
                try: f.inp = {"mv": (max(-1, min(1, float(mv[0]))), max(-1, min(1, float(mv[1])))), "sp": bool(msg.get("sp"))}
                except Exception: pass
                a = msg.get("a")
                if a and isinstance(a, list) and len(a) == 2 and a[1] in ("pass", "shoot", "tackle"):
                    if self._fb_last.get(pid, -1) < a[0]: self._fb_last[pid] = a[0]; f.acts.append(a[1])

    def _on_fb_start(self, pid, msg):
        g = self.g
        if getattr(g, "match", None) is not None: return
        self.close(); g.start_match_view(msg.get("setup") or {})

    def _on_fb_snap(self, pid, msg):
        m = getattr(self.g, "match", None)
        if m is not None and m.mode == "view": m.apply_snapshot(msg.get("s") or {})

    def _on_fb_end(self, pid, msg):
        m = getattr(self.g, "match", None)
        if m is not None and m.mode == "view" and not m.done: m.quit()

    def fb_input(self, mv=None, sp=None, act=None):
        s = self.sess
        if s is None: return
        now = time.time()
        if mv is not None: self._mv = (mv, sp)
        if act is not None:
            self.fb_seq += 1; self._act = [self.fb_seq, act]
            for _ in range(2): s.to_host({"t": "fbi", "mv": list(self._mv[0]) if hasattr(self, "_mv") else [0, 0], "sp": bool(self._mv[1]) if hasattr(self, "_mv") else False, "a": self._act})
            return
        if now - getattr(self, "_fbi_t", 0) > 0.05:
            self._fbi_t = now
            s.to_host({"t": "fbi", "mv": [round(v, 2) for v in self._mv[0]], "sp": bool(self._mv[1]), "a": getattr(self, "_act", None)})

    # ----------------------------------------------------------------- UI
    def open(self, view="main"):
        g = self.g
        if getattr(g, "match", None) is not None: return
        if g.phone: g.toggle_phone()
        if g.laptop.ui is not None: g.laptop.close()
        if self.app.pause_ui: self.app.hide_pause()
        if g.overlay is not None and g.overlay is not self.ui: g.close_overlay()
        self.view = view; self.refresh(force=True)

    def close(self):
        self._drop_preview()
        if self.lan is not None: self.lan.close(); self.lan = None
        if self.ui is not None:
            if self.g.overlay is self.ui: self.g.overlay = None
            self.ui.destroy(); self.ui = None
            self.g.refresh_buttons()

    def refresh(self, force=False):
        if self.ui is None and not force: return
        g = self.g
        if self.ui is not None:
            if g.overlay is self.ui: g.overlay = None
            self.ui.destroy()
        self.labels = []
        o = self.ui = DirectFrame(parent=self.app.aspect2d, frameColor=(0, 0, 0, 0.35), frameSize=(-4, 4, -2, 2), state=DGG.NORMAL)
        o.is_online = True; g.overlay = o
        getattr(self, "view_" + self.view, self.view_main)(o)
        g.refresh_buttons()

    def _hdr(self, o, sub, l=-1.05, r=1.05, b=-0.8, t=0.8):
        U.panel(o, l, r, b, t, edge=PINK)
        U.text(o, "FIREOUT ONLINE", ((l + r) / 2, t - 0.11), 0.07, fg=PINK)
        U.text(o, sub, ((l + r) / 2, t - 0.17), 0.03, fg=(0.85, 0.85, 0.95, 1), font=U.FONT_PLAIN)

    def _btn(self, o, lbl, pos, fn, w=0.28, edge=PINK, sc=0.034, h=0.045, hint=None):
        self.labels.append(lbl)
        return U.button(o, lbl, pos, fn, w=w, h=h, scale=sc, edge=edge, hint=hint)

    def view_main(self, o):
        s = self.sess
        self._hdr(o, "Play with friends over the internet  -  no account, no server, just a code")
        pf = self.profile
        U.text(o, "YOU:  %s   (%s hair, %s, %s)" % (pf["name"], pf["hair"], pf["top"], pf["acc"] if pf["acc"] != "none" else "no accessory"),
               (0, 0.5), 0.034, font=U.FONT_PLAIN)
        self._btn(o, "CUSTOMISE CHARACTER", (0, 0.42), lambda: self.goto("custom"), w=0.3, edge=VIOLET)
        y = 0.3
        if s is None:
            self._btn(o, "HOST A SESSION", (-0.36, y), lambda: self.goto("host"), edge=CY_)
            self._btn(o, "JOIN WITH A CODE", (0.36, y), lambda: self.goto("join"), edge=CY_)
        else:
            self._session_box(o, y)
        yb = -0.5
        if self.ai_friends: self._btn(o, "SEND AI FRIENDS HOME", (-0.36, yb), self.send_home, edge=(1, 0.6, 0.3, 1))
        else: self._btn(o, "BRING THEM IN (AI FRIENDS)", (-0.36, yb), self.bring_them_in, edge=(1, 0.6, 0.3, 1))
        self._btn(o, "SHINE SFC 27 FOOTBALL", (0.36, yb), lambda: self.goto("football"), edge=(0.3, 1.0, 0.45, 1))
        if s is not None: self._btn(o, "LEAVE SESSION" if s.role == "join" else "CLOSE SESSION", (-0.36, -0.62), self.leave, edge=(1, 0.3, 0.3, 1))
        self._btn(o, "CLOSE", (0.36 if s is not None else 0, -0.62), self.close, hint="Esc")

    def _session_box(self, o, y):
        s = self.sess; g = self.g
        if s.role == "host":
            code = s.code or "finding your internet address..."
            U.text(o, "JOIN CODE:  %s" % code, (0, y), 0.05, fg=(1, 0.9, 0.3, 1))
            U.text(o, "%s   -   UDP port %d%s" % (s.via or s.status, s.port, "   -   password set" if s.password else ""), (0, y - 0.06), 0.027, fg=(0.8, 0.85, 1, 1), font=U.FONT_PLAIN)
            if s.via and "LAN" in s.via:
                U.text(o, "No internet address found - friends on your Wi-Fi can still join. For the internet, forward UDP %d on your router." % s.port,
                       (0, y - 0.1), 0.024, fg=(1, 0.6, 0.5, 1), font=U.FONT_PLAIN, wrap=70)
            rows = [(0, s.name + " (HOST, YOU)", 0)] + [(pid, p["name"], p.get("ping")) for pid, p in s.peers.items()]
            for k, (pid, nm, ping) in enumerate(rows[:6]):
                yy = y - 0.17 - k * 0.055
                U.text(o, "%s   %s" % (nm, ("%d ms" % ping) if ping is not None else "--"), (-0.3, yy), 0.032, align=TextNode.A_left, font=U.FONT_PLAIN)
                if pid: self._btn(o, "KICK", (0.55, yy + 0.012), lambda pid=pid: self.kick(pid), w=0.08, h=0.03, sc=0.026, edge=(1, 0.3, 0.3, 1))
            self._btn(o, "LET A FRIEND IN (REPLY CODE)", (0, -0.22), lambda: self.goto("letin"), w=0.3, h=0.03, sc=0.026, edge=CY_)
        else:
            U.text(o, "SESSION  %s" % (s.code or ""), (0, y), 0.045, fg=(1, 0.9, 0.3, 1))
            U.text(o, s.status + (("   -   PING %d ms" % s.ping_ms) if s.ping_ms is not None else ""), (0, y - 0.06), 0.028, fg=(0.8, 0.85, 1, 1), font=U.FONT_PLAIN, wrap=60)
            if s.state == "joining":
                rc = s.reply_code()
                U.text(o, "YOUR REPLY CODE:  %s" % (rc or "(finding your address...)"), (0, y - 0.13), 0.034, fg=CY_)
                U.text(o, "Not connected after a few seconds? Send this to the host - they type it into LET A FRIEND IN and you connect.",
                       (0, y - 0.18), 0.024, fg=(0.85, 0.9, 1, 1), font=U.FONT_PLAIN)
                U.text(o, "Last resort only: " + s.forward_hint().lower() + ".", (0, y - 0.22), 0.022, fg=(1, 0.6, 0.5, 1), font=U.FONT_PLAIN)
            else:
                ros = getattr(s, "roster", [])
                for k, e in enumerate(ros[:6]):
                    U.text(o, "%s%s   %s" % (e.get("name"), " (HOST)" if e.get("host") else (" (YOU)" if e.get("id") == s.my_id else ""),
                                            ("%d ms" % e["ping"]) if e.get("ping") is not None else "--"), (-0.3, y - 0.14 - k * 0.05), 0.03, align=TextNode.A_left, font=U.FONT_PLAIN)
        # chat
        ent = DirectEntry(parent=o, initialText="", width=22, numLines=1, scale=0.034, pos=(-0.62, 0, -0.41), frameColor=(0.1, 0.08, 0.15, 1),
                          text_fg=(1, 1, 1, 1), entryFont=U.FONT_PLAIN, command=lambda t: send())
        def send():
            t = ent.get().strip()
            if t and self.sess: self.sess.say(t); ent.enterText("")
        self._btn(o, "SAY", (0.55, -0.395), send, w=0.08, h=0.03, sc=0.026, edge=CY_)
        o.ent = ent
        for k, line in enumerate(self.chat_log[-2:]):
            U.text(o, line[:70], (-0.62, -0.29 - k * 0.04), 0.026, fg=(1, 0.8, 0.95, 1), align=TextNode.A_left, font=U.FONT_PLAIN)

    def goto(self, v): self.view = v; self.refresh()

    def view_host(self, o):
        self._hdr(o, "HOST: your friends join with the code you get - share it any way you like")
        U.text(o, "Optional password (friends type it too):", (0, 0.4), 0.032, font=U.FONT_PLAIN)
        pw = DirectEntry(parent=o, initialText="", width=14, numLines=1, scale=0.045, pos=(-0.32, 0, 0.3), frameColor=(0.1, 0.08, 0.15, 1),
                         text_fg=(1, 1, 1, 1), entryFont=U.FONT_PLAIN, obscured=1); o.ent = pw
        U.text(o, "We ask public STUN servers for your internet address, ask your router (UPnP) to open UDP 47115, and pack\n"
                  "both into a SHINE-XXXX-XXXX code. Same Wi-Fi friends also see you under LAN SESSIONS.", (0, 0.12), 0.026,
               fg=(0.8, 0.85, 1, 1), font=U.FONT_PLAIN)
        self._btn(o, "START HOSTING", (0, -0.1), lambda: (self.host(pw.get().strip()), self.goto("main")), edge=CY_)
        self._btn(o, "BACK", (0, -0.62), lambda: self.goto("main"))

    def view_join(self, o):
        import fs_net as N
        self._hdr(o, "JOIN: type the code your friend sent you")
        U.text(o, "Code:", (-0.62, 0.42), 0.036, align=TextNode.A_left, font=U.FONT_PLAIN)
        ce = DirectEntry(parent=o, initialText="SHINE-", width=17, numLines=1, scale=0.05, pos=(-0.45, 0, 0.42), frameColor=(0.1, 0.08, 0.15, 1),
                         text_fg=(1, 1, 1, 1), entryFont=U.FONT_PLAIN, focus=1); o.ent = ce
        U.text(o, "Password:", (-0.62, 0.3), 0.032, align=TextNode.A_left, font=U.FONT_PLAIN)
        pe = DirectEntry(parent=o, initialText="", width=14, numLines=1, scale=0.04, pos=(-0.4, 0, 0.3), frameColor=(0.1, 0.08, 0.15, 1),
                         text_fg=(1, 1, 1, 1), entryFont=U.FONT_PLAIN, obscured=1)
        def go(addr=None, code=None):
            if self.join(code or ce.get().strip(), pe.get().strip(), addr): self.goto("main")
        self._btn(o, "JOIN", (0, 0.18), go, edge=CY_)
        U.text(o, "LAN SESSIONS (same Wi-Fi):", (0, 0.04), 0.03, fg=CY_, font=U.FONT_PLAIN)
        if self.lan is None: self.lan = N.LanBrowser()
        ss = self.lan.sessions() if self.lan else []
        if not ss: U.text(o, "none found yet - REFRESH in a moment", (0, -0.03), 0.026, fg=(0.7, 0.7, 0.8, 1), font=U.FONT_PLAIN)
        for k, e in enumerate(ss[:4]):
            yy = -0.04 - k * 0.075
            U.text(o, "%s   %d player%s%s" % (e.get("name"), e.get("n", 1), "" if e.get("n", 1) == 1 else "s", "   (password)" if e.get("pw") else ""),
                   (-0.5, yy - 0.01), 0.03, align=TextNode.A_left, font=U.FONT_PLAIN)
            self._btn(o, "JOIN", (0.5, yy), lambda e=e: go(tuple(e["lan_addr"]), e["code"]), w=0.08, h=0.03, sc=0.026, edge=CY_)
        self._btn(o, "REFRESH", (0, -0.4), lambda: self.goto("join"), w=0.12, h=0.03, sc=0.026)
        self._btn(o, "BACK", (0, -0.62), lambda: self.goto("main"))

    def view_letin(self, o):
        self._hdr(o, "LET A FRIEND IN: type the REPLY CODE on your friend's screen - your game calls them, so it gets through")
        ce = DirectEntry(parent=o, initialText="SHINE-", width=17, numLines=1, scale=0.05, pos=(-0.45, 0, 0.3), frameColor=(0.1, 0.08, 0.15, 1),
                         text_fg=(1, 1, 1, 1), entryFont=U.FONT_PLAIN, focus=1); o.ent = ce
        def go():
            if self.sess and self.sess.let_in(ce.get().strip()): self.g.toast("Calling your friend for 90 s...", 3.0); self.goto("main")
            else: self.g.toast("That reply code looks wrong", 2.5)
        self._btn(o, "LET THEM IN", (0, 0.15), go, edge=CY_)
        self._btn(o, "BACK", (0, -0.62), lambda: self.goto("main"))

    # customiser ---------------------------------------------------------------
    def view_custom(self, o):
        self._hdr(o, "Your FIREOUT ONLINE character - friends see you like this", l=-1.6, r=-0.1)
        pf = self.profile
        for k, p in enumerate(A.PRESETS):
            self._btn(o, p["name"], (-1.43 + (k % 4) * 0.25, 0.48 - (k // 4) * 0.08), lambda k=k: self._set(dict(A.preset(k))), w=0.11, h=0.03, sc=0.026, edge=VIOLET)
        U.text(o, "Name:", (-1.5, 0.3), 0.032, align=TextNode.A_left, font=U.FONT_PLAIN)
        ne = DirectEntry(parent=o, initialText=pf["name"], width=10, numLines=1, scale=0.04, pos=(-1.3, 0, 0.3), frameColor=(0.1, 0.08, 0.15, 1),
                         text_fg=(1, 1, 1, 1), entryFont=U.FONT_PLAIN, command=lambda t: self._set(dict(self.profile, name=t))); o.ent = ne
        self._btn(o, "OK", (-0.72, 0.31), lambda: self._set(dict(self.profile, name=ne.get())), w=0.05, h=0.03, sc=0.026)
        rows = [("SKIN", "skin", [n for n, _ in A.SKINS]), ("HAIR", "hair", A.HAIRS), ("HAIR COLOUR", "hair_col", [n for n, _ in A.HAIR_COLS]),
                ("TOP", "top", A.TOPS), ("TOP COLOUR", "top_col", [n for n, _ in A.COLS]), ("BOTTOM COLOUR", "bottom_col", [n for n, _ in A.COLS]),
                ("ACCESSORY", "acc", A.ACCS)]
        for k, (lbl, key, opts) in enumerate(rows):
            yy = 0.18 - k * 0.095; cur = pf[key]; i = cur if isinstance(cur, int) else opts.index(cur)
            U.text(o, lbl, (-1.5, yy - 0.01), 0.03, align=TextNode.A_left, font=U.FONT_PLAIN)
            U.text(o, str(opts[i]).upper(), (-0.62, yy - 0.01), 0.03, fg=(1, 0.9, 0.3, 1), font=U.FONT_PLAIN)
            def cyc(d, key=key, opts=opts):
                cur = self.profile[key]; i = cur if isinstance(cur, int) else opts.index(cur); i = (i + d) % len(opts)
                self._set(dict(self.profile, **{key: i if isinstance(cur, int) else opts[i]}))
            self._btn(o, "<", (-0.86, yy), lambda c=cyc: c(-1), w=0.03, h=0.03, sc=0.03)
            self._btn(o, ">", (-0.38, yy), lambda c=cyc: c(1), w=0.03, h=0.03, sc=0.03)
        self._btn(o, "DONE", (-0.85, -0.62), self._done_custom, edge=VIOLET)
        self._show_preview()

    def _set(self, cfg):
        self.profile = A.clean(cfg); self.refresh()
        if self.sess is not None: self.sess.update_profile(self.profile["name"], self.profile)

    def _done_custom(self):
        self._drop_preview()
        try: self.g.save()
        except Exception: pass
        if self.guest:        # rebuild your own look straight away
            me = self.g.me(); me.cfg = dict(self.profile); me.model.remove_node(); A.Avatar.build_model(me); me.sync()
        self.goto("main")

    def _show_preview(self):
        g = self.g; self._drop_preview(); cam = self.app.camera
        q = cam.get_quat(self.app.render); f = q.get_forward(); r = q.get_right(); p = cam.get_pos(self.app.render)
        x, y = p.x + f.x * 3.4 + r.x * 0.75, p.y + f.y * 3.4 + r.y * 0.75
        h = math.degrees(math.atan2(-(p.x - x), (p.y - y)))
        self.preview = A.Avatar(g, self.profile, x, y, h); self.preview.sync()
        self.preview.np.set_z(g.world.ground_z(x, y) if hasattr(g.world, "ground_z") else 0.0)

    def _drop_preview(self):
        if self.preview is not None: self.preview.destroy(); self.preview = None

    # football menu ---------------------------------------------------------------
    def view_football(self, o):
        import fs_sfc as F
        self._hdr(o, "SHINE SFC 27  -  7-a-side on a full-size pitch at the SHINE SFC 27 STADIUM, Hikari Beach")
        st = getattr(self, "fb", None) or {"home": 0, "away": 1, "min": 0.0}; self.fb = st
        def cyc(key, d):
            st[key] = (st[key] + d) % len(F.CLUBS)
            if st["home"] == st["away"]: st[key] = (st[key] + d) % len(F.CLUBS)
            self.refresh()
        for k, (lbl, key) in enumerate((("YOUR CLUB", "home"), ("OPPONENT", "away"))):
            yy = 0.42 - k * 0.1; c = F.CLUBS[st[key]]
            U.text(o, lbl, (-0.7, yy - 0.01), 0.032, align=TextNode.A_left, font=U.FONT_PLAIN)
            U.text(o, c[0], (0.1, yy - 0.01), 0.034, fg=c[2] + (1,))
            self._btn(o, "<", (-0.25, yy), lambda key=key: cyc(key, -1), w=0.03, h=0.03, sc=0.03)
            self._btn(o, ">", (0.5, yy), lambda key=key: cyc(key, 1), w=0.03, h=0.03, sc=0.03)
        U.text(o, ("MATCH LENGTH  UNLIMITED - the clock counts up, end it any time with END MATCH (Esc)" if not st["min"] else
                   "MATCH LENGTH  %d min (90' on the clock)" % st["min"]) + ("  -  your setting applies to everyone" if self.sess is not None and self.sess.role == "host" else ""),
               (0, 0.2), 0.028, font=U.FONT_PLAIN)
        for k, mn in enumerate((0, 4, 8, 12, 90)):
            self._btn(o, "UNLIMITED" if not mn else "%d MIN" % mn, (-0.52 + k * 0.26, 0.12), lambda mn=mn: (st.__setitem__("min", float(mn)), self.refresh()),
                      w=0.11, h=0.03, sc=0.024, edge=(1, 0.9, 0.3, 1) if st["min"] == mn else PINK)
        go = lambda versus=False: self.start_football(versus, st["min"], st["home"], st["away"])
        self._btn(o, "PLAY VS AI", (0, -0.02), go, edge=(0.3, 1.0, 0.45, 1))
        s = self.sess
        if s is not None and s.role == "host" and s.peers:
            self._btn(o, "ONLINE: ALL OF US VS AI", (-0.36, -0.14), lambda: go(False), edge=CY_)
            self._btn(o, "ONLINE: SPLIT TEAMS", (0.36, -0.14), lambda: go(True), edge=CY_)
        elif s is not None and s.role == "join":
            U.text(o, "Online matches are started by the session host - you'll be pulled in automatically.", (0, -0.14), 0.026, fg=CY_, font=U.FONT_PLAIN)
        else:
            U.text(o, "Host a session first to play ONLINE with friends (AI fills the empty spots).", (0, -0.14), 0.026, fg=CY_, font=U.FONT_PLAIN)
        U.text(o, "WASD move   SPACE pass   F shoot   R tackle   SHIFT sprint  -  or walk / take a JP TAXI to the stadium and press [E]",
               (0, -0.3), 0.024, fg=(0.8, 0.85, 1, 1), font=U.FONT_PLAIN)
        self._btn(o, "BACK", (0, -0.62), lambda: self.goto("main"))

    def destroy(self):
        self.close(); self.leave(quiet=True)
        for f in self.ai_friends: f.destroy()
        self.ai_friends = []
        if self.hud is not None: self.hud.destroy(); self.hud = None
