"""FIREOUT SHINE - game-ready heroine (and NPC base body) from the concept sculpt.
Decimates the SDF sculpt, bakes the v2 skin shader (tone, blush, lips, pores bump) into 2048 colour + normal maps,
bakes the eye shader, converts the bob hair strands into hair-card ribbons, splits legs for walk animation, exports GLB.
Run: blender -b -P blender/game_char.py"""
import bpy, bmesh, sys, os, json, math, numpy as np
CON = "/workspace/fireout-shine-concept"
sys.path.insert(0, CON + "/src")
from bl_util import mesh_from_arrays
from materials import skin_material, eye_material
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = os.path.join(ROOT, "assets", "tex"); OUT = os.path.join(ROOT, "assets", "models")
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; sc.render.engine = "CYCLES"; sc.cycles.samples = 4; sc.cycles.device = "CPU"
WHO = os.environ.get("WHO", "ana"); CD = CON + {"daniel": "/cache_daniel/", "miyo": "/cache_miyo/"}.get(WHO, "/cache/"); SUF = {"daniel": "_daniel", "miyo": "_miyo"}.get(WHO, "")
OUTFIT = os.environ.get("OUTFIT", "default")
BARE = OUTFIT in ("bikini", "swim")
if OUTFIT != "default": SUF = "_" + OUTFIT
D2 = np.load(CD + "char_%s.npz" % OUTFIT) if OUTFIT in ("bikini", "police", "swim") else None
D = np.load(CD + "char.npz"); HH = np.load(CD + "hair.npz"); rig = json.load(open(CD + "rig.json"))
# v1.0.3: arms hang free at the sides and are split into their own pivoting nodes (armR/armL) so the game can swing them
import character as C
if WHO == "daniel": import daniel   # applies Daniel's anatomy patches (torso/arm/neck) to the character module
def arm_d(c, side): return C.arm(np.asarray(c, np.float32), side)
def trunk_d(c): return C.body_noarms(np.asarray(c, np.float32))

def obj(name, V, F, attrs=None):
    return mesh_from_arrays(name, V, F, smooth=True, attrs=attrs)
def activate(o):
    bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); bpy.context.view_layer.objects.active = o
def decimate(o, tris):
    n = len(o.data.polygons)
    if n > tris:
        m = o.modifiers.new("d", "DECIMATE"); m.ratio = tris / n; activate(o); bpy.ops.object.modifier_apply(modifier="d")
def del_faces(o, pred):
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if pred(f.calc_center_median())], context="FACES")
    bm.to_mesh(o.data); bm.free()
def pmat(name, col, rough=0.6, metal=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*col, 1); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    return m

hk = [k[7:] for k in D.files if k.startswith("head_m_")]
head = obj("skin", D["head_V"], D["head_F"], {k: D["head_m_" + k] for k in hk})
_BD = D2 if (D2 is not None and "body_V" in D2.files) else D     # bikini: owner-requested larger bust body variant
body = obj("body", _BD["body_V"], _BD["body_F"], {k: np.zeros(len(_BD["body_V"]), np.float32) for k in hk})
def del_faces_vec(o, pred_arr):
    bm = bmesh.new(); bm.from_mesh(o.data); fs = list(bm.faces)
    cen = np.array([f.calc_center_median()[:] for f in fs], np.float32); kill = pred_arr(cen)
    bmesh.ops.delete(bm, geom=[f for f, k in zip(fs, kill) if k], context="FACES"); bm.to_mesh(o.data); bm.free()
# legs/hips are covered by the trousers (or the separate bare-leg mesh); the hanging arms/hands are kept
del_faces_vec(body, lambda c: (c[:, 2] < 0.99) & (np.minimum(arm_d(c, "R"), arm_d(c, "L")) > trunk_d(c)))
decimate(head, 14000); decimate(body, 7000)
activate(head); body.select_set(True)
if BARE:   # bare legs + feet
    legsk = obj("legsk", D2["legsk_V"], D2["legsk_F"], {k: np.zeros(len(D2["legsk_V"]), np.float32) for k in hk})
    del_faces(legsk, lambda c: c.z >= 0.99); decimate(legsk, 9000); activate(head); body.select_set(True); legsk.select_set(True)
