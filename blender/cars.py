"""FIREOUT SHINE - original car designs, modelled procedurally in Blender (bpy).
Run: blender -b -P blender/cars.py   -> assets/models/car_<type>.glb (+ docs/cars_render.png)
Each car is built from a lofted cross-section cage + subdivision surface. All designs are original (no real makes, no logos).
Objects per car: paint (white, tinted in game), glass, trim, lamp_f, lamp_r, wheel_FL/FR/RL/RR (pivot at hub), interior; + car_<type>_lod.glb for traffic (v1.0.5.3)."""
import bpy, bmesh, math, os, sys
from mathutils import Vector
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "models")
os.makedirs(OUT, exist_ok=True)

# L length, W width, wb wheelbase, wr wheel radius, ride: sill height, belt: shoulder height, roof height,
# A/C: cabin start/end as fraction of length from front (0..1), nose/tail heights, extras
TYPES = {
    # v1.0.5.3: ENERASTIC MG EVO SEDAN - low 4-door fastback, vertical-slat grille, C-shaped LED DRLs, splitter, skirts, wing (original design)
    "evo":    dict(L=4.85, W=1.90, wb=2.86, wr=0.37, ride=0.15, belt=0.92, roof=1.43, A=0.30, C=0.92, nose=0.74, tail=0.98, fast=True, rw=0.72, spoiler=True, fender=0.05,
                   slats=True, cdrl=True, splitter=True, chrome=True, rim=0.80, spokes=10, caliper=(0.85, 0.05, 0.05)),
    "gts":    dict(L=4.55, W=2.00, wb=2.70, wr=0.36, ride=0.17, belt=0.78, roof=1.15, A=0.40, C=0.78, nose=0.52, tail=0.86, rw=0.62, spoiler=True, fender=0.06, splitter=True, rim=0.80, spokes=7, caliper=(0.95, 0.75, 0.05)),
    "coupe":  dict(L=4.40, W=1.86, wb=2.60, wr=0.35, ride=0.18, belt=0.82, roof=1.30, A=0.36, C=0.80, nose=0.62, tail=0.90, rw=0.70, spoiler=True, fender=0.04, splitter=True, chrome=True, rim=0.78, spokes=6, caliper=(0.1, 0.1, 0.12)),
    "sedan":  dict(L=4.75, W=1.82, wb=2.80, wr=0.34, ride=0.22, belt=0.92, roof=1.45, A=0.33, C=0.76, nose=0.74, tail=0.95, rw=0.76, slats=True, chrome=True, rim=0.72, spokes=8),
    "taxi":   dict(L=4.60, W=1.75, wb=2.70, wr=0.32, ride=0.26, belt=0.95, roof=1.52, A=0.32, C=0.78, nose=0.78, tail=0.98, rw=0.80, taxi=True, chrome=True, rim=0.62, spokes=6),
    "police": dict(L=4.85, W=1.85, wb=2.85, wr=0.34, ride=0.26, belt=0.93, roof=1.47, A=0.33, C=0.77, nose=0.75, tail=0.96, rw=0.77, lightbar=True, rim=0.66, spokes=6),
    "hatch":  dict(L=3.90, W=1.74, wb=2.45, wr=0.32, ride=0.22, belt=0.92, roof=1.50, A=0.30, C=0.93, nose=0.72, tail=1.05, rw=0.85, rim=0.70, spokes=5),
    "kei":    dict(L=3.40, W=1.48, wb=2.35, wr=0.28, ride=0.24, belt=0.95, roof=1.85, A=0.12, C=0.97, nose=0.85, tail=1.70, rw=0.92, boxy=True, rim=0.62, spokes=4),
    "suv":    dict(L=4.70, W=1.95, wb=2.80, wr=0.41, ride=0.36, belt=1.15, roof=1.80, A=0.30, C=0.94, nose=0.98, tail=1.25, rw=0.88, boxy=True, chrome=True, rim=0.70, spokes=6),
    "ambulance": dict(L=5.40, W=1.95, wb=3.20, wr=0.36, ride=0.32, belt=1.15, roof=2.35, A=0.10, C=0.30, nose=1.10, tail=2.30, rw=0.95, boxy=True, cargo=True, lightbar=True, rim=0.62, spokes=6),
    "van":    dict(L=5.40, W=1.95, wb=3.20, wr=0.36, ride=0.32, belt=1.15, roof=2.35, A=0.10, C=0.30, nose=1.10, tail=2.30, rw=0.95, boxy=True, cargo=True, rim=0.62, spokes=6),
}

def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def mat(name, col, emit=0.0, metal=0.0, rough=0.4, alpha=1.0):
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*col, 1); b.inputs["Metallic"].default_value = metal; b.inputs["Roughness"].default_value = rough
    if emit:
        b.inputs["Emission Color"].default_value = (*col, 1); b.inputs["Emission Strength"].default_value = emit
    return m

