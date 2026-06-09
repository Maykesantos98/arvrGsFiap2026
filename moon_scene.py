"""
Cena lunar: superficie da Lua com crateras (entrada de caverna), fundo de
universo (estrelas + nebulosa), a Terra colorida ao fundo e robos-aranha
de exploracao com farois emissivos.

Escrito para Blender 5.1 (funciona em 4.x tambem; usa codigo a prova de versao).
Tudo via bpy.data + bmesh -- nao depende de contexto de UI.

Rodar headless (Windows / PowerShell):
  & "C:\\Program Files\\Blender Foundation\\Blender 5.1\\blender.exe" -b -P moon_scene.py -- --out C:\\Users\\mayke\\Desktop\\arvr\\moon_scene.png

Args opcionais (depois de "--"):
  --out  <caminho.png>     destino do render
  --save <caminho.blend>   salva tambem o .blend
  --samples <int>          amostras Cycles (default 64)
"""

import bpy
import bmesh
import sys
import os
import math
from mathutils import Vector, Matrix
from mathutils import noise as mnoise

# --------------------------------------------------------------------------- #
# Argumentos de linha de comando (apos "--")
# --------------------------------------------------------------------------- #
argv = sys.argv
argv = argv[argv.index("--") + 1:] if "--" in argv else []


def arg(flag, default=None):
    return argv[argv.index(flag) + 1] if flag in argv else default


HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
OUT_PATH = arg("--out", os.path.join(HERE, "moon_scene.png"))
BLEND_PATH = arg("--save", None)
SAMPLES = int(arg("--samples", "64"))
SHOTS_DIR = arg("--shots", None)   # se definido: renderiza a serie de prints do trabalho
ONLY = arg("--only", None)         # subconjunto de shots (nomes separados por virgula)
EXPORT_GLB = arg("--export", None) # se definido: exporta uma aranha em .glb (para a web)
SOLO = arg("--solo", None)         # se definido: breakdown de 1 objeto (final/clay/wire)

# --------------------------------------------------------------------------- #
# 1. Cena limpa e conhecida
# --------------------------------------------------------------------------- #
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# --------------------------------------------------------------------------- #
# Helpers a prova de versao
# --------------------------------------------------------------------------- #
def available_engines():
    builtin = [e.identifier for e in
               bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
    addon = [c.bl_idname for c in bpy.types.RenderEngine.__subclasses__()
             if hasattr(c, "bl_idname")]
    return list(dict.fromkeys(builtin + addon))


def setp(node, name, value):
    """Seta um input de node so se ele existir (nomes mudam entre versoes)."""
    if name in node.inputs:
        node.inputs[name].default_value = value
        return True
    return False


def new_mix(nt, blend='MIX'):
    """Cria um node de mistura de cor, lidando com MixRGB (legacy) e Mix novo.
    Retorna (node, fac_in, a_in, b_in, result_out)."""
    try:
        n = nt.nodes.new('ShaderNodeMixRGB')
        n.blend_type = blend
        return n, n.inputs['Fac'], n.inputs['Color1'], n.inputs['Color2'], n.outputs['Color']
    except Exception:
        n = nt.nodes.new('ShaderNodeMix')
        n.data_type = 'RGBA'
        n.blend_type = blend
        return n, n.inputs['Factor'], n.inputs[6], n.inputs[7], n.outputs[2]


def _cone(bm, seg, r1, r2, depth, M):
    try:
        return bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg,
                                     radius1=r1, radius2=r2, depth=depth, matrix=M, calc_uvs=True)
    except TypeError:
        return bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg,
                                     diameter1=r1 * 2, diameter2=r2 * 2, depth=depth, matrix=M, calc_uvs=True)


def _uvsphere(bm, useg, vseg, r, M):
    try:
        return bmesh.ops.create_uvsphere(bm, u_segments=useg, v_segments=vseg,
                                         radius=r, matrix=M, calc_uvs=True)
    except TypeError:
        return bmesh.ops.create_uvsphere(bm, u_segments=useg, v_segments=vseg,
                                         diameter=r * 2, matrix=M, calc_uvs=True)


def _icosphere(bm, subd, r, M):
    try:
        return bmesh.ops.create_icosphere(bm, subdivisions=subd, radius=r, matrix=M, calc_uvs=True)
    except TypeError:
        return bmesh.ops.create_icosphere(bm, subdivisions=subd, diameter=r * 2, matrix=M, calc_uvs=True)


def add_cylinder(bm, p1, p2, r1, r2=None, segments=10):
    """Cilindro/cone tronco de p1 (raio r1) a p2 (raio r2). r2 None => cilindro."""
    r2 = r1 if r2 is None else r2
    p1, p2 = Vector(p1), Vector(p2)
    vec = p2 - p1
    length = vec.length
    if length < 1e-6:
        return
    mid = (p1 + p2) / 2.0
    rot = vec.to_track_quat('Z', 'Y').to_matrix().to_4x4()
    M = Matrix.Translation(mid) @ rot
    _cone(bm, segments, r1, r2, length, M)


def merge_bm(bm, tmp):
    """Anexa a geometria de um bmesh temporario em bm e libera o temporario."""
    me = bpy.data.meshes.new("_tmp_merge")
    tmp.to_mesh(me)
    tmp.free()
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)


def add_box(bm, center, size, forward=None, bevel=0.04, seg=1):
    """Caixa chanfrada de dimensoes 'size' (full), orientada com +Y -> 'forward'."""
    tmp = bmesh.new()
    bmesh.ops.create_cube(tmp, size=1.0, calc_uvs=True)
    bmesh.ops.scale(tmp, vec=Vector(size), space=Matrix.Identity(4), verts=tmp.verts)
    if bevel > 0:
        bmesh.ops.bevel(tmp, geom=list(tmp.verts) + list(tmp.edges) + list(tmp.faces),
                        offset=bevel, segments=seg, profile=0.7, affect='EDGES')
    rot = forward.to_track_quat('Y', 'Z').to_matrix().to_4x4() if forward else Matrix.Identity(4)
    bmesh.ops.transform(tmp, matrix=Matrix.Translation(Vector(center)) @ rot,
                        space=Matrix.Identity(4), verts=tmp.verts)
    merge_bm(bm, tmp)


def add_ellipsoid(bm, center, radii, forward=None, useg=28, vseg=16):
    """Esfera escalada (elipsoide), orientada com +Y -> 'forward'. Forma suave/esculpida."""
    rot = forward.to_track_quat('Y', 'Z').to_matrix().to_4x4() if forward else Matrix.Identity(4)
    M = (Matrix.Translation(Vector(center)) @ rot
         @ Matrix.Diagonal((radii[0], radii[1], radii[2], 1.0)))
    _uvsphere(bm, useg, vseg, 1.0, M)


def add_sphere(bm, center, radius, useg=12, vseg=8):
    _uvsphere(bm, useg, vseg, radius, Matrix.Translation(Vector(center)))


def add_ico(bm, center, radius, subd=2):
    _icosphere(bm, subd, radius, Matrix.Translation(Vector(center)))


# --- Collections (camadas) para edicao manual no Blender ---
_COLLECTIONS = {}


def get_collection(name):
    if name in _COLLECTIONS:
        return _COLLECTIONS[name]
    col = bpy.data.collections.new(name)
    scene.collection.children.link(col)
    _COLLECTIONS[name] = col
    return col


def link_obj(ob, collection="Cena"):
    get_collection(collection).objects.link(ob)
    return ob


def bm_to_object(bm, name, material, smooth=True, collection="Cena"):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.update()
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    if material:
        ob.data.materials.append(material)
    link_obj(ob, collection)
    return ob


# --------------------------------------------------------------------------- #
# 2. Terreno lunar (grid deslocado por ruido + crateras)
# --------------------------------------------------------------------------- #
# (cx, cy, raio, profundidade, altura_da_borda)
CRATERS = [
    (0.0, 8.5, 5.4, 1.6, 0.55),    # cratera principal
    (0.6, 9.4, 2.6, 3.2, 0.65),    # poco largo e profundo = BOCA DA CAVERNA
    (-9.0, 3.0, 2.2, 0.7, 0.28),
    (7.5, 13.0, 3.0, 0.9, 0.30),
    (5.0, -3.0, 1.5, 0.5, 0.20),
    (-7.0, 14.0, 2.6, 0.8, 0.26),
    (11.0, 4.0, 2.0, 0.6, 0.24),
    (-4.0, -6.0, 1.2, 0.4, 0.16),
]

# Boca da caverna (poco profundo) -- usado para posicionar o "vazio" escuro
CAVE = (0.6, 9.4, 2.6)


def terrain_height(x, y):
    h = 0.0
    # colinas em varias escalas (Perlin)
    h += 0.65 * mnoise.noise(Vector((x * 0.055, y * 0.055, 0.0)))
    h += 0.28 * mnoise.noise(Vector((x * 0.15, y * 0.15, 10.0)))
    h += 0.09 * mnoise.noise(Vector((x * 0.5, y * 0.5, 20.0)))
    # crateras (tigela + borda elevada)
    for (cx, cy, r, depth, rim) in CRATERS:
        dist = math.hypot(x - cx, y - cy)
        if dist < r:
            nd = dist / r
            h += -depth * (1.0 - nd) ** 1.6
        sigma = r * 0.13
        h += rim * math.exp(-((dist - r) ** 2) / (2.0 * sigma * sigma))
    return h


