# two real game instances talking over UDP via the FIREOUT ONLINE code path. ROLE=host|join, CODEFILE shared.
import os, math, traceback, time as _t
ROLE = os.environ["ROLE"]; CF = os.environ.get("CODEFILE", "/tmp/fs_code.txt")
def G(): return app.game
def R(*a): print("RESULT", ROLE, *a, flush=True)
st = {"phase": "boot", "t0": _t.time(), "pt": _t.time()}
def phase(p): st["phase"] = p; st["pt"] = _t.time(); R("phase", p)
def el(): return _t.time() - st["pt"]
def tick():
    g = G(); o = g.online; s = o.sess; p = st["phase"]
    if p == "start":
        g.intro_t = 0.0; me = g.me(); me.x, me.y, me.h = 12, -40, 0; me.sync()
        if ROLE == "host": o.host("tiger"); phase("wait_code")
        else: phase("wait_file")
    elif p == "wait_code":
        if s.code: open(CF, "w").write(s.code); R("code", s.code, s.via); phase("wait_peer")
    elif p == "wait_peer":
        if s.peers:
            pid = list(s.peers)[0]; R("peer joined", s.peers[pid]["name"], s.peers[pid]["cfg"].get("hair")); phase("play")
        elif el() > 60: R("FAIL no peer"); phase("quit")
    elif p == "play":
        me = g.me(); me.x += 0.03; me.sync()
        if el() > 6:
            pid = list(s.peers)[0]; pr = s.peers[pid]
            R("peer state", pr.get("state") and {k: pr["state"][k] for k in ("x", "y")}, "ping", pr.get("ping"), "remotes", list(o.remotes), "chat", o.chat_log[-3:])
            o.start_football(versus=True, minutes=0.5); phase("match")
    elif p == "match":
        m = g.match
        if m is None: R("FAIL no match"); phase("quit"); return
        if el() > 3 and not st.get("m1"):
            st["m1"] = 1; hum = [f for f in m.fps if isinstance(f.human, int)]
            R("match remote human slot", [(f.team, f.name, f.inp) for f in hum])
        if m.done and not st.get("ft"): st["ft"] = 1; R("host fulltime", m.score, m.stats)
        if st.get("ft") and el() > 40:
            m.quit(); phase("kick")
    elif p == "kick":
        if el() > 2:
            pid = list(s.peers)[0] if s.peers else None
            if pid: o.kick(pid); R("kicked", pid)
            phase("end")
    elif p == "wait_file":
        if os.path.exists(CF):
            code = open(CF).read().strip(); R("joining", code)
            o.profile = __import__("fs_avatar").preset(2); o.join(code, "tiger"); phase("wait_join")
    elif p == "wait_join":
        if s is not None and s.state == "joined":
            me = g.me(); R("joined id", s.my_id, "guest", o.guest, "me cfg", getattr(me, "cfg", {}).get("name"), "names", __import__("fs_game").NAMES[g.active])
            s.say("hello host"); phase("joined")
        elif el() > 40: R("FAIL join", s and s.status); phase("quit")
    elif p == "joined":
        me = g.me(); me.y += 0.03; me.sync()
        if g.match is not None and not st.get("mv"):
            st["mv"] = 1; m = g.match; R("got match view", m.mode, "my slot", m.local and (m.local.team, m.local.name), "players", len(m.fps))
        if g.match is not None:
            g.vb["v_up"] = True
            if int(el() * 2) % 6 == 0: g.match.act("shoot")
        if g.match is not None and getattr(g.match, "target", None) is not None and not st.get("snap"):
            st["snap"] = 1; R("snapshot ok clock", g.match.target["c"])
        if g.match is not None and g.match.done and not st.get("ft"): st["ft"] = 1; R("client fulltime", g.match.score)
        if el() > 3 and not st.get("r"):
            st["r"] = 1; R("remotes", list(o.remotes), "host who", o.remotes.get(0) and o.remotes[0].who, "ping", s.ping_ms if s else None)
        if s is None or o.sess is None:
            g.vb.clear(); R("session over guest", o.guest, "active", g.active, "match", g.match); phase("end")
        elif el() > 200: R("FAIL timeout"); phase("quit")
    elif p == "end":
        if el() > 2: phase("quit")
    elif p == "quit":
        app.userExit()
def runner(task):
    try:
        if st["phase"] == "boot":
            if _t.time() - st["t0"] < 9.0 or app.world is None: return task.cont
            app.show_title(); app.show_menu(); app.start_game(None); phase("loading"); return task.cont
        if st["phase"] == "loading":
            if getattr(app, "game", None) is None or el() < 3: return task.cont
            phase("start"); return task.cont
        tick()
    except Exception:
        print("TESTERR", ROLE, traceback.format_exc(), flush=True); phase("quit")
    return task.cont
app.task_mgr.add(runner, "test-runner", sort=100)