def section(p, f, x):
    """half cross-section (list of (y_side, z)) at fraction f (0 front .. 1 rear)."""
    L, W = p["L"], p["W"] / 2
    # plan-view width taper at nose/tail
    taper = 1.0 - 0.10 * max(0, (0.12 - f) / 0.12) ** 1.6 - 0.08 * max(0, (f - 0.90) / 0.10) ** 1.6
    if p.get("boxy"): taper = 1.0 - 0.04 * max(0, (0.06 - f) / 0.06) - 0.03 * max(0, (f - 0.95) / 0.05)
    # v1.0.5.3: rounded nose / tail (no flat end caps) - plan-view and height roll-off over the last few cm
    rn = max(0.0, (0.035 - f) / 0.035) ** 2 + max(0.0, (f - 0.965) / 0.035) ** 2
    taper *= 1.0 - 0.22 * rn
    w = W * taper
    # fender bulges over the wheels
    fw = p.get("fender", 0.02)
    for wf in (0.5 - p["wb"] / L / 2, 0.5 + p["wb"] / L / 2):
        w += fw * math.exp(-((f - wf) / 0.07) ** 2)
    # top profile: nose -> hood -> windscreen -> roof -> rear screen -> deck -> tail
    A, C, nose, tail, roof, belt = p["A"], p["C"], p["nose"], p["tail"], p["roof"], p["belt"]
    if p.get("boxy"):
        if f < A: deck = nose + (belt - nose) * (f / max(A, 1e-3)) ** 0.5
        else: deck = belt
    else:
        if f < A: deck = nose + (belt - nose) * (f / A) ** 0.7
        elif f > C: deck = belt + (tail - belt) * ((f - C) / (1 - C)) ** 1.5
        else: deck = belt
    # v1.0.5.3: fender humps - the deck always clears the wheel arch (no arch cut through the hood)
    for wf in (0.5 - p["wb"] / L / 2, 0.5 + p["wb"] / L / 2):
        need = 2 * p["wr"] + 0.16
        deck += max(0.0, need - deck) * math.exp(-((f - wf) / 0.10) ** 2)
    # greenhouse
    rw = p["rw"]
    if p.get("cargo"):
        gh = roof if f > A * 0.6 else None; deck = deck if f < A else belt
    elif p.get("boxy"):
        gh = roof if A * 0.5 < f < C + 0.03 else None
    else:
        ws = A + (C - A) * (0.24 if p.get("fast") else 0.28); rs = A + (C - A) * (0.46 if p.get("fast") else 0.78)
        if A <= f <= C:
            if f < ws: gh = belt + (roof - belt) * math.sin((f - A) / (ws - A) * math.pi / 2)
            elif f > rs: gh = belt + (roof - belt) * math.cos((f - rs) / (C - rs) * math.pi / 2)
            else: gh = roof
        else: gh = None
    ride = p["ride"]
    deck -= 0.10 * rn; ride += 0.06 * rn
    if gh is not None: gh -= 0.10 * rn
    pts = [(0.0, ride - 0.02), (w * 0.86, ride), (w, ride + 0.18), (w, deck - 0.12), (w * 0.97, deck)]
    if gh is not None and gh > deck + 0.03:
        pts += [(w * rw + (w * 0.97 - w * rw) * 0.15, deck + 0.04), (w * rw, gh - 0.03), (w * rw * 0.6, gh)]
        top = gh
    else:
        # v1.0.5.3: same vertex count as the greenhouse rows (a mismatch twisted the ring and caved in the left-hand side)
        pts += [(w * 0.88, deck + 0.02), (w * 0.70, deck + 0.04), (w * 0.40, deck + 0.05)]
        top = deck + 0.05
    pts += [(0.0, top + (0.005 if gh is None else 0.0))]
    return pts, deck, gh

def build_body(p, name):
    L = p["L"]; N = 34
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    rows = []
    for i in range(N + 1):
        f = i / N
        f = 0.5 - 0.5 * math.cos(f * math.pi)        # denser at ends
        y = L / 2 - f * L                             # car faces +Y in Blender (front at +y)
        pts, deck, gh = section(p, f, 0)
        half = [bm.verts.new((sx, y, z)) for sx, z in pts]
        mirr = [bm.verts.new((-sx, y, z)) for sx, z in reversed(pts[1:-1])]
        rows.append(half + mirr)
    n = len(rows[0])
    for i in range(N):
        a, b = rows[i], rows[i + 1]
        for j in range(n):
            k = (j + 1) % n
            bm.faces.new((a[j], a[k], b[k], b[j]))
    # caps
    bm.faces.new(list(reversed(rows[0]))); bm.faces.new(rows[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(ob)
    sub = ob.modifiers.new("sub", "SUBSURF"); sub.levels = 3; sub.render_levels = 3  # v1.0.5.4 higher body detail
    bpy.context.view_layer.objects.active = ob; ob.select_set(True)
    bpy.ops.object.modifier_apply(modifier="sub")
    bpy.ops.object.shade_smooth()
    return ob

def cut_arches(ob, p):
    """v1.0.5.3: real round wheel arches (boolean) so the tyres sit in wheel wells."""
    R = p["wr"] + 0.065; ax = p["wb"] / 2
    for wy in (ax, -ax):
        bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=R, depth=p["W"] + 0.4, location=(0, wy, p["wr"]), rotation=(0, math.pi / 2, 0))
        cu = bpy.context.object
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, wy, p["wr"]))
        core = bpy.context.object; core.scale = (p["W"] * 0.62, 2 * R + 0.2, 2 * R + 0.2)
        b2 = cu.modifiers.new("b", "BOOLEAN"); b2.operation = "DIFFERENCE"; b2.object = core; b2.solver = "EXACT"
        bpy.context.view_layer.objects.active = cu; bpy.ops.object.modifier_apply(modifier="b"); bpy.data.objects.remove(core, do_unlink=True)
        b = ob.modifiers.new("arch", "BOOLEAN"); b.operation = "DIFFERENCE"; b.object = cu; b.solver = "EXACT"
        bpy.context.view_layer.objects.active = ob; bpy.ops.object.modifier_apply(modifier="arch")
        bpy.data.objects.remove(cu, do_unlink=True)
    bm = bmesh.new(); bm.from_mesh(ob.data); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(ob.data); bm.free()

