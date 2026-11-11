"""v1.0.5.4 SEASONAL EVENTS + live feed (FH6-style).
- Seasons rotate AUTOMATICALLY on a shared UTC clock: 7-day weeks aligned to UTC Mondays.
  Index = (ISO year * 53 + ISO week) % 4 -> spring, summer, autumn, winter (same pattern as COKA).
- Each season: a race, a photo challenge, and a drive-to, with yen or paint rewards (game economy).
- Pop-up feed + FESTIVAL phone panel: season name, countdown to next season, events with AVAILABLE/DONE.
- New events load from GitHub without a rebuild (events.json or seasons/events.json on main), cached offline
  under the player data dir with built-in fallbacks.
- Light seasonal look (sakura petals / warm night dust / autumn leaves / snow) + soft world tint. No bloom/glow.
- Settings force_season / env FS_SEASON is a hidden/dev override only (off by default).
©2026 EX ROMANIA/EX INC."""
import json, math, os, random, threading, time, datetime, urllib.request
from panda3d.core import CardMaker, TextNode, TransparencyAttrib, Vec3
from direct.gui.DirectGui import DirectFrame, DGG
import fs_ui as U

REMOTES = (
    "https://raw.githubusercontent.com/Teobokki/fireout-online/main/events.json",
    "https://raw.githubusercontent.com/Teobokki/fireout-online/main/seasons/events.json",
)
SEASONS = ("spring", "summer", "autumn", "winter")
SNAME = {"spring": "SPRING", "summer": "SUMMER", "autumn": "AUTUMN", "winter": "WINTER"}
STITLE = {
    "spring": "SPRING SAKURA",
    "summer": "SUMMER NIGHT RACES",
    "autumn": "AUTUMN DRIFTS",
    "winter": "WINTER RUN",
}
SCOL = {"spring": (1.0, 0.62, 0.78, 1), "summer": (0.35, 0.85, 1.0, 1), "autumn": (1.0, 0.55, 0.18, 1), "winter": (0.80, 0.90, 1.0, 1)}
# soft full-screen tint (RGBA). alpha kept low; never additive / never bloom
TINT = {
    "spring": (0.98, 0.70, 0.82, 0.07),
    "summer": (1.00, 0.55, 0.22, 0.08),   # warm night
    "autumn": (0.95, 0.45, 0.12, 0.09),
    "winter": (0.55, 0.70, 1.00, 0.10),
}
FOG_TINT = {
    "spring": Vec3(0.08, 0.04, 0.08),
    "summer": Vec3(0.10, 0.04, 0.06),
    "autumn": Vec3(0.09, 0.04, 0.03),
    "winter": Vec3(0.05, 0.06, 0.11),
}
ICON = {"race": "R", "photo": "P", "drive": "D", "collect": "C"}

