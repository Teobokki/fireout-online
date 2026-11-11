# House free-roam smoke: walk around the interior, every spot's [E] prompt, collision + camera. FS_TESTSCRIPT=test/house.py
import os, math, traceback
from panda3d.core import Filename
import fs_data as D
OUT = os.environ.get("FS_POSE_OUT", os.path.join(app.BASE, "docs"))
X, Y = D.HOME_INT
def G(): return app.game
BAD = []
def cam_ok():
    g = G(); c = app.camera.get_pos(); b = g.world.home_bounds
    if not (b[0] - 0.1 < c.x < b[2] + 0.1 and b[1] - 0.1 < c.y < b[3] + 0.1 and c.z < 3.15): return False
    return not any(r[0] < c.x < r[2] and r[1] < c.y < r[3] for r in g.world.home_cam_rects)
def inside_solid(x, y):
    return any(r[0] + 0.05 < x < r[2] - 0.05 and r[1] + 0.05 < y < r[3] - 0.05 for r in G().world.home_cam_rects)
def step(n=1):
    g = G()
    for _ in range(n):
        g.step(1 / 30.0)
        if g.home and g.home.get("mode") == "room":
            me = g.me()
            if not cam_ok(): BAD.append(("cam", round(app.camera.get_x() - X, 2), round(app.camera.get_y() - Y, 2)))
            if inside_solid(me.x, me.y): BAD.append(("wall", round(me.x - X, 2), round(me.y - Y, 2)))
def goto(wps, run=False, tmax=12.0):
    g = G(); me = g.me()
    for (tx, ty) in wps:
        tx += X; ty += Y; t = 0.0
        while math.hypot(tx - me.x, ty - me.y) > 0.35 and t < tmax:
            g.cam_yaw = math.degrees(math.atan2(-(tx - me.x), ty - me.y)); g.vb.clear(); g.vb["v_up"] = True; g.vb["v_nitro"] = run
            step(); t += 1 / 30.0
        g.vb.clear()
        print("RESULT goto (%.1f,%.1f) -> at (%.2f,%.2f) %s" % (tx - X, ty - Y, me.x - X, me.y - Y, "OK" if t < tmax else "TIMEOUT"), flush=True)
    step(3)
def bump(heading, sec=2.0):
    g = G(); me = g.me(); g.vb.clear(); g.vb["v_up"] = True
    for _ in range(int(sec * 30)): g.cam_yaw = heading; step()
    g.vb.clear(); print("RESULT bump h=%d end=(%.2f,%.2f)" % (heading, me.x - X, me.y - Y), flush=True)
def spot():
    g = G(); sp = g.home_spot(); s = sp[0] if sp else None
    lbl = None
    try: lbl = g.home_btn is not None
    except Exception: pass
    print("RESULT spot", s, "button", lbl, flush=True); return s
def use(expect):
    g = G(); s = spot(); print("RESULT use", expect, "match", s == expect, flush=True); g.key_e(); step(10)
    print("RESULT mode after", expect, g.home and g.home.get("mode"), flush=True)
def shot(name):
    app.graphicsEngine.render_frame(); app.graphicsEngine.render_frame()
    app.win.save_screenshot(Filename.from_os_specific(os.path.join(OUT, name + ".png"))); print("SHOT", name, flush=True)
def enter():
    g = G(); g.paused = False; g.enter_home(); step(30); print("RESULT entered", g.home is not None, "overlay", g.overlay, flush=True)
def check():
    print("RESULT bad_count", len(BAD), BAD[:10], flush=True)
def leave():
    g = G(); goto([(-1.0, 1.6), (2.8, -0.2), (4.0, -4.0)]); use("leave"); print("RESULT left", g.home is None, flush=True)
    me = g.me(); g.vb["v_up"] = True; x0, y0 = me.x, me.y
    for _ in range(60): g.cam_yaw = -90; g.step(1 / 30.0)
    g.vb.clear(); print("RESULT outside walk dist=%.2f" % math.hypot(me.x - x0, me.y - y0), flush=True)
import time as _t
_T0 = _t.time()
PLAN = [
    (0.1, lambda: app.show_title()), (0.3, lambda: app.show_menu()), (0.3, lambda: app.start_game(None)), (1.0, lambda: None),
    (0.1, lambda: [G().step(1 / 30.0) for _ in range(300)]),
    (0.1, enter), (0.1, lambda: goto([(2.5, -2.0), (0.5, -1.0), (-0.8, 0.2), (-1.0, 3.6), (-2.6, 3.9)])), (0.1, lambda: goto([(-3.2, 2.6)])), (0.1, lambda: shot("house_free_roam")),
    (0.1, lambda: goto([(-1.0, 3.6), (-0.8, 0.2), (1.25, -3.4)])), (0.1, spot), (0.1, lambda: shot("house_interact_prompt")), (0.1, lambda: use("tv")),
    (0.1, lambda: goto([(3.0, -0.0), (4.5, 1.8)])), (0.1, lambda: use("eat")),
    (0.1, lambda: goto([(1.3, 0.2)])), (0.1, lambda: use("save")),
    (0.1, lambda: goto([(-1.0, 0.0), (-1.0, 3.8), (-3.2, 3.8), (-3.1, 0.5), (-3.1, -3.6)])), (0.1, lambda: use("wardrobe")),
    (0.1, lambda: G().close_wardrobe(False)), (0.1, lambda: step(20)),
    (0.1, lambda: goto([(-4.0, -2.1)])), (0.1, lambda: use("sleep")),
    (0.1, lambda: bump(90, 3.0)), (0.1, lambda: bump(180, 2.0)),
    (0.1, lambda: goto([(-3.1, 0.5), (-3.2, 3.8), (-6.0, 3.7), (-6.1, 2.4)])), (0.1, spot), (0.1, lambda: shot("house_interact_shower")),
    (0.1, lambda: use("shower")), (0.1, lambda: step(40)), (0.1, lambda: G().key_e()), (0.1, lambda: step(10)),
    (0.1, lambda: print("RESULT after shower mode", G().home.get("mode"), flush=True)),
    (0.1, lambda: bump(-90, 4.0)), (0.1, lambda: bump(0, 2.0)),
    (0.1, lambda: shot("house_wall_cam")),
    (0.1, lambda: G().switch_char()), (0.1, lambda: goto([(3.9, 3.8), (0.0, 4.0), (-3.0, 4.0)], run=True)),
    (0.1, lambda: G().switch_char()),
    (0.1, check), (0.1, leave), (0.1, check),
    (0.1, lambda: app.userExit()),
]
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