def split_glass(ob, p):
    """faces above the beltline inside the cabin become glass (separate object)."""
    me = ob.data; bm = bmesh.new(); bm.from_mesh(me)
    L = p["L"]; belt = p["belt"]
    glass = []
    # v1.0.5.3: clean window outlines (smooth bands that follow the section rows) instead of a ragged per-normal pick,
    # with a roof rail, A-pillars and a B-pillar so the tinted (see-through) glass has proper frames
    for fc in bm.faces:
        c = fc.calc_center_median(); f = (L / 2 - c.y) / L
        _, deck, gh = section(p, min(1.0, max(0.0, f)), 0)
        if gh is None or abs(fc.normal.z) > 0.97: continue
        side = abs(fc.normal.x) > 0.45
        screen = (not side) and abs(fc.normal.y) > 0.25 and belt + 0.06 < c.z < p["roof"] - 0.05 and abs(c.x) < p["W"] / 2 * p["rw"] * 0.92
        if screen:
            glass.append(fc); continue
        if not side or not (belt + 0.07 < c.z < gh - 0.07): continue
        if side and not p.get("cargo"):
            if f < p["A"] + (p["C"] - p["A"]) * (0.12 if p.get("fast") else 0.22) or f > p["A"] + (p["C"] - p["A"]) * (0.80 if p.get("fast") else 0.86): continue      # A / C pillars
        if p.get("cargo") and f > p["A"] + 0.02 and abs(fc.normal.y) < 0.5: continue   # no side glass on the cargo box
        if p.get("cargo") and f > 0.9: continue
        glass.append(fc)
    gm = bpy.data.meshes.new(ob.name + "_glass"); gb = bmesh.new()
    vm = {}
    for fc in glass:
        vs = []
        for v in fc.verts:
            if v.index not in vm: vm[v.index] = gb.verts.new(v.co.copy())
            vs.append(vm[v.index])
        gb.faces.new(vs)
    bmesh.ops.delete(bm, geom=glass, context="FACES")
    bm.to_mesh(me); bm.free()
    for v in gb.verts: v.co += Vector((0, 0, 0))
    gb.to_mesh(gm); gb.free()
    go = bpy.data.objects.new(ob.name + "_glass", gm); bpy.context.collection.objects.link(go)
    # solidify-ish: offset glass slightly inward is not needed; mark smooth
    for pl in gm.polygons: pl.use_smooth = True
    return go

def box(name, c, s, m, rot=(0, 0, 0), bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=c, rotation=rot)
    o = bpy.context.object; o.name = name; o.scale = s
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        bv = o.modifiers.new("bv", "BEVEL"); bv.width = bevel; bv.segments = 2
        bpy.ops.object.modifier_apply(modifier="bv")
    o.data.materials.append(m); return o

def cyl(r, d, loc, verts=32, m=None, bevel=0.0, axis_x=True, caps=True):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=d, location=loc, rotation=(0, math.pi / 2, 0) if axis_x else (0, 0, 0),
                                        end_fill_type="NGON" if caps else "NOTHING")
    o = bpy.context.object; bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    if bevel:
        bv = o.modifiers.new("bv", "BEVEL"); bv.width = bevel; bv.segments = 3; bpy.ops.object.modifier_apply(modifier="bv")
    if m: o.data.materials.append(m)
    return o