bpy.ops.object.join()
skin = head; skin.name = "skin"
# --- UV + bake the v2 skin
activate(skin); bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.004); bpy.ops.object.mode_set(mode="OBJECT")
M = skin_material(); skin.data.materials.append(M)
def bake(o, m, img_name, size, kind):
    img = bpy.data.images.new(img_name, size, size, alpha=False)
    if kind == "NORMAL": img.colorspace_settings.name = "Non-Color"
    n = m.node_tree.nodes.new("ShaderNodeTexImage"); n.image = img; m.node_tree.nodes.active = n
    activate(o)
    if kind == "DIFFUSE":
        bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"}, margin=8)
    else:
        bpy.ops.object.bake(type="NORMAL", normal_space="TANGENT", margin=8)
    img.filepath_raw = os.path.join(TEX, img_name + ".png"); img.file_format = "PNG"; img.save()
    m.node_tree.nodes.remove(n); return img
img_c = bake(skin, M, "skin_c" + SUF, 2048, "DIFFUSE")
if WHO == "miyo":   # warmer, sun-tanned site-worker skin tone
    _p = np.empty(len(img_c.pixels), np.float32); img_c.pixels.foreach_get(_p); _p = _p.reshape(-1, 4)
    _p[:, :3] *= np.array([0.88, 0.76, 0.66], np.float32); img_c.pixels.foreach_set(_p.ravel()); img_c.save()
img_n = bake(skin, M, "skin_n" + SUF, 2048, "NORMAL")
print("BAKED skin", flush=True)
def tex_mat(name, img_c, img_n=None, rough=0.5):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = img_c; nt.links.new(t.outputs[0], b.inputs["Base Color"])
    if img_n:
        tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = img_n; nm = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(tn.outputs[0], nm.inputs["Color"]); nt.links.new(nm.outputs[0], b.inputs["Normal"])
    b.inputs["Roughness"].default_value = rough
    return m
skin.data.materials.clear(); skin.data.materials.append(tex_mat("skin", img_c, img_n, 0.5))
# --- eyes
HO = np.array(rig["HEAD_O"]); HR = np.array(rig["HEAD_R"])
ME = eye_material(); eyes = []
for sx in (-1, 1):
    c = HO + HR @ np.array([sx * rig["EYE_X"], rig["EYE_Y"], 0.0])
    bpy.ops.mesh.primitive_uv_sphere_add(radius=rig["EYE_R"], segments=20, ring_count=12, location=(0, 0, 0))
    e = bpy.context.object; e.name = "eye"; bpy.ops.object.shade_smooth()
    # point the eye forward (-Y) toward slightly right of camera, iris pattern is built around -Y in object space
    e.data.materials.append(ME); e.location = tuple(c); eyes.append(e)
img_e = bake(eyes[0], ME, "eye_c" + SUF, 256, "DIFFUSE")
for e in eyes:
    e.data.materials.clear(); e.data.materials.append(tex_mat("eye", img_e, None, 0.1))
activate(eyes[0]); eyes[1].select_set(True); bpy.ops.object.join(); eyes[0].name = "eyes"
# --- clothes
def part(name, key, tris, col, rough=0.7, metal=0.0):
    o = obj(name, D[key + "_V"], D[key + "_F"]); decimate(o, tris); o.data.materials.append(pmat(name, col, rough, metal)); return o
if WHO == "daniel" and OUTFIT == "swim":
    D0 = D; D = D2; trousers = part("trousers", "shorts", 4000, (0.08, 0.42, 0.58), 0.7); D = D0
