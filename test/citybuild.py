# v1.0.4 city-style MIYOYAZU builds. FS_TESTSCRIPT=test/citybuild.py
import os, math, traceback, time as _t
from panda3d.core import Filename, TransformState
OUT = os.environ.get("FS_POSE_OUT", os.path.join(app.BASE, "docs"))
def G(): return app.game
def step(n=1):
    for _ in range(n): G().step(1 / 30.0)
def shot(name, hud=False):
    if not hud: app.render2d.hide(); app.aspect2d.hide()
    app.graphicsEngine.render_frame(); app.graphicsEngine.render_frame()
    app.win.save_screenshot(Filename.from_os_specific(os.path.join(OUT, name + ".png"))); print("SHOT", name, flush=True)
    if not hud: app.render2d.show(); app.aspect2d.show()
def place(x, y, h, tod=14.5):
    g = G(); g.paused = False; g.tod = tod; app.settings["tod"] = "day" if 7 < tod < 17 else "cycle"
    me = g.me(); me.x, me.y, me.h = x, y, h; g.cam_yaw = h; me.sync(); g.cam_pos = None
    b = g.buddy(); b.x, b.y = x + 2, y - 2; b.sync(); step(25)
def st(tag=""):
    g = G(); me = g.me()
    print("RESULT", tag, "pos %.1f %.1f z %.2f" % (me.x, me.y, me.np.get_z()), "builds", [(i["label"], len(i["cols"])) for i in g.builds.items], flush=True)
def view(name, it, dist, up, ang=35, at=None, fov=55):
    cx, cy = it["center"]; g = G(); me = g.me()
    a = math.atan2(me.y - cy, me.x - cx) + math.radians(ang)
    app.camera.set_pos(cx + math.cos(a) * dist, cy + math.sin(a) * dist, up); app.camera.look_at(cx, cy, at if at is not None else up * 0.5)
    app.camLens.set_fov(fov if dist < 100 else 68); shot(name); app.camLens.set_fov(70)
def mk(text, name, dist, up, at, ang=35, x=530, y=-120, h=0, tod=14.5):
    def f():
        g = G(); g.miyo.clear(); place(x, y, h, tod); g.miyo.start_build(text); step(70); TransformState.garbage_collect()
        it = g.builds.items[-1]; st("built " + text); view(name, it, dist, up, ang, at)
    return f
def walk(sec, f=1):
    g = G(); g.vb["v_up"] = f > 0; g.vb["v_down"] = f < 0; step(int(sec * 30)); g.vb.clear(); st("walked")
_T0 = _t.time()
PLAN = [(0.1, lambda: app.show_title()), (0.3, lambda: app.show_menu()), (0.3, lambda: app.start_game(None)), (1.0, lambda: None),
        (0.1, lambda: [G().step(1 / 30.0) for _ in range(200)]), (0.1, lambda: G().select_char("miyo")), (0.1, lambda: step(5)),
        (0.1, mk("japanese pagoda", "miyo_build_city_1", 34, 9, 10)),
        (0.1, mk("house", "miyo_build_city_2", 20, 5, 3.5)),
        (0.1, mk("skyscraper", "miyo_build_city_3", 135, 30, 50, 30)),
        (0.1, mk("japanese castle", "_cb_castle", 50, 10, 14)),
        (0.1, mk("ramen shop", "_cb_shop", 18, 4, 3)),
        (0.1, mk("giant cat statue", "_cb_cat", 22, 6, 4)),
        (0.1, mk("zorblax emporium", "_cb_invent", 45, 10, 14)),
        (0.1, mk("sakura park", "_cb_park", 22, 7, 2)),
        (0.1, mk("temple", "_cb_temple", 36, 8, 5)),
        (0.1, mk("lighthouse", "_cb_light", 36, 8, 12)),
        (0.1, mk("pyrmid", "_cb_pyr", 55, 10, 8)),
        (0.1, mk("japanese pagoda", "_cb_pagoda_night", 34, 9, 10, tod=21.5)),
        # collision: walk into the house (blocked), climb the stairs (stand height rises)
        (0.1, mk("house", "_cb_house2", 20, 5, 3.5)), (0.1, lambda: walk(4.0)), (0.1, lambda: st("walk into house (expect blocked ~4.5 m short)")),
        (0.1, mk("stairs", "_cb_stairs", 14, 6, 2)), (0.1, lambda: [walk(0.5) for _ in range(10)]), (0.1, lambda: st("on stairs (expect z ~4.5)")),
        (0.1, lambda: (G().miyo.start_build("house"), step(60), G().miyo.undo(), st("undo"), G().miyo.clear(), st("clear"),
                       print("RESULT fac_nodes", len(G().world.fac_nodes), flush=True))),
        (0.1, lambda: app.userExit())]
state = {"i": 0, "t": 0.0}
def runner(task):
    try:
        if state["i"] >= len(PLAN): return task.done
        d, f = PLAN[state["i"]]
        if app.world is None or (state["i"] > 2 and getattr(app, "game", None) is None): return task.cont
        if state["i"] == 0 and _t.time() - _T0 < 9.0: return task.cont
        state["t"] += 0.05
        if state["t"] >= d:
            state["t"] = 0.0; state["i"] += 1; f()
    except Exception:
        print("TESTERR", traceback.format_exc(), flush=True); state["i"] += 1
    return task.cont
app.task_mgr.add(runner, "test-runner", sort=100)