def wheel(name, c, r, w, mt, mr, side, p, M_disc, M_dark):
    """v1.0.5.3: low-profile tyre with sidewall bulge, deep-dish multi-spoke alloy, lug nuts, centre cap and a drilled brake disc (rotates with the wheel)."""
    rim = p.get("rim", 0.66); ns = p.get("spokes", 5); rr = r * rim
    bpy.ops.mesh.primitive_torus_add(major_radius=r - (r - rr) * 0.5, minor_radius=(r - rr) * 0.55, major_segments=48, minor_segments=16, location=(0, 0, 0), rotation=(0, math.pi / 2, 0))
    t = bpy.context.object; t.scale = (1.0, 1.0, 1.0); bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    # squash the torus along the axle to tyre width
    for v in t.data.vertices: v.co.x *= (w * 0.5) / ((r - rr) * 0.55)
    t.data.materials.append(mt); bpy.ops.object.shade_smooth()
    parts = [t]
    o = cyl(rr * 0.99, w * 0.60, (-side * w * 0.08, 0, 0), 48, M_dark, caps=False); parts.append(o)        # barrel (open, dark inside)
    o = cyl(rr * 0.9, w * 0.02, (-side * w * 0.36, 0, 0), 40, M_dark); parts.append(o)                       # inner back plate (dark)
    bpy.ops.mesh.primitive_torus_add(major_radius=rr * 0.97, minor_radius=rr * 0.045, major_segments=48, minor_segments=8, location=(side * w * 0.40, 0, 0), rotation=(0, math.pi / 2, 0))
    o = bpy.context.object; bpy.ops.object.transform_apply(location=False, rotation=True, scale=True); o.data.materials.append(mr); parts.append(o)   # polished outer lip (ring)
    o = cyl(r * 0.64 * rim / 0.66 * 0.9, w * 0.06, (-side * w * 0.05, 0, 0), 40, M_disc); parts.append(o)    # brake disc
    o = cyl(rr * 0.17, w * 0.16, (side * w * 0.42, 0, 0), 24, mr, bevel=0.006); parts.append(o)  # hub
    o = cyl(rr * 0.09, w * 0.05, (side * w * 0.51, 0, 0), 20, M_dark); parts.append(o)            # centre cap (original plain cap, no logo)
    for k in range(ns):                                                                           # twin or single spokes
        a = k * 2 * math.pi / ns
        for dd in ((-0.09, 0.09) if ns >= 8 else (0.0,)):
            aa = a + dd * (0.6 if ns >= 8 else 0)
            bpy.ops.mesh.primitive_cube_add(size=1, location=(side * w * 0.40, math.cos(aa) * rr * 0.55, math.sin(aa) * rr * 0.55), rotation=(aa - math.pi / 2, 0, 0))
            sp = bpy.context.object; sp.scale = (w * 0.10, rr * (0.10 if ns >= 8 else 0.16), rr * 0.80)
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
            bv = sp.modifiers.new("bv", "BEVEL"); bv.width = 0.006; bv.segments = 2; bpy.ops.object.modifier_apply(modifier="bv")
            sp.data.materials.append(mr); parts.append(sp)
    for k in range(5):                                                                            # lug nuts
        a = k * 2 * math.pi / 5 + 0.3
        parts.append(cyl(rr * 0.035, w * 0.08, (side * w * 0.48, math.cos(a) * rr * 0.11, math.sin(a) * rr * 0.11), 8, M_disc))
    bpy.ops.object.select_all(action="DESELECT")
    for o in parts: o.select_set(True)
    bpy.context.view_layer.objects.active = t; bpy.ops.object.join()
    t.name = name; t.location = c
    return t

_BODY = {}
def surf_y(x, z, front=True, inset=0.0):
    """v1.0.5.3: y of the body surface at (x, z) (ray cast), so lamps / grille / badges sit ON the rounded nose and tail."""
    ob = _BODY["o"]; L = _BODY["L"]
    o = Vector((x, (L / 2 + 1.0) if front else (-L / 2 - 1.0), z)); d = Vector((0, -1 if front else 1, 0))
    hit, loc, nrm, idx = ob.ray_cast(o, d)
    if not hit: return (L / 2 - 0.05) if front else (-L / 2 + 0.05)
    return loc.y - inset if front else loc.y + inset

def surf_x(y, z, side=1):
    """x of the body side surface at (y, z) (ray cast from outside)."""
    ob = _BODY["o"]
    hit, loc, nrm, idx = ob.ray_cast(Vector((side * 3.0, y, z)), Vector((-side, 0, 0)))
    return loc.x if hit else side * 0.9

def ribbon(name, top, bot, m, out=0.006, rows=6):
    """thin surface-hugging patch between two point rows (each point: (x, z)); y comes from the body surface (front)."""
    me = bpy.data.meshes.new(name); bm = bmesh.new(); grid = []
    for (xt, zt), (xb, zb) in zip(top, bot):
        col = []
        for r in range(rows + 1):
            u = r / rows; x = xt + (xb - xt) * u; z = zt + (zb - zt) * u
            col.append(bm.verts.new((x, surf_y(x, z, True, -out), z)))
        grid.append(col)
    for c0, c1 in zip(grid, grid[1:]):
        for r in range(rows):
            bm.faces.new((c0[r + 1], c1[r + 1], c1[r], c0[r]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        if f.normal.y < 0: f.normal_flip()
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o); o.data.materials.append(m)
    for pl in me.polygons: pl.use_smooth = True
    return o

def badge_E(x, y, z, s, m, facing=1):
    """original 'E' emblem: chrome E inside a rounded chrome ring (no real logos)."""
    out = []
    bpy.ops.mesh.primitive_torus_add(major_radius=s * 0.62, minor_radius=s * 0.06, major_segments=32, minor_segments=8, location=(x, y, z), rotation=(math.pi / 2, 0, 0))
    o = bpy.context.object; bpy.ops.object.transform_apply(location=False, rotation=True, scale=True); o.data.materials.append(m); out.append(o)
    out.append(box("eb", (x - s * 0.18, y, z), (s * 0.09, s * 0.06, s * 0.70), m))
    for dz, ln in ((0.31, 0.5), (0.0, 0.40), (-0.31, 0.5)):
        out.append(box("eb", (x - s * 0.18 + s * ln / 2, y, z + dz * s), (s * ln, s * 0.06, s * 0.09), m))
    return out

def join(objs, name):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]; bpy.ops.object.join(); objs[0].name = name
    return objs[0]