elif WHO == "miyo":
    tank = part("tank", "tank", 4500, (0.10, 0.12, 0.16), 0.85)                     # charcoal work tee
    vest = part("vest", "vest", 4000, (1.0, 0.36, 0.02), 0.55)                     # hi-vis orange vest
    bands = part("bands", "bands", 1600, (0.86, 0.88, 0.84), 0.22, 0.35)           # reflective strips
    hat = part("hardhat", "hardhat", 3000, (1.0, 0.78, 0.04), 0.32)               # yellow hard hat
    trousers = part("trousers", "trousers", 7000, (0.30, 0.28, 0.21), 0.9)        # khaki cargo work trousers
    belt = part("belt", "belt", 700, (0.20, 0.12, 0.05), 0.4); buckle = part("buckle", "buckle", 200, (0.8, 0.8, 0.85), 0.2, 1.0)
elif WHO == "daniel":
    tank = part("tank", "tank", 4500, (1, 1, 1), 0.85)
    activate(tank); bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.01, scale_to_bounds=False); bpy.ops.object.mode_set(mode="OBJECT")
    for lp in tank.data.uv_layers.active.data: lp.uv = (lp.uv[0] * 3.0, lp.uv[1] * 3.0)
    fl = bpy.data.images.load(os.path.join(TEX, "floral.png")); tank.data.materials.clear(); tank.data.materials.append(tex_mat("shirt", fl, None, 0.85))
    trousers = part("trousers", "trousers", 7000, (0.09, 0.14, 0.30), 0.9)
    belt = part("belt", "belt", 700, (0.18, 0.10, 0.05), 0.4); buckle = part("buckle", "buckle", 200, (0.8, 0.8, 0.85), 0.2, 1.0)
elif OUTFIT in ("bikini", "police"):
    D0 = D; D = D2
    if OUTFIT == "bikini":
        tank = part("tank", "btop", 2500, (0.88, 0.22, 0.20), 0.6); trousers = part("trousers", "bbot", 2500, (0.88, 0.22, 0.20), 0.6)
    else:
        tank = part("tank", "shirt", 4500, (0.07, 0.10, 0.22), 0.8); capo = part("cap", "cap", 2500, (0.05, 0.07, 0.16), 0.6)
        badge = part("badge", "badge", 400, (0.95, 0.75, 0.25), 0.25, 1.0)
    D = D0
    if OUTFIT == "police":
        trousers = part("trousers", "trousers", 7000, (0.07, 0.10, 0.22), 0.85)
        belt = part("belt", "belt", 700, (0.02, 0.02, 0.02), 0.4); buckle = part("buckle", "buckle", 200, (0.8, 0.8, 0.85), 0.2, 1.0)
    else:
        choker = part("choker", "choker", 500, (0.01, 0.01, 0.012), 0.8)
else:
    tcol = (0.92, 0.92, 0.90) if OUTFIT == "crop" else (0.20, 0.21, 0.24)
    tank = part("tank", "tank", 3500, tcol); straps = part("straps", "straps", 800, tcol)
    if OUTFIT == "crop": del_faces(tank, lambda c: c.z < 1.125)      # fitted crop top: bare midriff (same body)
    trousers = part("trousers", "trousers", 7000, (0.62, 0.07, 0.06), 0.85)
    belt = part("belt", "belt", 700, (0.02, 0.02, 0.02), 0.4); buckle = part("buckle", "buckle", 200, (0.8, 0.8, 0.85), 0.2, 1.0)
    choker = part("choker", "choker", 500, (0.01, 0.01, 0.012), 0.8)
if WHO == "miyo":
    shoes = [part("shoe", k, 1600, (0.42, 0.26, 0.11) if k.startswith("boot") else (0.06, 0.05, 0.04), 0.6) for k in ("bootR", "soleR", "bootL", "soleL")]
elif OUTFIT == "police":
    D0 = D; D = D2; shoes = [part("shoe", k, 1600, (0.03, 0.03, 0.035), 0.35) for k in ("bootR", "bootL")]; D = D0
