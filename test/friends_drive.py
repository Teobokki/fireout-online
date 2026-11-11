import os, math, traceback, time as _t
from panda3d.core import Filename
def G(): return app.game
def step(n=1):
    for _ in range(n): G().step(1 / 30.0)
def a():
    g = G(); g.intro_t = 0; me = g.me(); me.x, me.y = g.own.x + 3, g.own.y; me.sync(); g.online.bring_them_in(); step(30)
    g.enter_car(g.own); step(10); print("RESULT in car", g.pcar is not None, flush=True)
    g.vb["v_up"] = True
    for k in range(20):
        step(30)
    g.vb.clear(); step(60)
    c = g.pcar; print("RESULT player car", round(c.x), round(c.y), flush=True)
    for f in g.online.ai_friends:
        print("RESULT friend", f.cfg["name"], "car", f.car is not None and (round(f.car.x), round(f.car.y), f.car in g.cars), "seated", f.p.in_car is f.car, "dist", f.car and round(math.hypot(f.car.x - c.x, f.car.y - c.y)), flush=True)
    for k in range(10): step(30)
    for f in g.online.ai_friends: print("RESULT friend later dist", f.car and round(math.hypot(f.car.x - c.x, f.car.y - c.y)), flush=True)
    g.exit_car(); step(60)
    for f in g.online.ai_friends: print("RESULT friend on foot", f.car, round(math.hypot(f.p.x - g.me().x, f.p.y - g.me().y), 1), flush=True)
    for k in range(400): step(1)
    for f in g.online.ai_friends: print("RESULT friend idle roam", round(math.hypot(f.p.x - g.me().x, f.p.y - g.me().y), 1), flush=True)
_T0 = _t.time()
PLAN = [(0.1, lambda: app.show_title()), (0.3, lambda: app.show_menu()), (0.3, lambda: app.start_game(None)), (1.0, lambda: None),
        (0.1, lambda: step(60)), (0.1, a), (0.1, lambda: app.userExit())]
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
