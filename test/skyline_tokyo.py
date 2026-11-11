# v1.0.5.4 Tokyo skyline / tower massing screenshots
import os, traceback, time as _t
from panda3d.core import Filename
OUT = os.environ.get("FS_QA_OUT", "/workspace/fireout-online/shots_seasons"); os.makedirs(OUT, exist_ok=True)

def G(): return app.game
def shot(name, hud=True):
    if not hud: app.aspect2d.hide()
    app.graphicsEngine.render_frame(); app.graphicsEngine.render_frame()
    app.win.save_screenshot(Filename.from_os_specific(os.path.join(OUT, name + ".png"))); print("SHOT", name, flush=True); app.aspect2d.show()

def run():
    g = G(); app.settings["tod"] = "night"; g.tod = 22.5; g.paused = False
    for i in range(8): g.step(1 / 30.0)
    # park near crossing and look at tall Tokyo towers
    cams = [
        # street-level look-up at setback glass tower
        ("tokyo_street_up", (22, 18, 7), (55, 70, 110)),
        # crossing district towers
        ("tokyo_towers_crossing", (35, -45, 55), (-60, 120, 130)),
        # needles / skyline rim
        ("tokyo_skyline_needles", (-40, 80, 100), (250, -250, 180)),
        ("tokyo_skyline_rim", (90, -140, 40), (-650, 450, 220)),
    ]
    for name, pos, look in cams:
        try:
            app.camera.set_pos(*pos); app.camera.look_at(*look)
            # keep player near so LOD doesn't cull
            if g.pcar is None:
                try:
                    rx, ry = g.world.nearest_road_point(pos[0], pos[1])[:2]
                    g.ensure_in_car(rx, ry, 0)
                except Exception:
                    pass
            else:
                try: g.pcar.np.set_pos(pos[0], pos[1], 0.4)
                except Exception: pass
            for i in range(6): g.step(1 / 30.0)
            shot(name, hud=False)
            print("RESULT cam", name, flush=True)
        except Exception:
            print("TESTERR", name, traceback.format_exc(), flush=True)
    print("RESULT skyline_done", flush=True)

_T0 = _t.time(); print("TEST LOADED skyline", flush=True)
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