elif BARE:
    D0 = D; D = D2; shoes = [part("ff" + k, "ff" + k, 900, (0.95, 0.45, 0.35), 0.6) for k in ("R", "L")]; D = D0
else: shoes = [part("shoe", k, 900, (0.92, 0.91, 0.88) if k.startswith("shoeU") else (0.85, 0.83, 0.78), 0.5) for k in ("shoeUR", "shoeSR", "shoeUL", "shoeSL")]
# split legs (trousers below the crotch + shoes) for procedural walk cycles
def split_off(o, pred, name):
    bm = bmesh.new(); bm.from_mesh(o.data)
    sel = [f for f in bm.faces if pred(f.calc_center_median())]
    nm = bpy.data.meshes.new(name); nb = bmesh.new(); vm = {}
    for f in sel:
        vs = []
        for v in f.verts:
            if v.index not in vm: vm[v.index] = nb.verts.new(v.co.copy())
            vs.append(vm[v.index])
        try: nb.faces.new(vs)
        except ValueError: pass
    bmesh.ops.delete(bm, geom=sel, context="FACES"); bm.to_mesh(o.data); bm.free()
    nb.to_mesh(nm); nb.free(); no = bpy.data.objects.new(name, nm); bpy.context.collection.objects.link(no)
    for p in nm.polygons: p.use_smooth = True
    no.data.materials.append(o.data.materials[0]); return no
CR = 0.86
def split_arm(o, side, name, margin_copy=0.008, margin_del=0.004):
    """copy the faces nearer this arm than the trunk into a new object (small overlap band so no gap opens when it swings)"""
    def mask(off):
        cen = np.array([f.center[:] for f in o.data.polygons], np.float32)
        return (arm_d(cen, side) < trunk_d(cen) + off) & (cen[:, 2] < rig["SEAM_Z"]) & (np.sign(cen[:, 0]) == (-1 if side == "R" else 1))
    activate(o); bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="DESELECT"); bpy.ops.object.mode_set(mode="OBJECT")
    m = mask(margin_copy)
    for f, k in zip(o.data.polygons, m): f.select = bool(k)
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.duplicate(); bpy.ops.mesh.separate(type="SELECTED"); bpy.ops.object.mode_set(mode="OBJECT")
    no = [x for x in bpy.context.selected_objects if x is not o][0]; no.name = name
    m = mask(-margin_del)
    activate(o); bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="DESELECT"); bpy.ops.object.mode_set(mode="OBJECT")
    for f, k in zip(o.data.polygons, m): f.select = bool(k)
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.delete(type="FACE"); bpy.ops.object.mode_set(mode="OBJECT")
    return no
arms = {sd: split_arm(skin, sd, "arm" + sd) for sd in ("R", "L")}
sleeves = {}
if (WHO in ("daniel", "miyo") and OUTFIT == "default") or OUTFIT == "police":     # short sleeves swing with the arm
    sleeves = {sd: split_arm(tank, sd, "sleeve" + sd, 0.004, 0.004) for sd in ("R", "L")}
print("ARMS", {k: len(v.data.polygons) for k, v in arms.items()}, {k: len(v.data.polygons) for k, v in sleeves.items()}, flush=True)
def sep(o, pred, name):   # UV-preserving split (bare skin legs keep the baked skin texture)
    activate(o); bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="DESELECT"); bpy.ops.object.mode_set(mode="OBJECT")
    for f in o.data.polygons: f.select = pred(f.center)
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.separate(type="SELECTED"); bpy.ops.object.mode_set(mode="OBJECT")
    no = [x for x in bpy.context.selected_objects if x is not o][0]; no.name = name; return no
if BARE:
    legR = sep(skin, lambda c: c.z < CR and c.x < 0, "legR"); legL = sep(skin, lambda c: c.z < CR and c.x >= 0, "legL")
    _ff_pairs = list(zip(shoes, (legR, legL)))