def build_terrain():
    S = 22.0      # meia-largura
    N = 180       # resolucao
    verts, faces = [], []
    for j in range(N):
        for i in range(N):
            x = -S + 2.0 * S * i / (N - 1)
            y = -S + 2.0 * S * j / (N - 1)
            verts.append((x, y, terrain_height(x, y)))
    for j in range(N - 1):
        for i in range(N - 1):
            a = j * N + i
            faces.append((a, a + 1, a + N + 1, a + N))
    me = bpy.data.meshes.new("LunarSurface")
    me.from_pydata(verts, [], faces)
    me.update(calc_edges=True)
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new("Solo_Lunar", me)
    ob.data.materials.append(make_moon_material())
    link_obj(ob, "Terreno")
    return ob


# --------------------------------------------------------------------------- #
# Materiais
# --------------------------------------------------------------------------- #
def make_moon_material():
    m = bpy.data.materials.new("MoonRegolith")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    tc = nt.nodes.new('ShaderNodeTexCoord')

    # variacao de cor (cinza regolito)
    n_col = nt.nodes.new('ShaderNodeTexNoise')
    setp(n_col, 'Scale', 1.4)
    setp(n_col, 'Detail', 6.0)
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.30
    ramp.color_ramp.elements[0].color = (0.14, 0.135, 0.13, 1)
    ramp.color_ramp.elements[1].position = 0.75
    ramp.color_ramp.elements[1].color = (0.42, 0.41, 0.40, 1)

    # micro-relevo (bump)
    n_bump = nt.nodes.new('ShaderNodeTexNoise')
    setp(n_bump, 'Scale', 9.0)
    setp(n_bump, 'Detail', 8.0)
    bump = nt.nodes.new('ShaderNodeBump')
    setp(bump, 'Strength', 0.35)
    setp(bump, 'Distance', 0.15)

    L = nt.links.new
    L(tc.outputs['Generated'], n_col.inputs['Vector'])
    L(tc.outputs['Generated'], n_bump.inputs['Vector'])
    L(n_col.outputs['Fac'], ramp.inputs['Fac'])
    L(ramp.outputs['Color'], bsdf.inputs['Base Color'])
    L(n_bump.outputs['Fac'], bump.inputs['Height'])
    L(bump.outputs['Normal'], bsdf.inputs['Normal'])
    setp(bsdf, 'Roughness', 0.96)
    setp(bsdf, 'Specular IOR Level', 0.15)
    setp(bsdf, 'Metallic', 0.0)
    L(bsdf.outputs['BSDF'], out.inputs['Surface'])
    return m


