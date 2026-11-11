# v1.0.4 MIYOYAZU: switch, outfit, portrait, BUILD, TSUNAMI. FS_TESTSCRIPT=test/miyo.py  (FS_MIYO_PART=look|build|tsunami|all)
import os, math, traceback
from panda3d.core import Filename
OUT = os.environ.get("FS_POSE_OUT", os.path.join(app.BASE, "docs"))
PART = os.environ.get("FS_MIYO_PART", "all")
def G(): return app.game
def step(n=1):
    for _ in range(n): G().step(1 / 30.0)
def shot(name, hud=True):
    if not hud: app.render2d.hide(); app.aspect2d.hide()
    app.graphicsEngine.render_frame(); app.graphicsEngine.render_frame()
    app.win.save_screenshot(Filename.from_os_specific(os.path.join(OUT, name + ".png"))); print("SHOT", name, flush=True)
    if not hud: app.render2d.show(); app.aspect2d.show()
def place(x, y, h, tod=14.5):
    g = G(); g.paused = False; g.tod = tod; app.settings["tod"] = "day" if 7 < tod < 17 else "cycle"
    me = g.me(); me.x, me.y, me.h = x, y, h; g.cam_yaw = h; me.sync(); g.cam_pos = None
    b = g.buddy(); b.x, b.y = x + 2, y - 2; b.sync(); step(25)
def look(name, dist=2.6, ang=0, z=1.2, at=1.0, fov=50, hud=False, who=None):
    g = G(); me = g.chars[who] if who else g.me(); h = math.radians(me.h + ang); fx, fy = -math.sin(h), math.cos(h)
    app.camera.set_pos(me.x + fx * dist, me.y + fy * dist, me.np.get_z() + z); app.camera.look_at(me.x, me.y, me.np.get_z() + at); app.camLens.set_fov(fov)
    shot(name, hud); app.camLens.set_fov(70)
