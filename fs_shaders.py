"""GLSL shaders (GLSL 1.20 / compatibility) for glossy car paint, city surfaces and skin/cloth characters.
v1.0.5.4: richer sun key, contact AO and distance haze on hard surfaces (sheen/characters kept as before). No bloom."""
from panda3d.core import Shader

VERT = """#version 120
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelMatrix;
uniform mat3 p3d_NormalMatrix;
uniform mat4 p3d_ModelViewMatrix;
attribute vec4 p3d_Vertex;
attribute vec3 p3d_Normal;
attribute vec2 p3d_MultiTexCoord0;
attribute vec4 p3d_Tangent;
attribute vec4 p3d_Color;
varying vec4 vcol;
uniform vec3 wspos_view;
varying vec3 wpos; varying vec3 wnrm; varying vec2 uv; varying vec3 wtan; varying float vdist; varying float tsign;
void main() {
  gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
  wpos = (p3d_ModelMatrix * p3d_Vertex).xyz;
  wnrm = normalize(mat3(p3d_ModelMatrix) * p3d_Normal);
  wtan = mat3(p3d_ModelMatrix) * p3d_Tangent.xyz; tsign = p3d_Tangent.w; vcol = p3d_Color;
  uv = p3d_MultiTexCoord0;
  vdist = length((p3d_ModelViewMatrix * p3d_Vertex).xyz);
}
"""