# built-in events (targets snapped to nearest road at runtime). Each season: race + photo + drive-to.
BUILTIN = {
    "spring": {"title": "SPRING SAKURA", "events": [
        {"id": "sp_race", "kind": "race", "title": "PETAL SPRINT", "line": "Reach the beach road in under 75 s", "x": 520, "y": -80, "start": [436, -300], "tlimit": 75, "reward": {"yen": 12000}},
        {"id": "sp_photo", "kind": "photo", "title": "HANAMI PHOTO", "line": "Take a phone photo at the Shinko Tower plaza", "x": 0, "y": 0, "tower": True, "reward": {"paint": "SAKURA PEARL", "col": [0.98, 0.62, 0.74]}},
        {"id": "sp_drive", "kind": "drive", "title": "SAKURA DRIVE", "line": "Drive to Hanami Park under the cherry blossoms", "x": 300, "y": -220, "reward": {"yen": 6000}}]},
    "summer": {"title": "SUMMER NIGHT RACES", "events": [
        {"id": "su_race", "kind": "race", "title": "SUMMER NIGHT RACE", "line": "Downtown to Hikari Beach in under 90 s", "x": 540, "y": -60, "start": [40, -40], "tlimit": 90, "reward": {"yen": 15000}},
        {"id": "su_photo", "kind": "photo", "title": "FIREWORKS PHOTO", "line": "Snap a photo at Hikari Beach", "x": 560, "y": -40, "reward": {"paint": "MATSURI BLUE", "col": [0.05, 0.30, 0.85]}},
        {"id": "su_drive", "kind": "drive", "title": "LANTERN STREET", "line": "Drive to the scramble crossing under the lanterns", "x": 20, "y": 30, "reward": {"yen": 8000}}]},
    "autumn": {"title": "AUTUMN DRIFTS", "events": [
        {"id": "au_race", "kind": "race", "title": "AUTUMN MOMIJI DRIFT", "line": "Hospital to the tower in under 70 s", "x": 0, "y": 0, "tower": True, "start": [-150, 100], "tlimit": 70, "reward": {"yen": 14000}},
        {"id": "au_photo", "kind": "photo", "title": "MOMIJI PHOTO", "line": "Take a photo in the Sakura district under the leaves", "x": 360, "y": -250, "reward": {"paint": "MOMIJI RED", "col": [0.72, 0.10, 0.04]}},
        {"id": "au_drive", "kind": "drive", "title": "MOMIJI DRIVE", "line": "Drive up to the stadium boulevard", "x": 503, "y": 232, "reward": {"yen": 6000}}]},
    "winter": {"title": "WINTER RUN", "events": [
        {"id": "wi_race", "kind": "race", "title": "WINTER SNOW RUN", "line": "Home to the stadium in under 95 s", "x": 503, "y": 232, "start": [436, -300], "tlimit": 95, "reward": {"yen": 16000}},
        {"id": "wi_photo", "kind": "photo", "title": "ILLUMINATION PHOTO", "line": "Take a photo at the Shinko Tower", "x": 0, "y": 0, "tower": True, "reward": {"paint": "FROST WHITE", "col": [0.92, 0.94, 0.98]}},
        {"id": "wi_drive", "kind": "drive", "title": "HOT SPRING TRIP", "line": "Drive to the hospital hill road", "x": -150, "y": 100, "reward": {"yen": 7000}}]},
}


def _utc_now():
    return datetime.datetime.now(datetime.timezone.utc)


def season_window(now=None):
    """(season_id, start_utc, end_utc) for the current 7-day UTC Monday window. Shared by all players."""
    now = now or _utc_now()
    if now.tzinfo is None:
        now = now.replace(tzinfo=datetime.timezone.utc)
    d = now.astimezone(datetime.timezone.utc).date()
    iso = d.isocalendar()
    idx = (iso[0] * 53 + iso[1]) % 4
    start_d = d - datetime.timedelta(days=d.weekday())
    end_d = start_d + datetime.timedelta(days=7)
    start = datetime.datetime(start_d.year, start_d.month, start_d.day, tzinfo=datetime.timezone.utc)
    end = datetime.datetime(end_d.year, end_d.month, end_d.day, tzinfo=datetime.timezone.utc)
    return SEASONS[idx], start, end


def resolve(settings=None, now=None):
    """Active season. Auto UTC rotation is the default; force_season / FS_SEASON is a hidden/dev override."""
    force = ""
    if settings:
        force = (settings.get("force_season") or "").strip().lower()
    env = (os.environ.get("FS_SEASON") or "").strip().lower()
    s, s0, s1 = season_window(now)
    if force in SEASONS:
        return force, s0, s1, True
    if env in SEASONS:
        return env, s0, s1, True
    return s, s0, s1, False


def countdown(end, now=None):
    now = now or _utc_now()
    if now.tzinfo is None:
        now = now.replace(tzinfo=datetime.timezone.utc)
    left = max(0, int((end - now).total_seconds()))
    d, rem = divmod(left, 86400); h, rem = divmod(rem, 3600); m = rem // 60
    if d > 0:
        return "%dd %02dh %02dm" % (d, h, m), left
    return "%02dh %02dm" % (h, m), left


def next_name(cur):
    return SNAME[SEASONS[(SEASONS.index(cur) + 1) % 4]]


