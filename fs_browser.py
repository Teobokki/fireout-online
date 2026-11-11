"""FIREOUT ONLINE v1.0.4 - IX NAVI, the IX LAPTOPOS G9 web browser: an in-game web of fictional sites (no real internet)."""
import os, time
from panda3d.core import Filename, TextNode, TransparencyAttrib
from direct.gui.DirectGui import DirectFrame, DirectButton, DirectEntry, DGG
from direct.gui.OnscreenImage import OnscreenImage
import fs_ui as U

HOME = "ix://home"
# url, title, Japanese title, keywords
SITES = [("news.neontokyo.jp", "NEON TOKYO NEWS", "ネオン東京ニュース", "news tsunami police chase wanted tokyo"),
         ("frgarage.jp/cars", "FRGARAGE CAR DEALER", "FRガレージ 中古車", "cars car dealer debauche garage buy kagerou raijin"),
         ("honoo-ramen.jp", "HONOO RAMEN & BAR", "炎ラーメン＆バー", "ramen food bar menu drinks beer sake noodles"),
         ("tenki.neontokyo.jp", "NEON TOKYO WEATHER", "ネオン東京の天気", "weather rain sun forecast tenki"),
         ("sumika-homes.jp", "SUMIKA HOMES", "すみかホーム 不動産", "real estate house apartment home rent buy"),
         ("exromania.dev/fan", "EX ROMANIA FAN PAGE", "EX ROMANIA ファンページ", "ex romania ex inc fan laptop phone ix g9 fireout"),
         ("kirakira.social", "KIRAKIRA SOCIAL", "キラキラ・ソーシャル", "social feed selfies photos friends posts")]
URLS = {s[0]: s for s in SITES}
W0, W1 = -0.97, 1.21


