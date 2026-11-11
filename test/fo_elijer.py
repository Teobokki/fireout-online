import os, math, traceback
from panda3d.core import Filename
OUT = "/tmp/fo_shots3"; os.makedirs(OUT, exist_ok=True)
def shot(name):
    app.graphicsEngine.render_frame(); app.graphicsEngine.render_frame()
    app.win.save_screenshot(Filename.from_os_specific(os.path.join(OUT, name + ".png")))
    print("SHOT", name, flush=True)
def G(): return app.game
def sim(sec):
    g=G()
    for _ in range(int(sec*30)): g.step(1/30.0)
state={"i":0,"t":0}
def closeup(side=0):
    g=G(); g.paused=True; c=g.me()
    h=math.radians(c.h + side)
    fx,fy=-math.sin(h), math.cos(h)
    app.camera.set_pos(c.x+fx*1.8, c.y+fy*1.8, 1.58)
    app.camera.look_at(c.x, c.y, 1.48); app.camLens.set_fov(38)
PLAN=[
    (0.3, lambda: (app.show_title() if app.world is not None else None)),
    (0.2, lambda: (app.show_menu(), None)),
    (0.6, lambda: shot("menu")),
    (0.1, lambda: app.start_game(None)),
    (0.3, lambda: sim(5.2)),
    (0.05, lambda: setattr(G(),"intro_t",0)),
    (0.05, lambda: G().letterbox(False)),
    (0.1, lambda: closeup(0)),
    (0.15, lambda: shot("elijer_front")),
    (0.05, lambda: closeup(40)),
    (0.15, lambda: shot("elijer_34")),
    (0.05, lambda: closeup(80)),
    (0.15, lambda: shot("elijer_side")),
    (0.1, lambda: (print("RESULT done", flush=True), app.userExit())),
]
def runner(task):
    try:
        if app.world is None: return task.cont
        if state["i"]>=len(PLAN): return task.done
        d,f=PLAN[state["i"]]; state["t"]+=0.05
        if state["t"]>=d:
            state["t"]=0; state["i"]+=1; f()
    except Exception:
        print("TESTERR", traceback.format_exc(), flush=True); state["i"]+=1
    return task.cont
app.task_mgr.add(runner,"fo-elijer",sort=100)
