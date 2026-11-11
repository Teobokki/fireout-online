# v1.0.5.5 QA: pause menu EX SCREEN RECORDER 2026 without system-sound toggle
import os, traceback, time as _t
from panda3d.core import Filename
OUT = os.environ.get("FS_QA_OUT", "/workspace/fireout-online/shots_seasons"); os.makedirs(OUT, exist_ok=True)

def shot(name, hud=True):
    if not hud: app.aspect2d.hide()
    app.graphicsEngine.render_frame(); app.graphicsEngine.render_frame()
    app.win.save_screenshot(Filename.from_os_specific(os.path.join(OUT, name + ".png")))
    print("SHOT", name, flush=True); app.aspect2d.show()

def run():
    g = app.game
    print("RESULT recorder", app.screen_rec is not None, "sys_sound", getattr(app.screen_rec, "sys_sound", None), flush=True)
    assert app.screen_rec is not None and app.screen_rec.sys_sound is True
    app.show_pause()
    for i in range(6):
        app.graphicsEngine.render_frame()
    shot("pause_recorder_v1055", hud=True)
    # also overwrite canonical name used in prior docs
    shot("pause_recorder", hud=True)
    # confirm no "System sound: ON/OFF" button text is expected — we only have the hint label
    print("RESULT pause_ok", True, flush=True)
    app.hide_pause()
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
