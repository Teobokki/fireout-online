"""v1.0.5.4 graphics modes: 'RTX' (ULTRA) and 'EX HD'.
Both modes are full HD cinematic: same models, HD city textures, paint, lights, filmic grade, film grain,
16x anisotropic filtering, 256 px dynamic cube-map every frame, long LOD and light-pool distances.
EX HD is no longer a cut-down mode. NO bloom, NO glow halos.
©2026 EX ROMANIA/EX INC."""
import os, re
from panda3d.core import (Shader, Texture, FrameBufferProperties, BitMask32, NodePath, loadPrcFileData, SamplerState, PTA_float)

MODES = [("RTX", "RTX (ULTRA)"), ("EXHD", "EX HD")]
CUBE_MASK = BitMask32.bit(6)


def detect(renderer):
    """NVIDIA RTX, AMD Radeon RX 6000+ / 7000 / 9000 or Intel Arc -> RTX; everything else -> EX HD."""
    r = (renderer or "").upper()
    if "RTX" in r: return "RTX"
    if re.search(r"\bARC\b", r) and "INTEL" in r: return "RTX"
    m = re.search(r"RX\s*(\d{4})", r)
    if m and int(m.group(1)) >= 6000 and ("AMD" in r or "RADEON" in r): return "RTX"
    return "EXHD"


def pre_window(settings):
    """prc options that must be set before the window opens (applied on restart when the mode changes)."""
    ms = 4
    loadPrcFileData("", "depth-bits 24\ntexture-minfilter linear-mipmap-linear\ntexture-magfilter linear\n"
                    "texture-anisotropic-degree 16\n")
    return ms


def lod_far(app):
    return 180.0  # v1.0.5.4 HD: keep full car models further out (both modes)


def light_far(app):
    """distance after which a car's road light pools (headlight beam / brake pool) are culled"""
    return 200.0  # v1.0.5.4 HD (both modes)


def traffic_scale(app):
    return 1.0  # v1.0.5.4 HD full traffic in both modes


GV = """#version 120
attribute vec4 p3d_Vertex; attribute vec2 p3d_MultiTexCoord0;
uniform mat4 p3d_ModelViewProjectionMatrix; varying vec2 uv;
void main() { gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex; uv = p3d_MultiTexCoord0; }
"""
GF = """#version 120
uniform sampler2D scene; uniform float gtime; uniform float grain; varying vec2 uv;
void main() {
  vec3 c = texture2D(scene, uv).rgb;
  // filmic toe/shoulder (stronger cinematic S-curve), no bloom / no glow
  c = clamp(c, 0.0, 1.0);
  c = mix(c, c * c * (3.0 - 2.0 * c), 0.42);
  float l = dot(c, vec3(0.2126, 0.7152, 0.0722));
  // LUT-style split toning: deeper teal shadows, warmer sodium highlights
  c += vec3(-0.028, 0.008, 0.036) * (1.0 - l) * (1.0 - l) + vec3(0.038, 0.014, -0.028) * l * l;
  c = mix(vec3(l), c, 1.12);
  c = (c - 0.5) * 1.08 + 0.5;
  // vignette
  vec2 d = (uv - 0.5) * vec2(1.0, 0.82);
  c *= mix(0.62, 1.0, smoothstep(0.82, 0.18, length(d)));
  // film grain
  float n = fract(sin(dot(floor(gl_FragCoord.xy) + vec2(gtime * 137.0, gtime * 61.0), vec2(12.9898, 78.233))) * 43758.5453);
  c += (n - 0.5) * grain * (0.55 + 0.45 * (1.0 - l));
  gl_FragColor = vec4(clamp(c, 0.0, 1.0), 1.0);
}
"""


