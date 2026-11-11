# v1.0.5.5 QA: circular speedo must not overlap RESET CAR DAMAGE
import os, traceback, time as _t
from panda3d.core import Filename
OUT = os.environ.get("FS_QA_OUT", "/workspace/fireout-online/shots_seasons"); os.makedirs(OUT, exist_ok=True)

def G(): return app.game
def step(n=1):
    for _ in range(n): G().step(1 / 30.0)
def shot(name, hud=True):
    if not hud: app.aspect2d.hide()
    app.graphicsEngine.render_frame(); app.graphicsEngine.render_frame()
    app.win.save_screenshot(Filename.from_os_specific(os.path.join(OUT, name + ".png"))); print("SHOT", name, flush=True); app.aspect2d.show()

def run():
    g = G(); app.settings["tod"] = "night"; g.tod = 22.5; g.paused = False
    try:
        if g.pcar is None:
            tx, ty, _ = g.world.tower_top
            rx, ry = g.world.nearest_road_point(tx + 10, ty - 80)[:2]
            g.ensure_in_car(rx, ry, 0)
        g.vb["v_up"] = True
        for i in range(50): g.step(1 / 30.0)
        g.vb["v_up"] = False
        # force button refresh so driving cluster is current
        g.btn_state = None; g.refresh_buttons()
        for i in range(4): app.graphicsEngine.render_frame()
        # geometry clearance check in a2dBottomRight space
        sx, _, sz = g.speedo_root.get_pos()
        # ring outer radius ~0.218; nitro bar extends ~0.145 below centre
        speedo_top = sz + 0.22
        speedo_bot = sz - 0.16
        # RESET CAR DAMAGE is at rows[4]=1.06 when driving, h=0.045
        reset_z = 1.06
        reset_bot = reset_z - 0.05
        gap = reset_bot - speedo_top
        print("RESULT speedo_pos", round(sx, 3), round(sz, 3), "top", round(speedo_top, 3),
              "reset_bot", round(reset_bot, 3), "gap", round(gap, 3), "kmh", int(g.pcar.speed * 3.6), flush=True)
        assert gap >= 0.05, "speedo overlaps RESET CAR DAMAGE (gap=%s)" % gap
        shot("speedo_drive", hud=True)
        shot("speedo_hud_v1055", hud=True)
        print("RESULT speedo_clear", True, flush=True)
    except Exception:
        print("TESTERR speedo", traceback.format_exc(), flush=True)
    print("RESULT done", flush=True)

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
        if state["t"] >= d: state["t"] = 0.0; state["i"] += 1; f()
    except Exception:
        print("TESTERR", traceback.format_exc(), flush=True); state["i"] += 1
    return task.cont
app.task_mgr.add(runner, "test-runner", sort=100)
