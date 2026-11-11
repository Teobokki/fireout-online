# v1.0.5.3 "bumper jumps" check: per-frame front bumper / plate height + close-up frame strip. FS_TESTSCRIPT=test/bumper.py  FS_BUMPTAG=before|after
import os, math, traceback, json
from panda3d.core import Filename, Point3
OUT = "/workspace/fs_bump"; TAG = os.environ.get("FS_BUMPTAG", "x")
def G(): return app.game
def shot(name):
    app.aspect2d.hide(); app.graphicsEngine.render_frame()
    app.win.save_screenshot(Filename.from_os_specific(os.path.join(OUT, name + ".png"))); app.aspect2d.show()
def run():
    g = G(); app.settings["tod"] = "day"; g.tod = 13.0; me = g.me(); me.x, me.y, me.h = 30, -32, 90; me.sync(); g.cam_pos = None
    for _ in range(20): g.step(1 / 30.0)
    c = g.spawn_car("sedan", 60, -32, 0); c.wake(); c.driver = "test"
    log = []
    # throttle script (keyboard-like on/off, as the player does; then AI-style stop at a light)
    plan = [1] * 30 + [0] * 8 + [1] * 10 + [-1] * 25 + [0] * 10 + [1] * 12 + [-1] * 20
    for i, thr in enumerate(plan):
        c.throttle = thr; c.steer = 0.4 if 40 < i < 70 else 0.0
        g.step(1 / 30.0); c.sync(0.0)
        bp = app.render.get_relative_point(c.model, Point3(0, c.spec["hl"], 0.35))     # bumper on the body
        pl = c.plates[0].get_pos(app.render)                                            # front plate
        log.append(dict(i=i, thr=thr, v=round(c.fspeed(), 2), bump=round(bp[2], 4), plate=round(pl[2], 4), pitch=round(c.model.get_p(), 3)))
        if i % 2 == 0 and 26 <= i < 60:
            r = math.radians(c.h); fx, fy = -math.sin(r), math.cos(r); rx, ry = math.cos(r), math.sin(r)
            app.camera.set_pos(c.x + fx * 3.2 + rx * 2.6, c.y + fy * 3.2 + ry * 2.6, 0.7); app.camera.look_at(c.x + fx * 2.3, c.y + fy * 2.3, 0.4); app.camLens.set_fov(40)
            shot("%s_%03d" % (TAG, i))
    json.dump(log, open(os.path.join(OUT, TAG + ".json"), "w"))
    d = [abs(log[k]["bump"] - log[k - 1]["bump"]) for k in range(1, len(log))]
    rel = [abs((log[k]["bump"] - log[k]["plate"]) - (log[k - 1]["bump"] - log[k - 1]["plate"])) for k in range(1, len(log))]
    print("RESULT max per-frame bumper jump m", round(max(d), 4), "max plate-vs-bumper slip m", round(max(rel), 4), flush=True)
import time as _t
_T0 = _t.time(); print("TEST LOADED", flush=True)
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
        if state["t"] == 0.05: print("STEP", state["i"], flush=True)
        if state["t"] >= d: state["t"] = 0.0; state["i"] += 1; f()
    except Exception:
        print("TESTERR", traceback.format_exc(), flush=True); state["i"] += 1
    return task.cont
app.task_mgr.add(runner, "test-runner", sort=100)