FRAG = """#version 120
uniform sampler2D p3d_Texture0;
uniform sampler2D envmap;
uniform sampler2D normalmap;
uniform samplerCube envcube; uniform float use_cube; uniform float clearcoat;
uniform vec4 p3d_ColorScale;
uniform struct { vec4 baseColor; vec4 emission; float roughness; float metallic; } p3d_Material;
uniform vec3 campos;
uniform vec3 fogcol; uniform float fogden;
uniform float gloss; uniform float use_tex; uniform float use_nmap; uniform float sheen; uniform float emitboost;
uniform vec4 tint;
uniform float dayk; uniform vec3 fogday; uniform vec3 sundir; uniform sampler2D envday;
varying vec3 wpos; varying vec3 wnrm; varying vec2 uv; varying vec3 wtan; varying float vdist; varying float tsign; varying vec4 vcol;
void main() {
  vec3 N = normalize(wnrm);
  if (use_nmap > 0.5 && dot(wtan, wtan) > 1e-6) {
    vec3 T = normalize(wtan - N * dot(N, wtan)); vec3 B = cross(N, T) * tsign;
    vec3 nm = texture2D(normalmap, uv).xyz * 2.0 - 1.0;
    N = normalize(T * nm.x + B * nm.y + N * nm.z);
  }
  vec3 V = normalize(campos - wpos);
  if (dot(N, V) < 0.0) N = -N;
  vec4 base = p3d_Material.baseColor * vcol;
  if (use_tex > 0.5) base *= texture2D(p3d_Texture0, uv);
  base.rgb *= tint.rgb;
  vec3 c = base.rgb;
  // night lighting: cool moon key + purple/orange hemisphere fill
  // v1.0.5.4 hard surfaces (sheen~0): stronger key/fill contrast + cheap contact AO. Characters (sheen>0) keep the soft wrap look.
  vec3 L = normalize(vec3(0.35, -0.45, 0.82));
  float ndl = max(dot(N, L), 0.0);
  float wrap = max((dot(N, L) + 0.45) / 1.45, 0.0);
  float hard = 1.0 - clamp(sheen, 0.0, 1.0);          // 1 = cars/city, 0 = skin/cloth
  vec3 hemi = mix(vec3(0.16, 0.10, 0.14), vec3(0.14, 0.15, 0.28), N.z * 0.5 + 0.5);
  float key = mix(ndl, wrap, sheen);
  // contact AO: darken downward-facing / crevice normals a touch on hard surfaces only
  float ao = mix(1.0, 0.55 + 0.45 * max(N.z, 0.0), hard * 0.85);
  vec3 diff = c * (hemi * mix(2.3, 1.55, hard) + vec3(0.62, 0.64, 0.80) * key * mix(1.15, 1.45, hard) + vec3(0.08, 0.07, 0.09)) * ao;
  // street-light pools: warm light from above (roads/buildings)
  diff += c * vec3(0.95, 0.62, 0.32) * mix(0.25, 0.38, hard) * max(N.z, 0.0);
  // daylight: warm sun key + blue sky / warm ground bounce, harder shadows on city surfaces
  vec3 Ls = normalize(sundir);
  float sdl = max(dot(N, Ls), 0.0); float swr = max((dot(N, Ls) + 0.45) / 1.45, 0.0);
  float dkey = mix(sdl, swr, sheen);
  // sharper sun terminator on hard surfaces (still no real shadow map / no bloom)
  dkey = mix(dkey, pow(sdl, 1.35), hard * 0.7);
  vec3 dhemi = mix(vec3(0.38, 0.34, 0.30), vec3(0.52, 0.64, 0.88), N.z * 0.5 + 0.5);
  vec3 ddiff = c * (dhemi * mix(1.0, 0.78, hard) + vec3(1.20, 1.08, 0.90) * dkey * mix(1.0, 1.25, hard)) * ao;
  diff = mix(diff, ddiff, dayk); L = normalize(mix(L, Ls, dayk));
  vec3 R = reflect(-V, N);
  vec2 euv = vec2(atan(R.y, R.x) / 6.2831 + 0.5, clamp(0.5 - asin(clamp(R.z, -1.0, 1.0)) / 3.1416, 0.01, 0.99));
  vec3 env = mix(texture2D(envmap, euv).rgb, texture2D(envday, vec2(euv.x, 1.0 - euv.y)).rgb, dayk);
  // v1.0.5.3 RTX: dynamic cube-map of the real surroundings around the player car (EX HD: static environment map)
  if (use_cube > 0.5) env = mix(env, textureCube(envcube, R).rgb * 1.15, 0.8);
  // v1.0.5.3 realism: the night environment is less saturated / dimmer, so white and silver cars stay white (no lilac paint)
  env = mix(vec3(dot(env, vec3(0.3, 0.55, 0.15))), env, mix(0.55, 0.9, dayk)) * mix(0.7, 1.0, dayk);
  float fres = 0.04 + 0.96 * pow(1.0 - max(dot(N, V), 0.0), 5.0);
  float spec_amt = gloss * mix(0.25, 1.0, p3d_Material.metallic);
  // v1.0.4: skin / cloth (sheen) get only a faint grazing reflection - no glowing white outline on arms and legs
  float fk = fres * gloss * (1.0 - 0.85 * clamp(sheen, 0.0, 1.0));
  vec3 col = diff * (1.0 - spec_amt * 0.5) + env * (fk + spec_amt * 0.35) * mix(vec3(1.0), c + 0.25, p3d_Material.metallic);
  vec3 H = normalize(L + V);
  col += vec3(0.7, 0.75, 1.0) * pow(max(dot(N, H), 0.0), mix(8.0, 90.0, gloss)) * gloss * 0.6;
  // v1.0.5.3 clearcoat (car paint): extra sharp lobe + fresnel-weighted mirror reflection on top of the metallic base
  float cfr = 0.04 + 0.96 * pow(1.0 - max(dot(N, V), 0.0), 5.0);
  col = mix(col, col * (1.0 - cfr * 0.5) + env * cfr * 1.1, clearcoat);
  col += vec3(1.0, 0.98, 0.95) * pow(max(dot(N, H), 0.0), 480.0) * clearcoat * 1.55;
  // (v1.0.4: the pink skin/cloth rim light was removed - it made legs and arms look like they were glowing)
  col += p3d_Material.emission.rgb * emitboost;
  col *= p3d_ColorScale.rgb;
  col = min(col, vec3(0.82) + 0.18 * (1.0 - exp(-(max(col - vec3(0.82), vec3(0.0))) * 4.0)));   // soft highlight roll-off instead of clipping to white
  // v1.0.5.4: longer atmospheric haze so distant city blocks read as layered depth (still flat fog, no bloom)
  float f = 1.0 - exp(-fogden * fogden * vdist * vdist * mix(1.0, 1.35, hard));
  f *= mix(1.0, 0.50, clamp(wpos.z / 90.0, 0.0, 1.0));
  vec3 fogc = mix(fogcol, fogday, dayk);
  // slight desat into the distance on hard surfaces
  col = mix(col, mix(vec3(dot(col, vec3(0.3, 0.55, 0.15))), col, 0.55), clamp(f, 0.0, 1.0) * hard * 0.35);
  col = mix(col, fogc, clamp(f, 0.0, 1.0));
  gl_FragColor = vec4(col, base.a * p3d_ColorScale.a);
}
"""

