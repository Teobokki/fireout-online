# glow / bloom check: city, house and legs shots. FS_TAG=before|after
import os, math, traceback
from panda3d.core import Filename
OUT = os.path.join(app.BASE, "docs"); TAG = os.environ.get("FS_TAG", "after")
def G(): return app.game
def step(n=1):
    for _ in range(n): G().step(1 / 30.0)
def shot(name, hud=False):
    if not hud: app.aspect2d.hide()
    app.graphicsEngine.render_frame(); app.graphicsEngine.render_frame()
    app.win.save_screenshot(Filename.from_os_specific(os.path.join(OUT, name + ".png"))); print("SHOT", name, flush=True)
    app.aspect2d.show()
def city():
    g = G(); app.settings["tod"] = "day"; g.tod = 13.0; me = g.me(); me.x, me.y, me.h = 8, -30, 180; me.sync(); g.cam_yaw = 180; g.cam_pos = None; step(40)
    app.camera.set_pos(me.x + 3, me.y + 9, 3.0); app.camera.look_at(me.x, me.y - 30, 8); app.camLens.set_fov(70); shot("_city_" + TAG)
def legs():
    g = G(); me = g.me(); me.x, me.y, me.h = 452, -300, 90; me.sync(); step(20)
    h = math.radians(me.h + 20); fx, fy = -math.sin(h), math.cos(h)
    app.camera.set_pos(me.x + fx * 2.6, me.y + fy * 2.6, 1.0); app.camera.look_at(me.x, me.y, 0.8); app.camLens.set_fov(50); shot("_legs_" + TAG); app.camLens.set_fov(70)
def house():
    g = G(); g.enter_home(); step(40); shot("_house_" + TAG); g.leave_home(); step(10)
import time as _t
_T0 = _t.time()
PLAN = [(0.1, lambda: app.show_title()), (0.3, lambda: app.show_menu()), (0.3, lambda: app.start_game(None)), (1.0, lambda: None),
        (0.1, lambda: [G().step(1 / 30.0) for _ in range(200)]), (0.1, city), (0.1, legs), (0.1, house), (0.1, lambda: app.userExit())]
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
        print("TESTERR", traceback.format_exc(), flush=True); state["i"] += 1
    return task.cont
app.task_mgr.add(runner, "test-runner", sort=100)