class Gfx:
    def __init__(self, app):
        self.app = app; self.fm = None; self.quad = None; self.cube_buf = None; self.cube_rig = None; self.cube_tex = None
        self.gtime = PTA_float([0.0]); self._k = 0
        app.render.set_shader_input("envcube", self.dummy_cube()); app.render.set_shader_input("use_cube", 0.0)

    def dummy_cube(self):
        t = Texture("dcube"); t.setup_cube_map(1, Texture.T_unsigned_byte, Texture.F_rgb)
        t.set_ram_image(b"\x20\x20\x28" * 6); return t

    def setup_grade(self):
        if self.fm is not None: return
        try:
            from direct.filter.FilterManager import FilterManager
            app = self.app; self.fm = FilterManager(app.win, app.cam)
            tex = Texture("scene"); fb = FrameBufferProperties(); fb.set_rgb_color(True); fb.set_depth_bits(24)
            fb.set_multisamples(4)
            self.quad = self.fm.renderSceneInto(colortex=tex, fbprops=fb)
            if self.quad is None:
                self.fm = None; return
            self.quad.set_shader(Shader.make(Shader.SL_GLSL, GV, GF))
            self.quad.set_shader_input("scene", tex); self.quad.set_shader_input("gtime", self.gtime)
            self.quad.set_shader_input("grain", 0.028)
        except Exception as e:
            self.fm = None; self.app_log("grade: %r" % e)

    def app_log(self, m):
        try:
            import fireout_online; fireout_online.log_error(m)
        except Exception:
            pass

    # ---------------------------------------------------------------- dynamic cube-map (RTX)
    def cube_on(self, on, size=256):
        app = self.app
        if on and self.cube_buf is not None and getattr(self, "cube_size", size) != size:
            self.cube_on(False)
        if on and self.cube_buf is None:
            self.cube_size = size
            try:
                self.cube_rig = app.render.attach_new_node("cuberig")
                self.cube_buf = app.win.make_cube_map("carenv", size, self.cube_rig, CUBE_MASK)
                self.cube_buf.set_sort(-50)
                for c in self.cube_rig.find_all_matches("**/+Camera"):
                    c.node().get_lens().set_near_far(0.3, 400)
                self.cube_tex = self.cube_buf.get_texture()
            except Exception as e:
                self.app_log("cubemap: %r" % e); self.cube_buf = None
        elif not on and self.cube_buf is not None:
            self.app.graphicsEngine.remove_window(self.cube_buf); self.cube_buf = None
            self.cube_rig.remove_node(); self.cube_rig = None; self.cube_tex = None

    def bind_car(self, car):
        """player car samples the dynamic cube-map; it is hidden from the cube cameras so it does not reflect itself."""
        if car is None: return
        if self.cube_tex is not None:
            car.model.set_shader_input("envcube", self.cube_tex); car.model.set_shader_input("use_cube", 1.0)
            car.np.hide(CUBE_MASK)
        else:
            car.model.set_shader_input("use_cube", 0.0)

    def unbind_car(self, car):
        if car is None: return
        car.model.set_shader_input("use_cube", 0.0); car.np.show(CUBE_MASK)

    def apply(self):
        app = self.app
        self.setup_grade()
        rtx = app.settings.get("gfx") == "RTX"
        self.cube_on(True, 256); self.cube_every = 1  # v1.0.5.4 HD cube both modes
        g = getattr(app, "game", None)
        if g is not None:
            for c in getattr(g, "cars", []):
                c.set_lod_far(lod_far(app)); self.unbind_car(c)
            self._bound = None

    def frame(self, dt):
        self.gtime[0] = (self.gtime[0] + dt) % 100.0; self._k += 1
        g = getattr(self.app, "game", None)
        pc = getattr(g, "pcar", None) if g else None
        if pc is not getattr(self, "_bound", None):
            ob = getattr(self, "_bound", None)
            if ob is not None and not ob.dead:
                self.unbind_car(ob); ob.set_lod_far(lod_far(self.app))
            if pc is not None:
                self.bind_car(pc); pc.set_lod_far(4000.0)
            self._bound = pc
        if self.cube_buf is not None:
            c = getattr(g, "pcar", None) if g else None
            if c is None or c.dead:
                self.cube_buf.set_active(False)
            else:
                self.cube_buf.set_active(self._k % getattr(self, "cube_every", 1) == 0)
                self.cube_rig.set_pos(c.x, c.y, 0.9)
        if g is not None and self._k % 15 == 0 and self.app.camera is not None:
            cp = self.app.camera.get_pos(self.app.render); lf = light_far(self.app)
            for o in getattr(g, "cars", []):
                gl = getattr(o, "glows", None)
                if gl is None or o is pc: continue
                far = (o.x - cp[0]) ** 2 + (o.y - cp[1]) ** 2 > lf * lf
                if far != gl.is_hidden(): gl.hide() if far else gl.show()
