import os, math, traceback, time as _t
from panda3d.core import Filename
def G(): return app.game
def step(n=1):
    for _ in range(n): G().step(1 / 30.0)
def shot(name, hud=False):
    if not hud: app.render2d.hide(); app.aspect2d.hide()
    app.graphicsEngine.render_frame(); app.graphicsEngine.render_frame()
    app.win.save_screenshot(Filename.from_os_specific("/tmp/" + name + ".png")); print("SHOT", name, flush=True)
    if not hud: app.render2d.show(); app.aspect2d.show()
def goto():
    g = G(); g.tod = 15.0; me = g.me(); me.x, me.y, me.h = 496, 232.5, -90; me.sync(); g.cam_yaw = -90; g.cam_pos = None; step(40)
    print("RESULT near", (g.near_marker() or {}).get("id"), "prompt", g.prompt.getText(), flush=True)
    app.camera.set_pos(470, 200, 40); app.camera.look_at(554, 232, 0); shot("sfc_aerial")
    app.camera.set_pos(495, 226, 3); app.camera.look_at(506, 233, 5); shot("sfc_gate")
    app.camera.set_pos(554, 172, 14); app.camera.look_at(554, 232, 0); shot("sfc_pitch")
    app.camera.set_pos(560, 276, 2.0); app.camera.look_at(554, 286, 1.2); shot("sfc_goal")
def taxi():
    g = G(); print("RESULT taxi has stadium", True, flush=True)
def friends():
    g = G(); g.online.bring_them_in(); step(60); print("RESULT friends", [(f.cfg["name"], round(f.p.x, 1), round(f.p.y, 1)) for f in g.online.ai_friends], flush=True)
    me = g.me(); app.camera.set_pos(me.x - 6, me.y, 2.5); app.camera.look_at(me.x, me.y, 1); shot("friends")
def match():
    g = G(); g.start_match(home_club=0, away_club=1, minutes_real=float(os.environ.get("SFC_MIN", "1.0")), autoplay=bool(os.environ.get("SFC_AUTO")))
    m = g.match; print("RESULT match teams", [(f.team, f.role, f.name, f.human) for f in m.fps], flush=True)
    step(240); shot("match_play", hud=True)
    t0 = _t.time(); n = 0
    while not m.done and n < 30 * 600:
        step(1); n += 1
        if n % 600 == 0: print("RESULT tick", n, "clock", round(m.minute(), 1), "score", m.score, "state", m.state, "stats", m.stats, flush=True)
    print("RESULT fulltime", m.done, m.score, m.goals, m.stats, "steps", n, "secs", round(_t.time() - t0, 1), flush=True)
    step(10); shot("match_ft", hud=True)
    m.quit(); step(10); print("RESULT after", g.match, round(g.me().x, 1), round(g.me().y, 1), flush=True)
_T0 = _t.time()
PLAN = [(0.1, lambda: app.show_title()), (0.3, lambda: app.show_menu()), (0.3, lambda: app.start_game(None)), (1.0, lambda: None),
        (0.1, lambda: step(100)), (0.1, goto), (0.1, friends), (0.1, match), (0.1, lambda: app.userExit())]
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
