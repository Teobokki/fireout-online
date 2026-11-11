# Phone CAMERA app smoke: selfie (ANA + DANIEL), rear, flip, in-car, saved PNGs. FS_TESTSCRIPT=test/camera.py
import os, math, traceback, shutil, glob
from panda3d.core import Filename
OUT = os.environ.get("FS_POSE_OUT", os.path.join(app.BASE, "docs"))
def G(): return app.game
def step(n=1):
    for _ in range(n): G().step(1 / 30.0)
def shot(name):
    app.graphicsEngine.render_frame(); app.graphicsEngine.render_frame()
    app.win.save_screenshot(Filename.from_os_specific(os.path.join(OUT, name + ".png"))); print("SHOT", name, flush=True)
def place(x=520, y=64, h=80):
    g = G(); g.paused = False; g.tod = 16.8; me = g.me(); me.x, me.y, me.h = x, y, h; g.cam_yaw = h; me.sync(); g.cam_pos = None; step(20)
def snap(copy_as=None):
    g = G(); g.cam_shutter(); step(2); p = g.camapp.get("last") if g.camapp else None
    print("RESULT saved", p, os.path.exists(p) if p else False, "toast", g.toast_t.getText() if hasattr(g.toast_t, "getText") else "", flush=True)
    if p and copy_as: shutil.copy(p, os.path.join(OUT, copy_as + ".png")); print("SHOT", copy_as, flush=True)
def side(name, ang=-70, dist=2.4):
    g = G(); me = g.me(); h = math.radians(me.h + ang); fx, fy = -math.sin(h), math.cos(h)
    app.camera.set_pos(me.x + fx * dist, me.y + fy * dist, 1.55); app.camera.look_at(me.x, me.y, 1.25); app.camLens.set_fov(50)
    for n in (app.aspect2d,): n.hide()
    shot(name)
    for n in (app.aspect2d,): n.show()
def click_shutter():
    g = G(); n0 = len(glob.glob(os.path.join(g.pictures_dir(), "*.png")))
    b = g.camapp["shutter"]; b.commandFunc(None); step(2)
    n1 = len(glob.glob(os.path.join(g.pictures_dir(), "*.png"))); p = g.camapp.get("last")
    print("RESULT click shutter: pngs %d -> %d  last=%s exists=%s flash=%s toast=%r" % (n0, n1, p, os.path.exists(p or ""), g.camapp.get("flash_np") is not None, g.toast_t.getText()), flush=True)
    return p
FACES = {}
def expr_shot(who, eid):
    g = G(); g.cam_set_expr(eid); step(3); p = click_shutter(); FACES[(who, eid)] = p
def selm_open():
    g = G(); g.camapp["selm_btn"].commandFunc(None); step(2); print("RESULT picker open", g.camapp.get("picker_np") is not None, flush=True)
def sheet(who):
    from PIL import Image, ImageDraw, ImageFont
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34)
    ims = [Image.open(FACES[(who, e)]).convert("RGB") for e in ("smile", "neutral", "frown")]
    w, h = ims[0].size; cw = int(w * 0.42); x0 = (w - cw) // 2
    W_ = Image.new("RGB", (cw * 3, h)); d = ImageDraw.Draw(W_)
    for i, (im, t) in enumerate(zip(ims, ("SMILE", "NEUTRAL", "GOOFY FROWN"))):
        W_.paste(im.crop((x0, 0, x0 + cw, h)), (i * cw, 0)); d.rectangle((i * cw + 10, 10, i * cw + 20 + d.textlength(t, font=f), 56), fill=(0, 0, 0))
        d.text((i * cw + 15, 14), t, font=f, fill=(255, 210, 60))
    W_.save(os.path.join(OUT, "selmotes_%s.png" % who)); print("SHOT selmotes_" + who, flush=True)
def st(): g = G(); print("RESULT camapp", g.camapp and g.camapp["mode"], "blocked", g.blocked(), "pcar", g.pcar is not None, flush=True)
def into_car():
    g = G(); me = g.me(); c = min(g.cars, key=lambda c: math.hypot(c.x - me.x, c.y - me.y))
    me.x, me.y = c.x + 2, c.y; me.sync(); g.enter_car(c); step(10); print("RESULT in car", g.pcar is not None, flush=True)