class Browser:
    def __init__(self, lap, parent, url=None):
        self.lap = lap; self.g = lap.g; self.app = lap.app; self.root = parent
        self.tabs = [{"hist": [url or HOME], "i": 0}]; self.cur = 0
        self.render()

    @property
    def url(self):
        t = self.tabs[self.cur]; return t["hist"][t["i"]]

    def go(self, url):
        url = (url or "").strip()
        for pre in ("https://", "http://", "www."):
            if url.startswith(pre): url = url[len(pre):]
        if url.endswith("/") and len(url) > 1: url = url[:-1]
        if url == "" or url == "home": url = HOME
        if " " in url or ("." not in url and not url.startswith("ix://")): url = "ix://search?q=" + url
        t = self.tabs[self.cur]; t["hist"] = t["hist"][:t["i"] + 1] + [url]; t["i"] += 1; self.render()

    def back(self):
        t = self.tabs[self.cur]
        if t["i"] > 0: t["i"] -= 1; self.render()

    def fwd(self):
        t = self.tabs[self.cur]
        if t["i"] < len(t["hist"]) - 1: t["i"] += 1; self.render()

    def new_tab(self):
        if len(self.tabs) >= 4: return
        self.tabs.append({"hist": [HOME], "i": 0}); self.cur = len(self.tabs) - 1; self.render()

    def close_tab(self, k):
        if len(self.tabs) == 1: return
        self.tabs.pop(k); self.cur = min(self.cur, len(self.tabs) - 1); self.render()

    def pick_tab(self, k): self.cur = k; self.render()

    def tx(self, p, t, pos, sc=0.032, fg=(0.05, 0.05, 0.1, 1), jp=False, align=TextNode.A_left, wrap=None):
        return U.text(p, t, pos, sc, fg=fg, font=self.app.jpfont if jp else U.FONT_PLAIN, align=align, wrap=wrap)

    def title_of(self, url):
        if url == HOME: return "IX NAVI"
        if url.startswith("ix://search"): return "Search"
        return URLS[url][1] if url in URLS else "Not found"

    def render(self):
        for c in self.root.get_children(): c.remove_node()
        r = self.root; a = self.app; T = lambda n: Filename.from_os_specific(os.path.join(a.BASE, "assets", "tex", n)).get_fullpath()
        # tabs
        for k, t in enumerate(self.tabs):
            x = W0 + 0.02 + k * 0.42; on = k == self.cur
            b = DirectButton(parent=r, frameColor=(0.98, 0.98, 1, 1) if on else (0.78, 0.8, 0.86, 1), frameSize=(0, 0.4, -0.035, 0.035), pos=(x, 0, 0.705),
                             relief=DGG.FLAT, command=self.pick_tab, extraArgs=[k])
            self.tx(b, self.title_of(t["hist"][t["i"]])[:20], (0.02, -0.01), 0.022)
            if len(self.tabs) > 1: U.button(b, "x", (0.37, 0.0), self.close_tab, w=0.018, h=0.018, scale=0.02, extra=[k], edge=(0.6, 0.6, 0.7, 1))
        if len(self.tabs) < 4: U.button(r, "+", (W0 + 0.06 + len(self.tabs) * 0.42, 0.705), self.new_tab, w=0.025, h=0.025, scale=0.03, edge=(0.4, 0.7, 0.9, 1))
        # toolbar: back / forward / reload / address bar
        DirectFrame(parent=r, frameColor=(0.86, 0.9, 0.95, 1), frameSize=(W0 + 0.015, W1 - 0.015, 0.57, 0.665))
        for k, (ic, fn) in enumerate((("ix_back.png", self.back), ("ix_fwd.png", self.fwd), ("ix_reload.png", self.render))):
            b = DirectButton(parent=r, image=T(ic), image_scale=0.026, relief=DGG.FLAT, frameColor=(0.25, 0.45, 0.7, 1), frameSize=(-0.035, 0.035, -0.035, 0.035),
                             pos=(W0 + 0.07 + k * 0.085, 0, 0.617), command=fn)
            b.set_transparency(TransparencyAttrib.M_alpha)
        self.addr = DirectEntry(parent=r, initialText=self.url, scale=0.032, width=44, pos=(W0 + 0.33, 0, 0.607), frameColor=(1, 1, 1, 1),
                                text_fg=(0.1, 0.1, 0.2, 1), entryFont=U.FONT_PLAIN, command=self.go, focus=0, numLines=1)
        U.button(r, "GO", (W1 - 0.08, 0.617), lambda: self.go(self.addr.get()), w=0.045, h=0.03, scale=0.026, edge=(0.25, 0.45, 0.7, 1))
        page = self.page = DirectFrame(parent=r, frameColor=(0, 0, 0, 0))
        url = self.url
        if url == HOME: self.p_home(page)
        elif url.startswith("ix://search"): self.p_search(page, url.split("q=", 1)[-1])
        elif url in URLS: getattr(self, "p_" + url.split(".")[0].replace("-", "_"))(page)
        else: self.p_404(page, url)

    # ---------------------------------------------------------------- pages
    def head(self, p, title, jp, col):
        DirectFrame(parent=p, frameColor=col, frameSize=(W0 + 0.015, W1 - 0.015, 0.42, 0.56))
        self.tx(p, title, (W0 + 0.05, 0.49), 0.05, fg=(1, 1, 1, 1)); self.tx(p, jp, (W0 + 0.05, 0.44), 0.03, fg=(1, 1, 1, 0.9), jp=True)

    def line(self, p, y, ja, en, sc=0.032):
        self.tx(p, ja, (W0 + 0.06, y), sc, jp=True, wrap=56); self.tx(p, en, (W0 + 0.06, y - sc * 1.25), sc * 0.78, fg=(0.35, 0.35, 0.45, 1), wrap=72)

    def link(self, p, url, y, x=W0 + 0.06):
        s = URLS[url]
        b = DirectButton(parent=p, frameColor=(0.94, 0.96, 1, 1), frameSize=(0, 1.0, -0.045, 0.045), pos=(x, 0, y), relief=DGG.FLAT, command=self.go, extraArgs=[url])
        self.tx(b, s[1], (0.02, 0.01), 0.028, fg=(0.1, 0.3, 0.8, 1)); self.tx(b, s[2] + "   " + url, (0.02, -0.03), 0.02, fg=(0.3, 0.45, 0.3, 1), jp=True)

    def p_home(self, p):
        self.tx(p, "IX NAVI", (0.12, 0.38), 0.11, fg=(0.15, 0.55, 0.85, 1), align=TextNode.A_center)
        self.tx(p, "ネオン東京のウェブを検索  -  search the Neon Tokyo web", (0.12, 0.3), 0.028, jp=True, align=TextNode.A_center)
        self.q = DirectEntry(parent=p, initialText="", scale=0.04, width=24, pos=(-0.42, 0, 0.18), frameColor=(1, 1, 1, 1), text_fg=(0.1, 0.1, 0.2, 1),
                             entryFont=U.FONT_PLAIN, command=lambda t: self.go("ix://search?q=" + t), focus=0)
        DirectFrame(parent=p, frameColor=(0.15, 0.55, 0.85, 1), frameSize=(-0.43, 0.56, 0.165, 0.17))
        U.button(p, "SEARCH", (0.75, 0.195), lambda: self.go("ix://search?q=" + self.q.get()), w=0.1, h=0.035, scale=0.026, edge=(0.15, 0.55, 0.85, 1))
        for k, s in enumerate(SITES):
            self.link(p, s[0], 0.02 - (k % 4) * 0.12, x=(W0 + 0.06) if k < 4 else 0.15)

    def p_search(self, p, q):
        ql = q.lower().strip(); words = [w for w in ql.replace("-", " ").split() if w]
        hits = [s for s in SITES if any(w in (s[0] + " " + s[1] + " " + s[3]).lower() or w in s[2] for w in words)] if words else list(SITES)
        self.tx(p, "「%s」の検索結果  -  results for \"%s\"" % (q, q), (W0 + 0.06, 0.5), 0.03, jp=True)
        if not hits: self.line(p, 0.38, "一致するサイトはありません。", "No matching sites. Try: news, cars, ramen, weather, homes, ex, social")
        for k, s in enumerate(hits): self.link(p, s[0], 0.4 - k * 0.12)

    def p_404(self, p, url):
        self.tx(p, "404", (0.12, 0.3), 0.2, fg=(0.85, 0.3, 0.5, 1), align=TextNode.A_center)
        self.tx(p, "ページが見つかりません", (0.12, 0.12), 0.05, jp=True, align=TextNode.A_center)
        self.tx(p, "Oops - \"%s\" isn't on the Neon Tokyo web (yet)." % url[:40], (0.12, 0.05), 0.03, align=TextNode.A_center)
        U.button(p, "GO HOME", (0.12, -0.1), lambda: self.go(HOME), w=0.14, h=0.04, scale=0.028, edge=(0.85, 0.3, 0.5, 1))

    def p_news(self, p):
        g = self.g; self.head(p, "NEON TOKYO NEWS", "ネオン東京ニュース", (0.75, 0.1, 0.12, 1)); y = 0.34
        items = []
        if g.tsunami is not None and not g.tsunami.drain:
            items.append(("【速報】光ビーチに津波警報！高台へ避難してください", "BREAKING: Tsunami warning at Hikari Beach! Get to high ground now"))
        for n in list(getattr(g, "news", []))[::-1][:4]:
            if n[0] == "tsunami":
                items.append(("光ビーチで津波（%s）が発生、現在は水が引いています" % {"small": "小", "medium": "中", "big": "大"}.get(n[1], ""),
                              "A %s tsunami hit Hikari Beach - the water has since drained away" % n[1].upper()))
            elif n[0] == "wanted":
                items.append(("警察が手配中の運転手、指名手配レベル%dで逃走" % n[1], "Police chase: a driver fled at WANTED level %d - still at large" % n[1]))
        items += [("新光交差点に新しいネオン看板が登場", "New neon signs light up Shinko Crossing"),
                  ("炎ラーメン、替え玉無料キャンペーン実施中", "HONOO RAMEN: free extra noodles all week"),
                  ("FRガレージ、DEBAUCHEの新色を発表", "FRGARAGE reveals new DEBAUCHE paint colours")]
        for ja, en in items[:6]:
            DirectFrame(parent=p, frameColor=(0.85, 0.85, 0.88, 1), frameSize=(W0 + 0.05, W1 - 0.05, y - 0.085, y - 0.083))
            self.line(p, y, ja, en); y -= 0.17

    def p_frgarage(self, p):
        from fs_vehicle import SPECS
        self.head(p, "FRGARAGE CAR DEALER", "FRガレージ 中古車センター", (0.1, 0.1, 0.12, 1))
        price = {"gts": 4800000, "coupe": 3900000, "sedan": 2200000, "taxi": 1500000, "hatch": 1300000, "kei": 900000, "suv": 2600000, "van": 1800000}
        for k, (kid, pr) in enumerate(price.items()):
            if kid not in SPECS: continue
            s = SPECS[kid]; x = W0 + 0.06 + (k % 2) * 1.08; y = 0.34 - (k // 2) * 0.2
            DirectFrame(parent=p, frameColor=(0.93, 0.93, 0.95, 1) if kid != "sedan" else (1.0, 0.92, 0.8, 1), frameSize=(0, 1.02, -0.08, 0.08), pos=(x, 0, y))
            self.tx(p, s["name"] + ("   ★ おすすめ PICK" if kid == "sedan" else ""), (x + 0.03, y + 0.02), 0.032, jp=kid == "sedan")
            self.tx(p, "¥%s   -   top speed %d km/h   -   %d kg" % (format(pr, ","), int(s["vmax"] * 3.6), s["mass"]), (x + 0.03, y - 0.04), 0.024, fg=(0.3, 0.3, 0.4, 1))
        self.line(p, -0.5, "ガレージでペイントとナンバープレートを変更できます。", "Visit the garage to change paint and plates.")

    def p_honoo_ramen(self, p):
        self.head(p, "HONOO RAMEN & BAR", "炎ラーメン＆バー  -  灯町", (0.85, 0.3, 0.05, 1))
        menu = [("醤油ラーメン", "Shoyu ramen", 900), ("味噌ラーメン", "Miso ramen", 950), ("とんこつラーメン", "Tonkotsu ramen", 1000),
                ("餃子（六個）", "Gyoza (6)", 400), ("ビール", "Beer", 600), ("日本酒", "Sake", 800), ("ハイボール", "Highball", 700), ("緑茶", "Green tea", 150)]
        for k, (ja, en, pr) in enumerate(menu):
            x = W0 + 0.06 + (k // 4) * 1.08; y = 0.34 - (k % 4) * 0.15
            self.tx(p, ja, (x, y), 0.036, jp=True); self.tx(p, en, (x, y - 0.045), 0.026, fg=(0.4, 0.4, 0.5, 1))
            self.tx(p, "¥%d" % pr, (x + 0.95, y - 0.02), 0.034, fg=(0.8, 0.3, 0.0, 1), align=TextNode.A_right)
        self.line(p, -0.35, "営業時間：十一時から二十三時まで。バーは光ビーチにもあります！", "Open 11:00-23:00. Our beach bar is down on Hikari Beach!")

    def p_tenki(self, p):
        g = self.g; self.head(p, "NEON TOKYO WEATHER", "ネオン東京の天気", (0.2, 0.55, 0.9, 1))
        rain = self.app.settings.get("rain", False); tod = getattr(g, "tod", 12.0) % 24
        self.tx(p, "雨" if rain else ("晴れ" if 6 <= tod < 18 else "晴れの夜"), (W0 + 0.1, 0.25), 0.1, jp=True, fg=(0.15, 0.35, 0.7, 1))
        self.tx(p, ("RAIN" if rain else ("SUNNY" if 6 <= tod < 18 else "CLEAR NIGHT")) + "   %d°C" % (24 if 6 <= tod < 18 else 19), (W0 + 0.1, 0.13), 0.05)
        for k, (d, ja, en, t) in enumerate((("MON", "晴れ", "Sunny", 26), ("TUE", "曇り", "Cloudy", 23), ("WED", "雨", "Rain", 20), ("THU", "晴れ", "Sunny", 25), ("FRI", "雷雨", "Storms", 22))):
            x = W0 + 0.15 + k * 0.42
            self.tx(p, d, (x, -0.1), 0.03); self.tx(p, ja, (x, -0.18), 0.04, jp=True); self.tx(p, "%s  %d°" % (en, t), (x, -0.24), 0.024)
        if g.tsunami is not None and not g.tsunami.drain: self.line(p, -0.4, "【津波警報】沿岸部の方はすぐに避難してください。", "TSUNAMI WARNING: coastal areas evacuate now.")

    def p_sumika_homes(self, p):
        self.head(p, "SUMIKA HOMES", "すみかホーム  -  不動産", (0.3, 0.6, 0.35, 1))
        L = [("新光タワー 2LDK", "Shinko Tower 2LDK - city view", "¥210,000 / month"), ("光ビーチ 一戸建て", "Hikari Beach house - sea view", "¥68,000,000"),
             ("灯町 ワンルーム", "Akari-cho studio - above a ramen shop", "¥72,000 / month"), ("黒金 倉庫ロフト", "Kurogane warehouse loft", "¥145,000 / month")]
        for k, (ja, en, pr) in enumerate(L):
            y = 0.32 - k * 0.18
            DirectFrame(parent=p, frameColor=(0.55 + 0.1 * k, 0.7, 0.8 - 0.1 * k, 1), frameSize=(W0 + 0.06, W0 + 0.3, y - 0.07, y + 0.07))
            self.tx(p, ja, (W0 + 0.36, y + 0.02), 0.036, jp=True); self.tx(p, en, (W0 + 0.36, y - 0.035), 0.026, fg=(0.4, 0.4, 0.5, 1))
            self.tx(p, pr, (W1 - 0.06, y), 0.032, fg=(0.2, 0.5, 0.25, 1), align=TextNode.A_right)

    def p_exromania(self, p):
        self.head(p, "EX ROMANIA FAN PAGE", "EX ROMANIA ファンページ", (0.15, 0.55, 0.25, 1))
        self.line(p, 0.32, "EX ROMANIA が作るゲームとアプリのファンページです。", "The fan page for games and apps from EX ROMANIA.")
        self.line(p, 0.16, "新機能：MISTO 2 で消える写真を友達に送ろう。", "New: send disappearing snaps to friends with MISTO 2.")
        self.line(p, 0.0, "いま注目：FIREOUT ONLINE のエリジャー。", "Now playing: Elijer in FIREOUT ONLINE.")
        self.line(p, -0.16, "コピーライト：", "©2026 EX ROMANIA/EX INC.")

    def p_kirakira(self, p):
        """the social feed: the player's own selfies (newest first), each with DELETE"""
        g = self.g; self.head(p, "KIRAKIRA SOCIAL", "キラキラ・ソーシャル  -  あなたのフィード", (0.95, 0.4, 0.65, 1))
        from fs_game import NAMES
        ph = g.photo_list()[::-1][:3]
        if not ph: self.line(p, 0.3, "まだ投稿がありません。スマホで自撮りしてみよう！", "No posts yet - take a selfie with the phone camera!"); return
        for k, path in enumerate(ph):
            x = W0 + 0.06 + k * 0.73
            DirectFrame(parent=p, frameColor=(0.96, 0.95, 0.98, 1), frameSize=(0, 0.69, -0.88, 0.0), pos=(x, 0, 0.4))
            self.tx(p, "@%s" % NAMES[g.active].lower(), (x + 0.03, 0.35), 0.026, fg=(0.8, 0.2, 0.5, 1))
            try:
                tex = self.app.loader.load_texture(Filename.from_os_specific(path)); OnscreenImage(parent=p, image=tex, pos=(x + 0.345, 0, 0.12), scale=(0.32, 1, 0.18))
            except Exception: pass
            ts = os.path.basename(path)
            self.tx(p, "いいね！ %d" % (12 + (hash(ts) % 80)), (x + 0.03, -0.12), 0.028, jp=True, fg=(0.85, 0.2, 0.4, 1))
            self.tx(p, ts[:30], (x + 0.03, -0.17), 0.02, fg=(0.4, 0.4, 0.5, 1))
            self.lap.del_btn(p, (x + 0.52, -0.4), path, lambda: self.render())
