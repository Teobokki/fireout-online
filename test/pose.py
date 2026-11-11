# Character pose shots (arms / hair). FS_TESTSCRIPT=test/pose.py FS_SUF=_before -> docs/pose_*.png
import os, math, traceback
from panda3d.core import Filename
OUT = os.environ.get("FS_POSE_OUT", os.path.join(app.BASE, "docs")); os.makedirs(OUT, exist_ok=True)
SUF = os.environ.get("FS_SUF", "")
def shot(name):
    app.graphicsEngine.render_frame(); app.graphicsEngine.render_frame()
    app.win.save_screenshot(Filename.from_os_specific(os.path.join(OUT, name + SUF + ".png"))); print("SHOT", name + SUF, flush=True)
def G(): return app.game
def sim(sec, fn=None):
    g = G()
    for _ in range(int(sec * 30)):
        if fn: fn()
        g.step(1 / 30.0)
def place():
    g = G(); g.paused = False; g.vb.clear(); a, d = g.chars["ana"], g.chars["daniel"]
    a.x, a.y, a.h = 40, -94, 0; d.x, d.y, d.h = 46, -94, 0; a.sync(); d.sync(); sim(0.5)
def cam(who, ang, dist=2.9, z=1.0, lz=0.95, fov=50):
    g = G(); g.paused = True; c = g.chars[who]; h = math.radians(c.h + ang); fx, fy = -math.sin(h), math.cos(h)
    app.camera.set_pos(c.x + fx * dist, c.y + fy * dist, z); app.camera.look_at(c.x, c.y, lz); app.camLens.set_fov(fov)
def hide_hud(on=True):
    for n in (app.aspect2d, app.render2d):
        if on: n.hide()
        else: n.show()
def walk(who, run=False, t=1.37):
    g = G(); g.paused = False; c = g.chars[who]
    if g.active != who: g.switch_char(); sim(0.3)
    g.vb.clear(); g.vb["v_up"] = True; g.vb["v_nitro"] = run; sim(t); g.vb.clear(); g.paused = True
def idle(who):
    g = G(); c = g.chars[who]; c.walk_anim(0.016, 0.0)
def armed(wid):
    g = G(); g.paused = False; g.arsenal.pick(wid); sim(0.3); g.paused = True
def aim(on):
    g = G(); g.paused = False; g.vb["v_aim"] = on; sim(0.4); g.paused = True
import time as _t
_T0 = _t.time()
def wait_boot():
    app.show_title()
