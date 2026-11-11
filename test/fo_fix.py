import os, math, traceback
from panda3d.core import Filename
OUT = os.environ.get("FO_SHOTS", "/tmp/fo_shots2")
os.makedirs(OUT, exist_ok=True)

def shot(name):
    app.graphicsEngine.render_frame(); app.graphicsEngine.render_frame()
    path = os.path.join(OUT, name + ".png")
    app.win.save_screenshot(Filename.from_os_specific(path))
    print("SHOT", name, path, flush=True)

def G(): return app.game
def sim(sec, fn=None):
    g = G()
    for _ in range(int(sec * 30)):
        if fn: fn()
        g.step(1 / 30.0)

state = {"i": 0, "t": 0.0}

def elijer_close():
    g = G(); g.paused = True
    c = g.me()
    # front 3/4
    h = math.radians(c.h)
    fx, fy = -math.sin(h), math.cos(h)
    rx, ry = math.cos(h), math.sin(h)
    app.camera.set_pos(c.x + fx * 2.0 + rx * 0.7, c.y + fy * 2.0 + ry * 0.7, 1.55)
    app.camera.look_at(c.x, c.y, 1.45)
    app.camLens.set_fov(40)

def go_kiosk():
    g = G(); h = g.hackeria
    p = [x for x in h.props if x.get("kind") == "kiosk"][0]
    if g.pcar: g.exit_car(force=True)
    me = g.me(); me.x, me.y = p["x"] + 3.2, p["y"] + 0.4
    me.h = math.degrees(math.atan2(-(p["x"]-me.x), (p["y"]-me.y))); me.sync()
    g.paused = False; g.cam_pos = None; sim(0.3); h._pick_target()

PLAN = [
    (0.4, lambda: shot("boot_loading_or_rex")),
    (2.2, lambda: shot("boot_rex")),
    (2.6, lambda: shot("boot_exromania")),
    (0.2, lambda: (app.show_title(), shot("title"))),
    (0.2, lambda: (app.show_menu(), None)),
    (0.8, lambda: shot("menu")),
    (0.1, lambda: app.start_game(None)),
    (0.4, lambda: sim(5.5)),
    (0.05, lambda: setattr(G(), "intro_t", 0.0)),
    (0.05, lambda: G().letterbox(False)),
    (0.1, lambda: elijer_close()),
    (0.2, lambda: shot("elijer_close")),
    (0.05, lambda: setattr(G(), "paused", False)),
    (0.1, lambda: go_kiosk()),
    (0.05, lambda: (G().vb.__setitem__("v_hack", True), G().hackeria._pick_target())),
    (0.05, lambda: sim(0.40, lambda: G().vb.__setitem__("v_hack", True))),
    (0.05, lambda: shot("hacking_ring")),
    (0.1, lambda: (G().hackeria.skills.add("camera"), go_kiosk() if False else None)),
    (0.1, lambda: (G().hackeria._hack_camera([x for x in G().hackeria.props if x["kind"]=="camera"][0]), None)),
    (0.3, lambda: shot("cctv2")),
    (0.1, lambda: (print("RESULT done", flush=True), app.userExit())),
]

def runner(task):
    try:
        if state["i"] >= len(PLAN): return task.done
        d, f = PLAN[state["i"]]
        state["t"] += 0.016
        if state["t"] >= d:
            state["t"] = 0.0; state["i"] += 1; f()
    except Exception:
        print("TESTERR", traceback.format_exc(), flush=True); state["i"] += 1
    return task.cont
app.task_mgr.add(runner, "fo-fix", sort=100)
