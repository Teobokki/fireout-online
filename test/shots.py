# headless test + soak: run with FS_TESTSCRIPT=test/shots.py (offscreen). Saves docs/*.png and prints RESULT lines.
import os, math, random, traceback
from panda3d.core import Filename
OUT = os.path.join(app.BASE, "docs"); os.makedirs(OUT, exist_ok=True)
def shot(name):
    app.graphicsEngine.render_frame(); app.graphicsEngine.render_frame()
    app.win.save_screenshot(Filename.from_os_specific(os.path.join(OUT, name + ".png"))); print("SHOT", name, flush=True)
def G(): return app.game
def sim(sec, fn=None):
    g = G()
    for _ in range(int(sec * 30)):
        if fn: fn()
        g.step(1 / 30.0)
state = {"i": 0, "t": 0.0, "wait": 0.0}
def drive(thr=1.0, st=0.0, nitro=False):
    g = G(); g.vb["v_up"] = thr > 0; g.vb["v_down"] = thr < 0; g.vb["v_left"] = st > 0; g.vb["v_right"] = st < 0; g.vb["v_nitro"] = nitro
def stop_input():
    G().vb.clear()
def soak_wall():
    g = G(); c = g.pcar; maxpen = 0
    for k in range(6):
        c.x, c.y, c.h = 50, -94, random.choice([0, 90, 180, 270]) + random.uniform(-30, 30); c.vx = c.vy = 0; c.wake()
        f = c.fwd; c.vx, c.vy = f[0] * 70, f[1] * 70
        for _ in range(120):
            g.step(1 / 60.0)
            for cx, cy, r, _ in c.circles():
                px, py, nx, ny, tag = g.world.grid.push_circle(cx, cy, r)
                maxpen = max(maxpen, math.hypot(px, py))
    print("RESULT wall_soak max_penetration_m=%.3f car=(%.1f,%.1f)" % (maxpen, c.x, c.y), flush=True)
def soak_jack():
    g = G(); n = 0
    for k in range(12):
        if g.pcar: g.pcar.vx = g.pcar.vy = 0; g.exit_car()
        me = g.me()
        cands = [c for c in g.cars if c.ai is not None and c.driver == "ai" and c not in g.police and not getattr(c, "racer", False)]
        if not cands: g.populate(); continue
        c = random.choice(cands); c.vx = c.vy = 0
        me.x, me.y = c.door_pos(1)
        g.key_f(); n += g.pcar is c
        for _ in range(30): g.step(1 / 60.0)
    print("RESULT jack_soak jacked=%d peds=%d cars=%d" % (n, len(g.peds), len(g.cars)), flush=True)
def _look(spot, d, up):
    g = G(); g.paused = True; w = g.world; x, y, z = spot
    best = None
    for a in range(0, 360, 20):
        import math as m
        cx, cy = x + m.cos(m.radians(a)) * d, y + m.sin(m.radians(a)) * d
        if not w.grid.segment_blocked(cx, cy, x, y) and (best is None or w.on_road(cx, cy)): best = (cx, cy)
    best = best or (x, y - d)
    app.camera.set_pos(best[0], best[1], up); app.camera.look_at(x, y, z); app.camLens.set_fov(60)
def duo_close():
    g = G(); g.paused = True; a, d = g.chars["ana"], g.chars["daniel"]
    mx, my = (a.x + d.x) / 2, (a.y + d.y) / 2; import math as m
    h = m.radians(a.h); fx, fy = -m.sin(h), m.cos(h)
    app.camera.set_pos(mx + fx * 3.2, my + fy * 3.2, 1.6); app.camera.look_at(mx, my, 1.3); app.camLens.set_fov(50)
def char_close(who, side):
    g = G(); g.paused = False; g.vb["v_up"] = True; sim(0.8); g.vb.clear(); g.vb["v_up"] = True; g.step(1 / 30.0); g.vb.clear(); g.paused = True
    c = g.chars[who]; import math as m
    h = m.radians(c.h + (90 if side else 0)); fx, fy = -m.sin(h), m.cos(h)
    app.camera.set_pos(c.x + fx * 1.25, c.y + fy * 1.25, 1.6); app.camera.look_at(c.x, c.y, 1.38); app.camLens.set_fov(45)
def skyline(day):
    g = G(); app.settings["tod"] = "day" if day else "night"; g.paused = False; sim(0.6); g.paused = True
    app.camera.set_pos(600, -60, 14); app.camera.look_at(0, 40, 70); app.camLens.set_fov(65)
def street(day):
    g = G(); app.settings["tod"] = "day" if day else "night"; g.paused = False; sim(0.6); g.paused = True
    app.camera.set_pos(8, -150, 2.2); app.camera.look_at(4, 0, 30); app.camLens.set_fov(70)
def home_ext():
    g = G(); g.paused = True; app.camera.set_pos(462, -270, 7); app.camera.look_at(430, -294, 3); app.camLens.set_fov(65)