else:
    legR = split_off(trousers, lambda c: c.z < CR and c.x < 0, "legR"); legL = split_off(trousers, lambda c: c.z < CR and c.x >= 0, "legL")
    for s, leg in zip(shoes, (legR, legR, legL, legL) if len(shoes) == 4 else (legR, legL)):
        activate(leg); s.select_set(True); bpy.ops.object.join()
# --- bob hair cards from the strand simulation
P = HH["scalp_P"]; N = HH["scalp_N"]; off = np.concatenate([[0], np.cumsum(N)[:-1]])
rng = np.random.default_rng(4)
TAPER = 0.55
def ribbons(name, idxs, npts, width, col_root, col_tip):
    verts, faces, cols = [], [], []
    cen = HO + HR @ np.array([0, 0.045, 0.0])
    for s in idxs:
        pts = P[off[s]:off[s] + N[s]]
        t = np.linspace(0, len(pts) - 1, npts); pts = np.array([pts[int(min(i, len(pts) - 2))] * (1 - (i % 1)) + pts[int(min(i, len(pts) - 2)) + 1] * (i % 1) for i in t])
        tang = np.gradient(pts, axis=0); tang /= np.linalg.norm(tang, axis=1, keepdims=True) + 1e-9
        outw = pts - cen; outw /= np.linalg.norm(outw, axis=1, keepdims=True)
        side = np.cross(tang, outw); side /= np.linalg.norm(side, axis=1, keepdims=True) + 1e-9
        b = len(verts)
        for k in range(npts):
            wk = width * (1 - TAPER * (k / (npts - 1)) ** 2)
            verts += [pts[k] - side[k] * wk / 2, pts[k] + side[k] * wk / 2]
            c = [col_root[j] + (col_tip[j] - col_root[j]) * k / (npts - 1) for j in range(3)]
            cols += [c, c]
        for k in range(npts - 1):
            a = b + 2 * k; faces.append((a, a + 2, a + 3, a + 1))
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in verts], [], faces); me.update()
    ca = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
    for i, c in enumerate(cols): ca.data[i].color = (*c, 1)
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    for p in me.polygons: p.use_smooth = True
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b_ = nt.nodes["Principled BSDF"]
    vc = nt.nodes.new("ShaderNodeVertexColor"); vc.layer_name = "Col"; nt.links.new(vc.outputs[0], b_.inputs["Base Color"])
    b_.inputs["Roughness"].default_value = 0.35; m.use_backface_culling = False
    o.data.materials.append(m); return o
ns = len(N)
TAPER = 0.22   # wide, barely tapered overlapping cards: no spiky silhouette, no sub-pixel shimmer
if WHO == "daniel":
    hair = ribbons("hair", rng.choice(ns, 2200, replace=False), int(N[0]), 0.015, (0.03, 0.02, 0.015), (0.06, 0.04, 0.03))
elif WHO == "miyo":
    hair = ribbons("hair", rng.choice(ns, 1500, replace=False), 11, 0.024, (0.05, 0.022, 0.012), (0.20, 0.08, 0.035))
else:
    hair = ribbons("hair", rng.choice(ns, 1500, replace=False), 11, 0.024, (0.04, 0.02, 0.022), (0.11, 0.04, 0.055))
