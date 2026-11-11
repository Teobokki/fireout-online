# v1.0.4 IX LAPTOPOS G9 + IX NAVI browser + photo delete + MISTO 2. FS_TESTSCRIPT=test/laptop.py
import os, math, traceback, json
from panda3d.core import Filename
OUT = os.path.join(app.BASE, "docs")
def G(): return app.game
def step(n=1):
    for _ in range(n): G().step(1 / 30.0)
def shot(name, hud=True):
    if not hud: app.aspect2d.hide()
    app.graphicsEngine.render_frame(); app.graphicsEngine.render_frame()
    app.win.save_screenshot(Filename.from_os_specific(os.path.join(OUT, name + ".png"))); print("SHOT", name, flush=True)
    app.aspect2d.show()
def place(x, y, h, tod=13.0):
    g = G(); app.settings["tod"] = "day"; g.tod = tod; me = g.me(); me.x, me.y, me.h = x, y, h; g.cam_yaw = h; me.sync(); g.cam_pos = None; step(30)
def selfies():
    g = G(); place(12, -40, 180)
    for k in range(3):
        g.open_camera(); step(10); g.cam_set_expr(["smile", "neutral", "frown"][k]); step(3); g.cam_shutter(); step(5); g.close_camera(); step(3); g.cam_yaw += 40
    print("RESULT photos", len(g.photo_list()), [os.path.basename(p) for p in g.photo_list()], flush=True)
def laptop():
    g = G(); place(12, -40, 0); g.refresh_buttons(); step(2); shot("laptop_hud_button")
    g.key_l(); step(20)
    me = g.me(); h = math.radians(me.h); fx, fy = -math.sin(h), math.cos(h)
    app.aspect2d.hide(); app.camera.set_pos(me.x - fx * 1.6 + fy * 0.9, me.y - fy * 1.6 - fx * 0.9, 2.1); app.camera.look_at(me.x + fx * 0.3, me.y + fy * 0.3, 1.15)
    shot("laptop_prop", False); app.aspect2d.show()
    step(30); shot("laptop_boot"); step(60); shot("laptop_desktop")
    L = g.laptop; L.app_bank(); step(1); shot("laptop_bank")
    L.app_browser(); step(1); shot("laptop_browser")
    L.browser.go("ramen"); step(1); shot("_laptop_search")
    g.miyo.start_tsunami("small"); g.add_heat(3, ""); step(5)
    L.browser.go("news.neontokyo.jp"); step(1); shot("laptop_site_news")
    L.browser.new_tab(); L.browser.go("frgarage.jp/cars"); step(1); shot("laptop_site_cars")
    L.browser.go("nowhere.example"); step(1); shot("laptop_404")
    L.browser.go("kirakira.social"); step(1); shot("_social_feed")
    p = g.photo_list()[-1]
    L.confirm_delete(p, lambda: L.browser.render()); step(1); shot("social_feed_delete")
    L.dlg.ok(); step(2); shot("_social_after_delete")
    print("RESULT deleted", os.path.basename(p), "exists", os.path.exists(p), "in list", p in g.photo_list(), flush=True)
    sv = json.load(open(app.save_path())); print("RESULT save photos", len(sv.get("photos", [])), p in sv.get("photos", []), flush=True)
    L.app_photos(); step(1); shot("laptop_photos")
    L.app_email(0); step(1); shot("_laptop_email"); L.app_shop(); step(1); shot("_laptop_shop"); L.app_music(); step(1); shot("_laptop_music"); L.app_map(); step(1); shot("_laptop_map")
    g.miyo.stop_tsunami(); g.heat = 0; L.close(); step(200)
    print("RESULT laptop closed", L.ui is None, g.overlay, flush=True)
def misto():
    g = G(); place(12, -40, 180)
    import fs_misto
    fs_misto.open_app(g); step(10); shot("misto2_camera")
    print("RESULT face", fs_misto.face_xform(g), app.camera.get_pos(), g.me().np.get_pos(app.render), flush=True)
    g.camapp["cap_ent"].enterText("TOKYO NIGHTS!"); fs_misto.set_lens(g, "cat"); g.cam_set_expr("smile"); step(3); shot("misto2_filters")
    g.cam_shutter(); step(3); shot("_misto2_snap")
    ui = g.overlay.mui; ui.show("send", ui.cur); step(1); shot("_misto2_send")
    ui.send("daniel", ui.cur); step(1)
    step(3); ui.reply("daniel")
    ui.show("chat", "daniel"); step(1); shot("misto2_chat")
    c = [x for x in g.misto["chats"]["daniel"] if x[0] != "me"][-1]; ui.view("daniel", c); step(3); shot("_misto2_view")
    for _ in range(200): step(1); app.task_mgr.step() if False else None
    ui.post(ui.cur) if hasattr(ui, "cur") else None; ui.show("stories"); step(1); shot("_misto2_stories")
    print("RESULT misto streak", g.misto["streak"], "chats", {k: len(v) for k, v in g.misto["chats"].items()}, flush=True); ui.close()
    g.key_l(); step(160); g.laptop.app_misto(); step(1); shot("_laptop_misto"); g.laptop.close()
def bar():
    g = G(); b = g.bar; place(b.x - 1.0, b.y, -90, 17.5); g.cash = 9000; step(3)
    print("RESULT bar near", b.near(), "prompt", g.prompt["text"], flush=True); shot("bar_prompt")
    g.key_e(); step(2); shot("bar_menu"); b.order("beer")
    me = g.me()
    def cam():
        app.camera.set_pos(b.x + 0.9, b.y - 1.5, 1.8); app.camera.look_at(b.x - 0.95, b.y, 1.35); app.camLens.set_fov(55)
    t = 0.0; k = 0
    for target in (0.35, 1.6, 2.1, 4.25):
        while t < target and g.eating is not None: g.step(1 / 30.0); t += 1 / 30.0
        cam(); shot("_bar_%d" % k, False); k += 1
    while g.eating is not None: g.step(1 / 30.0)
    print("RESULT drunk", g.drunk, flush=True)
    b.order("water")
    while g.eating is not None: g.step(1 / 30.0)
    print("RESULT drunk after water", g.drunk, flush=True)
import time as _t
_T0 = _t.time()
PLAN = [(0.1, lambda: app.show_title()), (0.3, lambda: app.show_menu()), (0.3, lambda: app.start_game(None)), (1.0, lambda: None),
        (0.1, lambda: [G().step(1 / 30.0) for _ in range(250)]), (0.1, selfies), (0.1, laptop), (0.1, misto), (0.1, bar), (0.5, lambda: None), (0.1, lambda: app.userExit())]
state = {"i": 0, "t": 0.0}
def runner(task):
    try:
        if state["i"] >= len(PLAN): return task.done
        d, f = PLAN[state["i"]]
        if app.world is None or (state["i"] > 2 and getattr(app, "game", None) is None): return task.cont
        if state["i"] == 0 and _t.time() - _T0 < 9.0: return task.cont
        state["t"] += 0.05
        if state["t"] >= d: state["t"] = 0.0; state["i"] += 1; f()
    except Exception:
        print("TESTERR", traceback.format_exc(), flush=True)
    return task.cont
app.task_mgr.add(runner, "test-runner", sort=100)