def flag_view():
    w = G().world; banners = [s for s in w.flag_spots if not any(abs(s[0] - p[0]) < 0.5 and abs(s[1] - p[1]) < 0.5 for p in w.flag_poles)]
    print("RESULT flags=%d poles=%d" % (len(w.flag_spots), len(w.flag_poles)), flush=True)
    _look((banners or w.flag_spots)[0], 34, 6)
def flag_view2():
    w = G().world
    if w.flag_poles: x, y, z, _ = w.flag_poles[0]; _look((x, y, z - 3), 45, z - 8)
PLAN = [
    (0.2, lambda: shot("boot_splash")),
    (6.0, lambda: shot("boot_intro")),
    (0.1, lambda: app.show_title()), (0.3, lambda: shot("title")),
    (0.1, lambda: app.show_menu()), (0.3, lambda: shot("menu")),
    (0.1, lambda: app.start_game(None)), (0.6, lambda: sim(6.0)), (0.1, lambda: shot("on_foot")),
    (0.1, lambda: G().toggle_phone()), (0.1, lambda: shot("phone")), (0.1, lambda: G().phone_screen("contacts")), (0.1, lambda: shot("phone_contacts")),
    (0.1, lambda: G().call_emergency()), (0.1, lambda: G().toggle_phone() if G().phone else None), (0.1, lambda: sim(12)), (0.1, lambda: shot("ambulance")),
    (0.1, lambda: G().switch_char()), (0.1, lambda: sim(1.5)), (0.1, lambda: shot("switch_daniel")), (0.1, lambda: G().switch_char()), (0.1, lambda: sim(1.0)),
    (0.1, lambda: home_ext()), (0.1, lambda: shot("home_exterior")), (0.1, lambda: setattr(G(), "paused", False)),
    (0.1, lambda: G().enter_home()), (0.1, lambda: sim(0.3)), (0.1, lambda: shot("home_interior")),
    (0.1, lambda: G().open_wardrobe()), (0.1, lambda: sim(0.2)), (0.1, lambda: shot("wardrobe_default")),
    (0.1, lambda: G().wardrobe_pick("crop")), (0.1, lambda: sim(1.0)), (0.1, lambda: shot("wardrobe_crop")),
    (0.1, lambda: G().wardrobe_pick("bikini")), (0.1, lambda: sim(1.5)), (0.1, lambda: shot("wardrobe_bikini")),
    (0.1, lambda: G().wardrobe_pick("police")), (0.1, lambda: sim(2.0)), (0.1, lambda: shot("wardrobe_police")),
    (0.1, lambda: G().close_wardrobe(False)), (0.1, lambda: G().start_shower()), (0.1, lambda: sim(2.0)), (0.1, lambda: shot("shower_ana")),
    (0.1, lambda: G().end_shower()), (0.1, lambda: G().switch_char()), (0.1, lambda: G().start_shower()), (0.1, lambda: sim(2.0)), (0.1, lambda: shot("shower_daniel")),
    (0.1, lambda: G().end_shower()), (0.1, lambda: G().switch_char()), (0.1, lambda: sim(0.5)),
    (0.1, lambda: G().open_wardrobe()), (0.1, lambda: G().wardrobe_pick("police")), (0.1, lambda: G().close_wardrobe(True)), (0.1, lambda: G().home_sleep()), (0.1, lambda: print("RESULT home tod=%.1f outfit=%s" % (G().tod, G().outfit), flush=True)),
    (0.1, lambda: G().leave_home()), (0.1, lambda: sim(1.0)), (0.1, lambda: shot("police_outfit_world")),
    (0.1, lambda: (setattr(G(), "outfit", "default"), G().chars["ana"].set_outfit("default"))),
    (0.1, lambda: (G().me().__setattr__("x", 40), G().me().__setattr__("y", -94), G().buddy().__setattr__("x", 42), G().buddy().__setattr__("y", -94))), (0.1, lambda: sim(1.0)),
    (0.1, lambda: shot("duo_on_foot")), (0.1, duo_close), (0.1, lambda: shot("duo_closeup")), (0.1, lambda: setattr(G(), "paused", False)),
    (0.1, lambda: char_close("ana", False)), (0.1, lambda: shot("ana_front")), (0.1, lambda: char_close("ana", True)), (0.1, lambda: shot("ana_side")),
    (0.1, lambda: G().switch_char()), (0.1, lambda: sim(1.0)),
    (0.1, lambda: char_close("daniel", False)), (0.1, lambda: shot("daniel_front")), (0.1, lambda: char_close("daniel", True)), (0.1, lambda: shot("daniel_side")),
    (0.1, lambda: setattr(G(), "paused", False)), (0.1, lambda: G().switch_char()), (0.1, lambda: sim(1.0)),
    (0.1, lambda: street(True)), (0.1, lambda: shot("city_day")), (0.1, lambda: skyline(True)), (0.1, lambda: shot("skyline_day")),
    (0.1, lambda: street(False)), (0.1, lambda: shot("city_night")), (0.1, lambda: skyline(False)), (0.1, lambda: shot("skyline_night")),
    (0.1, lambda: (app.settings.__setitem__("tod", "cycle"), setattr(G(), "tod", 15.0), setattr(G(), "paused", False))),
    (0.1, lambda: G().arsenal.open_wheel()), (0.1, lambda: shot("weapon_wheel")), (0.1, lambda: G().arsenal.pick("pistol")),
    (0.1, lambda: G().vb.__setitem__("v_aim", True)), (0.1, lambda: sim(0.5)), (0.1, lambda: [G().arsenal.fire(True) or sim(0.35) for _ in range(3)]),
    (0.1, lambda: shot("aim_pistol")), (0.1, lambda: G().vb.__setitem__("v_aim", False)), (0.1, lambda: G().arsenal.pick("pickaxe")),
    (0.1, lambda: [G().arsenal.fire(True) or sim(1.1) for _ in range(3)]), (0.1, lambda: print("RESULT weapons ok ammo=%s" % G().arsenal.ammo, flush=True)),
    (0.1, lambda: G().enter_car(G().own)), (0.1, lambda: sim(3.0, lambda: drive(1.0, 0.0))), (0.1, lambda: shot("driving")), (0.1, lambda: G().repair_car()), (0.1, lambda: shot("repair")), (0.1, stop_input),
    (0.1, lambda: G().toggle_map()), (0.1, lambda: shot("map")), (0.1, lambda: G().close_overlay()),
    (0.1, lambda: G().start_activity("sprint")), (0.1, lambda: sim(8.0, lambda: drive(1.0, 0.0, True))), (0.1, lambda: shot("race")), (0.1, stop_input),
    (0.1, lambda: G().quit_activity()),
    (0.1, lambda: G().start_activity("chase")), (0.1, lambda: sim(7.0, lambda: drive(1.0, 0.0))), (0.1, lambda: shot("police_chase")), (0.1, lambda: G().busted()), (0.1, lambda: sim(0.3)), (0.1, lambda: shot("busted")), (0.1, lambda: G()._ds_end()), (0.1, stop_input),
    (0.1, lambda: G().quit_activity()), (0.1, lambda: [G().remove_car(c) for c in list(G().police)]), (0.1, lambda: setattr(G(), "heat", 0)),
    (0.1, lambda: G().start_activity("garage")), (0.1, lambda: sim(1.0)), (0.1, lambda: shot("garage")), (0.1, lambda: G().garage_swap(1)), (0.1, lambda: sim(1.0)), (0.1, lambda: shot("garage_next")),
    (0.1, lambda: G().garage_swap(-1)), (0.1, lambda: G().garage_paint((0.95, 0.78, 0.05))),
    (0.1, lambda: G().garage_plate("ANA 2026")), (0.1, lambda: sim(2.0)), (0.1, lambda: shot("garage_custom")), (0.1, lambda: G().close_garage()),
    (0.1, soak_wall), (0.1, soak_jack), (0.1, lambda: sim(1.0)), (0.1, lambda: shot("after_soak")),
    (0.1, lambda: G().exit_car(force=True) if G().pcar else None), (0.1, lambda: G().request_taxi()), (0.1, lambda: sim(16.0)), (0.1, lambda: shot("taxi_arrive")),
    (0.1, lambda: print("RESULT taxi arrived=%s" % G().taxi_ai_arrived(), flush=True)),
    (0.1, lambda: (G().me().__setattr__("x", G().taxi.x + 3), G().me().__setattr__("y", G().taxi.y), G().key_f()) if G().taxi else print("RESULT no taxi")),
    (0.1, lambda: shot("taxi_menu")), (0.1, lambda: G().taxi_go((460, 0), "HIKARI BEACH") if G().ride else None), (0.1, lambda: sim(3.0)), (0.1, lambda: shot("taxi_ride")),
    (0.1, lambda: G().skip_ride()), (0.1, lambda: sim(3.0)), (0.1, lambda: shot("beach")),
    (0.1, lambda: app.settings.__setitem__("tod", "night")), (0.1, lambda: sim(0.6)), (0.1, lambda: shot("beach_night")), (0.1, lambda: app.settings.__setitem__("tod", "cycle")),
    (0.1, flag_view), (0.1, lambda: shot("flag_banner")), (0.1, flag_view2), (0.1, lambda: shot("flag_rooftop")), (0.1, lambda: setattr(G(), "paused", False)),
    (0.1, lambda: app.show_pause()), (0.1, lambda: shot("pause")), (0.1, lambda: app.open_settings(None)), (0.1, lambda: shot("settings")),
    (0.1, lambda: app.quit_to_title()), (0.1, lambda: app.show_credits()), (0.1, lambda: shot("credits")),
    (0.1, lambda: (print("RESULT done", flush=True), app.userExit())),
]
def runner(task):
    try:
        if state["i"] >= len(PLAN): return task.done
        d, f = PLAN[state["i"]]
        if app.world is None: return task.cont
        state["t"] += 0.05
        if state["t"] >= d:
            state["t"] = 0.0; state["i"] += 1; f()
    except Exception:
        print("TESTERR", traceback.format_exc(), flush=True); state["i"] += 1
    return task.cont
app.task_mgr.add(runner, "test-runner", sort=100)