TAPER = 0.55
# opaque hair shell offset ~3.5 mm off the scalp under the cards, so gaps never show skin and nothing z-fights the scalp
import mathutils
_kd = mathutils.kdtree.KDTree(len(P)); [_kd.insert(tuple(v), i) for i, v in enumerate(P)]; _kd.balance()
_root = P[off]
_kr = mathutils.kdtree.KDTree(len(_root)); [_kr.insert(tuple(v), i) for i, v in enumerate(_root)]; _kr.balance()
_HV = D["head_V"]; _HF = D["head_F"]
_hm = bpy.data.meshes.new("hshell_src"); _hm.from_pydata([tuple(v) for v in _HV], [], [tuple(f) for f in _HF]); _hm.update()
_vn = np.array([v.normal[:] for v in _hm.vertices]); bpy.data.meshes.remove(_hm)
_cent = _HV[_HF].mean(1)
_keep = np.array([_kr.find(tuple(c))[2] < 0.010 for c in _cent])
_SF = _HF[_keep]; _used = np.unique(_SF); _remap = -np.ones(len(_HV), int); _remap[_used] = np.arange(len(_used))
_SV = _HV[_used] + _vn[_used] * 0.0035
_sm = bpy.data.meshes.new("hshell"); _sm.from_pydata([tuple(v) for v in _SV], [], [tuple(_remap[f]) for f in _SF]); _sm.update()
_sc = (0.03, 0.02, 0.015) if WHO == "daniel" else ((0.05, 0.022, 0.012) if WHO == "miyo" else (0.04, 0.02, 0.022))
_ca = _sm.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
for i in range(len(_SV)): _ca.data[i].color = (*_sc, 1)
for p_ in _sm.polygons: p_.use_smooth = True
_so = bpy.data.objects.new("hshell", _sm); bpy.context.collection.objects.link(_so); _so.data.materials.append(hair.data.materials[0])
decimate(_so, 6000); print("HAIRSHELL", len(_SV), len(_SF))
BP = HH["brow_P"]; BN = HH["brow_N"]
P, N = BP, BN; off = np.concatenate([[0], np.cumsum(N)[:-1]])
brows = ribbons("brows", rng.choice(len(BN), 260, replace=False), 4, 0.0016, (0.05, 0.03, 0.03), (0.08, 0.05, 0.04))
P = HH["lash_P"]; N = HH["lash_N"]; off = np.concatenate([[0], np.cumsum(N)[:-1]])
lashes = ribbons("lashes", range(len(N)), 4, 0.0009, (0.01, 0.01, 0.01), (0.02, 0.02, 0.02))
activate(hair); brows.select_set(True); lashes.select_set(True); _so.select_set(True); bpy.ops.object.join(); hair.name = "hair"
# legs pivot at hips (origin) so the game can swing them
for leg, side in ((legR, "R"), (legL, "L")):
    hp = rig["S"]["hip" + side]
    sc.cursor.location = (hp[0], hp[1], CR + 0.03); activate(leg); bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
# forearms (elbow pivot) split off each arm, again with a small overlap band
def split_fore(o, sd, name):
    sh = np.array(rig["S"]["sho" + sd]); el = np.array(rig["S"]["elb" + sd]); ax = el - sh; L2 = float(ax @ ax)
    def mask(t0):
        cen = np.array([f.center[:] for f in o.data.polygons]); return ((cen - sh) @ ax) / L2 > t0
    activate(o); bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="DESELECT"); bpy.ops.object.mode_set(mode="OBJECT")
    for f, k in zip(o.data.polygons, mask(0.94)): f.select = bool(k)
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.duplicate(); bpy.ops.mesh.separate(type="SELECTED"); bpy.ops.object.mode_set(mode="OBJECT")
    no = [x for x in bpy.context.selected_objects if x is not o][0]; no.name = name
    activate(o); bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="DESELECT"); bpy.ops.object.mode_set(mode="OBJECT")
    for f, k in zip(o.data.polygons, mask(1.04)): f.select = bool(k)
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.delete(type="FACE"); bpy.ops.object.mode_set(mode="OBJECT")
    return no
fores = {sd: split_fore(arms[sd], sd, "fore" + sd) for sd in ("R", "L")}
# v1.0.3: real hands (palm + 4 fingers + thumb) replace the sculpt's mitten; relaxed + gripping variants, skin tone sampled
# from the baked skin around the wrist so the joint is seamless
HD = np.load(CD + "hands.npz")
def _wrist_u(o, sd):
    wr = np.array(rig["S"]["wri" + sd]); hd = np.array(rig["S"]["hnd" + sd]); ax = (hd - wr) / np.linalg.norm(hd - wr)
    cen = np.array([f.center[:] for f in o.data.polygons]); return (cen - wr) @ ax