def make_metal(name, color, rough, metallic=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    setp(bsdf, 'Base Color', (color[0], color[1], color[2], 1))
    setp(bsdf, 'Metallic', metallic)
    setp(bsdf, 'Roughness', rough)
    setp(bsdf, 'Specular IOR Level', 0.5)
    return m


def make_shell(name, color, rough=0.25):
    """Casca branca/clara com clear-coat (visual moderno e brilhante)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    setp(bsdf, 'Base Color', (color[0], color[1], color[2], 1))
    setp(bsdf, 'Metallic', 0.0)
    setp(bsdf, 'Roughness', rough)
    setp(bsdf, 'Specular IOR Level', 0.6)
    setp(bsdf, 'Coat Weight', 1.0)
    setp(bsdf, 'Coat Roughness', 0.08)
    return m


def make_emissive(name, color, strength):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (color[0], color[1], color[2], 1)
    em.inputs['Strength'].default_value = strength
    nt.links.new(em.outputs['Emission'], out.inputs['Surface'])
    return m


def make_earth_material():
    m = bpy.data.materials.new("Earth")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    L = nt.links.new
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mapping = nt.nodes.new('ShaderNodeMapping')
    L(tc.outputs['Generated'], mapping.inputs['Vector'])

    # ---- continentes vs oceano (1 ruido -> ColorRamp colorido) ----
    n_land = nt.nodes.new('ShaderNodeTexNoise')
    setp(n_land, 'Scale', 2.6)
    setp(n_land, 'Detail', 9.0)
    setp(n_land, 'Roughness', 0.62)
    L(mapping.outputs['Vector'], n_land.inputs['Vector'])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    cr = ramp.color_ramp
    cr.elements[0].position = 0.0
    cr.elements[0].color = (0.01, 0.04, 0.22, 1)     # oceano profundo
    cr.elements[1].position = 0.46
    cr.elements[1].color = (0.02, 0.12, 0.42, 1)     # oceano
    e = cr.elements.new(0.50); e.color = (0.0, 0.27, 0.46, 1)   # raso/costa
    e = cr.elements.new(0.53); e.color = (0.22, 0.42, 0.16, 1)  # praia/verde
    e = cr.elements.new(0.62); e.color = (0.08, 0.32, 0.06, 1)  # floresta
    e = cr.elements.new(0.74); e.color = (0.34, 0.26, 0.12, 1)  # terra/deserto
    e = cr.elements.new(0.88); e.color = (0.45, 0.40, 0.34, 1)  # montanha
    L(n_land.outputs['Fac'], ramp.inputs['Fac'])

    # ---- calotas polares (a partir do Z do Generated) ----
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    L(tc.outputs['Generated'], sep.inputs['Vector'])
    ice = nt.nodes.new('ShaderNodeValToRGB')
    ic = ice.color_ramp
    ic.elements[0].position = 0.10
    ic.elements[0].color = (1, 1, 1, 1)
    ic.elements[1].position = 0.16
    ic.elements[1].color = (0, 0, 0, 1)
    e = ic.elements.new(0.84); e.color = (0, 0, 0, 1)
    e = ic.elements.new(0.90); e.color = (1, 1, 1, 1)
    L(sep.outputs['Z'], ice.inputs['Fac'])
    mix_ice, f, a, b, res_ice = new_mix(nt, 'MIX')
    L(ice.outputs['Color'], f)
    L(ramp.outputs['Color'], a)
    b.default_value = (0.92, 0.95, 0.98, 1)

    # ---- nuvens ----
    n_cloud = nt.nodes.new('ShaderNodeTexNoise')
    setp(n_cloud, 'Scale', 4.2)
    setp(n_cloud, 'Detail', 8.0)
    setp(n_cloud, 'Roughness', 0.7)
    L(mapping.outputs['Vector'], n_cloud.inputs['Vector'])
    cloud = nt.nodes.new('ShaderNodeValToRGB')
    cc = cloud.color_ramp
    cc.elements[0].position = 0.52
    cc.elements[0].color = (0, 0, 0, 1)
    cc.elements[1].position = 0.64
    cc.elements[1].color = (1, 1, 1, 1)
    L(n_cloud.outputs['Fac'], cloud.inputs['Fac'])
    mix_cloud, f2, a2, b2, res_cloud = new_mix(nt, 'MIX')
    L(cloud.outputs['Color'], f2)
    L(res_ice, a2)
    b2.default_value = (1, 1, 1, 1)

    L(res_cloud, bsdf.inputs['Base Color'])
    setp(bsdf, 'Roughness', 0.55)
    setp(bsdf, 'Specular IOR Level', 0.4)

    # ---- atmosfera (brilho azul nas bordas via Layer Weight Fresnel) ----
    lw = nt.nodes.new('ShaderNodeLayerWeight')
    lw.inputs['Blend'].default_value = 0.35
    atm = nt.nodes.new('ShaderNodeEmission')
    atm.inputs['Color'].default_value = (0.25, 0.55, 1.0, 1)
    atm.inputs['Strength'].default_value = 2.2
    mix_sh = nt.nodes.new('ShaderNodeMixShader')
    L(lw.outputs['Fresnel'], mix_sh.inputs['Fac'])
    L(bsdf.outputs['BSDF'], mix_sh.inputs[1])
    L(atm.outputs['Emission'], mix_sh.inputs[2])

    # ---- luzes de cidade no lado NOTURNO (sobre os continentes) ----
    sun_dir = Vector((0.35, 0.55, -0.75)).normalized()
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    dot = nt.nodes.new('ShaderNodeVectorMath')
    dot.operation = 'DOT_PRODUCT'
    dot.inputs[1].default_value = (sun_dir.x, sun_dir.y, sun_dir.z)
    L(geo.outputs['Normal'], dot.inputs[0])
    night = nt.nodes.new('ShaderNodeValToRGB')   # dot<=0 (noite) -> 1 ; dia -> 0
    night.color_ramp.elements[0].position = 0.0
    night.color_ramp.elements[0].color = (1, 1, 1, 1)
    night.color_ramp.elements[1].position = 0.06
    night.color_ramp.elements[1].color = (0, 0, 0, 1)
    L(dot.outputs['Value'], night.inputs['Fac'])
    land = nt.nodes.new('ShaderNodeValToRGB')     # mascara de continente
    land.color_ramp.elements[0].position = 0.49
    land.color_ramp.elements[0].color = (0, 0, 0, 1)
    land.color_ramp.elements[1].position = 0.52
    land.color_ramp.elements[1].color = (1, 1, 1, 1)
    L(n_land.outputs['Fac'], land.inputs['Fac'])
    city_n = nt.nodes.new('ShaderNodeTexNoise')   # padrao esparso de cidades
    setp(city_n, 'Scale', 22.0)
    setp(city_n, 'Detail', 2.0)
    L(mapping.outputs['Vector'], city_n.inputs['Vector'])
    city = nt.nodes.new('ShaderNodeValToRGB')
    city.color_ramp.elements[0].position = 0.58
    city.color_ramp.elements[0].color = (0, 0, 0, 1)
    city.color_ramp.elements[1].position = 0.72
    city.color_ramp.elements[1].color = (1, 1, 1, 1)
    L(city_n.outputs['Fac'], city.inputs['Fac'])
    m1 = nt.nodes.new('ShaderNodeMath'); m1.operation = 'MULTIPLY'
    L(night.outputs['Color'], m1.inputs[0]); L(land.outputs['Color'], m1.inputs[1])
    m2 = nt.nodes.new('ShaderNodeMath'); m2.operation = 'MULTIPLY'
    L(m1.outputs['Value'], m2.inputs[0]); L(city.outputs['Color'], m2.inputs[1])
    m3 = nt.nodes.new('ShaderNodeMath'); m3.operation = 'MULTIPLY'
    m3.inputs[1].default_value = 9.0
    L(m2.outputs['Value'], m3.inputs[0])
    city_em = nt.nodes.new('ShaderNodeEmission')
    city_em.inputs['Color'].default_value = (1.0, 0.72, 0.38, 1)
    L(m3.outputs['Value'], city_em.inputs['Strength'])

    add = nt.nodes.new('ShaderNodeAddShader')
    L(mix_sh.outputs['Shader'], add.inputs[0])
    L(city_em.outputs['Emission'], add.inputs[1])
    L(add.outputs['Shader'], out.inputs['Surface'])
    return m


# --------------------------------------------------------------------------- #
# 3. Terra (esfera grande ao fundo)
# --------------------------------------------------------------------------- #
def build_earth():
    bm = bmesh.new()
    _uvsphere(bm, 64, 32, 9.0, Matrix.Identity(4))
    ob = bm_to_object(bm, "Planeta_Terra", make_earth_material(), collection="Terra")
    ob.location = (-7.0, 72.0, 30.0)
    ob.rotation_euler = (math.radians(18), 0, math.radians(40))
    return ob


# --------------------------------------------------------------------------- #
# 4. Robos-aranha de exploracao
# --------------------------------------------------------------------------- #
# ordem das pernas p/ marcha tripe: indices pares = 1 tripe, impares = outro
#   FL, FR, MR, ML, BL, BR  -> (lado, frente/meio/tras)  lado: -1=esq, +1=dir
LEG_LAYOUT = [(-1, 1), (1, 1), (1, 0), (-1, 0), (-1, -1), (1, -1)]


def build_spider(parts, base_x, base_y, facing, s=1.0, phase=0):
    """Aranha-exploradora dividida em PARTES nomeadas: Corpo (cefalotorax+abdome),
    Cabeca (visor+olhos+farois), Sonda, Domo_Antena e Pernas (6 hexapodes).
    Roteia a geometria em 'parts' = {parte: {material: bmesh}} para virar 1 objeto
    por parte. Materiais: shell, carbon, glass, accent, glow."""
    def bm(part, mat):
        return parts.setdefault(part, {}).setdefault(mat, bmesh.new())

    F = Vector((math.cos(facing), math.sin(facing), 0.0))   # frente
    R = Vector((math.sin(facing), -math.cos(facing), 0.0))  # direita
    UP = Vector((0.0, 0.0, 1.0))
    gz = terrain_height(base_x, base_y)
    body_z = gz + 1.05 * s                                  # postura alta de aranha
    C = Vector((base_x, base_y, body_z))

    # ---- Corpo: cefalotorax + ventre + abdome traseiro ----
    add_ellipsoid(bm("Corpo", "shell"), C, (0.55 * s, 0.74 * s, 0.42 * s), forward=F, useg=32, vseg=20)
    add_ellipsoid(bm("Corpo", "carbon"), C - UP * (0.16 * s), (0.52 * s, 0.70 * s, 0.26 * s), forward=F, useg=28, vseg=14)
    add_ellipsoid(bm("Corpo", "shell"), C - F * (0.62 * s) + UP * (0.02 * s),
                  (0.42 * s, 0.50 * s, 0.36 * s), forward=F, useg=28, vseg=16)

    # ---- Cabeca: visor escuro + cluster de 3 olhos + 2 farois ----
    head = C + F * (0.52 * s) + UP * (0.06 * s)
    add_ellipsoid(bm("Cabeca", "glass"), head, (0.34 * s, 0.30 * s, 0.30 * s), forward=F, useg=24, vseg=16)
    for off in (-0.15, 0.0, 0.15):
        eye = head + F * (0.20 * s) + R * (off * s) + UP * (0.03 * s)
        add_sphere(bm("Cabeca", "glow"), eye, 0.052 * s)
    for sgn in (1, -1):
        hl = C + F * (0.46 * s) + R * (sgn * 0.40 * s) - UP * (0.02 * s)
        add_cylinder(bm("Cabeca", "carbon"), hl, hl + F * (0.05 * s), 0.07 * s, 0.07 * s, segments=10)
        add_sphere(bm("Cabeca", "glow"), hl + F * (0.07 * s), 0.055 * s)

    # ---- Sonda articulada dianteira (instrumento do explorador) ----
    p0 = C + F * (0.40 * s) - UP * (0.06 * s)
    p1 = p0 + F * (0.42 * s) - UP * (0.34 * s)
    add_cylinder(bm("Sonda", "carbon"), p0, p1, 0.045 * s, 0.030 * s, segments=8)
    add_sphere(bm("Sonda", "accent"), p0, 0.06 * s)
    add_sphere(bm("Sonda", "glow"), p1, 0.045 * s)

    # ---- Domo_Antena no topo: domo lidar + antena ----
    dome = C + UP * (0.42 * s) - F * (0.10 * s)
    add_ellipsoid(bm("Domo_Antena", "glass"), dome, (0.20 * s, 0.22 * s, 0.16 * s), forward=F, useg=18, vseg=12)
    a0 = C + UP * (0.42 * s) - F * (0.34 * s)
    a1 = a0 + UP * (0.46 * s) - F * (0.06 * s)
    add_cylinder(bm("Domo_Antena", "carbon"), a0, a1, 0.018 * s, 0.010 * s, segments=6)
    add_sphere(bm("Domo_Antena", "glow"), a1, 0.030 * s)

    # ---- Pernas: 6 pernas grandes de aranha (joelho alto e para fora) ----
    for idx, (side, j) in enumerate(LEG_LAYOUT):
        swing = ((idx + phase) % 2 == 0)
        hip = C + F * (j * 0.34 * s) + R * (side * 0.46 * s) - UP * (0.06 * s)
        add_sphere(bm("Pernas", "accent"), hip, 0.11 * s)             # junta do ombro (coxa)

        outdir = (R * side + F * (j * 0.45)).normalized()
        reach = 1.65 * s                                     # passada larga
        stride = (0.32 * s) if swing else (-0.18 * s)
        fx = C.x + outdir.x * reach + F.x * stride
        fy = C.y + outdir.y * reach + F.y * stride
        fz = terrain_height(fx, fy) + (0.30 * s if swing else 0.0)
        foot = Vector((fx, fy, fz))

        # joelho ALTO e para fora -> silhueta de aranha
        knee = Vector((hip.x + outdir.x * 0.55 * s,
                       hip.y + outdir.y * 0.55 * s,
                       body_z + (0.62 if swing else 0.52) * s))
        add_cylinder(bm("Pernas", "carbon"), hip, knee, 0.075 * s, 0.058 * s, segments=12)   # femur
        add_sphere(bm("Pernas", "glow"), knee, 0.058 * s)             # joelho cyan
        add_cylinder(bm("Pernas", "carbon"), knee, foot, 0.055 * s, 0.025 * s, segments=10)  # tibia
        add_sphere(bm("Pernas", "carbon"), foot, 0.05 * s)            # pe


def build_robots():
    """Cada aranha vira uma Collection propria ('Aranha_N') com seus PROPRIOS
    materiais e uma identidade visual unica -> editavel individualmente."""
    cvx, cvy = CAVE[0], CAVE[1]   # boca da caverna

    def face_cave(x, y):
        return math.atan2(cvy - y, cvx - x)

    # x, y, escala, fase, facing, cor_shell, cor_accent, cor_glow
    robots = [
        (0.8, 0.2, 1.18, 0, math.radians(-65),
         (0.86, 0.88, 0.92), (0.00, 0.45, 0.50), (0.20, 0.85, 1.00)),   # 1 ciano/teal
        (-4.0, 4.0, 0.95, 1, face_cave(-4.0, 4.0),
         (0.91, 0.87, 0.82), (0.85, 0.35, 0.05), (1.00, 0.62, 0.15)),   # 2 ambar/laranja
        (4.6, 3.2, 0.90, 0, face_cave(4.6, 3.2),
         (0.82, 0.87, 0.92), (0.10, 0.55, 0.25), (0.30, 1.00, 0.45)),   # 3 verde
        (-2.2, 10.8, 0.80, 1, face_cave(-2.2, 10.8),
         (0.87, 0.84, 0.93), (0.55, 0.10, 0.55), (0.85, 0.35, 1.00)),   # 4 magenta/roxo
    ]
    for idx, (rx, ry, sc, ph, fac, c_shell, c_acc, c_glow) in enumerate(robots, start=1):
        parts = {}
        build_spider(parts, rx, ry, fac, s=sc, phase=ph)
        mats = {
            'shell':  make_shell("A%d_Shell" % idx, c_shell, rough=0.22),
            'carbon': make_metal("A%d_Carbon" % idx, (0.035, 0.040, 0.050), 0.34, 0.3),
            'glass':  make_metal("A%d_Glass" % idx, (0.010, 0.012, 0.020), 0.05, 0.0),
            'accent': make_metal("A%d_Accent" % idx, c_acc, 0.30, 1.0),
            'glow':   make_emissive("A%d_Glow" % idx, c_glow, 20.0),
        }
        col = "Aranha_%d" % idx
        # 1 objeto por PARTE (Corpo, Cabeca, Sonda, Domo_Antena, Pernas)
        for part_name, layers_dict in parts.items():
            layers = [(b, mats[mk]) for mk, b in layers_dict.items()]
            make_part("Aranha%d_%s" % (idx, part_name), layers, col, smooth=True)


def _rnd(i, k=0):
    """Pseudo-aleatorio deterministico em [0,1) (reproduzivel entre execucoes)."""
    return (math.sin(i * 12.9898 + k * 78.233) * 43758.5453) % 1.0


def make_rock_material():
    return make_metal("Rock", (0.085, 0.082, 0.078), 0.95, 0.0)


def make_void_material():
    m = bpy.data.materials.new("CaveVoid")
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    setp(bsdf, 'Base Color', (0.004, 0.004, 0.006, 1))
    setp(bsdf, 'Metallic', 0.0)
    setp(bsdf, 'Roughness', 1.0)
    setp(bsdf, 'Specular IOR Level', 0.0)
    return m


def build_rocks():
    """Pedras espalhadas (deterministicas) com variedade de tamanho/forma."""
    bm = bmesh.new()
    for i in range(40):
        a = i * 2.399963
        rad = 2.5 + _rnd(i, 1) * 16.0
        rx = math.cos(a) * rad + (_rnd(i, 2) - 0.5) * 4.0
        ry = 6.0 + math.sin(a) * rad + (_rnd(i, 3) - 0.5) * 4.0
        if abs(rx) > 21.0 or abs(ry) > 21.0:
            continue
        rz = terrain_height(rx, ry)
        boulder = _rnd(i, 4) > 0.85
        base = (0.55 if boulder else 0.12) + _rnd(i, 5) * (0.5 if boulder else 0.25)
        sx = base * (0.7 + 0.6 * _rnd(i, 6))
        sy = base * (0.7 + 0.6 * _rnd(i, 7))
        sz = base * (0.5 + 0.5 * _rnd(i, 8))
        M = (Matrix.Translation(Vector((rx, ry, rz + sz * 0.5)))
             @ Matrix.Rotation(_rnd(i, 9) * math.tau, 4, 'Z')
             @ Matrix.Diagonal((sx, sy, sz, 1.0)))
        _icosphere(bm, 2 if boulder else 1, 1.0, M)
    bm_to_object(bm, "Pedras_Espalhadas", make_rock_material(), collection="Pedras")


def build_cave():
    """Boca da caverna: vazio escuro fundo, brilho interno cyan, arco de rochas
    (overhang) sobre a entrada e anel de pedregulhos na borda."""
    cx, cy, cr = CAVE
    bottom = terrain_height(cx, cy)

    # vazio escuro no fundo do poco
    void = bmesh.new()
    add_ellipsoid(void, Vector((cx, cy, bottom + 0.10)), (cr * 0.85, cr * 0.85, 0.35),
                  useg=32, vseg=14)
    bm_to_object(void, "Caverna_Vazio", make_void_material(), collection="Caverna")

    # brilho interno fraco (a abertura "respira" luz cyan)
    glow = bmesh.new()
    add_ellipsoid(glow, Vector((cx, cy, bottom + 0.55)), (cr * 0.55, cr * 0.55, 0.18),
                  useg=24, vseg=10)
    bm_to_object(glow, "Caverna_Brilho", make_emissive("CaveGlow", (0.10, 0.55, 0.8), 2.2),
                 collection="Caverna")

    # anel de pedregulhos na borda (maiores, mais lisos)
    rim = bmesh.new()
    nb = 18
    for i in range(nb):
        t = i / nb * math.tau
        rr = cr * (1.02 + 0.12 * _rnd(i, 11))
        bx = cx + math.cos(t) * rr
        by = cy + math.sin(t) * rr
        bz = terrain_height(bx, by)
        sz = 0.28 + 0.42 * _rnd(i, 12)
        M = (Matrix.Translation(Vector((bx, by, bz + sz * 0.20)))
             @ Matrix.Rotation(_rnd(i, 13) * math.tau, 4, 'Z')
             @ Matrix.Diagonal((sz * 1.3, sz * 1.0, sz * 0.85, 1.0)))
        _icosphere(rim, 2, 1.0, M)

    # arco / overhang de rochas sobre um lado da entrada (lado norte, +Y)
    for i in range(5):
        u = i / 4.0
        ax = cx + (u - 0.5) * cr * 1.7
        ay = cy + cr * 1.05
        az = terrain_height(ax, ay) + 0.6 + math.sin(u * math.pi) * 1.0   # arco
        sz = 0.55 + 0.2 * _rnd(i, 21)
        M = (Matrix.Translation(Vector((ax, ay, az)))
             @ Matrix.Rotation(_rnd(i, 22) * math.tau, 4, 'Z')
             @ Matrix.Diagonal((sz * 1.4, sz * 1.1, sz * 0.9, 1.0)))
        _icosphere(rim, 2, 1.0, M)
    bm_to_object(rim, "Caverna_Arco_Rochas", make_rock_material(), collection="Caverna")


# =========================================================================== #
# Objetos espaciais autorais: satelite, modulo de pouso, bandeira
# =========================================================================== #
def make_part(name, layers, collection, smooth=True, loc=(0, 0, 0), rot=(0, 0, 0)):
    """Cria UM objeto nomeado (uma 'parte' logica do modelo) a partir de varias
    camadas (bmesh, material). Cada material distinto vira um slot do objeto, de
    modo que a modelagem possa ser avaliada PARTE A PARTE com nomes claros.
    Libera os bmesh de entrada e aplica o transform (origem = ponto de construcao)."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    mats = []
    for sub_bm, mat in layers:
        if mat not in mats:
            mats.append(mat)
        idx = mats.index(mat)
        tmp = bpy.data.meshes.new("_tmp_part")
        sub_bm.to_mesh(tmp)
        sub_bm.free()
        for poly in tmp.polygons:
            poly.material_index = idx
        bm.from_mesh(tmp)
        bpy.data.meshes.remove(tmp)
    bm.to_mesh(me)
    bm.free()
    me.update()
    if smooth:
        for poly in me.polygons:
            poly.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    for mat in mats:
        ob.data.materials.append(mat)
    ob.location = loc
    ob.rotation_euler = rot
    link_obj(ob, collection)
    return ob


def make_solar():
    """Painel solar: celulas azuis com linhas de grade (Brick)."""
    m = bpy.data.materials.new("SolarPanel")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (7.0, 16.0, 1.0)
    br = nt.nodes.new('ShaderNodeTexBrick')
    br.inputs['Color1'].default_value = (0.02, 0.05, 0.20, 1)
    br.inputs['Color2'].default_value = (0.03, 0.08, 0.28, 1)
    br.inputs['Mortar'].default_value = (0.005, 0.005, 0.01, 1)
    setp(br, 'Mortar Size', 0.04)
    nt.links.new(tc.outputs['Generated'], mp.inputs['Vector'])
    nt.links.new(mp.outputs['Vector'], br.inputs['Vector'])
    nt.links.new(br.outputs['Color'], bsdf.inputs['Base Color'])
    setp(bsdf, 'Metallic', 0.6)
    setp(bsdf, 'Roughness', 0.22)
    setp(bsdf, 'Specular IOR Level', 0.8)
    return m


def make_flag_material():
    """Bandeira azul com faixa inferior cyan emissiva (marco da missao)."""
    m = bpy.data.materials.new("Flag")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    setp(bsdf, 'Base Color', (0.03, 0.07, 0.30, 1))
    setp(bsdf, 'Roughness', 0.6)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Generated'], sep.inputs['Vector'])
    band = nt.nodes.new('ShaderNodeValToRGB')
    band.color_ramp.elements[0].position = 0.28
    band.color_ramp.elements[0].color = (1, 1, 1, 1)
    band.color_ramp.elements[1].position = 0.34
    band.color_ramp.elements[1].color = (0, 0, 0, 1)
    nt.links.new(sep.outputs['Z'], band.inputs['Fac'])
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (0.2, 0.85, 1.0, 1)
    em.inputs['Strength'].default_value = 6.0
    mix = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(band.outputs['Color'], mix.inputs['Fac'])
    nt.links.new(bsdf.outputs['BSDF'], mix.inputs[1])
    nt.links.new(em.outputs['Emission'], mix.inputs[2])
    nt.links.new(mix.outputs['Shader'], out.inputs['Surface'])
    return m


def _parabolic_dish(bm, center, radius, depth, forward, rings=12, seg=48):
    """Prato parabolico CONCAVO gerado por aneis (z = depth*(r/R)^2). A abertura
    aponta para 'forward'. Retorna (foco, [pontos de borda], centro_do_dorso) em
    coordenadas de construcao, para posicionar feed horn, tripe e nervuras."""
    center = Vector(center); forward = Vector(forward).normalized()
    rot = forward.to_track_quat('Z', 'Y').to_matrix().to_4x4()
    M = Matrix.Translation(center) @ rot

    def W(p):
        return (M @ Vector((p[0], p[1], p[2], 1.0))).to_3d()

    tmp = bmesh.new()
    cen = tmp.verts.new((0.0, 0.0, 0.0))
    rings_v = []
    for k in range(1, rings + 1):
        r = radius * k / rings
        z = depth * (k / rings) ** 2
        row = [tmp.verts.new((r * math.cos(2 * math.pi * s / seg),
                              r * math.sin(2 * math.pi * s / seg), z))
               for s in range(seg)]
        rings_v.append(row)
    first = rings_v[0]
    for s in range(seg):                     # cap central (triangulos)
        tmp.faces.new((cen, first[s], first[(s + 1) % seg]))
    for k in range(len(rings_v) - 1):        # quads entre aneis
        a, b = rings_v[k], rings_v[k + 1]
        for s in range(seg):
            s2 = (s + 1) % seg
            tmp.faces.new((a[s], a[s2], b[s2], b[s]))
    bmesh.ops.transform(tmp, matrix=M, space=Matrix.Identity(4), verts=tmp.verts)
    bmesh.ops.recalc_face_normals(tmp, faces=list(tmp.faces))
    merge_bm(bm, tmp)

    f = radius * radius / (4.0 * depth)      # distancia focal da parabola
    focus = W((0.0, 0.0, f))
    rim = [W((radius * math.cos(2 * math.pi * s / 12),
              radius * math.sin(2 * math.pi * s / 12), depth)) for s in range(12)]
    back_center = W((0.0, 0.0, -0.03))
    return focus, rim, back_center


def _solar_wing(sgn, inner_x, span_x, span_y, cols=6, rows=3, gap=0.05):
    """Uma asa de painel solar. Retorna (bm_estrutura, bm_celulas):
    estrutura = braco do corpo + spar + moldura (metal); celulas = grade cols x rows."""
    Y = Vector((0, 1, 0))
    z0 = 0.0
    frame = bmesh.new()
    cells = bmesh.new()
    cx0, far_x = inner_x, inner_x + span_x
    add_cylinder(frame, Vector((0.6 * sgn, 0, z0)), Vector((cx0 * sgn, 0, z0)), 0.06, 0.06, 8)   # braco
    add_cylinder(frame, Vector((cx0 * sgn, 0, z0)), Vector((far_x * sgn, 0, z0)), 0.045, 0.045, 6)  # spar
    fcx = (cx0 + far_x) / 2.0
    add_box(frame, Vector((fcx * sgn, 0, z0)),
            (span_x + 1.5 * gap, span_y + 1.5 * gap, 0.04), forward=Y, bevel=0.0)  # moldura
    cw = (span_x - (cols + 1) * gap) / cols
    ch = (span_y - (rows + 1) * gap) / rows
    for c in range(cols):
        for r in range(rows):
            px = cx0 + gap + (cw + gap) * c + cw / 2.0
            py = -span_y / 2.0 + gap + (ch + gap) * r + ch / 2.0
            add_box(cells, Vector((px * sgn, py, z0 + 0.05)), (cw, ch, 0.05), forward=Y, bevel=0.0)
    return frame, cells


def build_satellite():
    """Satelite de comunicacao em PARTES nomeadas (Collection 'Satelite'):
    Corpo, Modulo_Superior, Louvers_Termicos, Star_Tracker, Painel_Solar_Esquerdo/
    Direito, Antena_Parabolica, Alimentador, Antena_Mastro e Luzes."""
    O = Vector((0, 0, 0))
    X = Vector((1, 0, 0)); Y = Vector((0, 1, 0)); Z = Vector((0, 0, 1))
    LOC = (14.0, 34.0, 15.0)
    ROT = (math.radians(18), math.radians(-26), math.radians(12))
    COL = "Satelite"

    m_foil = make_metal("SatFoil", (0.86, 0.62, 0.20), 0.40, 1.0)
    m_panel = make_solar()
    m_dish = make_metal("SatDish", (0.86, 0.87, 0.90), 0.16, 0.6)
    m_metal = make_metal("SatMetal", (0.55, 0.57, 0.62), 0.30, 1.0)
    m_accent = make_metal("SatAccent", (0.80, 0.55, 0.16), 0.35, 1.0)
    m_light = make_emissive("SatLight", (0.3, 1.0, 0.4), 20.0)

    def part(name, layers, smooth):
        make_part("Satelite_" + name, layers, COL, smooth=smooth, loc=LOC, rot=ROT)

    # 1. Corpo (bus dourado, manta termica)
    bm = bmesh.new(); add_box(bm, O, (1.25, 1.70, 1.25), forward=Y, bevel=0.10)
    part("Corpo", [(bm, m_foil)], False)

    # 2. Modulo superior (eletronica)
    bm = bmesh.new(); add_box(bm, O + Z * 0.95, (0.72, 0.92, 0.55), forward=Y, bevel=0.06)
    part("Modulo_Superior", [(bm, m_metal)], False)

    # 3. Louvers termicos (radiador, face +Y)
    bm = bmesh.new()
    for i in range(4):
        add_box(bm, O + Y * 0.86 + Z * (-0.55 + i * 0.36), (1.05, 0.04, 0.16), forward=Y, bevel=0.0)
    part("Louvers_Termicos", [(bm, m_accent)], False)

    # 4. Star-tracker (sensor de estrelas)
    bm = bmesh.new(); add_box(bm, O + Z * 1.35 + X * 0.30, (0.22, 0.28, 0.32), forward=Y, bevel=0.03)
    part("Star_Tracker", [(bm, m_metal)], False)

    # 5/6. Paineis solares (uma asa = um objeto: moldura metal + grade de celulas)
    for sgn, nm in ((1, "Direito"), (-1, "Esquerdo")):
        frame, cells = _solar_wing(sgn, inner_x=1.55, span_x=3.0, span_y=1.7, cols=6, rows=3)
        part("Painel_Solar_" + nm, [(frame, m_metal), (cells, m_panel)], False)

    # 7. Antena parabolica (prato concavo + nervuras radiais + braco de suporte)
    dish_c = O + Y * (-1.25) + Z * 0.18
    R, depth = 1.0, 0.34
    bm_dish = bmesh.new()
    focus, rim, back_c = _parabolic_dish(bm_dish, dish_c, R, depth, forward=-Y)
    bm_rib = bmesh.new()
    add_cylinder(bm_rib, O + Y * (-0.85) + Z * 0.18, back_c, 0.09, 0.09, 10)   # braco/hub
    for p in rim:                                                              # nervuras
        add_cylinder(bm_rib, back_c, p, 0.02, 0.012, 5)
    part("Antena_Parabolica", [(bm_dish, m_dish), (bm_rib, m_metal)], True)

    # 8. Alimentador (feed horn no foco + tripe de sustentacao)
    bm = bmesh.new()
    add_cylinder(bm, Vector(focus), Vector(focus) + Y * 0.22, 0.05, 0.11, 12)
    for p in (rim[0], rim[4], rim[8]):
        add_cylinder(bm, p, Vector(focus), 0.014, 0.014, 4)
    part("Alimentador", [(bm, m_metal)], True)

    # 9. Mastro de antena (haste superior)
    bm = bmesh.new(); add_cylinder(bm, O + Z * 1.20, O + Z * 2.00, 0.02, 0.012, 6)
    part("Antena_Mastro", [(bm, m_metal)], True)

    # 10. Luzes de status (topo do mastro + foco da antena)
    bm = bmesh.new()
    add_sphere(bm, O + Z * 2.02, 0.05)
    add_sphere(bm, Vector(focus) + Y * 0.12, 0.05)
    part("Luzes", [(bm, m_light)], True)


def build_lander():
    """Foguete-lander em PARTES nomeadas (Collection 'Foguete'): Estagio_Descida,
    Corpo, Motor, Tanques, Pernas, Janelas, Aletas, Faixas e Antena_Luzes.
    Roteia a geometria em 'parts' = {parte: {material: bmesh}}."""
    parts = {}

    def bm(part, mat):
        return parts.setdefault(part, {}).setdefault(mat, bmesh.new())

    Z = Vector((0, 0, 1))
    ds_r, ds_h, ds_z = 1.35, 1.0, 0.85          # estagio de descida
    Cc = Z * ds_z
    body_r, body_bot, body_top = 0.92, 1.35, 3.30   # corpo do foguete
    nose_top = 4.45

    # --- Estagio_Descida (BASE robusta octogonal + saia + friso) ---
    add_cylinder(bm("Estagio_Descida", "foil"), Z * (ds_z - ds_h / 2), Z * (ds_z + ds_h / 2), ds_r, ds_r, segments=8)
    add_cylinder(bm("Estagio_Descida", "foil"), Z * 0.36, Z * 0.56, ds_r * 1.20, ds_r * 1.04, segments=8)
    add_cylinder(bm("Estagio_Descida", "accent"), Z * 0.55, Z * 0.63, ds_r * 1.07, ds_r * 1.07, segments=8)

    # --- Motor: sino grande + interior escuro + garganta + 4 verniers ---
    add_cylinder(bm("Motor", "metal"), Z * 0.40, Z * (-0.62), 0.30, 0.80, segments=24)
    add_cylinder(bm("Motor", "glass"), Z * 0.30, Z * (-0.42), 0.20, 0.54, segments=20)
    add_cylinder(bm("Motor", "metal"), Z * 0.42, Z * 0.30, 0.34, 0.30, segments=16)
    for k in range(4):
        ang = math.radians(45 + k * 90)
        d = Vector((math.cos(ang), math.sin(ang), 0.0))
        vt = d * (ds_r * 0.70) + Z * 0.34
        add_cylinder(bm("Motor", "metal"), vt, vt - Z * 0.22, 0.07, 0.11, segments=10)

    # --- Tanques: 3 tanques de combustivel ao redor da base ---
    for k in range(3):
        ang = math.radians(30 + k * 120)
        d = Vector((math.cos(ang), math.sin(ang), 0.0))
        tp = d * (ds_r * 1.02) + Z * 0.78
        add_sphere(bm("Tanques", "metal"), tp, 0.32)
        add_cylinder(bm("Tanques", "metal"), tp, tp - d * 0.28, 0.05, 0.05, 8)

    # --- Pernas: 4 pernas de pouso A-frame (stance largo) ---
    for k in range(4):
        ang = math.radians(45 + k * 90)
        d = Vector((math.cos(ang), math.sin(ang), 0.0))
        perp = Vector((-d.y, d.x, 0.0))
        pad = d * (ds_r * 1.95)                              # sapata bem aberta
        a1 = Cc + d * (ds_r * 0.92) + perp * 0.34 - Z * (ds_h * 0.35)
        a2 = Cc + d * (ds_r * 0.92) - perp * 0.34 - Z * (ds_h * 0.35)
        add_cylinder(bm("Pernas", "metal"), a1, pad + Z * 0.10, 0.075, 0.05, 8)   # montante A
        add_cylinder(bm("Pernas", "metal"), a2, pad + Z * 0.10, 0.075, 0.05, 8)   # montante A
        knee = Cc + d * (ds_r * 0.6) - Z * (ds_h * 0.05)
        add_cylinder(bm("Pernas", "metal"), knee, pad + Z * 0.14, 0.06, 0.05, 8)  # amortecedor
        add_cylinder(bm("Pernas", "metal"), pad, pad + Z * 0.13, 0.34, 0.34, 16)  # sapata
        add_cylinder(bm("Pernas", "accent"), pad, pad + Z * 0.05, 0.37, 0.37, 16) # rim da sapata

    # --- Corpo: transicao + cilindro branco + nariz conico ---
    add_cylinder(bm("Corpo", "metal"), Z * 1.32, Z * 1.62, ds_r * 0.82, body_r, segments=20)  # colar
    add_cylinder(bm("Corpo", "shell"), Z * body_bot, Z * body_top, body_r, body_r, segments=28)
    add_cylinder(bm("Corpo", "shell"), Z * body_top, Z * nose_top, body_r, 0.0, segments=28)

    # --- Janelas (vidro) em volta do corpo ---
    for k in range(3):
        ang = math.radians(60 + k * 60)
        wd = Vector((math.cos(ang), math.sin(ang), 0.0))
        wc = wd * body_r + Z * 2.55
        add_cylinder(bm("Janelas", "glass"), wc, wc + wd * 0.04, 0.13, 0.13, segments=14)

    # --- Aletas (fins) + luz na ponta ---
    for k in range(4):
        ang = math.radians(45 + k * 90)
        d = Vector((math.cos(ang), math.sin(ang), 0.0))
        add_box(bm("Aletas", "metal"), d * (body_r + 0.26) + Z * 1.95, (0.05, 0.7, 0.95), forward=d, bevel=0.02)
        add_sphere(bm("Aletas", "glow"), d * (body_r + 0.62) + Z * 1.52, 0.04)

    # --- Faixas de acento (laranja) ---
    add_cylinder(bm("Faixas", "accent"), Z * 1.33, Z * 1.46, ds_r * 1.005, ds_r * 1.005, segments=8)
    add_cylinder(bm("Faixas", "accent"), Z * 3.10, Z * 3.24, body_r * 1.02, body_r * 1.02, segments=28)

    # --- Antena_Luzes: antena no nariz + luzes de navegacao ---
    add_cylinder(bm("Antena_Luzes", "metal"), Z * nose_top, Z * (nose_top + 0.4), 0.02, 0.012, 6)
    add_sphere(bm("Antena_Luzes", "glow"), Z * (nose_top + 0.42), 0.05)
    for k in range(6):
        ang = math.radians(k * 60)
        lp = Cc + Vector((math.cos(ang) * ds_r * 1.02, math.sin(ang) * ds_r * 1.02, 0.18))
        add_sphere(bm("Antena_Luzes", "glow"), lp, 0.04)

    mats = {'foil': make_metal("LanderFoil", (0.86, 0.62, 0.20), 0.40, 1.0),
            'metal': make_metal("LanderMetal", (0.55, 0.57, 0.61), 0.32, 1.0),
            'accent': make_metal("LanderAccent", (0.85, 0.30, 0.05), 0.45, 0.3),
            'glow': make_emissive("LanderLight", (0.3, 1.0, 0.5), 18.0),
            'shell': make_shell("RocketShell", (0.88, 0.89, 0.92), rough=0.25),
            'glass': make_metal("RocketGlass", (0.02, 0.05, 0.12), 0.06, 0.0)}
    smooth = {'Estagio_Descida': False, 'Corpo': True, 'Motor': True, 'Tanques': True,
              'Pernas': True, 'Janelas': True, 'Aletas': True, 'Faixas': False,
              'Antena_Luzes': True}
    lx, ly = 8.0, 7.0
    LOC = (lx, ly, terrain_height(lx, ly))
    ROT = (0, 0, math.radians(18))
    for part_name, layers_dict in parts.items():
        layers = [(b, mats[mk]) for mk, b in layers_dict.items()]
        make_part("Foguete_" + part_name, layers, "Foguete",
                  smooth=smooth.get(part_name, True), loc=LOC, rot=ROT)


def _flag_poly(name, verts, faces, color, loc, rot, emit=0.6):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    ob = bpy.data.objects.new(name, me)
    # cor chapada com leve emissao para a bandeira ler bem sob qualquer luz
    m = bpy.data.materials.new(name + "_mat")
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    setp(bsdf, 'Base Color', (color[0], color[1], color[2], 1))
    setp(bsdf, 'Roughness', 0.55)
    setp(bsdf, 'Metallic', 0.0)
    setp(bsdf, 'Emission Color', (color[0], color[1], color[2], 1))
    setp(bsdf, 'Emission Strength', emit)
    ob.data.materials.append(m)
    link_obj(ob, "Bandeira")
    ob.location = loc
    ob.rotation_euler = rot
    return ob


def build_flag():
    """Bandeira do Brasil (campo verde, losango amarelo, circulo azul, faixa branca)
    montada por regioes geometricas coloridas, fincada num mastro."""
    fx, fy = 9.8, 5.2
    loc = (fx, fy, terrain_height(fx, fy))
    rot = (0, 0, math.radians(-28))

    # mastro
    bm = bmesh.new()
    add_cylinder(bm, Vector((0, 0, 0)), Vector((0, 0, 1.7)), 0.03, 0.025, 8)
    add_sphere(bm, Vector((0, 0, 1.72)), 0.05)
    pole = bm_to_object(bm, "Bandeira_Mastro", make_metal("FlagPole", (0.6, 0.62, 0.66), 0.3, 1.0),
                        smooth=True, collection="Bandeira")
    pole.location = loc
    pole.rotation_euler = rot

    # geometria do pano (plano X-Z, normal +Y; camadas empilhadas em +Y)
    x0, x1 = 0.07, 1.05
    z0, z1 = 1.02, 1.62
    W, H = x1 - x0, z1 - z0
    cx, cz = x0 + W / 2.0, z0 + H / 2.0

    GREEN = (0.00, 0.42, 0.12)
    YELLOW = (1.00, 0.82, 0.00)
    BLUE = (0.00, 0.07, 0.34)
    WHITE = (0.90, 0.92, 0.95)

    # campo verde
    _flag_poly("Bandeira_Campo_Verde",
               [(x0, 0.000, z0), (x1, 0.000, z0), (x1, 0.000, z1), (x0, 0.000, z1)],
               [(0, 1, 2, 3)], GREEN, loc, rot)

    # camadas coloridas: frente E verso do pano no MESMO objeto por regiao
    # (visivel de qualquer angulo, sem duplicatas ".001" no outliner)
    dx, dz = W * 0.42, H * 0.42
    r = H * 0.30
    n = 32
    bw = r * 0.98
    los_v, los_f = [], []
    cir_v, cir_f = [], []
    fai_v, fai_f = [], []
    for sy in (1.0, -1.0):
        y1, y2, y3 = 0.004 * sy, 0.008 * sy, 0.012 * sy
        # losango amarelo
        b = len(los_v)
        los_v += [(cx, y1, cz + dz), (cx + dx, y1, cz), (cx, y1, cz - dz), (cx - dx, y1, cz)]
        los_f.append((b, b + 1, b + 2, b + 3))
        # circulo azul (leque de triangulos)
        b = len(cir_v)
        cir_v.append((cx, y2, cz))
        for i in range(n):
            t = i / n * math.tau
            cir_v.append((cx + math.cos(t) * r, y2, cz + math.sin(t) * r * 0.92))
        cir_f += [(b, b + i + 1, b + (i + 1) % n + 1) for i in range(n)]
        # faixa branca
        b = len(fai_v)
        fai_v += [(cx - bw, y3, cz - r * 0.10), (cx + bw, y3, cz - r * 0.10),
                  (cx + bw, y3, cz - r * 0.34), (cx - bw, y3, cz - r * 0.34)]
        fai_f.append((b, b + 1, b + 2, b + 3))
    _flag_poly("Bandeira_Losango", los_v, los_f, YELLOW, loc, rot)
    _flag_poly("Bandeira_Circulo", cir_v, cir_f, BLUE, loc, rot)
    _flag_poly("Bandeira_Faixa", fai_v, fai_f, WHITE, loc, rot)


# --------------------------------------------------------------------------- #
# 5. Mundo: universo (estrelas + nebulosa)
# --------------------------------------------------------------------------- #
def build_world():
    world = bpy.data.worlds.new("Universe")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    L = nt.links.new
    out = nt.nodes.new('ShaderNodeOutputWorld')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mapping = nt.nodes.new('ShaderNodeMapping')
    mapping.inputs['Scale'].default_value = (1, 1, 1)
    L(tc.outputs['Generated'], mapping.inputs['Vector'])

    # estrelas: Voronoi (distancia) -> ColorRamp com pico branco em dist~0
    vor = nt.nodes.new('ShaderNodeTexVoronoi')
    vor.feature = 'F1'
    setp(vor, 'Scale', 18.0)
    L(mapping.outputs['Vector'], vor.inputs['Vector'])
    star = nt.nodes.new('ShaderNodeValToRGB')
    sc = star.color_ramp
    sc.elements[0].position = 0.0
    sc.elements[0].color = (1, 1, 1, 1)
    sc.elements[1].position = 0.04
    sc.elements[1].color = (0, 0, 0, 1)
    L(vor.outputs['Distance'], star.inputs['Fac'])

    # nebulosa: ruido suave azul/roxo + base quase preta
    neb = nt.nodes.new('ShaderNodeTexNoise')
    setp(neb, 'Scale', 1.8)
    setp(neb, 'Detail', 6.0)
    setp(neb, 'Roughness', 0.7)
    L(mapping.outputs['Vector'], neb.inputs['Vector'])
    nramp = nt.nodes.new('ShaderNodeValToRGB')
    nc = nramp.color_ramp
    nc.elements[0].position = 0.30
    nc.elements[0].color = (0.005, 0.006, 0.02, 1)   # fundo do espaco
    nc.elements[1].position = 0.85
    nc.elements[1].color = (0.10, 0.04, 0.22, 1)     # nebulosa roxa
    e = nc.elements.new(0.6); e.color = (0.02, 0.04, 0.12, 1)
    L(neb.outputs['Fac'], nramp.inputs['Fac'])

    bg_star = nt.nodes.new('ShaderNodeBackground')
    bg_star.inputs['Strength'].default_value = 3.0
    L(star.outputs['Color'], bg_star.inputs['Color'])
    bg_neb = nt.nodes.new('ShaderNodeBackground')
    bg_neb.inputs['Strength'].default_value = 0.18
    L(nramp.outputs['Color'], bg_neb.inputs['Color'])

    add = nt.nodes.new('ShaderNodeAddShader')
    L(bg_star.outputs['Background'], add.inputs[0])
    L(bg_neb.outputs['Background'], add.inputs[1])
    L(add.outputs['Shader'], out.inputs['Surface'])


# --------------------------------------------------------------------------- #
# 6. Luzes
# --------------------------------------------------------------------------- #
def _add_sun(name, energy, color, direction, angle_deg=0.6):
    d = bpy.data.lights.new(name, type='SUN')
    d.energy = energy
    d.color = color
    d.angle = math.radians(angle_deg)
    o = bpy.data.objects.new(name, d)
    o.rotation_euler = Vector(direction).normalized().to_track_quat('-Z', 'Y').to_euler()
    link_obj(o, "Iluminacao")
    return o


def build_lights():
    # KEY: Sol duro -- iluminacao principal (lado visivel da Terra + terreno)
    _add_sun("Sun", 4.6, (1.0, 0.96, 0.90), (0.35, 0.55, -0.75), angle_deg=0.5)

    # FILL: "Earthshine" azul suave vindo da direcao da Terra (levanta sombras)
    _add_sun("Earthshine", 0.7, (0.40, 0.58, 1.0), (-0.10, -0.90, -0.40))

    # RIM: contraluz fria atras dos robos para separar do fundo (silhueta)
    _add_sun("Rim", 1.6, (0.55, 0.70, 1.0), (-0.20, 0.85, -0.30))

    # FILL SUAVE proximo: area grande, fraca e fria, sobre os robos
    fa = bpy.data.lights.new("SoftFill", type='AREA')
    fa.shape = 'RECTANGLE'
    fa.size = 14.0
    fa.size_y = 8.0
    fa.energy = 220.0
    fa.color = (0.6, 0.72, 1.0)
    fo = bpy.data.objects.new("SoftFill", fa)
    fo.location = (-3.0, -6.0, 9.0)
    fo.rotation_euler = (Vector((3.5, 12.0, -9.0))).to_track_quat('-Z', 'Y').to_euler()
    link_obj(fo, "Iluminacao")


# --------------------------------------------------------------------------- #
# 7. Camera
# --------------------------------------------------------------------------- #
def build_camera():
    cam_data = bpy.data.cameras.new("Cam")
    cam_data.lens = 34.0
    cam = bpy.data.objects.new("Cam", cam_data)
    cam_loc = Vector((-2.4, -10.5, 2.0))      # leve angulo 3/4 (composicao em terco)
    target = Vector((0.4, 4.5, 2.9))
    cam.location = cam_loc
    cam.rotation_euler = (target - cam_loc).to_track_quat('-Z', 'Y').to_euler()

    # Profundidade de campo cinematografica: foco no robo da frente, fundo suave
    hero = Vector((0.8, 0.0, 1.0))
    cam_data.dof.use_dof = True
    cam_data.dof.focus_distance = (hero - cam_loc).length
    cam_data.dof.aperture_fstop = 3.5

    link_obj(cam, "Camera")
    scene.camera = cam


# --------------------------------------------------------------------------- #
# 8. Render (Cycles, com tentativa de GPU)
# --------------------------------------------------------------------------- #
def try_enable_gpu():
    addon = bpy.context.preferences.addons.get('cycles')
    if not addon:
        return None
    cprefs = addon.preferences
    for dtype in ('OPTIX', 'CUDA', 'HIP', 'ONEAPI', 'METAL'):
        try:
            cprefs.compute_device_type = dtype
        except Exception:
            continue
        try:
            cprefs.refresh_devices()
        except Exception:
            try:
                cprefs.get_devices()
            except Exception:
                pass
        devs = [d for d in cprefs.devices if getattr(d, 'type', None) == dtype]
        if devs:
            for d in cprefs.devices:
                d.use = (getattr(d, 'type', None) == dtype)
            return dtype
    return None


def configure_render():
    engines = available_engines()
    scene.render.engine = 'CYCLES' if 'CYCLES' in engines else engines[0]
    print("Engines disponiveis:", engines, "-> usando", scene.render.engine)

    if scene.render.engine == 'CYCLES':
        gpu = try_enable_gpu()
        scene.cycles.device = 'GPU' if gpu else 'CPU'
        print("Cycles device:", scene.cycles.device, "(", gpu, ")")
        scene.cycles.samples = SAMPLES
        scene.cycles.use_adaptive_sampling = True
        scene.cycles.adaptive_threshold = 0.01
        scene.cycles.use_denoising = True
        try:
            scene.cycles.denoiser = 'OPENIMAGEDENOISE'
        except Exception:
            pass
        scene.cycles.max_bounces = 12
        scene.cycles.caustics_reflective = False
        scene.cycles.caustics_refractive = False

    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.filepath = OUT_PATH
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_depth = '16'

    # Gerenciamento de cor profissional: AgX (alto alcance dinamico) + look "Punchy".
    try:
        scene.view_settings.view_transform = 'AgX'
        for look in ('AgX - Punchy', 'Punchy', 'AgX - Medium High Contrast'):
            try:
                scene.view_settings.look = look
                break
            except Exception:
                continue
    except Exception:
        try:
            scene.view_settings.view_transform = 'Filmic'
        except Exception:
            pass


# --------------------------------------------------------------------------- #
# Montagem
# --------------------------------------------------------------------------- #
def build_all():
    build_world()
    build_terrain()
    build_rocks()
    build_cave()
    build_earth()
    build_robots()
    build_satellite()
    build_lander()
    build_flag()
    build_lights()
    build_camera()


# --------------------------------------------------------------------------- #
# Serie de prints (camera multipla + wireframe/clay) para o documento
# --------------------------------------------------------------------------- #
def _aim(loc, target):
    cam = scene.camera
    cam.location = Vector(loc)
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()


def _set_view_transform(name):
    try:
        scene.view_settings.view_transform = name
    except Exception:
        pass


def _set_cycles(samples):
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = samples
    _set_view_transform('AgX')
    for look in ('AgX - Punchy', 'Punchy', 'AgX - Medium High Contrast'):
        try:
            scene.view_settings.look = look
            break
        except Exception:
            continue


def _set_workbench(mode):
    # SOLID para clay e tambem para wire (o tipo WIREFRAME nao renderiza headless;
    # o wireframe vem do modificador Wireframe aplicado em render_all_shots).
    scene.render.engine = 'BLENDER_WORKBENCH'
    _set_view_transform('Standard')
    try:
        scene.view_settings.look = 'None'
    except Exception:
        pass
    sh = scene.display.shading
    try:
        sh.light = 'STUDIO'
        sh.show_shadows = True
        sh.show_cavity = True
        sh.cavity_type = 'BOTH'
        sh.type = 'SOLID'
        sh.color_type = 'SINGLE'
        sh.background_type = 'VIEWPORT'
        if mode == 'wire':
            sh.single_color = (0.80, 0.88, 1.0)
            sh.background_color = (0.02, 0.02, 0.05)
        else:  # clay
            sh.single_color = (0.62, 0.63, 0.66)
            sh.background_color = (0.05, 0.05, 0.08)
    except Exception as e:
        print("Aviso workbench:", e)


def _add_wire_mods(thickness):
    mods = []
    for ob in scene.objects:
        if ob.type != 'MESH':
            continue
        m = ob.modifiers.new("WIRE", 'WIREFRAME')
        m.thickness = thickness
        m.use_replace = True
        m.use_even_offset = False
        mods.append((ob, m))
    return mods


def _remove_mods(mods):
    for ob, m in mods:
        try:
            ob.modifiers.remove(m)
        except Exception:
            pass


def _dof(fstop, loc, target):
    cam = scene.camera.data
    if fstop is None:
        cam.dof.use_dof = False
    else:
        cam.dof.use_dof = True
        cam.dof.aperture_fstop = fstop
        cam.dof.focus_distance = (Vector(target) - Vector(loc)).length


def render_all_shots(out_dir):
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir, exist_ok=True)
    th = terrain_height
    hero = (0.8, 0.3, 1.2)
    sat = (14.0, 34.0, 15.0)
    earth = (-7.0, 72.0, 30.0)

    # name, loc, target, lens, engine, fstop, samples
    shots = [
        ("01_hero",            (-2.4, -10.5, 2.0), (0.4, 4.5, 3.0),  34, 'cycles', 3.5, 170),
        ("02_panorama",        (-13.0, -15.0, 5.5), (2.0, 7.0, 1.5), 24, 'cycles', None, 120),
        ("03_robo_heroi",      (4.6, -5.2, 2.2),   (0.8, 0.6, 1.1),  38, 'cycles', 2.8, 150),
        ("04_robo_lateral",    (-3.8, -1.0, 1.0),  (0.8, 0.6, 1.1),  42, 'cycles', 2.8, 130),
        ("05_robo_visor",      (1.9, -3.2, 1.7),   (1.0, -0.3, 1.25), 65, 'cycles', 2.5, 150),
        ("06_satelite",        (20.0, 24.0, 11.0), sat,              55, 'cycles', None, 130),
        ("07_satelite_paineis", (10.0, 28.0, 24.0), sat,             50, 'cycles', 3.0, 130),
        ("08_foguete",         (2.5, 0.0, 3.2),    (8.0, 7.0, 2.6),  30, 'cycles', None, 130),
        ("09_foguete_detalhe", (12.5, 3.0, 1.4),   (8.0, 7.0, 1.0),  42, 'cycles', 4.0, 130),
        ("10_bandeira",        (12.6, 2.4, 1.7),   (9.8, 5.2, 1.35), 55, 'cycles', 2.8, 130),
        ("11_caverna",         (-3.5, 5.0, 4.8),   (0.4, 9.6, -0.4), 35, 'cycles', None, 130),
        ("12_terra",           (-3.0, -6.0, 2.6),  earth,            95, 'cycles', None, 140),
        ("13_orbital_topo",    (2.0, 8.0, 28.0),   (2.0, 8.0, 0.0),  40, 'cycles', None, 120),
        ("14_wireframe_cena",  (-11.0, -14.0, 6.5), (2.0, 7.0, 1.0), 28, 'wire',   None, 0),
        ("15_clay_robo",       (4.6, -5.2, 2.2),   hero,             38, 'clay',   None, 0),
        ("16_wireframe_robo",  (4.6, -5.2, 2.2),   hero,             38, 'wire',   None, 0),
    ]
    only = set(ONLY.split(",")) if ONLY else None
    done = 0
    for (name, loc, target, lens, engine, fstop, samples) in shots:
        if only and name not in only:
            continue
        scene.camera.data.lens = lens
        _aim(loc, target)
        wire_mods = None
        if engine == 'cycles':
            _set_cycles(samples)
            _dof(fstop, loc, target)
        elif engine == 'wire':
            scene.camera.data.dof.use_dof = False
            _set_workbench('wire')
            wire_mods = _add_wire_mods(0.035 if 'cena' in name else 0.012)
        else:  # clay
            scene.camera.data.dof.use_dof = False
            _set_workbench('clay')
        path = os.path.join(out_dir, name + ".png")
        scene.render.filepath = path
        print("Render shot ->", path, "(", engine, ")")
        bpy.ops.render.render(write_still=True)
        if wire_mods:
            _remove_mods(wire_mods)
        done += 1
    print("OK. %d prints salvos em %s" % (done, out_dir))


