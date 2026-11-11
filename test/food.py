# v1.0.4 FOOD menu + animated eating (+ food icons). FS_TESTSCRIPT=test/food.py  PART=icons|eat|house|all
import os, math, traceback, random
from panda3d.core import Filename, NodePath, AmbientLight, DirectionalLight, FrameBufferProperties, WindowProperties, GraphicsPipe, GraphicsOutput, Texture, Camera, PerspectiveLens, PNMImage
import fs_data as D
OUT = os.path.join(app.BASE, "docs"); PART = os.environ.get("PART", "all")
def G(): return app.game
def step(n=1):
    for _ in range(n): G().step(1 / 30.0)
def shot(name, hud=True):
    if not hud: app.aspect2d.hide()
    app.graphicsEngine.render_frame(); app.graphicsEngine.render_frame()
    app.win.save_screenshot(Filename.from_os_specific(os.path.join(OUT, name + ".png"))); print("SHOT", name, flush=True)
    app.aspect2d.show()
def place(x, y, h, tod=13.0):
    g = G(); app.settings["tod"] = "day"; g.tod = tod; me = g.me(); me.x, me.y, me.h = x, y, h; g.cam_yaw = h; me.sync(); g.cam_pos = None; step(30)
def icons():
    from fs_food import build_prop, INFO
    buf = app.win.make_texture_buffer("icons", 256, 256, to_ram=True); buf.set_clear_color((0, 0, 0, 0)); buf.set_clear_color_active(True)
    scene = NodePath("iconscene"); scene.set_state(app.render.get_state()); cam = app.make_camera(buf); cam.reparent_to(scene); cam.node().get_lens().set_fov(30); cam.node().get_lens().set_aspect_ratio(1); cam.node().get_lens().set_near_far(0.005, 50)
    for fid in list(INFO):
        for c in scene.get_children():
            if c != cam: c.remove_node()
        p, e = build_prop(fid, app); p.reparent_to(scene)
        b = p.get_tight_bounds(); ctr = (b[0] + b[1]) * 0.5; sz = max((b[1] - b[0]).length(), 0.05)
        cam.set_pos(ctr[0] + sz * 0.8, ctr[1] - sz * 1.7, ctr[2] + sz * 0.8); cam.look_at(ctr)
        app.graphicsEngine.render_frame(); app.graphicsEngine.render_frame()
        img = PNMImage(); buf.get_texture().store(img); img.write(Filename.from_os_specific(os.path.join(app.BASE, "assets", "tex", "food_%s.png" % fid)))
    print("RESULT icons", len(INFO), flush=True); app.graphicsEngine.remove_window(buf)
def frames(name, n=4, tt=(0.9, 1.55, 2.1, 3.3), cam=None):
    g = G(); a = g.eating; t = 0.0; k = 0
    for target in tt:
        while t < target and g.eating is not None: g.step(1 / 30.0); t += 1 / 30.0
        if cam: cam()
        shot("_%s_%d" % (name, k), False); k += 1
    while g.eating is not None: g.step(1 / 30.0)
def cam_front(d=1.7, z=1.55, side=0.55, look=1.35):
    def f():
        me = G().me(); h = math.radians(me.h); fx, fy = -math.sin(h), math.cos(h); rx, ry = math.cos(h), math.sin(h)
        app.camera.set_pos(me.x + fx * d + rx * side, me.y + fy * d + ry * side, me.np.get_z() + z); app.camera.look_at(me.x, me.y, me.np.get_z() + look); app.camLens.set_fov(50)
    return f
def eat(fid, name, who="ana"):
    def f():
        g = G(); g.select_char(who); step(3); place(12, -40, 0); g.cash = max(g.cash, 5000)
        if name == "eat_burger_anim":
            app.show_pause(); app.show_food(); step(0); shot("pause_food_menu"); app.money_ui.pick(fid)
        else: g.eat_food(fid)
        print("RESULT eating", fid, g.eating is not None, "cash", g.cash, flush=True)
        frames(name, cam=cam_front()); print("RESULT health", g.me().health, flush=True)
    return f
def house(who):
    def f():
        g = G(); g.select_char(who); step(3); g.enter_home(); step(30)
        g.house_snack(); fid = g.eating.fid; print("RESULT snack", who, fid, flush=True)
        X, Y = D.HOME_INT
        def c():
            app.camera.set_pos(X + 5.15, Y + 0.25, 1.65); app.camera.look_at(X + 4.45, Y + 1.85, 1.3); app.camLens.set_fov(60)
        frames("house_" + who, tt=(0.55, 1.95, 2.4, 3.6), cam=c); print("RESULT after", g.home.get("mode"), g.me().health, flush=True)
        g.leave_home(); step(20)
    return f
def car_block():
    g = G(); me = g.me(); c = min(g.cars, key=lambda c: math.hypot(c.x - me.x, c.y - me.y)); me.x, me.y = c.x + 2, c.y; me.sync(); g.enter_car(c); step(5)
    print("RESULT car food", g.eat_food("onigiri"), g.food_block(), flush=True); g.exit_car(force=True); step(10)
import time as _t
_T0 = _t.time()
PLAN = [(0.1, lambda: app.show_title()), (0.3, lambda: app.show_menu()), (0.3, lambda: app.start_game(None)), (1.0, lambda: None),
        (0.1, lambda: [G().step(1 / 30.0) for _ in range(250)])]
def poses():
    g = G(); g.select_char("ana"); step(3); place(12, -40, 0); me = g.me(); me.anim_lock = True
    C = [((-42, 24), (-132, 26)), ((-40, -10), (-130, -20)), ((-30, -25), (-140, -30)), ((-55, -15), (-120, -40)), ((-20, -30), (-150, -20)), ((-45, 0), (-140, 0))]
    from fs_food import build_prop
    pr, e = build_prop("onigiri", app); pr.reparent_to(me.handR); me.set_grip(True, False)
    for k, (a, f) in enumerate(C):
        me.set_arms(a, (-4, 4), f, (-10, 0)); cam_front(1.5, 1.5, 0.5, 1.4)(); shot("_pose_%d" % k, False)
    pr.remove_node(); me.anim_lock = False
if PART == "pose": PLAN += [(0.1, poses)]
if PART in ("icons", "all"): PLAN += [(0.1, icons)]
if PART in ("eat", "all"): PLAN += [(0.1, eat("burger", "eat_burger_anim")), (0.1, eat("sushi", "eat_sushi_anim", "daniel")), (0.1, eat("water", "eat_water_anim", "miyo")), (0.1, car_block)]
if PART in ("house", "all"): PLAN += [(0.1, house("ana")), (0.1, house("daniel")), (0.1, house("miyo"))]
PLAN += [(0.1, lambda: app.userExit())]
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
