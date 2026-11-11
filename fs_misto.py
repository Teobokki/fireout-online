"""FIREOUT ONLINE v1.0.4 - MISTO 2: a parody disappearing-photo messenger (original design: a mist swirl with a '2',
lavender -> mint colours). Opens straight into the phone camera (selfie + SELMOTES), lenses / frames, captions, send a snap
to contacts (it disappears after a few seconds), canned replies in Japanese with English underneath, a streak and STORIES."""
import os, time, random, shutil
from panda3d.core import Filename, PNMImage, PNMTextMaker, TextNode, TransparencyAttrib
from direct.gui.DirectGui import DirectFrame, DirectButton, DirectEntry, DGG
from direct.gui.OnscreenImage import OnscreenImage
import fs_ui as U

LAV = (0.62, 0.48, 1.0, 1); MINT = (0.3, 0.92, 0.82, 1); INK = (0.08, 0.05, 0.16, 0.96)
LENSES = [("none", "NONE"), ("sparkle", "SPARKLES"), ("cat", "CAT EARS"), ("shades", "SHADES"), ("frame_fs", "FIREOUT FRAME"), ("frame_tokyo", "TOKYO FRAME")]
CONTACTS = [("ana", "ANA", "アナ"), ("daniel", "DANIEL", "ダニエル"), ("nana", "NANA", "ナナ"), ("kenji", "KENJI", "ケンジ"),
            ("honoo", "HONOO RAMEN", "炎ラーメン")]
REPLIES = [("ramen", "見て！今日のラーメン最高！", "Look! Today's ramen is the best!"), ("beach", "ビーチの夕日、きれいでしょ？", "Beach sunset - pretty, right?"),
           ("neon", "今夜の新光、めっちゃ明るい！", "Shinko is so bright tonight!"), ("site", "現場から一枚！", "One from the building site!"),
           (None, "いい写真！笑った！", "Great snap! Made me laugh!"), (None, "それどこ？今度連れてって！", "Where's that? Take me next time!")]


def T(app, n): return Filename.from_os_specific(os.path.join(app.BASE, "assets", "tex", n)).get_fullpath()


def data(g):
    m = getattr(g, "misto", None)
    if not isinstance(m, dict): m = g.misto = {}
    m.setdefault("streak", 0); m.setdefault("last", ""); m.setdefault("stories", []); m.setdefault("chats", {})
    return m


def snap_dir(g):
    d = os.path.join(os.path.dirname(g.app.save_path()), "misto2"); os.makedirs(d, exist_ok=True); return d


FACE_LENS = ("cat", "shades")
ANCHOR = (640.0, 262.0); HEAD_PX = 300.0          # where the face sits in the 1280x720 lens art, and its width there


def face_xform(g):
    """screen position (fractions of width / height, y down) and scale of the active character's face, so face lenses
    (cat ears, shades) track the face instead of sitting at a fixed spot"""
    from panda3d.core import Point3, Point2
    a = g.app; me = g.me(); cam = a.camera; lens = a.camLens
    base = me.np.get_pos(a.render); z = base.z + (1.60 if me.who == "daniel" else 1.55)
    def proj(p):
        q = cam.get_relative_point(a.render, p); s2 = Point2()
        return (s2.x, s2.y) if lens.project(q, s2) else None
    c = proj(Point3(base.x, base.y, z)); right = cam.get_quat(a.render).get_right()
    e = proj(Point3(base.x, base.y, z) + right * 0.09)
    if c is None or e is None: return 0.5, 0.36, 1.0
    fx, fy = (c[0] + 1) / 2, (1 - c[1]) / 2
    wpx = abs(e[0] - c[0]) / 2 * 1280.0 * 2          # head width (0.18 m) in 1280-wide pixels
    return fx, fy, max(0.25, min(4.0, wpx / HEAD_PX))


