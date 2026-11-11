import os, time
from panda3d.core import Filename
OUT = os.path.join(app.BASE, "docs"); os.makedirs(OUT, exist_ok=True)
T0 = time.time(); n = [0]
def shot(name):
    app.win.save_screenshot(Filename.from_os_specific(os.path.join(OUT, name + ".png"))); print("SHOT", name, "%.1fs" % (time.time() - T0), "frames", n[0], flush=True)
PLAN = [(8, lambda: app.show_title()), (3, lambda: shot("title")), (1, lambda: app.show_menu()), (6, lambda: shot("menu")),
        (1, lambda: (print("RESULT done", flush=True), app.userExit()))]
st = {"i": 0, "f": 0}
def run(task):
    n[0] += 1; st["f"] += 1
    if st["i"] < len(PLAN) and st["f"] >= PLAN[st["i"]][0]:
        st["f"] = 0; f = PLAN[st["i"]][1]; st["i"] += 1; f()
    return task.cont
app.task_mgr.add(run, "quick", sort=100)