_px = np.empty(img_c.size[0] * img_c.size[1] * 4, np.float32); img_c.pixels.foreach_get(_px); _px = _px.reshape(img_c.size[1], img_c.size[0], 4)
hand_objs = {}
for sd in ("R", "L"):
    fo = fores[sd]; u = _wrist_u(fo, sd)
    # sample skin colour on the forearm just above the wrist
    uvl = fo.data.uv_layers.active.data; cols = []
    for f, uu in zip(fo.data.polygons, u):
        if -0.06 < uu < -0.01:
            for li in f.loop_indices:
                x, y = uvl[li].uv; cols.append(_px[min(img_c.size[1] - 1, int(y * img_c.size[1])), min(img_c.size[0] - 1, int(x * img_c.size[0])), :3])
    tone = tuple(0.92 * float(c) for c in np.median(np.array(cols), 0)) if cols else (0.74, 0.57, 0.5)
    print("HAND TONE", sd, tone, len(cols), flush=True)
    activate(fo); bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="DESELECT"); bpy.ops.object.mode_set(mode="OBJECT")
    for f, uu in zip(fo.data.polygons, u): f.select = bool(uu > 0.004)          # cut the mitten off just past the wrist
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.delete(type="FACE"); bpy.ops.object.mode_set(mode="OBJECT")
    hm = pmat("hand" + sd, tone, 0.55)
    for nm, key in (("fingers" + sd, "hand" + sd), ("fist" + sd, "grip" + sd)):
        ho = obj(nm, HD[key + "_V"], HD[key + "_F"]); decimate(ho, 3200); ho.data.materials.append(hm); hand_objs[nm] = (ho, sd)
# arms pivot at the shoulder joint, forearms at the elbow; sleeves + a hand anchor (weapon grip) ride along
for sd, arm in arms.items():
    sh = rig["S"]["sho" + sd]; el = rig["S"]["elb" + sd]
    sc.cursor.location = (sh[0], sh[1], sh[2] - 0.015); activate(arm); bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
    sc.cursor.location = tuple(el); activate(fores[sd]); bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
bpy.context.view_layer.update()
for sd, arm in arms.items():
    fo = fores[sd]; fo.parent = arm; fo.matrix_parent_inverse = arm.matrix_world.inverted()
    for nm, (ho, hs) in hand_objs.items():
        if hs == sd: ho.parent = fo; ho.matrix_parent_inverse = fo.matrix_world.inverted()
    if sd in sleeves:
        sleeves[sd].parent = arm; sleeves[sd].matrix_parent_inverse = arm.matrix_world.inverted()
    hn = rig["S"]["hnd" + sd]; wr = rig["S"]["wri" + sd]
    e = bpy.data.objects.new("hand" + sd, None); bpy.context.collection.objects.link(e)
    e.location = (0.5 * (hn[0] + wr[0]), 0.5 * (hn[1] + wr[1]) - 0.01, 0.5 * (hn[2] + wr[2]) - 0.01)
    bpy.context.view_layer.update(); e.parent = fo; e.matrix_parent_inverse = fo.matrix_world.inverted()
if BARE:
    bpy.context.view_layer.update()
    for s_, leg in _ff_pairs:
        s_.parent = leg; s_.matrix_parent_inverse = leg.matrix_world.inverted()
bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, {"daniel": "daniel", "miyo": "miyoyazu"}.get(WHO, "heroine") + ("" if OUTFIT == "default" else "_" + OUTFIT) + ".glb"), export_format="GLB", export_apply=True, export_tangents=True,
                          export_image_format="JPEG", export_jpeg_quality=90)
print("EXPORTED", {o.name: len(o.data.polygons) for o in bpy.data.objects if o.type == "MESH"}, flush=True)
