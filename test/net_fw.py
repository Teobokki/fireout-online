import os, time, sys
os.environ["FS_NET_ADDR"] = "127.0.0.1"
sys.path.insert(0, ".")
import fs_net as N
def pump(ss, secs, until=None):
    t0 = time.time()
    while time.time() - t0 < secs:
        for s in ss: s.poll(time.time(), None)
        if until and until(): return round(time.time() - t0, 2)
        time.sleep(0.03)
    return None
# A: both sides behind a stateful firewall (no rule, prompt dismissed)
h = N.Session("host", "HOSTY", upnp=False, stun=False, sim_firewall=True)
pump([h], 2, lambda: h.code)
g = N.Session("join", "GUESTY", upnp=False, stun=False, sim_firewall=True); g.join(h.code)
r = pump([h, g], 6, lambda: g.state == "joined")
print("A1 guest-only call, firewalled host: joined", g.state == "joined", "host dropped", h.dropped, "status", g.status)
rc = g.reply_code(); print("A2 reply code", rc); h.let_in(rc)
r = pump([h, g], 6, lambda: g.state == "joined" and h.peers)
print("A3 after host calls guest: joined in", r, "s; peers", [p["name"] for p in h.peers.values()])
r2 = pump([h, g], 16)
print("A4 idle 16 s (pings + keep-alive): guest", g.state, "host peers", len(h.peers), "guest ping", g.ping_ms, "drops host/guest", h.dropped, g.dropped)
g.say("hi"); pump([h, g], 1); print("A5 chat reached host", any("hi" in c for c in h.chat))
g.close(); h.close()
# B: no firewall: direct join, no reply code needed
h = N.Session("host", "H2", upnp=False, stun=False, port=47120); pump([h], 2, lambda: h.code)
g = N.Session("join", "G2", upnp=False, stun=False); g.join(h.code)
print("B open network: joined in", pump([h, g], 5, lambda: g.state == "joined"), "s")
g.close(); h.close()
# C: firewalled host, LAN browser discovers it by asking (outbound broadcast query, host answers)
h = N.Session("host", "H3", upnp=False, stun=False, sim_firewall=True); pump([h], 2, lambda: h.code)
b = N.LanBrowser(); t = pump([h], 6, lambda: b.sessions())
print("C LAN query -> host reply: found", [x["name"] for x in b.sessions()], "in", t, "s")
b.close(); h.close()
