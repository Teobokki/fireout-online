"""Main-menu stage: ELIJER (in-game model) posed beside the car in the live night city."""
from fs_vehicle import Car
from fs_people import Person


class _Stub:
    def __init__(self, app):
        self.app = app; self.world = app.world; self.time = 0.0
        self.outfits = {"elijer": "default"}
    def on_impact(self, *a): pass
    def on_car_water(self, *a): pass


class Stage:
    def __init__(self, app):
        g = self.g = _Stub(app)
        save = app.load_save() or {}
        kind = save.get("car", "evo") if save.get("car") in ("evo", "gts", "coupe", "sedan", "hatch", "kei", "suv", "van") and save.get("evo_v1053") else "evo"
        cfg = (save.get("cars") or {}).get(kind, {})
        self.car = Car(g, kind, -1.2, -40.0, 28.0, tuple(cfg.get("paint", (0.06, 0.07, 0.08) if kind == "evo" else (0.08, 0.08, 0.10))), cfg.get("plate", "ELIJER"), True, "player")
        self.car.sync(0.0)
        self.elijer = Person(g, "elijer", 2.2, -42.0, 200.0)
        self.elijer.sync()
        app.task_mgr.add(self._t, "stage-anim")

    def _t(self, task):
        import math
        self.g.time = task.time
        self.elijer.model.set_r(math.sin(task.time * 1.2) * 0.8)
        return task.cont

    def destroy(self):
        self.g.app.task_mgr.remove("stage-anim")
        self.car.destroy(); self.elijer.destroy()