def portrait():
    look("_miyo_head", 1.0, 18, 1.62, 1.56, 30)
    from PIL import Image
    im = Image.open(os.path.join(OUT, "_miyo_head.png")).convert("RGB"); w, h = im.size; s = min(w, h)
    im = im.crop(((w - s) // 2, 0, (w + s) // 2, s)).resize((512, 512), Image.LANCZOS)
    im.save(os.path.join(app.BASE, "assets", "tex", "portrait_miyo.png")); im.save(os.path.join(OUT, "miyo_portrait.png")); print("SHOT portrait_miyo", flush=True)
def st(tag=""):
    g = G(); me = g.me()
    print("RESULT", tag, "active", g.active, "mate", g.mate, "benched", [k for k, p in g.chars.items() if getattr(p, "benched", False)],
          "pos %.1f %.1f z %.2f swim %s" % (me.x, me.y, me.np.get_z(), getattr(me, "swim", None)), "builds", len(g.builds.items),
          "tsu", g.tsunami and (g.tsunami.phase, round(g.tsunami.level, 2), round(g.tsunami.front, 1)), flush=True)
def build(text):
    g = G(); g.miyo.start_build(text); step(60); st("built " + text)
def walk(sec, f=1, run=False):
    g = G(); g.vb["v_up"] = f > 0; g.vb["v_down"] = f < 0; g.vb["v_nitro"] = run
    step(int(sec * 30)); g.vb.clear(); st("walked")
def overview(name, back=16, up=9, ang=180, fov=60, hud=True, tx=None):
    g = G(); me = g.me(); h = math.radians(me.h + ang); fx, fy = -math.sin(h), math.cos(h)
    app.camera.set_pos(me.x + fx * back, me.y + fy * back, up); app.camera.look_at(me.x - fx * 6, me.y - fy * 6, 2.0); app.camLens.set_fov(fov)
    shot(name, hud); app.camLens.set_fov(70)
import time as _t
_T0 = _t.time()
PLAN = [(0.1, lambda: app.show_title()), (0.3, lambda: app.show_menu()), (0.3, lambda: app.start_game(None)), (1.0, lambda: None),
        (0.1, lambda: [G().step(1 / 30.0) for _ in range(300)]), (0.1, st)]
if PART in ("look", "all"):
    PLAN += [(0.1, lambda: G().switch_char()), (0.1, lambda: G().switch_char()), (0.1, lambda: step(20)), (0.1, lambda: st("after 2 switches")),
             (0.1, lambda: place(452, -300, 90)), (0.1, portrait),
             (0.1, lambda: G().update_portraits()), (0.1, lambda: step(5)), (0.1, lambda: shot("miyoyazu_switch")),
             (0.1, lambda: look("miyoyazu_outfit", 3.0, 25, 1.3, 1.0, 45)), (0.1, lambda: look("miyoyazu_outfit_back", 3.0, 200, 1.3, 1.0, 45)),
             (0.1, lambda: look("miyoyazu_face", 0.9, 10, 1.65, 1.6, 35)),
             (0.1, lambda: G().arsenal.open_wheel()), (0.1, lambda: step(3)), (0.1, lambda: shot("miyoyazu_weapons")), (0.1, lambda: G().arsenal.close_wheel()),
             (0.1, lambda: G().toggle_phone()), (0.1, lambda: G().open_camera()), (0.1, lambda: step(15)), (0.1, lambda: G().cam_set_expr("smile")), (0.1, lambda: step(3)),
             (0.1, lambda: shot("miyoyazu_selfie_smile")), (0.1, lambda: G().cam_set_expr("frown")), (0.1, lambda: step(3)), (0.1, lambda: shot("miyoyazu_selfie_frown")),
             (0.1, lambda: G().key_esc()), (0.1, lambda: step(3)), (0.1, lambda: G().toggle_phone() if G().phone else None),
             (0.1, lambda: G().switch_char()), (0.1, lambda: step(5)), (0.1, lambda: st("after 3rd switch")), (0.1, lambda: G().select_char("miyo")), (0.1, lambda: step(5)), (0.1, lambda: st("select miyo"))]
if PART in ("build", "all"):
    PLAN += [(0.1, lambda: G().select_char("miyo")), (0.1, lambda: place(530, -120, 0, 15.0)), (0.1, lambda: G().key_b()), (0.1, lambda: step(3)), (0.1, lambda: shot("miyo_build_menu")),
             (0.1, lambda: G().miyo.close_ui()),
             (0.1, lambda: build("stairs")), (0.1, lambda: [walk(0.5) for _ in range(9)]), (0.1, lambda: overview("miyo_on_stairs", 7, 6.5, 120, 60)),
             (0.1, lambda: place(536, -113, 90, 15.0)), (0.1, lambda: walk(3.0)), (0.1, lambda: st("walk into stairs side (expect blocked near x=532)")),
             (0.1, lambda: place(530, -120, 90, 15.0)), (0.1, lambda: build("japanese pagoda")),
             (0.1, lambda: place(530, -120, 180, 15.0)), (0.1, lambda: build("lighthouse")),
             (0.1, lambda: place(530, -120, -90, 15.0)), (0.1, lambda: G().miyo.start_build("small hosue")), (0.1, lambda: step(12)), (0.1, lambda: shot("miyo_building_anim")), (0.1, lambda: step(50)),
             (0.1, lambda: place(530, -132, 0, 15.0)), (0.1, lambda: overview("miyoyazu_build", 20, 14, 180, 65)),
             (0.1, lambda: walk(4.0)), (0.1, lambda: st("walked into stairs side?")),
             (0.1, lambda: G().miyo.undo()), (0.1, lambda: step(3)), (0.1, lambda: st("undo")), (0.1, lambda: G().miyo.clear()), (0.1, lambda: step(3)), (0.1, lambda: st("clear"))]
if PART in ("tsunami", "all"):
    def tsu(sev, name, wait=180, view=None):
        def f():
            g = G(); g.select_char("miyo"); place(520, 40, 90, 15.0)
            g.key_n(); step(2); shot("tsunami_menu")
            g.miyo.start_tsunami(sev); step(wait); st("tsunami " + str(sev))
            overview(name, 22, 12, 90 + 180, 70)
        return f
    def stopped():
        g = G(); g.miyo.stop_tsunami(); step(200); st("stopped"); overview("tsunami_stopped", 22, 12, 270, 70)
        print("RESULT car z", [round(c.np.get_z(), 2) for c in g.cars[:6]], flush=True)
    PLAN += [(0.1, tsu("small", "tsunami_small", 330)), (0.1, lambda: overview("tsunami_small_side", 30, 9, 0, 70)), (0.1, stopped),
             (0.1, tsu("big", "tsunami_big_surge", 200)), (0.1, lambda: step(150)),
             (0.1, lambda: overview("tsunami_big", 26, 14, 270, 70)), (0.1, lambda: overview("tsunami_big_side", 30, 12, 0, 70)), (0.1, lambda: st("big")),
             (0.1, lambda: walk(3.0)), (0.1, lambda: overview("tsunami_big_swim", 5, 3, 180, 60)), (0.1, lambda: step(30)), (0.1, lambda: shot("tsunami_big_hud")), (0.1, stopped)]
if PART in ("clothing", "all"):
    def cl_car():
        g = G(); me = g.me(); c = min(g.cars, key=lambda c: math.hypot(c.x - me.x, c.y - me.y)); me.x, me.y = c.x + 2, c.y; me.sync(); g.enter_car(c); step(5)
        app.show_pause(); app.show_clothing(); app.money_ui.pick("crop"); step(0)
        print("RESULT car block outfit", g.me().outfit, g.outfit_block(), flush=True); shot("_clothing_car"); app.money_ui.close(); app.hide_pause(); g.exit_car(force=True); step(10)
    def cl(who, oid, name=None):
        def f():
            g = G(); g.select_char(who); step(5); app.show_pause(); step(0); app.show_clothing(); app.money_ui.pick(oid)
            app.graphicsEngine.render_frame()
            print("RESULT clothing", who, "->", g.chars[who].outfit, "saved", g.outfits, flush=True)
            if name: shot(name)
            app.money_ui.close(); shot("_pause_after_" + who); app.hide_pause(); step(3)
        return f
    PLAN += [(0.1, lambda: G().select_char("ana")), (0.1, lambda: place(10, -30, 200, 13.0)), (0.1, cl("ana", "police", "pause_clothing")),
             (0.1, cl("daniel", "swim", "pause_clothing_daniel")), (0.1, cl("miyo", "default", "pause_clothing_miyo")), (0.1, cl_car),
             (0.1, lambda: (G().save(), print("RESULT saved file outfits", __import__("json").load(open(app.save_path())).get("outfits"), flush=True)))]
PLAN += [(0.1, lambda: app.userExit())]
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
