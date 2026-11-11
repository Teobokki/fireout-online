# v1.0.4 taxi body check: outside (front 3/4 + side + close-up) and first-person. FS_TESTSCRIPT=test/taxifix.py
import os, math, traceback
from panda3d.core import Filename
OUT = os.path.join(app.BASE, "docs")
def G(): return app.game
def step(n=1):
    for _ in range(n): G().step(1 / 30.0)
def shot(name):
    app.aspect2d.hide(); app.graphicsEngine.render_frame(); app.graphicsEngine.render_frame()
    app.win.save_screenshot(Filename.from_os_specific(os.path.join(OUT, name + ".png"))); print("SHOT", name, flush=True); app.aspect2d.show()
def run():
    g = G(); app.settings["tod"] = "day"; g.tod = 13.0; me = g.me(); me.x, me.y, me.h = 30, -32, 90; me.sync(); g.cam_pos = None; step(30)
    c = g.spawn_car("taxi", me.x - 4, me.y, 90, role="taxi"); c.driver = "ai"; g.taxi = c
    s = g.spawn_car("sedan", me.x - 4, me.y + 6, 90)
    from fs_ai import ResponderAI
    c.ai = ResponderAI(g, c, (me.x, me.y)); c.ai.arrived = True; g.board_taxi(); step(20)
    print("RESULT near", app.camLens.get_near(), flush=True)
    shot("_tf_fp")
    g.paused = False
    x0, y0, h0 = c.x, c.y, c.h
    for _ in range(150):
        g.step(1 / 30.0); c.x, c.y, c.h, c.vx, c.vy = x0, y0, h0, 0, 0; c.np.set_pos(x0, y0, 0); c.np.set_h(h0)
    g.paused = True; me.np.show(); c.taxi_driver.set_chew(1.0)
    r = math.radians(c.h); fx, fy = -math.sin(r), math.cos(r); rx, ry = math.cos(r), math.sin(r)
    views = [("_tf_front", (fx * 5.5 + rx * 3.5, fy * 5.5 + ry * 3.5, 2.0), 1.0, 50),
             ("_tf_side", (rx * 5.5, ry * 5.5, 1.6), 0.9, 50),
             ("_tf_close", (fx * 2.4 + rx * 0.9, fy * 2.4 + ry * 0.9, 1.35), 1.4, 25),
             ("_tf_close2", (fx * 3.6 + rx * 1.2, fy * 3.6 + ry * 1.2, 1.45), 1.3, 30)]
    for nm, (ox, oy, oz), lz, fov in views:
        app.camera.set_pos(c.x + ox, c.y + oy, oz); app.camera.look_at(c.x, c.y, lz); app.camLens.set_fov(fov); shot(nm)
    d = c.taxi_driver; hp = d.np.get_pos(app.render)
    print("RESULT nodes", sorted(set(n.get_name() for n in d.model.find_all_matches("**/+GeomNode"))), flush=True)
    print("RESULT parents", sorted(set(n.get_parent().get_name() for n in d.model.find_all_matches("**/+GeomNode"))), flush=True)
    if d.head is not None if hasattr(d, "head") else False: pass
    app.camera.set_pos(c.x + fx * 2.3 + rx * 0.75, c.y + fy * 2.3 + ry * 0.75, 1.62); app.camera.look_at(hp[0], hp[1], hp[2] + 1.42); app.camLens.set_fov(24); shot("taxi_driver")
    app.camera.set_pos(c.x + rx * 1.6 + fx * 0.5, c.y + ry * 1.6 + fy * 0.5, 1.5); app.camera.look_at(hp[0], hp[1], hp[2] + 1.1); app.camLens.set_fov(45); shot("_tf_driver_side")
    # back / side of the driver with the car body hidden (diagnostic for shoulder shapes)
    hid = [n for n in c.np.get_children() if n != d.np and not n.is_hidden()]
    for n in hid: n.hide()
    hz = hp[2] + 1.25
    for nm, (ox, oy, oz) in (("_tdb_back", (-fx * 2.0 + rx * 0.2, -fy * 2.0 + ry * 0.2, 0.3)), ("_tdb_side", (rx * 1.4 - fx * 0.3, ry * 1.4 - fy * 0.3, 0.1)),
                             ("_tdb_back3", (-fx * 1.0 - rx * 0.9, -fy * 1.0 - ry * 0.9, 0.35))):
        app.camera.set_pos(hp[0] + ox, hp[1] + oy, hz + oz); app.camera.look_at(hp[0], hp[1], hz + 0.05); app.camLens.set_fov(45); shot(nm)
        print("RESULT cam", nm, "driver fwd", d.np.get_quat(app.render).get_forward(), "car fwd", fx, fy, flush=True)
    for n in hid: n.show()
    s.model.find("**/glass")  # sedan untouched check
    g.paused = False
    from panda3d.core import TransformState
    for k in range(40): g.populate(); g.step(1 / 30.0)
    g.taxi_go((-100, 100), "TEST RIDE"); t = 0
    while g.ride and t < 3600:
        g.step(1 / 30.0); t += 1
        if t % 60 == 0: TransformState.garbage_collect()
        if t % 300 == 0: print("RESULT ride t", t // 30, "pos", round(c.x), round(c.y), "speed", round(c.speed, 1), "bumps", g.ride and g.ride.get("bumped"), flush=True)
    print("RESULT ride finished", g.ride is None, "after s", t // 30, flush=True)
    app.camera.set_pos(s.x + fx * 5.5 + rx * 3.5, s.y + fy * 5.5 + ry * 3.5, 2.0); app.camera.look_at(s.x, s.y, 1.0); app.camLens.set_fov(50); shot("_tf_sedan")
import time as _t
_T0 = _t.time()
PLAN = [(0.1, lambda: app.show_title()), (0.3, lambda: app.show_menu()), (0.3, lambda: app.start_game(None)), (1.0, lambda: None),
        (0.1, run), (0.1, lambda: app.userExit())]
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