_cache = {}


def shader():
    if "s" not in _cache:
        _cache["s"] = Shader.make(Shader.SL_GLSL, VERT, FRAG)
    return _cache["s"]


def apply(np_, app, gloss=0.6, tex=False, nmap=None, sheen=0.0, emitboost=1.0, tint=(1, 1, 1, 1), clearcoat=0.0):
    np_.set_shader(shader())
    np_.set_shader_input("envmap", app.envtex)
    np_.set_shader_input("normalmap", nmap or app.flat_nmap)
    np_.set_shader_input("campos", app.campos_np)
    np_.set_shader_input("fogcol", app.fogcol)
    np_.set_shader_input("fogden", app.fogden)
    np_.set_shader_input("gloss", gloss)
    np_.set_shader_input("use_tex", 1.0 if tex else 0.0)
    np_.set_shader_input("use_nmap", 1.0 if nmap is not None else 0.0)
    np_.set_shader_input("sheen", sheen)
    np_.set_shader_input("emitboost", emitboost)
    np_.set_shader_input("tint", tint)
    np_.set_shader_input("wspos_view", (0, 0, 0))
    np_.set_shader_input("clearcoat", clearcoat)


# ---------------------------------------------------------------- sky only (cel). Never applied to characters or cars.
SKY_VERT = """#version 120
uniform mat4 p3d_ModelViewProjectionMatrix;
attribute vec4 p3d_Vertex; attribute vec2 p3d_MultiTexCoord0;
varying vec2 uv; varying float elev;
void main() {
  gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
  uv = p3d_MultiTexCoord0;
  elev = p3d_MultiTexCoord0.y;   // dome UV: ~0 horizon .. ~1 zenith
}
"""
SKY_FRAG = """#version 120
uniform sampler2D p3d_Texture0;
uniform vec4 p3d_ColorScale;
uniform float dayk;
varying vec2 uv; varying float elev;
void main() {
  vec3 tex = texture2D(p3d_Texture0, uv).rgb;
  // cel bands by elevation: flat cinematic sky slices (sky dome only)
  float e = clamp(elev * 2.0 - 0.15, 0.0, 1.0);
  // night palette
  vec3 n0 = vec3(0.02, 0.02, 0.06);   // zenith
  vec3 n1 = vec3(0.08, 0.04, 0.18);   // mid
  vec3 n2 = vec3(0.35, 0.12, 0.32);   // horizon neon wash
  // day palette
  vec3 d0 = vec3(0.25, 0.48, 0.92);
  vec3 d1 = vec3(0.45, 0.70, 0.95);
  vec3 d2 = vec3(0.78, 0.88, 0.98);
  vec3 night, dayc;
  if (e > 0.66) { night = n0; dayc = d0; }
  else if (e > 0.33) { night = n1; dayc = d1; }
  else { night = n2; dayc = d2; }
  // soft mix with the photo sky so stars/moon/clouds still read, then re-quantize
  vec3 base = mix(night, dayc, clamp(dayk, 0.0, 1.0));
  vec3 mixc = mix(base, tex, 0.35);
  float l = dot(mixc, vec3(0.30, 0.59, 0.11));
  float ql = floor(l * 5.0 + 0.5) / 5.0;
  vec3 cel = mixc * (ql / max(l, 1e-3));
  // hard horizon band edge
  float edge = smoothstep(0.28, 0.32, e) * (1.0 - smoothstep(0.34, 0.38, e));
  cel = mix(cel, cel * 1.08 + vec3(0.04, 0.02, 0.06), edge * (1.0 - dayk));
  cel *= p3d_ColorScale.rgb;
  gl_FragColor = vec4(clamp(cel, 0.0, 1.0), p3d_ColorScale.a);
}
"""


def sky_shader():
    if "sky" not in _cache:
        _cache["sky"] = Shader.make(Shader.SL_GLSL, SKY_VERT, SKY_FRAG)
    return _cache["sky"]


def apply_sky(np_, dayk=0.0):
    """Cel-shade a sky dome only. Do not call for characters, cars, or city props."""
    np_.set_shader(sky_shader())
    np_.set_shader_input("dayk", float(dayk))

