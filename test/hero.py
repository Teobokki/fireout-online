import os, math, traceback, time as _t
from panda3d.core import Filename
def G(): return app.game
def step(n=1):
    for _ in range(n): G().step(1 / 30.0)
OUT = os.environ.get("HERO_OUT", "/tmp/hero.png")
def hero():
    import fs_avatar as A, fs_sfc as F
    g = G(); g.intro_t = 0; g.letterbox(False); g.tod = float(os.environ.get("HERO_TOD", "16.6")); app.settings["tod"] = "cycle"
    me = g.me(); me.x, me.y = 470, 140; me.sync(); b = g.buddy(); b.x, b.y = 471, 138; b.sync()
    step(30); g.time_scale = 0.0
    cfg = dict(A.preset(3), name="HIKARI", acc="none", kit_top=(1.0, 0.84, 0.05), kit_bottom=(1.0, 0.84, 0.05), kit_socks=(1.0, 0.84, 0.05), number=10)
    px, py = F.CX + 2.5, F.CY + 3.0
    cam = (px - 2.9, py - 5.2, 0.8)
    h_to_cam = math.degrees(math.atan2(-(cam[0] - px), (cam[1] - py)))
    p = A.Avatar(g, cfg, px, py, h_to_cam + 38); p.sync(); p.np.set_z(0.04)
    p.set_arms((-6, 9), (8, 9), (-18, 0), (-12, 0)); p.legR.set_p(-12); p.legL.set_p(6)
    m = A.Mesh(); r = 0.11; m.blob((0, 0, 0), (r, r, r), (0.97, 0.97, 0.97), 18, 12)
    for k in range(12):
        a = k * 2.4; bb = math.acos(1 - 2 * ((k + 0.5) / 12)); d = (math.sin(bb) * math.cos(a), math.sin(bb) * math.sin(a), math.cos(bb))
        m.blob(tuple(r * 0.93 * c for c in d), (0.035, 0.035, 0.035), (0.08, 0.08, 0.1), 8, 5)
    ball = A._put(app.render, "ball", m, app, 0.5, 0.0)
    hr = math.radians(p.h); fx, fy = -math.sin(hr), math.cos(hr)
    ball.set_pos(px + fx * 0.45 - fy * 0.18, py + fy * 0.45 + fx * 0.18, 0.15)
    app.render2d.hide(); app.aspect2d.hide()
    for _ in range(3): g.step(1 / 30.0)
    app.camera.set_pos(*cam); app.camera.look_at(px - 0.2, py + 8.0, 2.1); app.camLens.set_fov(72)
    for _ in range(4): app.graphicsEngine.render_frame()
    app.win.save_screenshot(Filename.from_os_specific(OUT)); print("SHOT", OUT, flush=True)
_T0 = _t.time()
PLAN = [(0.1, lambda: app.show_title()), (0.3, lambda: app.show_menu()), (0.3, lambda: app.start_game(None)), (1.0, lambda: None),
        (0.1, lambda: step(60)), (0.1, hero), (0.1, lambda: app.userExit())]
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
