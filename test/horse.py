# v1.0.4 city-style MIYOYAZU builds. FS_TESTSCRIPT=test/citybuild.py
import os, math, traceback, time as _t
from panda3d.core import Filename, TransformState
OUT = os.environ.get("FS_POSE_OUT", os.path.join(app.BASE, "docs"))
def G(): return app.game
def step(n=1):
    for _ in range(n): G().step(1 / 30.0)
def shot(name, hud=False):
    if not hud: app.render2d.hide(); app.aspect2d.hide()
    app.graphicsEngine.render_frame(); app.graphicsEngine.render_frame()
    app.win.save_screenshot(Filename.from_os_specific(os.path.join(OUT, name + ".png"))); print("SHOT", name, flush=True)
    if not hud: app.render2d.show(); app.aspect2d.show()
def place(x, y, h, tod=14.5):
    g = G(); g.paused = False; g.tod = tod; app.settings["tod"] = "day" if 7 < tod < 17 else "cycle"
    me = g.me(); me.x, me.y, me.h = x, y, h; g.cam_yaw = h; me.sync(); g.cam_pos = None
    b = g.buddy(); b.x, b.y = x + 2, y - 2; b.sync(); step(25)
def st(tag=""):
    g = G(); me = g.me()
    print("RESULT", tag, "pos %.1f %.1f z %.2f" % (me.x, me.y, me.np.get_z()), "builds", [(i["label"], len(i["cols"])) for i in g.builds.items], flush=True)
def view(name, it, dist, up, ang=35, at=None, fov=55):
    cx, cy = it["center"]; g = G(); me = g.me()
    a = math.atan2(me.y - cy, me.x - cx) + math.radians(ang)
    app.camera.set_pos(cx + math.cos(a) * dist, cy + math.sin(a) * dist, up); app.camera.look_at(cx, cy, at if at is not None else up * 0.5)
    app.camLens.set_fov(fov if dist < 100 else 68); shot(name); app.camLens.set_fov(70)
def mk(text, name, dist, up, at, ang=35, x=530, y=-120, h=0, tod=14.5):
    def f():
        g = G(); g.miyo.clear(); place(x, y, h, tod); g.miyo.start_build(text); step(70); TransformState.garbage_collect()
        it = g.builds.items[-1]; st("built " + text); view(name, it, dist, up, ang, at)
    return f
def walk(sec, f=1):
    g = G(); g.vb["v_up"] = f > 0; g.vb["v_down"] = f < 0; step(int(sec * 30)); g.vb.clear(); st("walked")
WORDS = ["horse"]
_T0 = _t.time()
def hshots():
    g = G(); g.miyo.clear(); place(530, -120, 0, 14.5); g.miyo.start_build("horse"); step(70); TransformState.garbage_collect()
    it = g.builds.items[-1]; st("built horse"); cx, cy = it["center"]
    from PIL import Image
    ims = []
    for nm, ang, d, up, fov in (("_horse_side", 90, 7.5, 2.2, 45), ("_horse_34", 35, 7.5, 2.6, 45), ("_horse_front34", -40, 6.5, 2.4, 45)):
        a = math.atan2(G().me().y - cy, G().me().x - cx) + math.radians(ang)
        app.camera.set_pos(cx + math.cos(a) * d, cy + math.sin(a) * d, up); app.camera.look_at(cx, cy, 1.9); app.camLens.set_fov(fov); shot(nm); app.camLens.set_fov(70)
        ims.append(Image.open(os.path.join(OUT, nm + ".png")).convert("RGB"))
    w, h = ims[0].size; S = Image.new("RGB", (w // 2 * 3, h // 2))
    for i, im in enumerate(ims): S.paste(im.resize((w // 2, h // 2)), (i * w // 2, 0))
    S.save(os.path.join(OUT, "miyo_build_horse.png")); print("SHOT horse sheet", flush=True)
PLAN = [(0.1, lambda: app.show_title()), (0.3, lambda: app.show_menu()), (0.3, lambda: app.start_game(None)), (1.0, lambda: None),
        (0.1, lambda: [G().step(1 / 30.0) for _ in range(200)]), (0.1, lambda: G().select_char("miyo")), (0.1, lambda: step(5)), (0.1, hshots), (0.1, lambda: app.userExit())]
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
