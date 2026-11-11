# v1.0.5.5 QA: seasons + circular speedo + pause-menu EX SCREEN RECORDER 2026 (no system-sound toggle)
import os, traceback, time as _t
from panda3d.core import Filename
from fs_events import SCOL, ICON, BUILTIN
OUT = os.environ.get("FS_QA_OUT", "/workspace/fireout-online/shots_seasons"); os.makedirs(OUT, exist_ok=True)
SEASONS = ["spring", "summer", "autumn", "winter"]

def G(): return app.game
def step(n=1):
    for _ in range(n): G().step(1 / 30.0)
def shot(name, hud=True):
    if not hud: app.aspect2d.hide()
    app.graphicsEngine.render_frame(); app.graphicsEngine.render_frame()
    app.win.save_screenshot(Filename.from_os_specific(os.path.join(OUT, name + ".png"))); print("SHOT", name, flush=True); app.aspect2d.show()

def force(s):
    app.settings["force_season"] = s
    g = G()
    g.events.data = BUILTIN; g.events.source = "built-in"
    g.events.reapply_from_settings()
    for i in range(8): g.step(1 / 30.0)

def run():
    g = G(); app.settings["tod"] = "night"; g.tod = 22.5; g.paused = False
    g.events.data = BUILTIN; g.events.source = "built-in"
    app.settings["force_season"] = ""
    g.events.reapply_from_settings()
    for i in range(10): g.step(1 / 30.0)
    print("RESULT auto_season", g.events.season, "forced", g.events.forced, flush=True)
    print("RESULT recorder", app.screen_rec is not None, flush=True)
    shot("feed_auto", hud=True)
    g.toggle_phone(); g.phone_screen("festival"); step(2); shot("festival_auto", hud=True)
    g.toggle_phone(); step(2)
    for s in SEASONS:
        force(s)
        kinds = [e["kind"] for e in g.events.events()]
        print("RESULT season", s, "kinds", kinds, flush=True)
        assert "race" in kinds and "photo" in kinds and "drive" in kinds, kinds
        e0 = next(e for e in g.events.events() if e["kind"] == "race")
        g.events.feed.push(e0["title"], e0["line"], g.events.reward_txt(e0), ICON[e0["kind"]], SCOL[s])
        for i in range(10): g.step(1 / 30.0)
        shot("feed_%s" % s, hud=True)
        g.toggle_phone(); g.phone_screen("festival"); step(2); shot("festival_%s" % s, hud=True)
        g.toggle_phone(); step(2)
    app.settings["force_season"] = ""
    g.events.reapply_from_settings()
    # circular speedometer
    try:
        if g.pcar is None:
            tx, ty, _ = g.world.tower_top
            rx, ry = g.world.nearest_road_point(tx + 10, ty - 80)[:2]
            g.ensure_in_car(rx, ry, 0)
        g.vb["v_up"] = True
        for i in range(40): g.step(1 / 30.0)
        g.vb["v_up"] = False
        print("RESULT speedo_kmh", int(g.pcar.speed * 3.6), "bucket", g.speedo_bucket, flush=True)
        shot("speedo_drive", hud=True)
    except Exception:
        print("TESTERR speedo", traceback.format_exc(), flush=True)
    # pause menu with EX SCREEN RECORDER 2026 on the same screen
    try:
        app.show_pause()
        for i in range(4):
            app.graphicsEngine.render_frame()
        shot("pause_recorder", hud=True)
        print("RESULT pause_has_recorder", "EX SCREEN RECORDER" in str(getattr(app, "_rec_btn", None) is not None),
              "rec", app.screen_rec is not None, flush=True)
        print("RESULT sys_sound_default", getattr(app.screen_rec, "sys_sound", None), flush=True)
        assert getattr(app.screen_rec, "sys_sound", False) is True
        from fs_recorder import downloads_dir
        print("RESULT downloads_dir", downloads_dir(), flush=True)
        app.hide_pause()
    except Exception:
        print("TESTERR pause", traceback.format_exc(), flush=True)
    print("RESULT done", flush=True)

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
