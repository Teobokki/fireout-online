import math
# v1.0.4 NPC checks: Japanese speech + English underneath, NPC skin, JP TAXI glass + driver. FS_TESTSCRIPT=test/npc.py
import os, math, traceback, random
from panda3d.core import Filename
OUT = os.path.join(app.BASE, "docs")
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
def ped_near(dx=2.2, dy=3.5):
    g = G(); me = g.me(); g.populate(); step(2)
    if not g.peds:
        from fs_people import Ped
        g.peds.append(Ped(g, random.choice(g.world.ped_loops), 0))
    p = min(g.peds, key=lambda p: math.hypot(p.x - me.x, p.y - me.y))
    h = math.radians(me.h); fx, fy = -math.sin(h), math.cos(h)
    p.x, p.y = me.x + fx * dy + fy * dx, me.y + fy * dy - fx * dx; p.h = me.h + 180; p.speed = 0.0; p.flee = 0; p.sync(); return p
def talk(name, group=None):
    def f():
        g = G(); p = ped_near()
        if group: g.npc_say(group, p)
        else: g.say_line(p)
        step(3); cam_front(p); shot(name)
    return f
def cam_front(p, d=5.5, z=2.4):
    g = G(); me = g.me()
    app.camera.set_pos(me.x - (p.x - me.x) * 0.6 + 0, me.y - (p.y - me.y) * 0.6 - 0.0, z); app.camera.look_at(p.x, p.y, 1.9); app.camLens.set_fov(60)
def ramen():
    g = G(); r = g.miyo.ramen; hr = math.radians(r.h); fx, fy = -math.sin(hr), math.cos(hr)
    place(r.x - fx * 3.0, r.y - fy * 3.0, r.h); r.cd = 0; step(3)
    app.camera.set_pos(r.x - fx * 5.5 + fy * 1.5, r.y - fy * 5.5 - fx * 1.5, 2.3); app.camera.look_at(r.x, r.y, 1.6); app.camLens.set_fov(60); shot("npc_japanese_2")
def police():
    g = G(); place(8, -60, 0); g.add_heat(3, ""); step(200)
    cops = [c for c in g.police]; me = g.me()
    if cops:
        c = min(cops, key=lambda c: math.hypot(c.x - me.x, c.y - me.y)); c.x, c.y = me.x + 3, me.y + 9; c.vx = c.vy = 0; c.sync(1 / 30)
        g._cop_cd = 99; g.npc_say("police", c); g.npc_say("busted", who="警察官"); g.subtitle("警察官：止まれ！警察だ！", 4, en="Police officer: Stop! Police!")
        step(2); app.camera.set_pos(me.x - 4, me.y - 5, 3.2); app.camera.look_at(c.x, c.y, 2.0); app.camLens.set_fov(60); shot("npc_japanese_3")
    print("RESULT cops", len(cops), flush=True); g.heat = 0; step(5)
def traffic():
    from panda3d.core import TransformState
    print("RESULT states at traffic start", TransformState.get_num_states(), flush=True)
    g = G(); place(-8, -30, 0, 13.0); n0 = len(g.cars)
    for _ in range(40):
        g.populate(); g.step(1 / 30.0)
    for k in range(900):
        g.step(1 / 30.0)
        if k % 30 == 0: g.populate()
        if k % 30 == 0: TransformState.garbage_collect()
        if k % 300 == 0: print("RESULT states", k, TransformState.get_num_states(), len(g.cars), flush=True)
    import time, cProfile, pstats
    from panda3d.core import NodePath, TransformState, RenderState
    n = app.render.attach_new_node("bench"); t1 = time.time()
    for k in range(5000): n.set_r(k * 0.01)
    c0 = g.cars[0]; t2 = time.time()
    for k in range(5000): c0.np.set_r(k * 0.01)
    t3 = time.time()
    print("RESULT setr fresh %.3f ms  car %.3f ms  transform cache %d states %d" % ((t2 - t1) / 5, (t3 - t2) / 5, TransformState.get_num_states(), RenderState.get_num_states()), flush=True)
    t0 = time.time()
    TransformState.garbage_collect()
    for k in range(120): g.step(1 / 30.0); app.graphicsEngine.render_frame()
    print("RESULT frame (sim+render, software GL) ms", round((time.time() - t0) / 120 * 1000, 1), flush=True); t0 = time.time()
    for k in range(120): g.step(1 / 30.0)
    print("RESULT sim ms/step", round((time.time() - t0) / 120 * 1000, 2), flush=True)
    from fs_ai import TrafficAI
    print("RESULT traffic cars", sum(1 for c in g.cars if isinstance(c.ai, TrafficAI)), "density", app.settings.get("traffic"), flush=True)
    best = -1
    for k in range(40):
        for _ in range(15): g.step(1 / 30.0)
        if k % 2 == 0: g.populate()
        n = sum(1 for c in g.cars if -45 < c.y < 60 and -24 < c.x < 20)
        if n > best:
            best = n; app.camera.set_pos(-8, -60, 14); app.camera.look_at(0, 10, 0); app.camLens.set_fov(70); shot("traffic_dense", False)
    print("RESULT visible cars in shot", best, flush=True)
    app.camera.set_pos(-6, -26, 2.2); app.camera.look_at(12, -12, 3.6); app.camLens.set_fov(60); g.step(1 / 30.0)
    app.camera.set_pos(-6, -26, 2.2); app.camera.look_at(12, -12, 3.6); shot("_signal", False)
    from fs_ai import TrafficAI
    import collections
    sp = [math.hypot(c.vx, c.vy) for c in g.cars if isinstance(c.ai, TrafficAI)]
    print("RESULT moving", sum(1 for v in sp if v > 2), "of", len(sp), "phase", g.signals.state, flush=True)
    print("RESULT nodesX", sorted(set(round(v[0]) for v in g.world.nodes.values())), flush=True)
