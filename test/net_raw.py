"""two processes, real UDP sockets, loopback address in the code (FS_NET_ADDR=127.0.0.1)"""
import os, sys, time, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["FS_NET_ADDR"] = "127.0.0.1"
import fs_net as N
role = sys.argv[1] if len(sys.argv) > 1 else "main"
if role == "host":
    s = N.Session("host", "HOSTY", {"skin": 1}, password=sys.argv[2], upnp=False, stun=False)
    while s.code is None: s.poll(); time.sleep(0.02)
    print("CODE", s.code, flush=True)
    t0 = time.time(); kicked = False
    while time.time() - t0 < 14:
        s.poll(my_state={"x": 1.0, "y": 2.0}); time.sleep(0.03)
        if s.peers and time.time() - t0 > 6 and not kicked:
            pid = list(s.peers)[0]; print("HOST peers", [(k, p["name"], p["ping"], p["state"]) for k, p in s.peers.items()], flush=True); s.kick(pid); kicked = True
    print("HOST chat", s.chat, flush=True); s.close()
elif role == "join":
    s = N.Session("join", "JOINY", {"skin": 3}, password=sys.argv[3]); s.join(sys.argv[2])
    t0 = time.time(); said = False
    while time.time() - t0 < 12 and s.state not in ("ended", "error"):
        s.poll(my_state={"x": 5.0, "y": 6.0}); time.sleep(0.03)
        if s.state == "joined" and not said and time.time() - (s.joined_at or 0) > 1: s.say("hello from joiner"); said = True
    print("JOIN state", s.state, s.status, "id", s.my_id, "ping", s.ping_ms, "remote", s.remote_states, "chat", s.chat, flush=True); s.close()
else:
    for pw, jpw in (("", ""), ("tiger", "tiger"), ("tiger", "wrong")):
        h = subprocess.Popen([sys.executable, __file__, "host", pw], stdout=subprocess.PIPE, text=True)
        code = h.stdout.readline().split()[1]; print("code", code)
        j = subprocess.run([sys.executable, __file__, "join", code, jpw], capture_output=True, text=True, timeout=40)
        print(j.stdout.strip(), j.stderr[-500:]); print(h.communicate(timeout=30)[0].strip())
