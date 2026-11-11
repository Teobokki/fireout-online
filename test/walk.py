# On-foot walk smoke (beach sand, boardwalk, sidewalks/kerbs). FS_TESTSCRIPT=test/walk.py -> RESULT walk lines
import os, math, traceback
from panda3d.core import Filename
OUT = os.environ.get("FS_POSE_OUT", os.path.join(app.BASE, "docs"))
def G(): return app.game
LOG = []
def walk_leg(name, x, y, heading, sec=4.0, run=False):
    g = G(); g.paused = False; me = g.me()
    if g.pcar: g.exit_car(force=True)
    me.x, me.y, me.h = x, y, heading; g.cam_yaw = heading; me.sync()
    g.vb.clear(); g.vb["v_up"] = True; g.vb["v_nitro"] = run
    n = int(sec * 30); stuck = 0; px, py = me.x, me.y; zs = []
    for _ in range(n):
        g.cam_yaw = heading; g.step(1 / 30.0)
        d = math.hypot(me.x - px, me.y - py)
        if d < 0.02:
            stuck += 1
            if stuck < 4:
                pc = [(c.kind, round(c.x, 1), round(c.y, 1)) for c in g.cars_near(me.x, me.y, 4)]
                print("STUCK", name, round(me.x, 2), round(me.y, 2), "blocked", g.blocked(), "intro", round(g.intro_t, 2), "grid", g.world.grid.push_circle(me.x, me.y, 0.35), "cars", pc, "knock", me.knock, flush=True)
        px, py = me.x, me.y; zs.append(me.np.get_z())
    g.vb.clear()
    dist = math.hypot(me.x - x, me.y - y); exp = (5.8 if run else 2.1) * sec
    r = "RESULT walk %-22s dist=%.2f expected=%.2f ratio=%.2f stuck_frames=%d z=[%.2f..%.2f] end=(%.1f,%.1f)" % (name, dist, exp, dist / exp, stuck, min(zs), max(zs), me.x, me.y)
    print(r, flush=True); LOG.append(dist / exp)
def fps(name, x, y, h=-90):
    import time
    g = G(); g.paused = False; me = g.me(); me.x, me.y, me.h = x, y, h; g.cam_yaw = h; me.sync()
    for _ in range(20): g.step(1 / 30.0); app.graphicsEngine.render_frame()
    t = time.time()
    for _ in range(40): g.step(1 / 30.0); app.graphicsEngine.render_frame()
    f = 40 / (time.time() - t); print("RESULT fps %-12s %.1f" % (name, f), flush=True); return f
def lowfps(name, x, y, h, fdt=0.1, sec=3.0):
    g = G(); g.paused = False; me = g.me(); me.x, me.y, me.h = x, y, h; g.cam_yaw = h; me.sync()
    clk = app.clock
    class T: cont = 1
    class Fake:
        def get_dt(self): return fdt
    try:
        app.clock = Fake()
        g.vb.clear(); g.vb["v_up"] = True
        for _ in range(int(sec / fdt)): g.cam_yaw = h; g.update(T)
    finally:
        app.clock = clk
    g.vb.clear(); d = math.hypot(me.x - x, me.y - y); exp = 2.1 * sec
    print("RESULT lowfps %-14s %.0ffps dist=%.2f expected=%.2f ratio=%.2f" % (name, 1 / fdt, d, exp, d / exp), flush=True); LOG.append(d / exp)
def shot(name):
    app.graphicsEngine.render_frame(); app.graphicsEngine.render_frame()
    app.win.save_screenshot(Filename.from_os_specific(os.path.join(OUT, name + ".png"))); print("SHOT", name, flush=True)
def beach_cam():
    g = G(); g.paused = True; me = g.me(); h = math.radians(me.h + 140); fx, fy = -math.sin(h), math.cos(h)
    app.camera.set_pos(me.x + fx * 5.5, me.y + fy * 5.5, 2.6); app.camera.look_at(me.x, me.y, 1.0); app.camLens.set_fov(55)
