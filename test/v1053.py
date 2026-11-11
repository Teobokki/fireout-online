# v1.0.5.3 QA: EVO reference angle, street canyon, chase cam, all car models, festival feed/page. FS_TESTSCRIPT=test/v1053.py FS_QA=quick|full
import os, math, traceback, time as _t
from panda3d.core import Filename
OUT = os.environ.get("FS_QA_OUT", "/workspace/fs_bump/qa"); os.makedirs(OUT, exist_ok=True); FULL = os.environ.get("FS_QA") == "full"
def G(): return app.game
def step(n=1):
    for _ in range(n): G().step(1 / 30.0)
def shot(name, hud=False):
    if not hud: app.aspect2d.hide()
    app.graphicsEngine.render_frame(); app.graphicsEngine.render_frame()
    app.win.save_screenshot(Filename.from_os_specific(os.path.join(OUT, name + ".png"))); print("SHOT", name, flush=True); app.aspect2d.show()
def cam(x, y, z, lx, ly, lz, fov):
    app.camera.set_pos(x, y, z); app.camera.look_at(lx, ly, lz); app.camLens.set_fov(fov)
def run():
    g = G(); app.settings["tod"] = "night"; g.tod = 22.5; g.paused = False
    print("RESULT gfx", app.settings.get("gfx"), getattr(app, "gfx_detected", ""), "grade", app.gfx.fm is not None, "cube", app.gfx.cube_buf is not None, flush=True)
    tx, ty, th = g.world.tower_top
    rx, ry = g.world.nearest_road_point(tx + 10, ty - 120)[:2]
    me = g.me(); me.x, me.y = rx + 4, ry - 6; me.sync(); g.cam_pos = None
    c = g.ensure_in_car(rx, ry, 0); step(10)
    print("RESULT car", c.kind, c.spec["name"], "lod", c.lod is not None, flush=True)
    g.paused = True; h_road = c.h
    r = math.radians(c.h); fx, fy = -math.sin(r), math.cos(r); sx, sy = math.cos(r), math.sin(r)
    cam(c.x + fx * 5.2 - sx * 3.4, c.y + fy * 5.2 - sy * 3.4, 0.75, c.x + fx * 0.6, c.y + fy * 0.6, 0.65, 50); shot("evo_ref_night")
    cam(c.x + fx * 2.6 - sx * 1.9, c.y + fy * 2.6 - sy * 1.9, 0.55, c.x + fx * 1.4 - sx * 0.9, c.y + fy * 1.4 - sy * 0.9, 0.4, 35); shot("evo_wheel_close")
    cam(c.x - fx * 5.5 + sx * 3.0, c.y - fy * 5.5 + sy * 3.0, 1.3, c.x, c.y, 0.7, 50); shot("evo_rear_night")
    cam(c.x + sx * 2.2 + fx * 0.4, c.y + sy * 2.2 + fy * 0.4, 1.25, c.x - sx * 0.2, c.y - sy * 0.2, 0.8, 50); shot("evo_interior")
    for o in list(g.cars):
        if o is not c and o.role == "traffic" and math.hypot(o.x - c.x, o.y - c.y) < 40: o.np.hide()
    dx, dy = fx, fy          # look straight down the road the car stands on
    cam(c.x - dx * 9, c.y - dy * 9, 2.2, c.x + dx * 60, c.y + dy * 60, 9, 62); shot("street_canyon_tower")
    for o in list(g.cars): o.np.show()
    # A/D direction check (driving): hold D -> the car must turn RIGHT on screen (heading decreases)
    g.paused = False; g.cam_pos = None
    h0 = c.h
    g.vb["v_right"] = True; g.vb["v_up"] = True
    for i in range(30): g.step(1 / 30.0)
    g.vb["v_right"] = False; g.vb["v_up"] = False
    print("RESULT drive D heading change", round(c.h - h0, 1), "(negative = right turn)", flush=True)
    h0 = c.h; g.vb["v_left"] = True; g.vb["v_up"] = True
    for i in range(30): g.step(1 / 30.0)
    g.vb["v_left"] = False; g.vb["v_up"] = False
    print("RESULT drive A heading change", round(c.h - h0, 1), "(positive = left turn)", flush=True)
    c.x, c.y, c.h = rx, ry, h_road; c.vx = c.vy = c.w = 0; g.cam_pos = None
    for o in list(g.cars):          # clear road for the chase-cam shot (a traffic car sat right behind the camera last run)
        if o is not c and o.driver != "player" and math.hypot(o.x - c.x, o.y - c.y) < 60: o.np.hide(); o.x += 500
    g.vb["v_up"] = True
    for i in range(45): g.step(1 / 30.0)
    g.vb["v_up"] = False
    shot("chase_cam_drive", hud=True)
    g.paused = True
    if FULL:
        kinds = ["evo", "gts", "coupe", "sedan", "taxi", "police", "hatch", "kei", "suv", "van", "ambulance"]
        bx, by = c.x + 30, c.y + 40
        bx, by = g.world.nearest_road_point(bx, by)[:2]
        cars = []
        for k, kind in enumerate(kinds):
            o = g.spawn_car(kind, bx + (k % 4) * 6.0 - 9, by + (k // 4) * 7.0, 0, parked=True); cars.append(o)
        step(2); g.paused = True
        for o in cars:
            r = math.radians(o.h); fx, fy = -math.sin(r), math.cos(r); sx, sy = math.cos(r), math.sin(r)
            for nm, (a, b, z, fov) in (("fq", (5.0, -3.4, 1.1, 45)), ("rq", (-5.2, 3.2, 1.3, 45))):
                for cc in cars: cc.np.hide() if cc is not o else cc.np.show()
                cam(o.x + fx * a + sx * b, o.y + fy * a + sy * b, z, o.x, o.y, 0.6, fov); shot("car_%s_%s" % (o.kind, nm))
        for cc in cars: cc.np.show()
        app.settings["tod"] = "day"; g.tod = 13.0; step(3); g.paused = True
        cam(c.x - fx * 3 + sx * 3, c.y - fy * 3 + sy * 3, 1.7, tx, ty, 30, 62); shot("street_day")
        o = cars[0]; r = math.radians(o.h); fx, fy = -math.sin(r), math.cos(r); sx, sy = math.cos(r), math.sin(r)
        cam(o.x + fx * 5.2 - sx * 3.4, o.y + fy * 5.2 - sy * 3.4, 0.8, o.x, o.y, 0.6, 50); shot("evo_day")
        cam(c.x, c.y - 10, 30, c.x, c.y + 300, 0, 60); shot("distance_shimmer")
    g.paused = False
    # A/D direction check (walking): exit the car, hold D -> the player must move to the RIGHT of the camera view
    try:
        if g.pcar is not None: g.exit_car(force=True)
        for i in range(20): g.step(1 / 30.0)
        me = g.me()
        for key, nm in (("v_right", "D"), ("v_left", "A")):
            g.update_camera(1 / 30.0); rv = app.camera.get_quat(app.render).get_right(); x0, y0 = me.x, me.y
            g.vb[key] = True
            for i in range(12): g.step(1 / 30.0)
            g.vb[key] = False
            d = (me.x - x0) * rv[0] + (me.y - y0) * rv[1]
            print("RESULT walk %s moves along camera-right" % nm, round(d, 2), "(D should be +, A should be -)", flush=True)
    except Exception:
        print("TESTERR walk", traceback.format_exc(), flush=True)
    if g.events: 
        g.events.notify("New car unlocked", "ENERASTIC MG EVO SEDAN", small=False)
        g.events.feed.push("SUMMER NIGHT RACE", "Downtown to Hikari Beach in under 90 s", "\u00a515,000", "R", (0.35, 0.85, 1.0, 1))
        for i in range(25): g.step(1 / 30.0)
        shot("feed_hud", hud=True)
        g.toggle_phone(); g.phone_screen("festival"); g.step(1 / 30.0); shot("festival_page", hud=True)
        print("RESULT season", g.events.season, [e["id"] for e in g.events.events()], flush=True)
_T0 = _t.time(); print("TEST LOADED", flush=True)
PLAN = [(0.1, lambda: app.show_title()), (0.3, lambda: app.show_menu()), (0.3, lambda: app.start_game(None)), (1.0, lambda: None),
        (0.1, run), (0.1, lambda: app.userExit())]
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