def _build_one_spider(collection="WebSpider", emit=6.0):
    """Constroi UMA aranha centrada (origem), em objetos por PARTE, na coleção dada."""
    parts = {}
    build_spider(parts, 0.0, 0.0, math.radians(90), s=1.3, phase=0)
    mats = {
        'shell':  make_shell("ShellWhite", (0.86, 0.88, 0.92), rough=0.22),
        'carbon': make_metal("Carbon", (0.035, 0.040, 0.050), 0.34, 0.3),
        'glass':  make_metal("Visor", (0.010, 0.012, 0.020), 0.05, 0.0),
        'accent': make_metal("Anodized", (0.0, 0.45, 0.50), 0.30, 1.0),
        'glow':   make_emissive("Glow", (0.20, 0.85, 1.0), emit),
    }
    for part_name, layers_dict in parts.items():
        layers = [(b, mats[mk]) for mk, b in layers_dict.items()]
        make_part("Aranha_" + part_name, layers, collection, smooth=True)


def export_web_model(path):
    """Constroi UMA aranha centrada e exporta em .glb para o visualizador 3D web."""
    _build_one_spider("WebSpider")
    vl = bpy.context.view_layer
    for ob in bpy.data.objects:
        ob.select_set(False)
    for ob in get_collection("WebSpider").objects:
        ob.select_set(True)
        vl.objects.active = ob
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True)
    print("GLB exportado:", path)