from fs_world import block_rect
import fs_data as D
def sw_legs():
    x0, y0, x1, y1 = block_rect(2, 2)
    walk_leg("road->sidewalk(+x)", x0 - 6, (y0 + y1) / 2 + 0.3, -90, 4.0)      # heading -90 = +x
    walk_leg("sidewalk->road(-x)", x0 + 1.0, y0 + 3.3, 90, 3.0)
    walk_leg("along sidewalk(+y)", x0 + 1.2, y0 + 2, 0, 5.0)
    walk_leg("over kerb diag", x0 - 4, y0 - 4, -45, 4.0)
    walk_leg("run over kerb", x0 - 12, (y0 + y1) / 2 + 2.2, -90, 3.0, True)
import time as _t
_T0 = _t.time()
def wait_boot():
    app.show_title()
PLAN = [
    (0.1, wait_boot), (0.3, lambda: app.show_menu()), (0.3, lambda: app.start_game(None)), (1.0, lambda: None), (0.1, lambda: [G().step(1 / 30.0) for _ in range(300)]),
    (0.1, lambda: walk_leg("boardwalk->sand(+x)", 466, 30, -90, 6.0)),
    (0.1, lambda: walk_leg("sand(+x) run", 500, 120, -90, 5.0, True)),
    (0.1, lambda: walk_leg("sand along(+y)", 540, -200, 0, 6.0)),
    (0.1, lambda: walk_leg("sand(-x) to road", 560, 20, 90, 8.0)),
    (0.1, lambda: walk_leg("sand to sea", 580, -30, -90, 6.0)),
    (0.1, lambda: walk_leg("coast road->promenade", 452, 30, 90, 5.0)),
    (0.1, lambda: walk_leg("sand->pier deck", 552, 148, -90, 6.0)),
    (0.1, lambda: walk_leg("promenade->boardwalk", 466, -60, -90, 3.0)),
    (0.1, sw_legs),
    (0.1, lambda: lowfps("sand 10fps", 500, 110, -90)), (0.1, lambda: lowfps("sand 6fps", 500, 100, -90, 1 / 6.0)),
    (0.1, lambda: fps("city", block_rect(2, 2)[0] - 3, block_rect(2, 2)[1] + 30)), (0.1, lambda: fps("beach", 530, 60)), (0.1, lambda: fps("boardwalk", 474, 60, 0)), (0.1, lambda: fps("sidewalk", block_rect(3, 3)[0] + 1, block_rect(3, 3)[1] + 20, 0)),
    (0.1, lambda: walk_leg("beach shot", 520, 70, -60, 3.0)), (0.1, beach_cam), (0.1, lambda: shot("beach_walk")),
    (0.1, lambda: walk_leg("game cam sand", 500, 70, -90, 2.0)), (0.1, lambda: shot("gamecam_sand")),
    (0.1, lambda: walk_leg("game cam boardwalk", 474, 70, 0, 2.0)), (0.1, lambda: shot("gamecam_boardwalk")),
    (0.1, lambda: walk_leg("game cam sidewalk", block_rect(2, 2)[0] - 3, block_rect(2, 2)[1] + 30, -90, 1.6)), (0.1, lambda: shot("gamecam_sidewalk")),
    (0.1, lambda: (print("RESULT walk_min_ratio=%.2f" % min(LOG), flush=True), app.userExit())),
]
state = {"i": 0, "t": 0.0}
def runner(task):
    try:
        if state["i"] >= len(PLAN): return task.done
        d, f = PLAN[state["i"]]
        if app.world is None or (state["i"] > 2 and getattr(app, "game", None) is None): return task.cont
        if state["i"] == 0 and _t.time() - _T0 < 9.0: return task.cont
        state["t"] += 0.05
        if state["t"] >= d:
            state["t"] = 0.0; state["i"] += 1; f()
    except Exception:
        print("TESTERR", traceback.format_exc(), flush=True); state["i"] += 1
    return task.cont
app.task_mgr.add(runner, "test-runner", sort=100)
