"""FIREOUT ONLINE v1.0.4 - IX LAPTOPOS G9: the in-game laptop (3D prop + typing animation + desktop OS with apps:
BANK, MAP, SHOP, MUSIC, EMAIL, PHOTOS, IX NAVI browser, MISTO 2, SHUT DOWN). Fictional brands only."""
import os, math, time, random
from panda3d.core import Filename, TextNode, TransparencyAttrib, NodePath, Point3
from direct.gui.DirectGui import DirectFrame, DirectButton, DirectEntry, DirectScrolledFrame, DGG
from direct.gui.OnscreenImage import OnscreenImage
import fs_ui as U
import fs_data as D

NAME = "IX LAPTOPOS G9"
COPY = "©2026 EX ROMANIA/EX INC."
ACC = (0.35, 0.85, 1.0, 1)
X0, X1, Y0, Y1 = -1.32, 1.32, -0.86, 0.86        # laptop screen in aspect2d
TB = -0.78                                        # taskbar top
OUTFIT_PRICE = 1200


def T(app, n): return Filename.from_os_specific(os.path.join(app.BASE, "assets", "tex", n)).get_fullpath()


EMAILS = [("ナナ（カフェ・ルミエール）", "Nana (Café Lumière)", "新作ラテ、試しに来てね！", "Come and try our new latte!",
           "灯町の店で桜ラテを始めました。写真を撮ってくれたら一杯無料です。", "We've started a sakura latte at the Akari-cho shop. Take a photo and your first cup is free."),
          ("ケンジ（FRGARAGE）", "Kenji (FRGARAGE)", "愛車の点検はいかが？", "Time for a check-up?",
           "最近ぶつけてない？ガレージでペイントとナンバープレートの変更もできるよ。", "Been scraping that paint? At the garage you can also change the paint and the number plate."),
          ("ネオン東京ニュース", "Neon Tokyo News", "今週のトップニュース", "This week's top stories",
           "湾岸道路でカーチェイス、光ビーチで工事現場の謎の建物が話題に。", "A car chase on the coast road, and mystery buildings popping up at Hikari Beach."),
          ("EX Inc.", "EX Inc.", "IX LAPTOPOS G9 へようこそ", "Welcome to IX LAPTOPOS G9",
           "新しいノートパソコンをお買い上げいただきありがとうございます。", "Thank you for buying your new laptop. Enjoy the browser, MISTO 2 and more."),
          ("炎ラーメン", "HONOO RAMEN", "替え玉無料キャンペーン", "Free extra noodles",
           "今週末は替え玉無料！夜十一時まで営業しています。", "Free extra noodles this weekend! We're open until 11 pm."),
          ("ダニエル", "DANIEL", "ビーチで会おう", "See you at the beach",
           "アナ、ビーチに新しい階段を作ってくれてありがとう！", "Ana, thanks for building those new stairs on the beach!")]


