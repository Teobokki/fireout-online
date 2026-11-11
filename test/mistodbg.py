import os, math, traceback
from panda3d.core import Filename
def G(): return app.game
def step(n=1):
    for _ in range(n): G().step(1 / 30.0)
def shot(name):
    app.graphicsEngine.render_frame(); app.graphicsEngine.render_frame()
    app.win.save_screenshot(Filename.from_os_specific(os.path.join(app.BASE, "docs", name + ".png"))); print("SHOT", name, flush=True)
def run():
    g = G(); app.settings["tod"] = "day"; g.tod = 13; me = g.me(); me.x, me.y, me.h = 12, -40, 180; g.cam_yaw = 180; me.sync(); step(20)
    import fs_misto
    fs_misto.open_app(g); step(10); fs_misto.set_lens(g, "cat"); step(5)
    ln = g.camapp["lens_np"]
    print("RESULT ln", ln.get_pos(), ln.get_scale(), fs_misto.face_xform(g), app.win.get_x_size(), app.win.get_y_size(), flush=True)
    shot("_mdbg"); fs_misto.set_lens(g, "shades"); g.camapp["ang"] = 0.4; step(10); shot("_mdbg2")
    print("RESULT ln2", g.camapp["lens_np"].get_pos(), g.camapp["lens_np"].get_scale(), fs_misto.face_xform(g), flush=True)
import time as _t
_T0 = _t.time()
PLAN = [(0.1, lambda: app.show_title()), (0.3, lambda: app.show_menu()), (0.3, lambda: app.start_game(None)), (1.0, lambda: None),
        (0.1, lambda: [G().step(1 / 30.0) for _ in range(100)]), (0.1, run), (0.1, lambda: app.userExit())]
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