def _scene_bbox_mesh():
    mn = Vector((1e9, 1e9, 1e9))
    mx = Vector((-1e9, -1e9, -1e9))
    for o in scene.objects:
        if o.type != 'MESH':
            continue
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            mn = Vector((min(mn.x, w.x), min(mn.y, w.y), min(mn.z, w.z)))
            mx = Vector((max(mx.x, w.x), max(mx.y, w.y), max(mx.z, w.z)))
    return mn, mx


def render_solo(kind, out_dir):
    """Breakdown de um objeto: render final + clay + wireframe, isolado."""
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    if kind == 'aranha':
        _build_one_spider("Aranha")
    elif kind == 'foguete':
        build_lander()
    elif kind == 'satelite':
        build_satellite()
    elif kind == 'bandeira':
        build_flag()
    else:
        raise ValueError("kind invalido: " + kind)

    # fundo neutro escuro
    w = bpy.data.worlds.new("BG")
    scene.world = w
    w.use_nodes = True
    bgn = next(n for n in w.node_tree.nodes if n.type == 'BACKGROUND')
    bgn.inputs['Color'].default_value = (0.02, 0.025, 0.04, 1)
    bgn.inputs['Strength'].default_value = 0.5
    build_lights()

    # camera enquadrando a bbox dos modelos (atualiza matrizes antes!)
    bpy.context.view_layer.update()
    mn, mx = _scene_bbox_mesh()
    center = (mn + mx) / 2.0
    size = (mx - mn).length
    cam_data = bpy.data.cameras.new("CamSolo")
    cam_data.lens = 55
    cam = bpy.data.objects.new("CamSolo", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    dirv = Vector((1.0, -1.0, 0.55)).normalized()
    cam.location = center + dirv * size * 1.15
    cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler()

    scene.render.resolution_x, scene.render.resolution_y = 1400, 1050
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    base = os.path.join(out_dir, kind)

    # 1) final (Cycles)
    gpu = try_enable_gpu()
    scene.cycles.device = 'GPU' if gpu else 'CPU'
    _set_cycles(110)
    scene.cycles.use_denoising = True
    scene.render.filepath = base + "_final.png"
    print("Solo final ->", scene.render.filepath)
    bpy.ops.render.render(write_still=True)

    # 2) clay (Workbench solid)
    _set_workbench('clay')
    scene.render.filepath = base + "_clay.png"
    bpy.ops.render.render(write_still=True)

    # 3) wireframe (Workbench solid + modificador Wireframe)
    _set_workbench('wire')
    mods = _add_wire_mods(max(0.006, size * 0.004))
    scene.render.filepath = base + "_wire.png"
    bpy.ops.render.render(write_still=True)
    _remove_mods(mods)
    print("Breakdown '%s' salvo em %s" % (kind, out_dir))


def main():
    if SOLO:
        render_solo(SOLO, SHOTS_DIR or os.path.join(HERE, "docs", "prints", "modelagem"))
        return
    if EXPORT_GLB:
        export_web_model(EXPORT_GLB)
        return
    build_all()
    configure_render()
    bpy.data.orphans_purge(do_recursive=True)

    if BLEND_PATH:
        bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
        print("Salvo .blend em", BLEND_PATH)

    if SHOTS_DIR:
        render_all_shots(SHOTS_DIR)
        return

    print("Renderizando ->", OUT_PATH)
    bpy.ops.render.render(write_still=True)
    print("OK. Render salvo em", OUT_PATH)


main()