def dbg():
    from fs_people import Ped
    from panda3d.core import MaterialAttrib
    p = Ped(G(), G().world.ped_loops[0], 0)
    t = p.model.find("**/trousers"); gn = t.find("**/+GeomNode") if t.node().get_type().get_name() != "GeomNode" else t
    st = gn.node().get_geom_state(0); print("RESULT dbg", p.who, t, gn, st.get_attrib(MaterialAttrib).get_material().get_base_color(), flush=True)
    print("RESULT net", gn.get_net_state(), flush=True)
def skin():
    g = G(); place(10, -40, 0); ps = []
    me = g.me()
    from fs_people import Ped
    for _ in range(4): g.peds.append(Ped(g, random.choice(g.world.ped_loops), 0))
    for k, p in enumerate(g.peds[-4:]):
        p.x, p.y, p.h = me.x - 2.4 + k * 1.6, me.y + 4.5, 180; p.speed = 0; p.flee = 0; p.sync(); ps.append(p)
    step(1)
    for p in ps: p.x, p.y = p.x, p.y; p.sync()
    app.camera.set_pos(me.x + 0.0, me.y + 1.0, 1.6); app.camera.look_at(me.x, me.y + 4.5, 1.25); app.camLens.set_fov(55); shot("npc_skin", False)
def taxi():
    g = G(); place(30, -32, 90); me = g.me()
    c = g.spawn_car("taxi", me.x - 4, me.y, 90, role="taxi"); c.driver = "ai"; g.taxi = c
    from fs_ai import ResponderAI
    c.ai = ResponderAI(g, c, (me.x, me.y)); c.ai.arrived = True; g.board_taxi()
    for _ in range(20): g.step(1 / 30.0)
    shot("taxi_first_person")
    print("RESULT voice files", [e["file"] for e in app.voice_index.get("taxi_en_hello", [])], flush=True)
    g.taxi_go((300, 300), "TEST")
    for _ in range(140): g.step(1 / 30.0)
    shot("taxi_rear_view")
    # slapstick bump: spawn a car just ahead in his lane, force the bump, grab the mid-crash frame
    f = c.fwd; o = g.spawn_car("sedan", c.x + f[0] * 6 - f[1] * 1.2, c.y + f[1] * 6 + f[0] * 1.2, c.h); o.wake() if hasattr(o, "wake") else None
    g.taxi_bump(c)
    for _ in range(4): g.step(1 / 30.0)
    shot("taxi_crash")
    sp0 = c.speed
    for _ in range(30): g.step(1 / 30.0)
    print("RESULT bump speed before/after 1s", round(sp0, 1), round(c.speed, 1), "bumped", g.ride.get("bumped"), flush=True)
    g.key_c()
    for _ in range(60): g.step(1 / 30.0)
    shot("_taxi_fp_riding")
    c.vx = c.vy = 0; g.paused = True
    r = math.radians(c.h); fx, fy = -math.sin(r), math.cos(r); rx, ry = math.cos(r), math.sin(r)
    me.np.show()
    app.camera.set_pos(c.x + rx * 4.2 + fx * 0.2, c.y + ry * 4.2 + fy * 0.2, 1.75); app.camera.look_at(c.x, c.y - 0.0, 0.95); app.camLens.set_fov(55); shot("taxi_glass", False)
    d = c.taxi_driver; hp = d.np.get_pos(app.render)
    d.np.set_h(0); d.set_chew(0.0)
    app.camera.set_pos(c.x + fx * 2.3 + rx * 0.75, c.y + fy * 2.3 + ry * 0.75, 1.62); app.camera.look_at(hp[0], hp[1], hp[2] + 1.42); app.camLens.set_fov(24); shot("taxi_driver", False)
    app.camLens.set_fov(70); g.paused = False
    g.skip_ride()
    for _ in range(60): g.step(1 / 30.0)
    print("RESULT taxi after skip ride", g.ride, flush=True)
import time as _t
_T0 = _t.time()
PLAN = [(0.1, lambda: app.show_title()), (0.3, lambda: app.show_menu()), (0.3, lambda: app.start_game(None)), (1.0, lambda: None),
        (0.1, lambda: [G().step(1 / 30.0) for _ in range(250)]),
        (0.1, lambda: place(12, -40, 0)), (0.1, talk("npc_japanese_1")),
        (0.1, ramen),
        (0.1, police), (0.1, skin), (0.1, traffic), (0.1, taxi), (0.1, lambda: app.userExit())]
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