def make(tname, p):
    clear()
    M_paint = mat("paint", (0.9, 0.9, 0.9), metal=0.45, rough=0.12)
    M_glass = mat("glass", (0.02, 0.025, 0.04), rough=0.03, alpha=0.62)
    M_glass.blend_method = "BLEND"; M_glass.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 0.62
    M_disc = mat("disc", (0.38, 0.38, 0.40), metal=1.0, rough=0.35); M_dark = mat("rimdark", (0.06, 0.06, 0.07), metal=0.6, rough=0.4)
    M_seat = mat("leather", (0.05, 0.045, 0.045), rough=0.55); M_dash = mat("dash", (0.03, 0.03, 0.035), rough=0.6)
    M_cal = mat("caliper", p.get("caliper", (0.18, 0.18, 0.2)), metal=0.2, rough=0.3)
    M_trim = mat("trim", (0.03, 0.03, 0.035), rough=0.5)
    M_chrome = mat("chrome", (0.75, 0.75, 0.78), metal=1.0, rough=0.15)
    M_tire = mat("tire", (0.02, 0.02, 0.02), rough=0.9)
    M_hl = mat("lamp_f", (1.0, 0.97, 0.9), emit=6)
    M_led = mat("lamp_f_led", (0.50, 0.78, 1.0), emit=9)            # cool white / icy-blue LED
    M_hlhouse = mat("hlhouse", (0.015, 0.016, 0.02), metal=0.3, rough=0.08)
    M_tl = mat("lamp_r", (1.0, 0.05, 0.08), emit=6)
    M_red = mat("bar_red", (1.0, 0.05, 0.05), emit=8); M_blue = mat("bar_blue", (0.1, 0.3, 1.0), emit=8)
    M_white = mat("whitepanel", (0.95, 0.95, 0.95), rough=0.3); M_taxi = mat("taxilamp", (1.0, 0.85, 0.2), emit=4)
    L, W = p["L"], p["W"]
    body = build_body(p, "paint"); body.data.materials.append(M_paint)
    cut_arches(body, p)
    bpy.context.view_layer.update(); _BODY["o"] = body; _BODY["L"] = p["L"]
    glass = split_glass(body, p); glass.name = "glass"; glass.data.materials.append(M_glass)
    trim = []; inner = []
    yf, yr = L / 2, -L / 2
    nz, tz = p["nose"], p["tail"]
    boxy = p.get("boxy")
    # v1.0.5.3 lights: slim sharp LED headlight strips + C-shaped DRL; thin full-width LED tail bar + corner blocks
    hlw = W * 0.26 if not boxy else W * 0.20
    lf = []
    for sx in (-1, 1):
        hx = sx * W * 0.31
        if not p.get("cdrl"):
            lf.append(box("hl", (hx, surf_y(hx, nz - 0.13, True, 0.03), nz - 0.13), (hlw, 0.10, 0.035 if not boxy else 0.12), M_hl, bevel=0.008))
            continue
        # v1.0.5.3 ENERASTIC MG EVO SEDAN front lights (as the reference):
        # slim swept-back headlight units angled up towards the bonnet: glossy black housing, projector lenses, icy-blue LED strip on the top edge
        n = 14; x_in, x_out = sx * W * 0.16, sx * W * 0.455
        zt = lambda t: nz - 0.115 + 0.085 * t ** 1.3          # top edge rises towards the outer corner (swept up to the bonnet)
        zb = lambda t: nz - 0.205 + 0.135 * t ** 1.1           # bottom edge: unit tapers to a sharp point
        X = lambda t: x_in + (x_out - x_in) * t
        T = [k / n for k in range(n + 1)]
        trim.append(ribbon("hlhouse", [(X(t), zt(t)) for t in T], [(X(t), zb(t)) for t in T], M_hlhouse, 0.006))
        lf.append(ribbon("hlled", [(X(t), zt(t) + 0.004) for t in T], [(X(t), zt(t) - 0.014) for t in T], M_led, 0.009))
        for t in (0.24, 0.50):                                                        # projector lenses
            xm = X(t); zm = (zt(t) + zb(t)) / 2 - 0.004
            ym = surf_y(xm, zm, True, 0.0)
            bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.027, depth=0.02, location=(xm, ym + 0.006, zm), rotation=(math.pi / 2, 0, 0))
            o = bpy.context.object; bpy.ops.object.transform_apply(location=False, rotation=True, scale=True); o.data.materials.append(M_chrome); trim.append(o)
            bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.018, depth=0.022, location=(xm, ym + 0.008, zm), rotation=(math.pi / 2, 0, 0))
            o = bpy.context.object; bpy.ops.object.transform_apply(location=False, rotation=True, scale=True); o.data.materials.append(M_led); lf.append(o)
        # separate vertical C-shaped (bracket) LED DRL low in each bumper corner, beside the grille (opening towards the grille)
        cxo = sx * W * 0.395; cxi = sx * W * 0.315; ztp, zbt = p["ride"] + 0.30, p["ride"] + 0.11; e = 0.024
        L_ = lambda a, b, n=8: [a + (b - a) * k / n for k in range(n + 1)]
        trim.append(ribbon("drlpocket", [(x, ztp + 0.03) for x in L_(cxi - sx * 0.02, cxo + sx * 0.03)], [(x, zbt - 0.03) for x in L_(cxi - sx * 0.02, cxo + sx * 0.03)], M_hlhouse, 0.005))
        lf.append(ribbon("drl", [(x, ztp) for x in L_(cxo - sx * e, cxo, 3)], [(x, zbt) for x in L_(cxo - sx * e, cxo, 3)], M_led, 0.010))
        lf.append(ribbon("drl", [(x, ztp) for x in L_(cxi, cxo)], [(x, ztp - e) for x in L_(cxi, cxo)], M_led, 0.010))
        lf.append(ribbon("drl", [(x, zbt + e) for x in L_(cxi, cxo)], [(x, zbt) for x in L_(cxi, cxo)], M_led, 0.010))
    tlz = max(p["ride"] + 0.35, tz - 0.16)
    lr = [box("tl", (0, surf_y(0, tlz, False, 0.02), tlz), (W * 0.86, 0.06, 0.028), M_tl, bevel=0.006)]
    for sx in (-1, 1): lr.append(box("tlc", (sx * W * 0.36, surf_y(sx * W * 0.36, tlz - 0.03, False, 0.03), tlz - 0.03), (W * 0.14, 0.07, 0.07), M_tl, bevel=0.01))
    # grille: dark recess + vertical chrome slats (or horizontal bars), with the original E badge
    gy = surf_y(0, p["ride"] + (0.22 if not p.get("boxy") else 0.30), True, 0.06) - 0.0; gz = p["ride"] + (0.22 if not boxy else 0.30); gw = W * (0.50 if p.get("slats") else 0.58); gh = 0.20 if not boxy else 0.22
    trim.append(box("grille", (0, gy - 0.02, gz), (gw, 0.14, gh), M_trim, bevel=0.02))
    if p.get("slats"):
        xs_ = [-gw / 2 + gw * k / 12 for k in range(13)]
        trim.append(ribbon("grilleback", [(x, gz + gh / 2) for x in xs_], [(x, gz - gh / 2) for x in xs_], M_hlhouse, 0.004))
        n = 15
        for k in range(n):
            xx = -gw / 2 + gw * (k + 0.5) / n
            trim.append(box("slat", (xx, gy + 0.045, gz), (0.012, 0.06, gh * 0.86), M_chrome))
    else:
        for k in range(3):
            trim.append(box("bar", (0, gy + 0.045, gz - gh * 0.3 + k * gh * 0.3), (gw * 0.94, 0.05, 0.016), M_chrome if p.get("chrome") else M_trim))
    trim += badge_E(0, gy + 0.08, gz + 0.01, 0.075, M_chrome)
    trim += badge_E(0, surf_y(0, tlz + 0.11, False, -0.005), tlz + 0.11, 0.05, M_chrome)
    # lower intake + splitter + diffuser with fins + thicker side skirts
    trim.append(box("intake", (0, surf_y(0, p["ride"] + 0.07, True, 0.05), p["ride"] + 0.07), (W * 0.70, 0.12, 0.08), M_trim, bevel=0.015))
    if p.get("splitter"):
        trim.append(box("splitter", (0, surf_y(0, p["ride"] + 0.04, True, 0.04), p["ride"] - 0.01), (W * 0.86, 0.14, 0.022), M_trim, bevel=0.008))
    trim.append(box("diff", (0, surf_y(0, p["ride"] + 0.08, False, 0.05), p["ride"] + 0.08), (W * 0.80, 0.12, 0.12), M_trim, bevel=0.01))
    for k in range(5):
        trim.append(box("fin", (-W * 0.30 + k * W * 0.15, surf_y(0, p["ride"] + 0.08, False, 0.02), p["ride"] + 0.04), (0.012, 0.18, 0.08), M_trim))
    for s_ in (-1, 1):
        trim.append(box("skirt", (s_ * (W / 2 * 0.90), 0, p["ride"] + 0.03), (0.07, p["wb"] - 2 * p["wr"] - 0.2, 0.07), M_trim, bevel=0.012))
        trim.append(box("mirror", (s_ * (W / 2 * p["rw"] + 0.22), L / 2 - L * p["A"] - 0.05, p["belt"] + 0.10), (0.18, 0.09, 0.09), M_paint, bevel=0.03))
        trim.append(box("mirrorarm", (s_ * (W / 2 * p["rw"] + 0.10), L / 2 - L * p["A"] - 0.05, p["belt"] + 0.06), (0.12, 0.04, 0.03), M_trim))
        if p.get("chrome") and not p.get("cargo"):     # chrome window-line trim along the belt
            y0c, y1c = L / 2 - L * p["A"] - 0.1, L / 2 - L * p["C"] + 0.15
            trim.append(box("chrome", (s_ * (W / 2 * 0.955), (y0c + y1c) / 2, p["belt"] + 0.035), (0.02, abs(y0c - y1c), 0.018), M_chrome))
        span_ = p["C"] - p["A"]
        doors = (0.30, 0.64) if (not p.get("cargo") and span_ > 0.40 and p["L"] > 4.3 and not p.get("spoiler") or p.get("fast")) else (0.42,)
        for fd in doors:                                # door handles (4-door cars get front + rear door handles)
            dy = L / 2 - L * (p["A"] + span_ * fd)
            hx_ = surf_x(dy, p["belt"] - 0.07, s_)
            trim.append(box("handle", (hx_ + s_ * 0.008, dy, p["belt"] - 0.07), (0.02, 0.16, 0.025), M_chrome if p.get("chrome") else M_trim, bevel=0.006))
        if p.get("fast") or (p.get("chrome") and not p.get("cargo") and not p.get("boxy")):     # door shut lines (front/rear door split + rear door edge)
            for fd in ((0.05, 0.52, 0.93) if len(doors) > 1 else (0.05, 0.93)):
                dy = L / 2 - L * (p["A"] + span_ * fd)
                for k in range(7):
                    z0 = p["ride"] + 0.12 + k * (p["belt"] - p["ride"] - 0.1) / 7.0; z1 = z0 + (p["belt"] - p["ride"] - 0.1) / 7.0
                    xm = surf_x(dy, (z0 + z1) / 2, s_)
                    trim.append(box("seam", (xm + s_ * 0.002, dy, (z0 + z1) / 2), (0.006, 0.007, z1 - z0 + 0.004), M_dark))
    # wheel-well liners (dark, hide the body interior through the arch cut-outs)
    for sy_ in (1, -1):
        for sx_ in (-1, 1):
            bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=p["wr"] + 0.062, depth=0.30, location=(sx_ * (W / 2 - 0.17), sy_ * p["wb"] / 2, p["wr"]), rotation=(0, math.pi / 2, 0))
            lo = bpy.context.object; bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
            bm_ = bmesh.new(); bm_.from_mesh(lo.data)
            bmesh.ops.delete(bm_, geom=[v for v in bm_.verts if v.co.z < -0.02 - p["wr"] * 0.35], context="VERTS")
            bm_.to_mesh(lo.data); bm_.free(); lo.data.materials.append(M_dark); trim.append(lo)
    # brake calipers (static, behind the spokes)
    tw0 = 0.25 if p["wr"] > 0.3 else 0.20
    for sx_, sy_ in ((-1, 1), (1, 1), (-1, -1), (1, -1)):
        trim.append(box("caliper", (sx_ * (W / 2 - tw0 / 2 + 0.02) - sx_ * tw0 * 0.05, sy_ * p["wb"] / 2 + 0.10, p["wr"] + p["wr"] * 0.32),
                        (0.05, p["wr"] * 0.30, p["wr"] * 0.22), M_cal, bevel=0.012))
    # interior (visible through the tinted glass): seats, dashboard, wheel, console
    inner = []
    if not p.get("cargo"):
        ycab0 = L / 2 - L * p["A"]; zf = p["ride"] + 0.25
        inner.append(box("dash", (0, ycab0 - L * (p["C"] - p["A"]) * 0.16, p["belt"] - 0.05), (W * 0.78, 0.40, 0.18), M_dash, bevel=0.04))
        for sx_ in (-1, 1):
            span = L * (p["C"] - p["A"])
            for row, yy in ((0, ycab0 - span * 0.42), (1, ycab0 - span * 0.70)):
                if span < 2.0 and row == 1: continue
                xs = sx_ * W * 0.21 if row == 0 else sx_ * W * 0.2
                inner.append(box("seat", (xs, yy, zf + 0.08), (W * 0.22, 0.50, 0.12), M_seat, bevel=0.04))
                inner.append(box("back", (xs, yy - 0.26, zf + 0.42), (W * 0.22, 0.12, 0.60), M_seat, bevel=0.05))
                if row == 0: inner.append(box("head", (xs, yy - 0.28, zf + 0.82), (W * 0.13, 0.10, 0.16), M_seat, bevel=0.04))
        bpy.ops.mesh.primitive_torus_add(major_radius=0.18, minor_radius=0.022, location=(W * 0.21, ycab0 - L * (p["C"] - p["A"]) * 0.26, p["belt"] + 0.02), rotation=(math.radians(70), 0, 0))
        sw = bpy.context.object; bpy.ops.object.transform_apply(location=False, rotation=True, scale=True); sw.data.materials.append(M_dash); inner.append(sw)
        inner.append(box("console", (0, ycab0 - L * (p["C"] - p["A"]) * 0.42, zf + 0.12), (0.22, 0.9, 0.22), M_dash, bevel=0.03))
    if p.get("spoiler"):
        trim.append(box("wing", (0, yr + 0.28, tz + 0.15), (W * 0.80, 0.26, 0.025), M_trim, bevel=0.01))
        for s in (-1, 1): trim.append(box("strut", (s * W * 0.28, yr + 0.30, tz + 0.07), (0.03, 0.10, 0.16), M_trim))
    if p.get("lightbar"):
        rz = p["roof"]
        trim.append(box("barbase", (0, -0.15, rz + 0.04), (1.2, 0.26, 0.06), M_trim))
        lf.append(box("bar_r", (-0.32, -0.15, rz + 0.11), (0.52, 0.22, 0.10), M_red, bevel=0.02))
        lr.append(box("bar_b", (0.32, -0.15, rz + 0.11), (0.52, 0.22, 0.10), M_blue, bevel=0.02))
    if p.get("taxi"):
        trim.append(box("taxisign", (0, -0.25, p["roof"] + 0.10), (0.42, 0.18, 0.16), M_taxi, bevel=0.03))
    # bake objects
    objs = {"paint": body, "glass": glass, "trim": join(trim, "trim") if trim else None}
    if inner: objs["interior"] = join(inner, "interior")
    if p.get("lightbar"):
        br = [o for o in lf if o.name.startswith("bar_r")][0]; bb = [o for o in lr if o.name.startswith("bar_b")][0]
        lf.remove(br); lr.remove(bb); br.name = "bar_red"; bb.name = "bar_blue"
    objs["lamp_f"] = join(lf, "lamp_f")
    objs["lamp_r"] = join(lr, "lamp_r")
    tw = 0.25 if p["wr"] > 0.3 else 0.20
    ax = p["wb"] / 2
    for nm, (sx, sy) in {"wheel_FL": (-1, 1), "wheel_FR": (1, 1), "wheel_RL": (-1, -1), "wheel_RR": (1, -1)}.items():
        wheel(nm, (sx * (W / 2 - tw / 2 + 0.02), sy * ax, p["wr"]), p["wr"], tw, M_tire, M_chrome, sx, p, M_disc, M_dark)
    for o in bpy.data.objects:
        if o.type == "MESH":
            o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "car_%s.glb" % tname), export_format="GLB", use_selection=False,
                              export_apply=True, export_yup=True)
    # v1.0.5.3 traffic LOD: no interior, decimated body/wheels, same silhouette + lights (switch is far and fog-covered)
    for nm in ("interior",):
        o = bpy.data.objects.get(nm)
        if o: bpy.data.objects.remove(o, do_unlink=True)
    for o in list(bpy.data.objects):
        if o.type == "MESH" and (o.name in ("paint", "glass") or o.name.startswith("wheel_")):
            d = o.modifiers.new("dec", "DECIMATE"); d.ratio = 0.35 if o.name.startswith("wheel_") else 0.50  # v1.0.5.4 denser traffic LOD
            bpy.context.view_layer.objects.active = o; bpy.ops.object.modifier_apply(modifier="dec")
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "car_%s_lod.glb" % tname), export_format="GLB", use_selection=False,
                              export_apply=True, export_yup=True)
    print("CAR", tname, flush=True)

ONLY = [a for a in sys.argv if a in TYPES]
for k, p in TYPES.items():
    if not ONLY or k in ONLY: make(k, p)

# --- contact sheet render of all designs (Eevee)
if "--render" in sys.argv:
    clear()
    for i, k in enumerate(TYPES):
        bpy.ops.import_scene.gltf(filepath=os.path.join(OUT, "car_%s.glb" % k))
        for o in bpy.context.selected_objects:
            if o.parent is None: o.location.x += (i % 3) * 6.5 - 6.5; o.location.y += (i // 3) * 7 - 7
    sc = bpy.context.scene; sc.render.engine = "BLENDER_EEVEE_NEXT"; sc.render.resolution_x = 1600; sc.render.resolution_y = 1000
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
    cam.location = (14, -22, 14); cam.rotation_euler = (math.radians(58), 0, math.radians(32))
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sc.collection.objects.link(sun); sun.rotation_euler = (0.7, 0.2, 0.5); sun.data.energy = 3
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.04, 0.1, 1)
    sc.render.filepath = os.path.join(ROOT, "docs", "cars_render.png"); bpy.ops.render.render(write_still=True)
