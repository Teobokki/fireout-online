# FIREOUT ONLINE 1.0.0 ship shots: intro sequence + hacking feel
import os, math, time, traceback
from panda3d.core import Filename
OUT = os.environ.get("FO_SHOTS", os.path.join(app.BASE, "docs"))
os.makedirs(OUT, exist_ok=True)

def shot(name):
    app.graphicsEngine.render_frame(); app.graphicsEngine.render_frame()
    path = os.path.join(OUT, name + ".png")
    app.win.save_screenshot(Filename.from_os_specific(path))
    print("SHOT", name, path, flush=True)

def G():
    return app.game

def sim(sec, fn=None):
    g = G()
    for _ in range(int(sec * 30)):
        if fn: fn()
        g.step(1 / 30.0)

PLAN = []
state = {"i": 0, "t": 0.0}

def face(px, py):
    me = G().me()
    me.h = math.degrees(math.atan2(-(px - me.x), (py - me.y)))
    me.sync()

def go_to_prop(kind="kiosk"):
    g = G(); h = g.hackeria
    props = [p for p in h.props if p.get("kind") == kind]
    p = props[0]
    me = g.me()
    if g.pcar:
        g.exit_car(force=True)
    me.x = p["x"] + 3.2
    me.y = p["y"] + 0.4
    face(p["x"], p["y"])
    g.cam_pos = None
    sim(0.4)
    h._pick_target()
    return p

def start_hold():
    G().vb["v_hack"] = True
    G().hackeria._pick_target()

def hold_step():
    G().vb["v_hack"] = True

PLAN = [
    (1.2, lambda: shot("boot_rex")),
    (2.6, lambda: shot("boot_exromania")),
    (3.0, lambda: (app.show_title(), None)),
    (0.4, lambda: shot("title")),
    (0.1, lambda: app.show_menu()),
    (0.6, lambda: shot("menu")),
    (0.1, lambda: app.start_game(None)),
    (0.8, lambda: sim(6.0)),
    (0.1, lambda: setattr(G(), "intro_t", 0.0)),
    (0.1, lambda: (G().letterbox(False) if hasattr(G(), "letterbox") else None)),
    (0.2, lambda: shot("on_foot_night")),
    (0.1, lambda: go_to_prop("kiosk")),
    (0.3, lambda: shot("kiosk_target")),
    (0.05, lambda: start_hold()),
    (0.05, lambda: sim(0.45, hold_step)),
    (0.05, lambda: shot("hacking_hold")),
    (0.05, lambda: sim(0.6, hold_step)),
    (0.1, lambda: shot("hacked_glitch")),
    (0.1, lambda: go_to_prop("camera")),
    (0.05, lambda: start_hold()),
    (0.05, lambda: sim(0.9, hold_step)),
    (0.2, lambda: shot("cctv_feed")),
    (0.1, lambda: (G().hackeria.exit_cam(), G().vb.clear())),
    (0.1, lambda: go_to_prop("traffic")),
    (0.05, lambda: start_hold()),
    (0.05, lambda: sim(0.9, hold_step)),
    (0.2, lambda: shot("traffic_hack")),
    (0.1, lambda: (G().hackeria.skills.add("blackout"), G().hackeria.blackout())),
    (0.4, lambda: shot("blackout")),
    (0.1, lambda: (G().hackeria.open_skills(), None)),
    (0.3, lambda: shot("skill_tree")),
    (0.1, lambda: (G().hackeria.close_ui(), G().hackeria.open_contracts())),
    (0.3, lambda: shot("contracts")),
    (0.1, lambda: (G().hackeria.close_ui(), print("RESULT done", flush=True), app.userExit())),
]

def runner(task):
    try:
        if state["i"] >= len(PLAN):
            return task.done
        d, f = PLAN[state["i"]]
        state["t"] += 0.05
        if state["t"] >= d:
            state["t"] = 0.0
            state["i"] += 1
            f()
    except Exception:
        print("TESTERR", traceback.format_exc(), flush=True)
        state["i"] += 1
    return task.cont

app.task_mgr.add(runner, "fo-ship", sort=100)
