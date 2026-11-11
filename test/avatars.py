import os, math, traceback, time as _t
from panda3d.core import Filename
exec(open(os.path.join(app.BASE, "test/_common.py")).read()) if os.path.exists(os.path.join(app.BASE, "test/_common.py")) else None
def G(): return app.game
def step(n=1):
    for _ in range(n): G().step(1 / 30.0)
def shot(name):
    app.render2d.hide(); app.aspect2d.hide(); app.graphicsEngine.render_frame(); app.graphicsEngine.render_frame()
    app.win.save_screenshot(Filename.from_os_specific("/tmp/" + name + ".png")); app.render2d.show(); app.aspect2d.show(); print("SHOT", name, flush=True)
def av():
    import fs_avatar as A
    g = G(); g.tod = 13; me = g.me(); me.x, me.y = 12, -40; me.sync(); step(10)
    L = []
    for i in range(8):
        a = A.Avatar(g, A.preset(i), 8 + i * 1.1, -44, 0); a.sync(); L.append(a)
    for _ in range(20):
        for a in L: a.walk_anim(1 / 30, 0.0 if L.index(a) % 2 else 2.0)
    app.camera.set_pos(11.85, -49.5, 1.5); app.camera.look_at(11.85, -44, 1.0); app.camLens.set_fov(50); shot("av_front")
    app.camera.set_pos(11.85, -38.5, 1.5); app.camera.look_at(11.85, -44, 1.0); shot("av_back")
    app.camera.set_pos(8.0, -42.4, 1.62); app.camera.look_at(8.0, -44, 1.6); app.camLens.set_fov(30); shot("av_face0")
    app.camera.set_pos(10.2, -42.4, 1.62); app.camera.look_at(10.2, -44, 1.6); shot("av_face2")
    app.camLens.set_fov(70)
_T0 = _t.time()
PLAN = [(0.1, lambda: app.show_title()), (0.3, lambda: app.show_menu()), (0.3, lambda: app.start_game(None)), (1.0, lambda: None),
        (0.1, lambda: step(60)), (0.1, av), (0.1, lambda: app.userExit())]
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