def valid(data):
    try:
        for s in SEASONS:
            ev = data[s]["events"]
            if not (1 <= len(ev) <= 6): return False
            for e in ev:
                if e["kind"] not in ICON or not isinstance(e["title"], str) or not isinstance(e["reward"], dict): return False
                float(e["x"]); float(e["y"])
        return True
    except Exception:
        return False


def _cache_path():
    try:
        import fireout_online as FS
        return os.path.join(FS.DATA, "events_cache.json")
    except Exception:
        return os.path.join(os.path.expanduser("~"), ".fireout-online", "events_cache.json")


def load_cached():
    try:
        d = json.load(open(_cache_path(), encoding="utf-8"))
        if valid(d): return d
    except Exception:
        pass
    return None


def save_cache(data):
    try:
        p = _cache_path(); os.makedirs(os.path.dirname(p), exist_ok=True)
        json.dump(data, open(p, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    except Exception:
        pass


class Feed:
    """sliding notification cards (left column under portraits)."""
    def __init__(self, g):
        self.g = g; self.cards = []; self.queue = []
        self.root = DirectFrame(parent=g.app.a2dTopLeft, frameColor=(0, 0, 0, 0), pos=(0, 0, 0))

    def push(self, title, line="", reward="", icon="!", col=(1, 1, 1, 1), small=False):
        self.queue.append((title, line, reward, icon, col, small))

    def _make(self, title, line, reward, icon, col, small):
        h = 0.065 if small else 0.115; w = 0.58
        outer = DirectFrame(parent=self.root, frameColor=(0, 0, 0, 0), relief=DGG.FLAT)
        f = DirectFrame(parent=outer, frameColor=(0.04, 0.04, 0.06, 0.88), frameSize=(-w, 0, -h, 0), relief=DGG.FLAT); f.set_x(w)
        DirectFrame(parent=f, frameColor=col, frameSize=(-w, -w + 0.012, -h, 0), relief=DGG.FLAT)
        DirectFrame(parent=f, frameColor=(col[0] * 0.35, col[1] * 0.35, col[2] * 0.35, 1), frameSize=(-w + 0.03, -w + 0.03 + h - 0.03, -h + 0.015, -0.015), relief=DGG.FLAT)
        U.text(f, icon, (-w + 0.015 + h / 2, -h / 2 - 0.018), 0.05 if not small else 0.032, fg=col)
        x0 = -w + h + 0.03
        U.text(f, title, (x0, -0.042 if not small else -0.04), 0.034 if not small else 0.028, fg=col, align=TextNode.A_left)
        if line and not small: U.text(f, line, (x0, -0.072), 0.024, font=U.FONT_PLAIN, align=TextNode.A_left, wrap=19)
        if reward: U.text(f, reward, (-0.02, -0.042 if not small else -0.04), 0.026, fg=U.GOLD, align=TextNode.A_right, font=U.FONT_PLAIN)
        return {"f": outer, "h": h, "t": 0.0, "dur": 3.2 if small else 5.5, "x": -0.7}

    def update(self, dt):
        if self.queue and len(self.cards) < 4:
            self.cards.append(self._make(*self.queue.pop(0)))
        y = -0.42
        for c in list(self.cards):
            c["t"] += dt
            tgt = 0.03 if c["t"] < c["dur"] else -0.75
            c["x"] += (tgt - c["x"]) * min(1.0, dt * 9.0)
            c["f"].set_pos(c["x"], 0, y); y -= c["h"] + 0.015
            if c["t"] > c["dur"] + 0.6:
                c["f"].destroy(); self.cards.remove(c)

    def destroy(self):
        self.root.destroy()


class Particles:
    """light seasonal look around the camera. alpha-blended, never additive / never bloom."""
    def __init__(self, g, season):
        self.g = g; app = g.app; self.np = app.render.attach_new_node("season-fx"); self.parts = []
        col = {
            "spring": (1.0, 0.72, 0.82, 0.9),
            "summer": (1.0, 0.70, 0.30, 0.75),   # warm night dust / lantern glow motes
            "autumn": (0.85, 0.32, 0.08, 0.95),
            "winter": (0.95, 0.97, 1.0, 0.85),
        }.get(season)
        if col is None: return
        tex = self.shape_tex(season)
        cm = CardMaker("p"); s = 0.028 if season == "summer" else (0.035 if season == "winter" else 0.05); cm.set_frame(-s, s, -s, s)
        n = 55 if season == "summer" else 70
        for _ in range(n):
            q = self.np.attach_new_node(cm.generate()); q.set_texture(tex)
            q.set_color(col[0] * random.uniform(0.8, 1.0), col[1] * random.uniform(0.8, 1.0), col[2], col[3] * random.uniform(0.5, 0.9))
            q.set_two_sided(True); self.parts.append([q, random.uniform(-18, 18), random.uniform(-18, 18), random.uniform(0, 14), random.uniform(0, 6.28), random.uniform(0.6, 1.4)])
        self.np.set_transparency(TransparencyAttrib.M_alpha); self.np.set_light_off(); self.np.set_shader_off(1)
        self.np.set_depth_write(False); self.np.set_bin("fixed", 40)
        self.fall = 0.35 if season == "summer" else (1.6 if season == "winter" else 0.9)
        self.season = season

    @staticmethod
    def shape_tex(season, n=64):
        from panda3d.core import PNMImage, Texture
        im = PNMImage(n, n, 4); im.fill(1, 1, 1); im.alpha_fill(0)
        for j in range(n):
            for i in range(n):
                u, v = (i + 0.5) / n * 2 - 1, (j + 0.5) / n * 2 - 1
                if season in ("winter", "summer"):
                    d = math.hypot(u, v); a = max(0.0, 1 - d) ** (1.2 if season == "summer" else 1.5)
                else:
                    w = 0.5 * (1 - v * v) * (0.75 if season == "autumn" else 1.0)
                    if season == "spring" and v > 0.75: w *= max(0.0, 1 - 6 * (0.06 - abs(u)) if abs(u) < 0.06 else 1)
                    d = abs(u) / max(w, 1e-3); a = max(0.0, min(1.0, (1 - d) * 6)) if abs(v) < 1 else 0
                    if season == "autumn" and abs(u) < 0.03: a *= 0.6
                im.set_alpha(i, j, a)
        t = Texture("season-shape"); t.load(im); t.set_wrap_u(Texture.WM_clamp); t.set_wrap_v(Texture.WM_clamp)
        t.set_minfilter(Texture.FT_linear_mipmap_linear); return t

    def update(self, dt, t):
        if not self.parts: return
        cam = self.g.app.camera.get_pos(self.g.app.render)
        for p in self.parts:
            q, x, y, z, ph, sp = p
            z -= dt * self.fall * sp; ph += dt * (2.4 if self.season == "summer" else 1.7)
            if z < -1.5: z = 14.0; x = random.uniform(-20, 20); y = random.uniform(-20, 20)
            p[3] = z; p[4] = ph
            q.set_pos(cam[0] + x + math.sin(ph) * 0.6, cam[1] + y + math.cos(ph * 0.7) * 0.5, max(0.05, cam[2] - 3 + z))
            q.set_hpr(ph * 60, ph * 40, ph * 25)

    def destroy(self):
        self.np.remove_node()


class Events:
    def __init__(self, g, saved=None):
        self.g = g
        cached = load_cached()
        self.data = cached if cached is not None else BUILTIN
        self.source = "cache" if cached is not None else "built-in"
        self.done = dict(saved.get("done", {})) if isinstance(saved, dict) else {}
        self.paints = list(saved.get("paints", [])) if isinstance(saved, dict) else []
        self.feed = Feed(g); self.active = None; self.tokens = []; self.mk = g.app.render.attach_new_node("event-markers")
        self.forced = False; self._fog_base = None; self._tint = None; self._cd_card = None; self._cd_txt = None
        self.chain = 0; self.chain_t = 0.0; self._drift_t = 0.0; self._remote = None; self._last_cd = -1
        self.apply_season(announce=True)
        self._make_countdown()
        threading.Thread(target=self._fetch, daemon=True).start()

    # ---------------------------------------------------------------- season (auto UTC; force is hidden/dev)
    def apply_season(self, announce=False):
        settings = getattr(self.g.app, "settings", {}) or {}
        s, s0, s1, forced = resolve(settings)
        prev = getattr(self, "season", None)
        self.season, self.s0, self.s1, self.forced = s, s0, s1, forced
        if getattr(self, "fx", None) is not None:
            try: self.fx.destroy()
            except Exception: pass
        self.fx = Particles(self.g, s)
        self._apply_tint(s)
        self.build_markers()
        if announce or prev != s:
            title = self.data.get(s, {}).get("title") or STITLE[s]
            tag = " (DEV)" if forced else ""
            self.feed.push("Season: %s%s" % (SNAME[s], tag), title + " is live", "", "*", SCOL[s])
            for e in self.events():
                if not self.is_done(e):
                    self.feed.push(e["title"], e["line"], self.reward_txt(e), ICON[e["kind"]], SCOL[s]); break
            left_s, _ = countdown(s1)
            self.feed.push("Next season in " + left_s, "%s up next" % next_name(s), "", ">", SCOL[s], small=True)

    def reapply_from_settings(self):
        """Called when Settings force_season (dev) changes. Auto season also re-checks here."""
        settings = getattr(self.g.app, "settings", {}) or {}
        s, s0, s1, forced = resolve(settings)
        if s != self.season or forced != self.forced:
            self.apply_season(announce=True)

    def _apply_tint(self, s):
        app = self.g.app
        if self._tint is not None:
            try: self._tint.destroy()
            except Exception: pass
            self._tint = None
        col = TINT[s]
        self._tint = DirectFrame(parent=app.render2d, frameColor=col, frameSize=(-2, 2, -2, 2), relief=DGG.FLAT)
        self._tint.set_transparency(TransparencyAttrib.M_alpha); self._tint.set_bin("fixed", 60)
        # nudge fog toward the season (restore previous base once)
        if self._fog_base is None:
            try: self._fog_base = Vec3(app.fogcol)
            except Exception: self._fog_base = Vec3(0.05, 0.03, 0.09)
        try:
            base = self._fog_base; tint = FOG_TINT[s]
            app.fogcol = Vec3(base[0] * 0.55 + tint[0] * 0.45, base[1] * 0.55 + tint[1] * 0.45, base[2] * 0.55 + tint[2] * 0.45)
            app.fog.set_color(app.fogcol)
        except Exception:
            pass

    def _make_countdown(self):
        """Always-on tiny countdown under the feed so the auto season clock is visible."""
        if self._cd_card is not None:
            try: self._cd_card.destroy()
            except Exception: pass
        self._cd_card = DirectFrame(parent=self.g.app.a2dTopLeft, frameColor=(0.04, 0.04, 0.06, 0.75),
                                    frameSize=(0.03, 0.55, -0.38, -0.33), relief=DGG.FLAT)
        self._cd_txt = U.text(self._cd_card, "", (0.29, -0.365), 0.022, font=U.FONT_PLAIN, fg=(1, 1, 1, 0.85))
        self._refresh_countdown(force=True)

    def _refresh_countdown(self, force=False):
        txt, left = countdown(self.s1)
        # refresh text about once a minute (or on force)
        bucket = left // 60
        if not force and bucket == self._last_cd: return
        self._last_cd = bucket
        label = "%s  ·  %s left" % (SNAME[self.season], txt)
        if self.forced: label += "  [DEV]"
        try: self._cd_txt.setText(label)
        except Exception: pass
        try:
            col = SCOL[self.season]
            self._cd_card["frameColor"] = (col[0] * 0.15, col[1] * 0.15, col[2] * 0.15, 0.8)
        except Exception: pass

    # ---------------------------------------------------------------- data
    def _fetch(self):
        for url in REMOTES:
            try:
                req = urllib.request.Request(url + "?t=%d" % int(time.time() // 600), headers={"User-Agent": "FIREOUT-ONLINE"})
                d = json.loads(urllib.request.urlopen(req, timeout=6).read().decode("utf-8"))
                if valid(d):
                    self._remote = d; save_cache(d); return
            except Exception:
                continue

    def events(self):
        return self.data[self.season]["events"]

    def key(self, e):
        return "%s:%s" % (self.s0.strftime("%Y%m%d"), e["id"])

    def is_done(self, e):
        return bool(self.done.get(self.key(e)))

    @staticmethod
    def reward_txt(e):
        r = e["reward"]
        if "yen" in r: return "\u00a5%s" % format(int(r["yen"]), ",")
        if "paint" in r: return "PAINT: %s" % r.get("paint", "NEW")
        return "REWARD"

    def target(self, e):
        x, y = float(e["x"]), float(e["y"])
        if e.get("tower"):
            try:
                tx, ty, _ = self.g.world.tower_top; x, y = tx, ty - 26
            except Exception: pass
        try:
            rx, ry = self.g.world.nearest_road_point(x, y)[:2]; return rx, ry
        except Exception:
            return x, y

    # ---------------------------------------------------------------- markers
    def build_markers(self):
        for ch in self.mk.get_children(): ch.remove_node()
        self.tokens = []
        for e in self.events():
            if self.is_done(e): continue
            x, y = self.target(e) if e["kind"] != "race" else self._road(*e["start"])
            n = self.mk.attach_new_node("ev"); n.set_pos(x, y, 0.06)
            col = SCOL[self.season]
            seg = 40
            from panda3d.core import GeomVertexFormat, GeomVertexData, GeomVertexWriter, GeomTriangles, Geom, GeomNode
            vd = GeomVertexData("r", GeomVertexFormat.get_v3c4(), Geom.UH_static); vw = GeomVertexWriter(vd, "vertex"); cw = GeomVertexWriter(vd, "color")
            tri = GeomTriangles(Geom.UH_static)
            for k in range(seg + 1):
                a = k / seg * 6.2832
                for rr in (4.6, 5.4):
                    vw.add_data3(math.cos(a) * rr, math.sin(a) * rr, 0); cw.add_data4(col[0], col[1], col[2], 0.85)
                if k < seg:
                    i = k * 2; tri.add_vertices(i, i + 1, i + 3); tri.add_vertices(i, i + 3, i + 2)
            gm = Geom(vd); gm.add_primitive(tri); gn = GeomNode("ring"); gn.add_geom(gm); n.attach_new_node(gn)
            tn = TextNode("lbl"); tn.set_text("%s  [%s]" % (e["title"], self.reward_txt(e))); tn.set_align(TextNode.A_center)
            if U.FONT: tn.set_font(U.FONT)
            tn.set_text_color(col); tn.set_shadow(0.05, 0.05); tn.set_shadow_color(0, 0, 0, 0.8)
            t = n.attach_new_node(tn); t.set_z(4.2); t.set_scale(1.1); t.set_billboard_point_eye()
            e["_np"] = n
        self.mk.set_transparency(TransparencyAttrib.M_alpha); self.mk.set_light_off(); self.mk.set_shader_off(1); self.mk.set_two_sided(True)
        self.mk.set_depth_offset(2)

    def _road(self, x, y):
        try: return self.g.world.nearest_road_point(x, y)[:2]
        except Exception: return x, y

    def map_points(self):
        out = []
        for e in self.events():
            if self.is_done(e): continue
            x, y = self.target(e) if e["kind"] != "race" else self._road(*e["start"])
            out.append((x, y, SCOL[self.season], ICON[e["kind"]]))
        return out

    # ---------------------------------------------------------------- progress
    def complete(self, e):
        if self.is_done(e): return
        self.done[self.key(e)] = True; g = self.g; r = e["reward"]
        if "yen" in r:
            try: g.add_cash(int(r["yen"]))
            except Exception: g.cash = g.cash + int(r["yen"])
        else:
            nm = r.get("paint", "EVENT PAINT"); col = tuple(r.get("col", (1, 1, 1)))[:3]
            if nm not in [p[0] for p in self.paints]: self.paints.append([nm, list(col)])
            self.feed.push("New paint unlocked", nm + " (FRGARAGE)", "", "+", (1, 1, 1, 1), small=True)
        self.feed.push("Event completed", e["title"], self.reward_txt(e), "\u2713", U.GOLD)
        g.app.sfx("checkpoint", 0.6)
        if "_np" in e: e["_np"].remove_node(); del e["_np"]
        for t in self.tokens: t.remove_node()
        self.tokens = []; self.active = None
        if all(self.is_done(x) for x in self.events()):
            self.feed.push("Season complete!", SNAME[self.season] + " festival finished", "", "*", SCOL[self.season])
        try: g.save()
        except Exception: pass

    def notify(self, title, line="", small=True):
        self.feed.push(title, line, "", "!", (1, 1, 1, 1), small=small)

    def update(self, dt):
        g = self.g
        self.feed.update(dt); self.fx.update(dt, g.time); self._refresh_countdown()
        if getattr(self, "_remote", None) is not None:
            d = self._remote; self._remote = None
            if json.dumps(d, sort_keys=True) != json.dumps(self.data, sort_keys=True, default=str):
                self.data = d; self.source = "online"; self.build_markers()
                self.notify("Festival updated", "New seasonal events from HQ")
        # auto-rotate when the UTC week rolls (or when a hidden force override is cleared)
        s, s0, s1, forced = resolve(getattr(g.app, "settings", {}) or {})
        if s != self.season or forced != self.forced:
            self.season, self.s0, self.s1, self.forced = s, s0, s1, forced
            self.apply_season(announce=True)
        if g.blocked() and not getattr(g, "camapp", None): return
        px, py = g.player_pos(); c = g.pcar
        if c is not None and c.drift > 7 and c.speed > 12:
            self._drift_t += dt
            if self._drift_t > 1.2:
                self._drift_t = 0.0; self.chain += 1; self.chain_t = 3.0
                if self.chain >= 2: self.feed.push("Skill chain x%d" % self.chain, "", "+%d" % (self.chain * 50), "~", U.PINK, small=True)
        else:
            self._drift_t = 0.0
        self.chain_t -= dt
        if self.chain_t <= 0: self.chain = 0
        for e in self.events():
            if self.is_done(e): continue
            k = e["kind"]
            if k == "race":
                sx, sy = self._road(*e["start"])
                if self.active is None and c is not None and math.hypot(px - sx, py - sy) < 6:
                    self.active = {"e": e, "t": float(e.get("tlimit", 90))}
                    self.feed.push(e["title"], "GO! Reach the finish in %d s" % int(e.get("tlimit", 90)), "", "R", SCOL[self.season])
                    g.waypoint = self.target(e)
            elif k == "drive" and c is not None:
                tx, ty = self.target(e)
                if math.hypot(px - tx, py - ty) < 7: self.complete(e); return
            elif k == "photo":
                tx, ty = self.target(e)
                if getattr(g, "camapp", None) and math.hypot(px - tx, py - ty) < 14 and getattr(g, "_ev_photo", 0) > 0:
                    self.complete(e); return
            elif k == "collect":
                tx, ty = self.target(e)
                if not self.tokens and math.hypot(px - tx, py - ty) < 90 and (self.active is None or self.active["e"] is e):
                    self.spawn_tokens(e, tx, ty); self.active = {"e": e, "t": None, "got": 0}
                for t in list(self.tokens):
                    q = t.get_pos(g.app.render)
                    t.set_h(g.time * 90 % 360)
                    if math.hypot(px - q[0], py - q[1]) < 3.0:
                        t.remove_node(); self.tokens.remove(t); self.active["got"] += 1
                        self.feed.push("%s %d/%d" % (e["title"], self.active["got"], e.get("n", 5)), "", "", "C", SCOL[self.season], small=True)
                        if not self.tokens: self.complete(e); return
        g._ev_photo = 0
        a = self.active
        if a is not None and a.get("t") is not None:
            a["t"] -= dt; e = a["e"]; tx, ty = self.target(e)
            g.big.setText("%d" % max(0, math.ceil(a["t"]))) if a["t"] < 10 else None
            if c is not None and math.hypot(px - tx, py - ty) < 8:
                g.big.setText(""); self.complete(e)
            elif a["t"] <= 0:
                g.big.setText(""); self.active = None; self.feed.push("Event failed", e["title"] + " - try again", "", "x", (1, 0.4, 0.4, 1), small=True)

    def spawn_tokens(self, e, tx, ty):
        col = SCOL[self.season]; n = int(e.get("n", 5))
        cm = CardMaker("tok"); cm.set_frame(-0.6, 0.6, -0.6, 0.6)
        for k in range(n):
            a = k / n * 6.2832 + 0.4; r = 18 + 10 * (k % 2)
            x, y = self._road(tx + math.cos(a) * r, ty + math.sin(a) * r)
            q = self.mk.attach_new_node(cm.generate()); q.set_pos(x, y, 1.3); q.set_color(col[0], col[1], col[2], 0.95); q.set_two_sided(True)
            self.tokens.append(q)

    def photo_taken(self):
        self.g._ev_photo = 1.0

    def save(self):
        keep = {k: v for k, v in self.done.items() if k[:8] >= (self.s0 - datetime.timedelta(days=35)).strftime("%Y%m%d")}
        return {"done": keep, "paints": self.paints}

    # ---------------------------------------------------------------- phone page
    def page(self, root, cx, top, btn, W):
        s = self.season; col = SCOL[s]
        title = self.data.get(s, {}).get("title") or STITLE[s]
        W("FESTIVAL", 0.29, 0.05, fg=col, font=U.FONT)
        W("Season: %s  -  %s" % (SNAME[s], title), 0.345, 0.024, fg=col)
        txt, left = countdown(self.s1)
        done = sum(1 for e in self.events() if self.is_done(e)); n = len(self.events())
        bw = 0.22
        DirectFrame(parent=root, frameColor=(0.2, 0.2, 0.25, 1), frameSize=(cx - bw, cx + bw, top - 0.395, top - 0.38), relief=DGG.FLAT)
        DirectFrame(parent=root, frameColor=col, frameSize=(cx - bw, cx - bw + 2 * bw * done / max(1, n), top - 0.395, top - 0.38), relief=DGG.FLAT)
        W("%d/%d events   next (%s) in %s" % (done, n, next_name(s), txt), 0.425, 0.021)
        y = 0.47
        for e in self.events():
            st = "DONE" if self.is_done(e) else ("AVAILABLE  ·  " + self.reward_txt(e))
            W("[%s] %s  -  %s" % (ICON[e["kind"]], e["title"], st), y, 0.022, fg=(0.6, 0.6, 0.6, 1) if self.is_done(e) else (1, 1, 1, 1))
            W(e["line"], y + 0.03, 0.017, wrap=22)
            if not self.is_done(e):
                tgt = self.target(e) if e["kind"] != "race" else self._road(*e["start"])
                btn("GO", (lambda t=tgt: (setattr(self.g, "waypoint", t), self.g.toast("Waypoint set"))), y + 0.065, w=0.05)
            y += 0.115
        src = self.source + ("  ·  DEV override" if self.forced else "  ·  UTC auto")
        W("events: %s" % src, 0.8, 0.016, fg=(1, 1, 1, 0.5))

    def destroy(self):
        self.feed.destroy(); self.fx.destroy(); self.mk.remove_node()
        if self._tint is not None:
            try: self._tint.destroy()
            except Exception: pass
        if self._cd_card is not None:
            try: self._cd_card.destroy()
            except Exception: pass
        if self._fog_base is not None:
            try:
                self.g.app.fogcol = Vec3(self._fog_base); self.g.app.fog.set_color(self.g.app.fogcol)
            except Exception: pass
