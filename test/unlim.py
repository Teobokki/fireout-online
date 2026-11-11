import traceback, time as _t
def chk():
    try:
        import fs_sfc as F
        g = app.game; g.start_match(home_club=0, away_club=1, autoplay=True); m = g.match
        print("UNL secs", m.secs, "unlimited", m.unlimited(), flush=True)
        t0 = _t.time()
        for i in range(int(260 / 0.05)): g.step(0.05)
        print("UNL after", round(m.clock, 1), "clock", m.clock_text(), "done", m.done, "state", m.state, "score", m.score, "wall", round(_t.time() - t0, 1), flush=True)
        app.show_pause(); print("UNL pause open", app.pause_ui is not None, flush=True)
        # press END MATCH the way the menu does
        app.hide_pause(); m.end_match()
        for i in range(10): g.step(0.05)
        print("UNL ended done", m.done, "state", m.state, "result", m.result_ui is not None, "banner", m.banner_txt, flush=True)
        m.quit(); me = g.me()
        print("UNL quit match", g.match, "me", round(me.x, 1), round(me.y, 1), "gate", F.GATE, flush=True)
        for i in range(30): g.step(0.05)
        print("UNL steady ok", flush=True)
        # timed still works
        g.start_match(minutes_real=0.5, autoplay=True); m = g.match
        for i in range(int(45 / 0.05)): g.step(0.05)
        print("UNL timed secs", m.secs, m.clock_text(), "done", m.done, "banner", m.banner_txt, flush=True); m.quit()
    except Exception: print("TESTERR", traceback.format_exc(), flush=True)
_T0 = _t.time()
PLAN = [(0.1, lambda: app.show_title()), (0.3, lambda: app.show_menu()), (0.3, lambda: app.start_game(None)), (1.0, lambda: None), (0.5, chk), (0.1, lambda: app.userExit())]
state = {"i": 0, "t": 0.0}
def runner(task):
    if state["i"] >= len(PLAN): return task.done
    if app.world is None or (state["i"] > 2 and getattr(app, "game", None) is None): return task.cont
    if state["i"] == 0 and _t.time() - _T0 < 9.0: return task.cont
    state["t"] += 0.05
    if state["t"] >= PLAN[state["i"]][0]: state["t"] = 0.0; f = PLAN[state["i"]][1]; state["i"] += 1; f()
    return task.cont
app.task_mgr.add(runner, "test-runner", sort=100)