PLAN = [
    (0.1, wait_boot), (0.3, lambda: app.show_menu()), (0.3, lambda: app.start_game(None)), (0.6, lambda: sim(3.0)), (0.1, place), (0.1, lambda: hide_hud(True)),
    (0.1, lambda: (idle("ana"), cam("ana", 25))), (0.1, lambda: shot("ana_idle")),
    (0.1, lambda: cam("ana", 0, 2.6)), (0.1, lambda: shot("ana_idle_front")),
    (0.1, lambda: cam("ana", 28, 1.05, 0.95, 0.80, 40)), (0.1, lambda: shot("ana_fingers")),
    (0.1, lambda: cam("ana", -28, 1.05, 0.95, 0.80, 40)), (0.1, lambda: shot("ana_fingers_l")),
    (0.1, lambda: cam("ana", 90, 0.9, 0.9, 0.80, 40)), (0.1, lambda: shot("ana_fingers_side")),
    (0.1, lambda: walk("ana")), (0.1, lambda: cam("ana", 80, 3.0)), (0.1, lambda: shot("ana_walk")),
    (0.1, lambda: walk("ana", True, 1.12)), (0.1, lambda: cam("ana", 80, 3.0)), (0.1, lambda: shot("ana_run")),
    (0.1, lambda: armed("pistol")), (0.1, lambda: (idle("ana"), cam("ana", 40, 2.6))), (0.1, lambda: shot("ana_pistol")),
    (0.1, lambda: cam("ana", 40, 1.0, 0.95, 0.80, 40)), (0.1, lambda: shot("ana_pistol_grip")),
    (0.1, lambda: aim(True)), (0.1, lambda: cam("ana", 60, 2.6, 1.3, 1.15)), (0.1, lambda: shot("ana_aim")), (0.1, lambda: aim(False)),
    (0.1, lambda: armed("bat") if "bat" in [w for w in G().arsenal.ammo] else armed("pickaxe")), (0.1, lambda: (idle("ana"), cam("ana", 40, 2.6))), (0.1, lambda: shot("ana_melee")),
    (0.1, lambda: armed("fists")),
    (0.1, lambda: walk("daniel")), (0.1, lambda: cam("daniel", 80, 3.0)), (0.1, lambda: shot("daniel_walk")),
    (0.1, lambda: (idle("daniel"), cam("daniel", 25))), (0.1, lambda: shot("daniel_idle")),
    (0.1, lambda: cam("daniel", 28, 1.1, 0.95, 0.80, 40)), (0.1, lambda: shot("daniel_fingers")),
    (0.1, lambda: cam("daniel", 150, 1.0, 1.68, 1.62, 45)), (0.1, lambda: shot("daniel_hair_back")),
    (0.1, lambda: cam("daniel", 75, 0.95, 1.66, 1.6, 45)), (0.1, lambda: shot("daniel_hair_side")),
    (0.1, lambda: cam("daniel", 20, 0.9, 1.66, 1.6, 45)), (0.1, lambda: shot("daniel_hair_front")),
    (0.1, lambda: (hide_hud(False), setattr(G(), "paused", False), G().switch_char() if G().active != "ana" else None)),
    (0.1, lambda: G().enter_home()), (0.1, lambda: sim(0.3)), (0.1, lambda: G().start_shower()), (0.1, lambda: sim(1.2)), (0.1, lambda: shot("shower_scrub_1")),
    (0.1, lambda: sim(1.2)), (0.1, lambda: shot("shower_scrub_1b")),
    (0.1, lambda: sim(1.2)), (0.1, lambda: shot("shower_scrub_2")), (0.1, lambda: sim(2.4)), (0.1, lambda: shot("shower_scrub_3")),
    (0.1, lambda: sim(4.8)), (0.1, lambda: shot("shower_scrub_4")), (0.1, lambda: sim(2.4)), (0.1, lambda: shot("shower_scrub_5")),
    (0.1, lambda: G().end_shower()), (0.1, lambda: G().switch_char()), (0.1, lambda: G().start_shower()), (0.1, lambda: sim(1.2)), (0.1, lambda: shot("shower_scrub_daniel")),
    (0.1, lambda: G().end_shower()), (0.1, lambda: G().switch_char()), (0.1, lambda: sim(0.5)), (0.1, lambda: G().leave_home()), (0.1, lambda: sim(1.0)),
    (0.1, lambda: G().enter_car(G().own)), (0.1, lambda: sim(1.0)), (0.1, lambda: (setattr(G(), "paused", True), cam_car())), (0.1, lambda: shot("ana_incar")),
    (0.1, lambda: (print("RESULT done", flush=True), app.userExit())),
]
def cam_car():
    c = G().pcar; h = math.radians(c.h + 60); fx, fy = -math.sin(h), math.cos(h)
    app.camera.set_pos(c.x + fx * 3.2, c.y + fy * 3.2, 1.6); app.camera.look_at(c.x, c.y, 0.9); app.camLens.set_fov(50)
state = {"i": 0, "t": 0.0}
def runner(task):
    try:
        if state["i"] >= len(PLAN): return task.done
        d, f = PLAN[state["i"]]
        if app.world is None: return task.cont
        if state["i"] == 0 and _t.time() - _T0 < 9.0: return task.cont
        state["t"] += 0.05
        if state["t"] >= d:
            state["t"] = 0.0; state["i"] += 1; f()
    except Exception:
        print("TESTERR", traceback.format_exc(), flush=True); state["i"] += 1
    return task.cont
app.task_mgr.add(runner, "test-runner", sort=100)