def compose(g, path, lens, caption, fx=None):
    """burn the lens / frame and the caption into the snap PNG"""
    img = PNMImage()
    if not img.read(Filename.from_os_specific(path)): return
    if lens and lens != "none":
        ov = PNMImage()
        if ov.read(Filename.from_os_specific(os.path.join(g.app.BASE, "assets", "tex", "misto_%s.png" % lens))):
            W, H = img.get_x_size(), img.get_y_size()
            if not img.has_alpha(): img.add_alpha(); img.alpha_fill(1.0)
            if lens in FACE_LENS and fx is not None:
                cx, cy, s = fx; k = W / 1280.0 * s
                sw, sh = max(2, int(1280 * k)), max(2, int(720 * k))
                sc = PNMImage(sw, sh, 4); sc.quick_filter_from(ov)
                x0 = int(cx * W - ANCHOR[0] * k); y0 = int(cy * H - ANCHOR[1] * k)
                xf, yf = max(0, -x0), max(0, -y0)
                img.blend_sub_image(sc, max(0, x0), max(0, y0), xf, yf, min(sw - xf, W - max(0, x0)), min(sh - yf, H - max(0, y0)))
            else:
                sc = PNMImage(W, H, 4); sc.quick_filter_from(ov); img.blend_sub_image(sc, 0, 0, 0, 0)
    if caption:
        try:
            jp = any(ord(c) > 0x2000 for c in caption)
            tm = PNMTextMaker(Filename.from_os_specific(os.path.join(g.app.BASE, "assets", "jp_font.otf" if jp else "ui_plain.ttf")), 0)
            tm.set_pixel_size(int(img.get_y_size() * 0.055)); tm.set_align(TextNode.A_center); tm.set_fg((1, 1, 1, 1))
            y = int(img.get_y_size() * 0.66); h = int(img.get_y_size() * 0.09)
            for yy in range(y - h // 2 - h // 3, y + h // 2 - h // 6):
                for xx in range(img.get_x_size()):
                    c = img.get_xel(xx, yy); img.set_xel(xx, yy, c[0] * 0.35, c[1] * 0.35, c[2] * 0.35)
            tm.generate_into(caption, img, img.get_x_size() // 2, y)
        except Exception as e: print("caption failed", e)
    img.write(Filename.from_os_specific(path))


# ---------------------------------------------------------------- phone app: camera with lenses + caption
def open_app(g):
    g.open_camera(misto=True)


def cam_extras(g, o):
    """drawn by cam_ui when the camera runs as MISTO 2"""
    ca = g.camapp; a = g.app; ar = a.getAspectRatio(); m = data(g)
    if ca.get("lens_np"): ca["lens_np"].destroy(); ca["lens_np"] = None
    lens = ca.get("lens", "none")
    if lens != "none":
        ln = ca["lens_np"] = OnscreenImage(parent=a.render2d, image=T(a, "misto_%s.png" % lens), scale=(1, 1, 1)); ln.set_transparency(TransparencyAttrib.M_alpha)
        ln.set_bin("gui-popup", 45); ln.face = lens in FACE_LENS
        track_lens(g)
    hd = DirectFrame(parent=o, frameColor=INK, frameSize=(-0.62, 0.62, -0.06, 0.06), pos=(0, 0, 0.9))
    OnscreenImage(parent=hd, image=T(a, "ix_icon_misto2.png"), pos=(-0.55, 0, 0), scale=0.05).set_transparency(TransparencyAttrib.M_alpha)
    U.text(hd, "MISTO 2", (-0.3, -0.018), 0.05, fg=LAV); U.text(hd, "ミスト2", (-0.06, -0.016), 0.034, fg=MINT, font=a.jpfont)
    OnscreenImage(parent=hd, image=T(a, "ix_flame.png"), pos=(0.36, 0, 0), scale=0.035).set_transparency(TransparencyAttrib.M_alpha)
    U.text(hd, "%d" % m["streak"], (0.43, -0.018), 0.045, fg=(1, 0.65, 0.2, 1), align=TextNode.A_left)
    U.button(o, "CHATS", (ar - 0.2, 0.9), lambda: (g.close_camera(), MistoUI(g, "chats")), w=0.11, h=0.035, scale=0.026, edge=MINT)
    U.button(o, "STORIES", (ar - 0.2, 0.81), lambda: (g.close_camera(), MistoUI(g, "stories")), w=0.11, h=0.035, scale=0.026, edge=LAV)
    # lens strip (right side)
    U.text(o, "LENSES", (ar - 0.2, 0.62), 0.034, fg=MINT)
    for k, (lid, nm) in enumerate(LENSES):
        on = lid == lens
        U.button(o, nm, (ar - 0.2, 0.54 - k * 0.1), set_lens, w=0.14, h=0.038, scale=0.024, extra=[g, lid], edge=MINT if on else (0.45, 0.4, 0.6, 1),
                 col=(0.25, 0.15, 0.45, 0.95) if on else (0.08, 0.05, 0.16, 0.85))
    U.text(o, "CAPTION", (-ar + 0.32, 0.62), 0.03, fg=LAV)
    ent = ca["cap_ent"] = DirectEntry(parent=o, initialText=ca.get("caption", ""), scale=0.034, width=12, pos=(-ar + 0.08, 0, 0.53), frameColor=(1, 1, 1, 0.9),
                                      text_fg=(0.1, 0.05, 0.2, 1), entryFont=U.FONT_PLAIN, focus=0, command=lambda t: ca.__setitem__("caption", t),
                                      focusOutCommand=lambda: ca.__setitem__("caption", ent.get()))
    o.misto = True


def track_lens(g):
    """keep a face lens on the face in the viewfinder (called every frame by the camera app)"""
    ca = g.camapp
    ln = ca.get("lens_np") if ca else None
    if ln is None or not getattr(ln, "face", False): return
    fx, fy, s = face_xform(g)
    sx, sy = fx * 1280 + (640 - ANCHOR[0]) * s, fy * 720 + (360 - ANCHOR[1]) * s
    ln.set_pos(sx / 640.0 - 1, 0, 1 - sy / 360.0); ln.set_scale(s, 1, s)


def set_lens(g, lid):
    ca = g.camapp
    if not ca: return
    if ca.get("cap_ent"): ca["caption"] = ca["cap_ent"].get()
    ca["lens"] = lid; g.cam_ui(); g.app.sfx("click", 0.5)


def after_shot(g, path):
    """the camera saved the raw snap into the MISTO 2 folder: burn lens + caption, then show the snap screen"""
    ca = g.camapp
    cap = ca["cap_ent"].get() if ca and ca.get("cap_ent") else ""
    compose(g, path, ca.get("lens", "none") if ca else "none", cap, face_xform(g) if ca else None)
    g.close_camera(); MistoUI(g, "snap", path)


class MistoUI:
    def __init__(self, g, page="chats", arg=None, parent=None, lap=None):
        self.g = g; self.app = g.app; self.lap = lap; self.timer = None
        if parent is None:
            o = self.root = DirectFrame(parent=self.app.aspect2d, frameColor=(0, 0, 0, 0.6), frameSize=(-4, 4, -2, 2), state=DGG.NORMAL)
            o.set_bin("gui-popup", 55); g.overlay = o; o.is_misto = True; o.mui = self
            self.app.accept("escape", self.close)
            self.box = (-0.8, 0.8, -0.92, 0.92)
        else:
            self.root = parent; self.box = (-0.97, 1.21, -0.72, 0.74)
        self.show(page, arg)

    def close(self):
        if self.timer: self.app.task_mgr.remove(self.timer); self.timer = None
        if self.lap is None:
            self.root.destroy(); self.g.overlay = None; self.app.accept("escape", self.g.key_esc); self.g.refresh_buttons()

    def clear(self):
        if self.timer: self.app.task_mgr.remove(self.timer); self.timer = None
        for c in self.root.get_children():
            if self.lap is not None or c.get_name() != "keep": c.remove_node()

    def frame(self, title):
        l, r, b, t = self.box; a = self.app; m = data(self.g)
        DirectFrame(parent=self.root, frameColor=LAV, frameSize=(l - 0.008, r + 0.008, b - 0.008, t + 0.008))
        DirectFrame(parent=self.root, frameColor=INK, frameSize=(l, r, b, t))
        OnscreenImage(parent=self.root, image=T(a, "ix_icon_misto2.png"), pos=(l + 0.09, 0, t - 0.08), scale=0.055).set_transparency(TransparencyAttrib.M_alpha)
        U.text(self.root, "MISTO 2", (l + 0.18, t - 0.1), 0.055, fg=LAV, align=TextNode.A_left)
        U.text(self.root, title, (l + 0.18, t - 0.15), 0.028, fg=MINT, font=a.jpfont, align=TextNode.A_left)
        OnscreenImage(parent=self.root, image=T(a, "ix_flame.png"), pos=(r - 0.2, 0, t - 0.085), scale=0.04).set_transparency(TransparencyAttrib.M_alpha)
        U.text(self.root, "%d" % m["streak"], (r - 0.15, t - 0.105), 0.05, fg=(1, 0.65, 0.2, 1), align=TextNode.A_left)
        U.text(self.root, "streak", (r - 0.2, t - 0.15), 0.022, fg=(1, 0.75, 0.4, 1), font=U.FONT_PLAIN)
        y = t - 0.24
        for k, (pid, nm) in enumerate((("chats", "CHATS"), ("stories", "STORIES"))):
            U.button(self.root, nm, (l + 0.2 + k * 0.32, y), lambda p=pid: self.show(p), w=0.14, h=0.035, scale=0.026, edge=MINT if k == 0 else LAV)
        if self.lap is None:
            U.button(self.root, "CAMERA", (r - 0.42, y), lambda: (self.close(), open_app(self.g)), w=0.12, h=0.035, scale=0.026, edge=(1, 1, 1, 1))
            U.button(self.root, "CLOSE", (r - 0.14, y), self.close, w=0.1, h=0.035, scale=0.026, hint="Esc")
        return l, r, b, y - 0.08

    def show(self, page, arg=None):
        self.clear(); self.page = page
        getattr(self, "p_" + page)(arg)

    def tx(self, t, pos, sc=0.03, fg=(1, 1, 1, 1), jp=False, align=TextNode.A_left, wrap=None, parent=None):
        return U.text(parent or self.root, t, pos, sc, fg=fg, font=self.app.jpfont if jp else U.FONT_PLAIN, align=align, wrap=wrap)

    def img(self, path, pos, sc):
        try:
            tex = self.app.loader.load_texture(Filename.from_os_specific(path)); return OnscreenImage(parent=self.root, image=tex, pos=(pos[0], 0, pos[1]), scale=sc)
        except Exception: return None

    # ---- the snap you just took
    def p_snap(self, path):
        l, r, b, y = self.frame("YOUR SNAP"); self.cur = path
        self.img(path, (0, y - 0.38), (0.6, 1, 0.3375))
        bx = y - 0.82
        U.button(self.root, "SEND TO...", (l + 0.3, bx), lambda: self.show("send", path), w=0.17, h=0.045, scale=0.03, edge=MINT, col=(0.15, 0.4, 0.38, 1))
        U.button(self.root, "POST STORY", (l + 0.72, bx), lambda: self.post(path), w=0.17, h=0.045, scale=0.03, edge=LAV)
        U.button(self.root, "SAVE", (l + 1.1, bx), lambda: self.save(path), w=0.1, h=0.045, scale=0.03, edge=(1, 1, 1, 1))
        U.button(self.root, "DISCARD", (l + 1.38, bx), lambda: self.show("chats"), w=0.13, h=0.045, scale=0.03, edge=(1, 0.4, 0.4, 1))
        self.msg = self.tx("", (0, bx - 0.11), 0.03, fg=MINT, align=TextNode.A_center)

    def save(self, path):
        g = self.g; d = g.pictures_dir(); dst = os.path.join(d, "misto2_" + os.path.basename(path))
        try:
            shutil.copyfile(path, dst); g.add_photo(dst); self.msg.setText("Saved to Pictures/FIREOUT ONLINE - in PHOTOS + KIRAKIRA")
        except Exception as e: self.msg.setText("Couldn't save: %s" % e)

    def post(self, path):
        m = data(self.g); m["stories"].append(path); self.bump_streak(); self.g.save(); self.msg.setText("Posted to your STORY!")

    def bump_streak(self):
        m = data(self.g); today = time.strftime("%Y-%m-%d")
        if m["last"] != today:
            yest = time.strftime("%Y-%m-%d", time.localtime(time.time() - 86400))
            m["streak"] = m["streak"] + 1 if m["last"] in (yest, "") or m["streak"] == 0 else 1
            m["last"] = today

    def p_send(self, path):
        l, r, b, y = self.frame("SEND TO..."); from fs_game import NAMES
        k = 0
        for cid, nm, ja in CONTACTS:
            if cid == self.g.active: continue
            U.button(self.root, nm, (l + 0.4, y - 0.05 - k * 0.12), self.send, w=0.25, h=0.045, scale=0.03, extra=[cid, path], edge=MINT)
            self.tx(ja, (l + 0.72, y - 0.06 - k * 0.12), 0.034, jp=True); k += 1

    def send(self, cid, path):
        m = data(self.g); ch = m["chats"].setdefault(cid, [])
        ch.append(["me", "snap", "スナップを送信しました", "You sent a snap", path, True]); self.bump_streak(); self.g.save()
        self.app.sfx("click", 0.6)
        self.app.do_method_later(2.5, lambda t, c=cid: self.reply(c) or t.done, "misto-reply")
        self.show("chat", cid)

    def reply(self, cid):
        m = data(self.g)
        rp = random.choice(REPLIES[:4]) if not m["chats"].get(cid) or len(m["chats"][cid]) < 3 else random.choice(REPLIES); img = os.path.join(self.app.BASE, "assets", "tex", "misto_reply_%s.png" % rp[0]) if rp[0] else None
        m["chats"].setdefault(cid, []).append([cid, "snap" if img else "text", rp[1], rp[2], img, False])
        if getattr(self, "page", "") == "chat" and getattr(self, "chat_id", None) == cid and not self.root.is_empty(): self.show("chat", cid)
        self.g.toast("MISTO 2: new snap from %s" % dict((c[0], c[1]) for c in CONTACTS)[cid])

    def p_chats(self, _=None):
        l, r, b, y = self.frame("CHATS  -  チャット"); m = data(self.g)
        k = 0
        for cid, nm, ja in CONTACTS:
            if cid == self.g.active: continue
            ch = m["chats"].get(cid, []); new = any(c[0] != "me" and not c[5] for c in ch)
            last = ch[-1] if ch else None
            b_ = DirectButton(parent=self.root, frameColor=(0.16, 0.1, 0.3, 1), frameSize=(l + 0.04, r - 0.04, -0.05, 0.05), pos=(0, 0, y - k * 0.12),
                              relief=DGG.FLAT, command=self.show, extraArgs=["chat", cid])
            DirectFrame(parent=b_, frameColor=MINT if new else (0.45, 0.4, 0.6, 1), frameSize=(l + 0.07, l + 0.11, -0.02, 0.02))
            self.tx(nm + "  " + ja, (l + 0.15, 0.0), 0.03, jp=True, parent=b_)
            self.tx(("NEW SNAP - tap to view" if new else (last[3] if last else "Say hi!")), (l + 0.15, -0.035), 0.022, fg=(0.75, 0.75, 0.85, 1), parent=b_)
            k += 1

    def p_chat(self, cid):
        self.chat_id = cid; nm = dict((c[0], c[1]) for c in CONTACTS)[cid]
        l, r, b, y = self.frame("CHAT WITH %s" % nm); m = data(self.g); ch = m["chats"].get(cid, [])[-6:]
        for k, c in enumerate(ch):
            yy = y - 0.1 - k * 0.15; me = c[0] == "me"; x = r - 0.06 if me else l + 0.06; al = TextNode.A_right if me else TextNode.A_left
            if c[1] == "snap" and not me and not c[5]:
                U.button(self.root, "▶ NEW SNAP - TAP TO VIEW (5s)", (l + 0.45, yy), self.view, w=0.38, h=0.045, scale=0.026, extra=[cid, c], edge=MINT,
                         col=(0.15, 0.4, 0.38, 1), font=self.app.jpfont)
                continue
            self.tx(c[2] if not (c[1] == "snap" and not me) else "（開封済みのスナップ）", (x, yy + 0.01), 0.032, fg=LAV if me else MINT, jp=True, align=al)
            self.tx(c[3] if not (c[1] == "snap" and not me) else "(opened snap - it's gone)", (x, yy - 0.035), 0.024, fg=(0.8, 0.8, 0.9, 1), align=al)
        if self.lap is None:
            U.button(self.root, "SEND A SNAP", (0, b + 0.08), lambda: (self.close(), open_app(self.g)), w=0.2, h=0.045, scale=0.03, edge=MINT)

    def view(self, cid, c):
        """a received snap: shown for 5 seconds with a countdown, then it disappears for good"""
        l, r, b, y = self.frame("SNAP FROM %s" % dict((x[0], x[1]) for x in CONTACTS)[cid])
        for ch in self.root.get_children(): pass
        self.img(c[4], (0, y - 0.38), (0.6, 1, 0.3375))
        self.tx(c[2], (0, y - 0.82), 0.042, jp=True, align=TextNode.A_center); self.tx(c[3], (0, y - 0.88), 0.03, fg=(0.8, 0.8, 0.9, 1), align=TextNode.A_center)
        cd = self.tx("5", (r - 0.12, y - 0.05), 0.08, fg=MINT, align=TextNode.A_center)
        c[5] = True; self.g.save(); t0 = [5.0]
        def tick(task):
            if self.root.is_empty(): return task.done
            t0[0] -= globalClock.get_dt()
            if t0[0] <= 0: self.timer = None; self.show("chat", cid); return task.done
            cd.setText("%d" % (int(t0[0]) + 1)); return task.cont
        self.timer = self.app.task_mgr.add(tick, "misto-view")

    def p_stories(self, _=None):
        l, r, b, y = self.frame("STORIES  -  ストーリー"); st = [p for p in data(self.g)["stories"] if os.path.exists(p)][-6:][::-1]
        if not st: self.tx("まだストーリーはありません", (0, y - 0.2), 0.04, jp=True, align=TextNode.A_center); self.tx("No stories yet - snap and POST STORY", (0, y - 0.26), 0.028, align=TextNode.A_center); return
        for k, p in enumerate(st):
            x = l + 0.32 + (k % 3) * ((r - l - 0.2) / 3); yy = y - 0.18 - (k // 3) * 0.42
            self.img(p, (x, yy), (0.22, 1, 0.124)); self.tx("my story", (x, yy - 0.16), 0.022, fg=LAV, align=TextNode.A_center)


def laptop_view(lap):
    w = lap.window("MISTO 2", LAV, "ミスト2")
    lap.misto = MistoUI(lap.g, "chats", parent=w.body, lap=lap)