class Laptop:
    def __init__(self, game):
        self.g = game; self.app = game.app; self.ui = None; self.prop = None; self.t = 0.0; self.phase = None; self.desk = False
        self.win = None; self.browser = None

    # ------------------------------------------------------------------ open / close + 3D prop
    def block(self):
        g = self.g
        if g.pcar is not None or g.ride: return "Pull over to use the laptop"
        if g.eating is not None: return "Finish eating first"
        if g.camapp or g.phone or (g.overlay is not None and g.overlay is not self.ui): return "Not right now"
        if g.home and g.home.get("mode") not in ("room",): return "Not right now"
        if g.paused or g.intro_t > 0 or g.garage is not None: return "Not right now"
        if getattr(g.me(), "swim", False): return "Not while swimming"
        return None

    def toggle(self, desk=False):
        if self.ui is not None or self.phase is not None: self.close(); return
        b = self.block()
        if b: self.g.toast(b); return
        if hasattr(self.g, "arsenal"): self.g.arsenal.unequip()
        me = self.g.me(); self.desk = desk; self.t = 0.0; self.phase = "pull"
        me.anim_lock = True; me.set_grip(False, False); me.speed = 0
        if self.g.home: self.g.home["mode"] = "laptop"; self.g.home_prompt_off()
        if not desk: self.make_prop(me)
        self.app.sfx("click", 0.6)

    def make_prop(self, me):
        from fs_miyo import box_mesh, shade
        r = self.prop = me.np.attach_new_node("ix-laptop"); r.set_pos(0, 0.30, 1.08); r.set_scale(0.001)
        body = (0.16, 0.17, 0.2, 1); key = (0.05, 0.05, 0.06, 1)
        b = r.attach_new_node(box_mesh("base", [(-0.17, -0.12, 0.0, 0.17, 0.12, 0.018, body), (-0.15, -0.06, 0.018, 0.15, 0.10, 0.021, key),
                                               (-0.05, -0.11, 0.018, 0.05, -0.07, 0.020, (0.3, 0.3, 0.33, 1))]))
        shade(b, self.app, 0.6)
        lid = self.lid = r.attach_new_node("lid"); lid.set_pos(0, 0.12, 0.018)
        l = lid.attach_new_node(box_mesh("lid", [(-0.17, -0.012, 0.0, 0.17, 0.0, 0.23, body), (-0.155, -0.0125, 0.012, 0.155, -0.011, 0.218, (0.2, 0.5, 1.0, 1))]))
        shade(l, self.app, 0.6); l.find("**/lid")
        tn = TextNode("brand"); tn.set_text(NAME); tn.set_align(TextNode.A_center); tn.set_text_color(0.75, 0.9, 1.0, 1)
        if U.FONT: tn.set_font(U.FONT)
        bt = lid.attach_new_node(tn.generate()); bt.set_pos(0, 0.002, 0.115); bt.set_h(180); bt.set_scale(0.026); bt.set_light_off()
        lg = lid.attach_new_node(box_mesh("logo", [(-0.022, 0.0005, 0.14, 0.022, 0.0025, 0.184, (0.4, 0.85, 1.0, 1))])); lg.set_light_off()
        lid.set_p(0)

    def close(self):
        g = self.g; me = g.me()
        if self.ui is not None:
            self.ui.destroy(); self.ui = None
            if g.overlay is not None and getattr(g.overlay, "is_laptop", False): g.overlay = None
        if self.prop is not None: self.prop.remove_node(); self.prop = None
        self.phase = None; self.win = None; self.browser = None
        me.anim_lock = False; me.model.set_p(0)
        if g.home and g.home.get("mode") == "laptop": g.home["mode"] = "room"
        g.refresh_buttons(); self.app.sfx("click", 0.5)

    def typing(self):
        return self.ui is not None

    def update(self, dt):
        if self.phase is None: return
        self.t += dt; t = self.t; me = self.g.me()
        # arms: forward to the keyboard, forearms bent, alternating finger taps (typing loop)
        if not self.desk:
            u = min(1.0, t / 0.6); e = u * u * (3 - 2 * u)
            tap = math.sin(t * 17.0) * 4.0 * min(1.0, max(0.0, t - 0.8))
            me.set_arms((-6 - 26 * e, 4 - 14 * e), (-6 - 26 * e, 4 - 14 * e), (-10 - 24 * e + tap, -12 * e), (-10 - 24 * e - tap, -12 * e))
            me.model.set_p(-3 * e)
            if self.prop is not None:
                self.prop.set_scale(max(0.001, e)); self.prop.set_z(0.8 + 0.28 * e)
                lo = min(1.0, max(0.0, (t - 0.55) / 0.5)); self.lid.set_p(-(lo * lo * (3 - 2 * lo)) * 105)
        if self.phase == "pull" and t > (1.15 if not self.desk else 0.2):
            self.phase = "boot"; self.open_ui()
        if self.phase == "boot" and self.ui is not None and t > (2.9 if not self.desk else 1.9):
            self.phase = "desk"; self.desktop()
        if self.ui is not None and getattr(self, "clock", None) is not None and int(t * 2) % 2 == 0:
            self.clock.setText(self.time_str())

    # ------------------------------------------------------------------ desktop
    def time_str(self):
        tod = getattr(self.g, "tod", 12.0) % 24; return "%02d:%02d" % (int(tod), int((tod % 1) * 60))

    def open_ui(self):
        a = self.app; g = self.g
        o = self.ui = DirectFrame(parent=a.aspect2d, frameColor=(0, 0, 0, 0.55), frameSize=(-4, 4, -2, 2), state=DGG.NORMAL); o.is_laptop = True
        o.set_bin("gui-popup", 40); g.overlay = o
        DirectFrame(parent=o, frameColor=(0.08, 0.08, 0.1, 1), frameSize=(X0 - 0.04, X1 + 0.04, Y0 - 0.06, Y1 + 0.04))     # bezel
        U.text(o, NAME, (0, Y0 - 0.045), 0.022, fg=(0.55, 0.6, 0.7, 1))
        self.scr = DirectFrame(parent=o, frameColor=(0, 0, 0, 1), frameSize=(X0, X1, Y0, Y1))
        U.text(self.scr, NAME, (0, 0.1), 0.13, fg=(0.4, 0.85, 1.0, 1)); U.text(self.scr, "Developed by EX ROMANIA", (0, -0.02), 0.035, fg=(0.8, 0.8, 0.9, 1))
        bar = DirectFrame(parent=self.scr, frameColor=(0.15, 0.15, 0.2, 1), frameSize=(-0.4, 0.4, -0.012, 0.012), pos=(0, 0, -0.2))
        self.bootbar = DirectFrame(parent=bar, frameColor=ACC, frameSize=(-0.4, -0.4, -0.012, 0.012))
        U.text(self.scr, COPY, (0, -0.72), 0.03, fg=(0.6, 0.65, 0.75, 1), font=U.FONT_PLAIN)
        self.app.task_mgr.add(self._boot_task, "ix-boot")

    def _boot_task(self, task):
        if self.ui is None or self.phase != "boot": return task.done
        k = min(1.0, (self.t - (1.15 if not self.desk else 0.2)) / 1.6)
        self.bootbar["frameSize"] = (-0.4, -0.4 + 0.8 * k, -0.012, 0.012)
        return task.cont

    def desktop(self):
        a = self.app
        if self.scr is not None: self.scr.destroy()
        s = self.scr = DirectFrame(parent=self.ui, frameColor=(0, 0, 0, 1), frameSize=(X0, X1, Y0, Y1))
        OnscreenImage(parent=s, image=T(a, "ix_wall.png"), pos=(0, 0, (Y1 + TB) / 2), scale=((X1 - X0) / 2, 1, (Y1 - TB) / 2))
        apps = [("bank", "BANK", self.app_bank), ("map", "MAP", self.app_map), ("shop", "SHOP", self.app_shop), ("music", "MUSIC", self.app_music),
                ("email", "EMAIL", self.app_email), ("photos", "PHOTOS", self.app_photos), ("browser", "IX NAVI", self.app_browser),
                ("misto2", "MISTO 2", self.app_misto)]
        if hasattr(self.g, "online_app"): apps.append(("online", "FIREOUT ONLINE", self.g.online_app))
        for k, (ic, nm, fn) in enumerate(apps):
            x = X0 + 0.16 + (k // 6) * 0.26; y = Y1 - 0.14 - (k % 6) * 0.25
            b = DirectButton(parent=s, image=T(a, "ix_icon_%s.png" % ic), image_scale=0.075, relief=None, pos=(x, 0, y), command=fn)
            b.set_transparency(TransparencyAttrib.M_alpha)
            U.text(s, nm, (x, y - 0.11), 0.026, fg=(1, 1, 1, 1), font=U.FONT_PLAIN, shadow=(0, 0, 0, 1))
        tb = DirectFrame(parent=s, frameColor=(0.04, 0.04, 0.08, 0.92), frameSize=(X0, X1, Y0, TB))
        U.text(tb, "IX", (X0 + 0.07, (Y0 + TB) / 2 - 0.015), 0.045, fg=ACC)
        U.text(tb, COPY, (-0.1, (Y0 + TB) / 2 - 0.01), 0.024, fg=(0.7, 0.75, 0.85, 1), font=U.FONT_PLAIN)
        self.clock = U.text(tb, self.time_str(), (X1 - 0.38, (Y0 + TB) / 2 - 0.013), 0.036, fg=(1, 1, 1, 1), font=U.FONT_PLAIN)
        U.button(tb, "SHUT DOWN", (X1 - 0.15, (Y0 + TB) / 2), self.close, w=0.12, h=0.03, scale=0.024, edge=(1, 0.35, 0.35, 1), hint="Esc")
        self.win = None
        self.g.refresh_buttons()

    def window(self, title, col=ACC, jp=None):
        if self.win is not None: self.win.destroy()
        w = self.win = DirectFrame(parent=self.scr, frameColor=col, frameSize=(-0.99, 1.23, -0.74, 0.82), state=DGG.NORMAL)
        DirectFrame(parent=w, frameColor=(0.97, 0.97, 0.98, 1), frameSize=(-0.985, 1.225, -0.735, 0.75))
        U.text(w, title, (-0.96, 0.765), 0.04, fg=(0.02, 0.02, 0.05, 1), align=TextNode.A_left)
        if jp: U.text(w, jp, (-0.96 + 0.032 * len(title) * 0.75 + 0.06, 0.765), 0.032, fg=(0.1, 0.1, 0.2, 1), align=TextNode.A_left, font=self.app.jpfont)
        U.button(w, "X", (1.19, 0.785), self.close_win, w=0.03, h=0.03, scale=0.03, edge=(1, 0.3, 0.3, 1))
        w.body = DirectFrame(parent=w, frameColor=(0, 0, 0, 0))
        return w

    def close_win(self):
        if self.win is not None: self.win.destroy(); self.win = None
        self.browser = None

    def tx(self, p, t, pos, sc=0.034, fg=(0.05, 0.05, 0.1, 1), jp=False, align=TextNode.A_left, wrap=None):
        return U.text(p, t, pos, sc, fg=fg, font=self.app.jpfont if jp else U.FONT_PLAIN, align=align, wrap=wrap)

    # ------------------------------------------------------------------ apps
    def app_bank(self):
        g = self.g; w = self.window("HIKARI BANK", (0.2, 0.75, 0.5, 1), "光銀行").body
        self.tx(w, "ようこそ、%s さん" % {"elijer": "エリジャー", "ana": "アナ", "daniel": "ダニエル"}.get(g.active, "エリジャー"), (-0.9, 0.6), 0.04, jp=True)
        from fs_game import NAMES
        self.tx(w, "Welcome, %s" % NAMES[g.active], (-0.9, 0.54), 0.03, fg=(0.3, 0.3, 0.4, 1))
        self.tx(w, "残高  BALANCE", (-0.9, 0.38), 0.035, jp=True)
        self.tx(w, "¥%s" % format(g.cash, ","), (-0.9, 0.24), 0.11, fg=(0.05, 0.45, 0.25, 1))
        self.tx(w, "最近の取引  RECENT TRANSACTIONS", (-0.9, 0.06), 0.032, jp=True)
        led = list(getattr(g, "ledger", []))[-9:][::-1] or [("—", 0)]
        for k, (what, amt) in enumerate(led):
            self.tx(w, what, (-0.9, -0.03 - k * 0.07), 0.03)
            if amt: self.tx(w, ("+" if amt > 0 else "-") + "¥%s" % format(abs(amt), ","), (1.1, -0.03 - k * 0.07), 0.03,
                            fg=(0.05, 0.5, 0.2, 1) if amt > 0 else (0.75, 0.1, 0.1, 1), align=TextNode.A_right)

    def app_map(self):
        g = self.g; w = self.window("MAP", (0.3, 0.55, 1.0, 1), "地図").body
        S = 0.66; cx, cy = 0.12, 0.02; xmin, ymin, span = -470.0, -590.0, 1180.0
        img = DirectFrame(parent=w, frameColor=(1, 1, 1, 1), frameSize=(cx - S, cx + S, cy - S, cy + S), state=DGG.NORMAL, image=g.map_tex,
                          image_scale=(S, 1, S), image_pos=(cx, 0, cy))
        def mp(x, y): return cx + ((x - xmin) / span * 2 - 1) * S, cy + ((y - ymin) / span * 2 - 1) * S
        if g.waypoint: x, y = mp(*g.waypoint); U.text(w, "X", (x, y - 0.015), 0.05, fg=(0.1, 0.8, 0.2, 1))
        px, py = g.player_pos(); x, y = mp(px, py); U.text(w, "●", (x, y - 0.015), 0.045, fg=(1, 0.2, 0.3, 1), font=self.app.jpfont)
        self.tx(w, "クリックで目的地を設定", (-0.95, 0.6), 0.03, jp=True); self.tx(w, "Click the map to set a waypoint", (-0.95, 0.55), 0.024)
        def click(ev):
            mw = self.app.mouseWatcherNode
            if mw is None or not mw.has_mouse(): return
            p = w.get_relative_point(self.app.render2d, Point3(mw.get_mouse()[0], 0, mw.get_mouse()[1]))
            self.set_wp(xmin + ((p.x - cx) / S + 1) / 2 * span, ymin + ((p.z - cy) / S + 1) / 2 * span)
        img.bind(DGG.B1PRESS, click); self.map_click = click

    def set_wp(self, x, y):
        self.g.waypoint = (x, y); self.g.toast("Waypoint set"); self.app.sfx("click", 0.6); self.app_map()

    def app_shop(self, tab="food"):
        g = self.g; w = self.window("KAIMONO SHOP", (1.0, 0.6, 0.2, 1), "買い物").body
        U.button(w, "FOOD DELIVERY", (-0.7, 0.66), lambda: self.app_shop("food"), w=0.22, h=0.035, scale=0.026, edge=(1, 0.6, 0.2, 1) if tab == "food" else (0.5, 0.5, 0.6, 1))
        U.button(w, "OUTFITS", (-0.2, 0.66), lambda: self.app_shop("outfits"), w=0.22, h=0.035, scale=0.026, edge=(1, 0.6, 0.2, 1) if tab == "outfits" else (0.5, 0.5, 0.6, 1))
        self.tx(w, "Cash ¥%s" % format(g.cash, ","), (1.15, 0.65), 0.03, align=TextNode.A_right)
        self.shop_msg = self.tx(w, "", (0.1, -0.68), 0.028, align=TextNode.A_center)
        if tab == "food":
            from fs_food import FOODS
            for k, (fid, ja, en, price, hp, kind, _) in enumerate(FOODS):
                x = -0.72 + (k % 4) * 0.5; y = 0.42 - (k // 4) * 0.36
                b = DirectButton(parent=w, frameColor=(0.93, 0.9, 0.85, 1), frameSize=(-0.23, 0.23, -0.15, 0.15), pos=(x, 0, y), relief=DGG.FLAT,
                                 command=self.order_food, extraArgs=[fid])
                try: OnscreenImage(parent=b, image=T(self.app, "food_%s.png" % fid), pos=(-0.13, 0, 0.0), scale=0.09).set_transparency(TransparencyAttrib.M_alpha)
                except Exception: pass
                self.tx(b, ja, (0.07, 0.04), 0.034, jp=True, align=TextNode.A_center)
                self.tx(b, en, (0.07, -0.02), 0.024, align=TextNode.A_center)
                self.tx(b, "¥%d" % price, (0.07, -0.08), 0.026, fg=(0.7, 0.3, 0.0, 1), align=TextNode.A_center)
        else:
            from fs_game import NAMES
            self.tx(w, "%s  -  outfits ¥%s each (owned ones are free to wear)" % (NAMES[g.active], format(OUTFIT_PRICE, ",")), (-0.9, 0.52), 0.03)
            own = getattr(g, "owned", {}).get(g.active, ["default"])
            for k, (oid, nm, desc) in enumerate(g.outfit_list()):
                y = 0.36 - k * 0.15; on = g.chars[g.active].outfit == oid
                U.button(w, nm + ("  (wearing)" if on else ("  (owned)" if oid in own else "  ¥%d" % OUTFIT_PRICE)), (-0.5, y), self.order_outfit,
                         w=0.36, h=0.045, scale=0.028, extra=[oid], edge=(1, 0.55, 0.85, 1) if on else (0.5, 0.5, 0.6, 1))
                self.tx(w, desc, (-0.05, y - 0.012), 0.026)

    def order_food(self, fid):
        from fs_food import INFO
        g = self.g; f = INFO[fid]
        if g.cash < f[3]: self.shop_msg.setText("Not enough cash for %s" % f[2]); return
        self.close(); g.eat_food(fid)

    def order_outfit(self, oid):
        g = self.g; own = g.owned.setdefault(g.active, ["default"])
        b = g.outfit_block() if g.outfit_block() != "Close the camera first" else None
        if g.pcar is not None: self.shop_msg.setText("Exit the vehicle first"); return
        if oid not in own:
            if g.cash < OUTFIT_PRICE: self.shop_msg.setText("Not enough cash"); return
            g.cash -= OUTFIT_PRICE; own.append(oid); g.ledger.append(("KAIMONO SHOP outfit", -OUTFIT_PRICE))
        g.apply_outfit(g.active, oid); self.app_shop("outfits"); self.shop_msg.setText("Delivered and changed!")

    def app_music(self):
        w = self.window("IX MUSIC", (0.75, 0.3, 0.9, 1), "音楽").body
        tracks = [("music_menu", "NEON NIGHT DRIVE", "ネオン・ナイト・ドライブ"), ("music_race", "RACE FEVER", "レース・フィーバー")]
        cur = getattr(self.app, "cur_music", None)
        for k, (mid, nm, ja) in enumerate(tracks):
            y = 0.5 - k * 0.2; on = cur == mid
            U.button(w, ("■ " if on else "▶ ") + nm, (-0.45, y), self.play, w=0.4, h=0.05, scale=0.03, extra=[mid], edge=(0.75, 0.3, 0.9, 1) if on else (0.5, 0.5, 0.6, 1), font=self.app.jpfont)
            self.tx(w, ja, (0.05, y - 0.012), 0.032, jp=True)
        U.button(w, "STOP", (-0.45, 0.0), self.play, w=0.2, h=0.045, scale=0.03, extra=[None])
        self.tx(w, "Now playing: %s" % ({t[0]: t[1] for t in tracks}.get(cur, "-")), (-0.9, -0.2), 0.032)

    def play(self, mid):
        self.app.play_music(mid) if mid else self.app.play_music(None)
        self.g.laptop_music = mid; self.app_music()

    def app_email(self, i=None):
        w = self.window("IX MAIL", (0.95, 0.3, 0.4, 1), "メール").body
        for k, e in enumerate(EMAILS):
            y = 0.62 - k * 0.2; sel = k == i
            b = DirectButton(parent=w, frameColor=(0.9, 0.85, 0.95, 1) if sel else (0.95, 0.95, 0.97, 1), frameSize=(-0.95, -0.12, -0.085, 0.085),
                             pos=(0, 0, y), relief=DGG.FLAT, command=self.app_email, extraArgs=[k])
            self.tx(b, e[0], (-0.92, 0.035), 0.028, jp=True); self.tx(b, e[2], (-0.92, -0.015), 0.026, jp=True, fg=(0.2, 0.2, 0.3, 1))
            self.tx(b, e[3], (-0.92, -0.06), 0.022, fg=(0.35, 0.35, 0.45, 1))
        if i is not None:
            e = EMAILS[i]
            self.tx(w, e[0], (-0.05, 0.62), 0.034, jp=True); self.tx(w, e[1], (-0.05, 0.57), 0.026, fg=(0.4, 0.4, 0.5, 1))
            self.tx(w, e[2], (-0.05, 0.47), 0.04, jp=True); self.tx(w, e[3], (-0.05, 0.41), 0.03, fg=(0.3, 0.3, 0.4, 1))
            self.tx(w, e[4], (-0.05, 0.28), 0.034, jp=True, wrap=34); self.tx(w, e[5], (-0.05, 0.12), 0.028, fg=(0.3, 0.3, 0.4, 1), wrap=42)
        else:
            self.tx(w, "メールを選んでください", (0.5, 0.2), 0.04, jp=True, align=TextNode.A_center); self.tx(w, "Pick a message", (0.5, 0.14), 0.03, align=TextNode.A_center)

    # ---- photos (selfies the game saved in Pictures\FIREOUT ONLINE) with DELETE
    def app_photos(self, view=None):
        g = self.g; w = self.window("PHOTOS", (1.0, 0.7, 0.3, 1), "写真").body
        ph = g.photo_list()
        if view is not None and view in ph:
            self.photo_view(w, view, lambda: self.app_photos(), lambda: self.app_photos()); return
        if not ph:
            self.tx(w, "写真はまだありません", (0.12, 0.1), 0.045, jp=True, align=TextNode.A_center)
            self.tx(w, "No photos yet - take a selfie with the phone CAMERA or MISTO 2", (0.12, 0.02), 0.03, align=TextNode.A_center); return
        for k, p in enumerate(ph[-12:][::-1]):
            x = -0.72 + (k % 4) * 0.5; y = 0.5 - (k // 4) * 0.4
            b = DirectButton(parent=w, frameColor=(0.2, 0.2, 0.25, 1), frameSize=(-0.22, 0.22, -0.13, 0.13), pos=(x, 0, y), relief=DGG.FLAT,
                             command=self.app_photos, extraArgs=[p])
            try:
                tex = self.app.loader.load_texture(Filename.from_os_specific(p)); OnscreenImage(parent=b, image=tex, scale=(0.21, 1, 0.12))
            except Exception: pass
            self.del_btn(w, (x + 0.16, y - 0.1), p, lambda: self.app_photos(), small=True)

    def photo_view(self, w, p, back, after):
        try:
            tex = self.app.loader.load_texture(Filename.from_os_specific(p)); OnscreenImage(parent=w, image=tex, pos=(0.12, 0, 0.06), scale=(0.95 * 0.75, 1, 0.535 * 0.75))
        except Exception: pass
        self.tx(w, os.path.basename(p), (-0.9, -0.55), 0.026)
        U.button(w, "BACK", (-0.75, -0.65), back, w=0.12, h=0.035, scale=0.026)
        self.del_btn(w, (0.95, -0.65), p, after)

    def del_btn(self, parent, pos, path, after, small=False):
        b = DirectButton(parent=parent, frameColor=(0.8, 0.12, 0.15, 1), frameSize=(-0.12 if not small else -0.05, 0.12 if not small else 0.05, -0.035, 0.035),
                         pos=(pos[0], 0, pos[1]), relief=DGG.FLAT, command=self.confirm_delete, extraArgs=[path, after])
        OnscreenImage(parent=b, image=T(self.app, "ix_trash.png"), pos=(-0.08 if not small else 0, 0, 0), scale=0.026).set_transparency(TransparencyAttrib.M_alpha)
        if not small: self.tx(b, "DELETE", (0.02, -0.01), 0.028, fg=(1, 1, 1, 1), align=TextNode.A_center)
        return b

    def confirm_delete(self, path, after):
        if getattr(self, "dlg", None): self.dlg.destroy()
        d = self.dlg = DirectFrame(parent=self.scr, frameColor=(0, 0, 0, 0.6), frameSize=(X0, X1, Y0, Y1), state=DGG.NORMAL)
        DirectFrame(parent=d, frameColor=(0.95, 0.3, 0.35, 1), frameSize=(-0.62, 0.62, -0.27, 0.27))
        DirectFrame(parent=d, frameColor=(0.98, 0.98, 0.99, 1), frameSize=(-0.61, 0.61, -0.26, 0.26))
        OnscreenImage(parent=d, image=T(self.app, "ix_trash.png"), pos=(-0.5, 0, 0.14), scale=0.05, color=(0.85, 0.15, 0.2, 1)).set_transparency(TransparencyAttrib.M_alpha)
        self.tx(d, "この写真を削除しますか？", (0.03, 0.15), 0.05, jp=True, align=TextNode.A_center)
        self.tx(d, "Delete this photo?", (0.03, 0.07), 0.04, align=TextNode.A_center)
        self.tx(d, os.path.basename(path), (0.03, 0.01), 0.024, fg=(0.4, 0.4, 0.5, 1), align=TextNode.A_center)
        def ok():
            self.dlg.destroy(); self.dlg = None
            if self.g.delete_photo(path): self.g.toast("Photo deleted")
            after()
        def cancel(): self.dlg.destroy(); self.dlg = None
        U.button(d, "DELETE", (-0.22, -0.14), ok, w=0.16, h=0.045, scale=0.032, edge=(1, 0.25, 0.3, 1), col=(0.75, 0.1, 0.15, 1))
        U.button(d, "CANCEL", (0.25, -0.14), cancel, w=0.16, h=0.045, scale=0.032, edge=(0.5, 0.5, 0.6, 1))
        d.ok = ok; d.cancel = cancel

    def app_browser(self, url=None):
        from fs_browser import Browser
        self.window("IX NAVI", (0.2, 0.75, 0.85, 1), "ブラウザ")
        self.browser = Browser(self, self.win.body, url)

    def app_misto(self):
        import fs_misto
        fs_misto.laptop_view(self)
