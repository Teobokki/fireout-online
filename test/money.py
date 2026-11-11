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
SUF = os.environ.get("FS_SUF", "")
def mon():
    return app.money_ui
def mtry(t):
    m = mon(); m.ent.enterText(t); m.do_add(); print("RESULT add %r -> %r cash=%d" % (t, m.msg["text"], G().cash), flush=True)
def check_save():
    import json
    g = G(); g.save(); d = app.load_save()
    print("RESULT saved_cash", d and d.get("cash"), "hud", g.cash_t["text"], flush=True)
PLAN = [
    (0.2, lambda: None), (6.0, lambda: None),
    (0.1, lambda: app.show_title()), (0.3, lambda: None), (0.1, lambda: app.show_menu()), (0.3, lambda: None),
    (0.1, lambda: app.start_game(None)), (0.6, lambda: sim(9.0)),
    (0.1, lambda: G().enter_car(G().own)), (0.1, lambda: sim(2.0, lambda: drive(1.0, 0.0))), (0.1, lambda: G().toggle_phone()),
    (0.1, lambda: sim(1.0, lambda: drive(1.0, 0.0))), (0.3, lambda: shot("phone_driving_v102" + SUF)), (0.1, stop_input),
    (0.1, lambda: G().toggle_phone()), (0.1, lambda: sim(1.0)),
    (0.1, lambda: app.show_pause()), (0.3, lambda: shot("pause_menu_v102" + SUF)),
    (0.1, lambda: app.show_add_money()), (0.1, lambda: mtry("-5")), (0.1, lambda: mtry("abc")), (0.1, lambda: mtry("0")), (0.1, lambda: mtry("")),
    (0.1, lambda: mtry("1,000,000")),
    (0.1, lambda: (mon().quick(10 ** 9), mon().quick(10 ** 6), mon().quick(1000))), (0.3, lambda: shot("add_money" + SUF)),
    (0.1, lambda: mon().do_add()), (0.1, lambda: print("RESULT cash", G().cash, flush=True)),
    (0.1, lambda: mtry("500000000000")), (0.3, lambda: shot("cash_limit_added" + SUF)),
    (0.1, lambda: mtry("1")), (0.3, lambda: shot("cash_limit" + SUF)),
    (0.1, check_save),
    (0.1, lambda: app.hide_pause()), (0.1, lambda: (setattr(G(), "cash_pop_k", 2.6), G().cash_pop.setText("+¥98,998,999,000"))), (0.1, lambda: sim(0.5)), (0.3, lambda: shot("cash_hud" + SUF)),
    (0.1, lambda: print("RESULT done", flush=True)),
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