import time as _t
_T0 = _t.time()
PLAN = [
    (0.1, lambda: app.show_title()), (0.3, lambda: app.show_menu()), (0.3, lambda: app.start_game(None)), (1.0, lambda: None),
    (0.1, lambda: [G().step(1 / 30.0) for _ in range(300)]),
    (0.1, place), (0.1, lambda: G().toggle_phone()), (0.1, lambda: step(3)), (0.1, lambda: shot("phone_home_camera")),
    (0.1, lambda: G().open_camera()), (0.1, lambda: step(20)), (0.1, st), (0.1, lambda: shot("phone_camera_viewfinder")),
    (0.1, click_shutter), (0.1, lambda: snap("selfie_ana")), (0.1, lambda: side("selfie_pose_ana")),
    (0.1, selm_open), (0.1, lambda: shot("selmotes_menu")),
    (0.1, lambda: expr_shot("ana", "smile")), (0.1, lambda: expr_shot("ana", "neutral")), (0.1, lambda: G().key_num(2)), (0.1, lambda: step(3)), (0.1, lambda: FACES.__setitem__(("ana", "frown"), click_shutter())),
    (0.1, lambda: sheet("ana")), (0.1, lambda: shot("selmotes_frown_ui")), (0.1, lambda: G().cam_set_expr("neutral")), (0.1, lambda: G().cam_selmotes()), (0.1, lambda: step(3)), (0.1, lambda: step(4)), (0.1, lambda: shot("phone_camera_flash")), (0.1, lambda: step(30)),
    (0.1, lambda: G().key_r()), (0.1, lambda: setattr(G().me(), "h", -95)), (0.1, lambda: step(15)), (0.1, st), (0.1, lambda: shot("phone_camera_rear")), (0.1, lambda: snap("photo_rear")),
    (0.1, lambda: G().key_esc()), (0.1, lambda: step(5)), (0.1, st),
    (0.1, lambda: G().switch_char()), (0.1, lambda: step(30)), (0.1, lambda: place(524, 60, 80)),
    (0.1, lambda: G().toggle_phone()), (0.1, lambda: shot("phone_home_daniel")), (0.1, lambda: G().phone_ok() if False else G().open_camera()), (0.1, lambda: step(20)),
    (0.1, lambda: shot("phone_camera_viewfinder_daniel")), (0.1, lambda: snap("selfie_daniel")), (0.1, lambda: side("selfie_pose_daniel")),
    (0.1, selm_open), (0.1, lambda: expr_shot("daniel", "smile")), (0.1, lambda: expr_shot("daniel", "neutral")), (0.1, lambda: expr_shot("daniel", "frown")), (0.1, lambda: sheet("daniel")),
    (0.1, lambda: (G().key_esc(), print("RESULT expr after close", G().me().expression, G().me().face_np, flush=True))), (0.1, lambda: G().open_camera()), (0.1, lambda: step(5)), (0.1, lambda: G().key_esc()), (0.1, st),
    (0.1, lambda: G().switch_char()), (0.1, lambda: step(10)),
    (0.1, into_car), (0.1, lambda: G().toggle_phone()), (0.1, lambda: G().open_camera()), (0.1, lambda: step(10)), (0.1, st),
    (0.1, lambda: G().key_r()), (0.1, st), (0.1, lambda: shot("phone_camera_car")), (0.1, lambda: snap()), (0.1, lambda: G().key_esc()), (0.1, st),
    (0.1, lambda: (G().exit_car(force=True), step(10))),
    (0.1, lambda: G().enter_home()), (0.1, lambda: step(20)), (0.1, lambda: G().toggle_phone()), (0.1, lambda: G().open_camera()), (0.1, lambda: step(20)), (0.1, st),
    (0.1, lambda: shot("phone_camera_house")), (0.1, lambda: G().key_esc()), (0.1, st), (0.1, lambda: print("RESULT home roam", G().home_roam(), flush=True)),
    (0.1, lambda: app.userExit()),
]
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
