import os, math, traceback, time as _t
from panda3d.core import Filename
def G(): return app.game
def step(n=1):
    for _ in range(n): G().step(1 / 30.0)
def shot(name):
    app.graphicsEngine.render_frame(); app.graphicsEngine.render_frame()
    app.win.save_screenshot(Filename.from_os_specific("/tmp/" + name + ".png")); print("SHOT", name, flush=True)
def a():
    g = G(); g.intro_t = 0; g.tod = 13; me = g.me(); me.x, me.y = 12, -40; me.sync(); step(20)
    g.toggle_phone(); step(2); shot("ui_phone"); g.online_app(); step(2); shot("ui_main")
    g.online.goto("custom"); step(2); shot("ui_custom"); g.online._done_custom()
    g.online.goto("football"); step(2); shot("ui_football"); g.online.goto("join"); step(2); shot("ui_join")
    g.online.goto("main"); g.online.host("pw"); step(5)
    for _ in range(80): step(1); _t.sleep(0.05)
    g.online.refresh(); step(2); shot("ui_hosting"); g.online.close()
    app.show_pause(); step(1); shot("ui_pause"); app.hide_pause()
    g.laptop.toggle()
def b():
    g = G(); step(5); shot("ui_laptop"); g.laptop.close(); g.online.leave()
_T0 = _t.time()
PLAN = [(0.1, lambda: app.show_title()), (0.3, lambda: app.show_menu()), (0.3, lambda: app.start_game(None)), (1.0, lambda: None),
        (0.1, lambda: step(60)), (0.1, a), (5.0, b), (0.1, lambda: app.userExit())]
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
