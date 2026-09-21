"""Blender/Cycles massing renderer, ported from the Three.js version
(frontend/massing_3d.py):
  Step 2 — volume + roof shapes + per-style material colors.
  Step 3 — construction-phase animation (foundation, one reveal per floor,
  roof), baked as a glTF animation for <model-viewer>, replacing the old
  clip-plane trick since it doesn't survive a glTF export.
  Step 4 (this revision) — HDRI environment lighting, real recessed window
  openings + a ground-floor door (boolean-cut, not a texture), and a small
  garden (path/hedges/trees), each wired into the two new construction phases
  ("Second oeuvre" and "Finitions") this step adds.

Deliberately NOT yet included: balconies, pilotis-side windows, back/far-side
window openings (only the two faces the camera actually sees are cut — see
the note above the floor-slice loop below, now a real limitation since the
model is orbitable, unlike the original fixed-camera Three.js hero shot).

Run via:
    blender --background --factory-startup --python scene_builder.py -- \
        <brief_json_path> <output_png_path> <output_glb_path>
"""

import json
import math
import os
import sys

import bmesh
import bpy

args = sys.argv[sys.argv.index("--") + 1 :]
brief_path, output_png_path, output_glb_path = args[0], args[1], args[2]

with open(brief_path, encoding="utf-8") as f:
    brief = json.load(f)

LENGTH = float(brief["footprint_length_m"])
WIDTH = float(brief["footprint_width_m"])
FLOORS = int(brief["floors"])
FLOOR_H = float(brief.get("floor_height_m", 3.0))
TOTAL_H = FLOORS * FLOOR_H
ROOF_TYPE = str(brief.get("roof_type", "plat"))
STYLE = str(brief.get("architectural_style", "contemporain")).lower()
FRAMES_PER_PHASE = 15

# Same 4 real, documented architectural movements as massing_3d.py — kept in
# sync deliberately (a style added there must be added here too).
STYLE_PRESETS = {
    "haussmannien": {"wall": (0.90, 0.87, 0.78), "roof": (0.24, 0.27, 0.31), "pilotis": False},
    "moderniste": {"wall": (0.95, 0.94, 0.91), "roof": (0.79, 0.79, 0.76), "pilotis": True},
    "contemporain": {"wall": (0.80, 0.78, 0.73), "roof": (0.29, 0.31, 0.33), "pilotis": False},
    "traditionnel": {"wall": (0.85, 0.72, 0.47), "roof": (0.63, 0.31, 0.24), "pilotis": False},
}
style = STYLE_PRESETS.get(STYLE, STYLE_PRESETS["contemporain"])
BASE_Y = FLOOR_H * 0.55 if style["pilotis"] else 0.0


def srgb_to_linear(c):
    """Every color constant in this file is written as an sRGB value (same
    convention as the '#rrggbb' hex codes in the Three.js version this ports
    from). Blender's Base Color input expects LINEAR values — feeding it sRGB
    directly renders everything much brighter/washed out than intended."""
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def make_material(name, srgb_color, roughness=0.85):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*[srgb_to_linear(c) for c in srgb_color], 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


def new_box(size_xyz, location, material=None):
    bpy.ops.mesh.primitive_cube_add(size=1)
    obj = bpy.context.active_object
    obj.scale = size_xyz
    obj.location = location
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if material is not None:
        obj.data.materials.append(material)
    return obj


def cut_windows(floor_obj, span, axis, face_pos, floor_base_z, has_door, glass_mat, door_mat):
    """Cuts real recessed window openings (and, if has_door, a door opening)
    into floor_obj's given face via a boolean difference — not a texture, so
    the relief actually catches light — then fills each opening with a glass
    (or door) panel. axis='x' cuts a front/back wall (openings spaced along
    X); axis='y' cuts a side wall (openings spaced along Y). floor_base_z is
    the world Z of this floor's own bottom (its sill/door reference point)."""
    win_count = max(2, round(span / 2.5))
    margin = span * 0.08
    usable = span - margin * 2
    gap = usable / win_count
    win_w = gap * 0.55
    win_h = FLOOR_H * 0.5
    win_sill = floor_base_z + FLOOR_H * 0.28
    cut_depth = 0.4
    door_w = 1.0
    door_h = min(FLOOR_H * 0.78, 2.2)
    door_center_index = win_count // 2

    cutters = []
    for i in range(win_count):
        center = -span / 2 + margin + gap * (i + 0.5)
        is_door_slot = has_door and i == door_center_index
        if is_door_slot:
            w, h, z = door_w, door_h, floor_base_z + door_h / 2
        else:
            w, h, z = win_w, win_h, win_sill + win_h / 2

        if axis == "x":
            loc, size = (center, face_pos, z), (w, cut_depth, h)
            panel_size, panel_loc = (w * 0.9, 0.02, h * 0.92), (center, face_pos, z)
        else:
            loc, size = (face_pos, center, z), (cut_depth, w, h)
            panel_size, panel_loc = (0.02, w * 0.9, h * 0.92), (face_pos, center, z)

        cutters.append(new_box(size, loc))
        panel = new_box(panel_size, panel_loc, door_mat if is_door_slot else glass_mat)
        assign_phase(panel, SECOND_OEUVRE_PHASE)

    bpy.ops.object.select_all(action="DESELECT")
    for c in cutters:
        c.select_set(True)
    bpy.context.view_layer.objects.active = cutters[0]
    bpy.ops.object.join()
    cutter_obj = bpy.context.active_object

    bpy.context.view_layer.objects.active = floor_obj
    mod = floor_obj.modifiers.new(name="WindowCut", type="BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = cutter_obj
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter_obj, do_unlink=True)


bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# ---- phase groups: one Empty per construction phase, keyframed further down.
# An object parented to a phase's Empty inherits its scale, so animating the
# Empty from 0 to 1 makes everything in that phase pop in together — this
# replaces the old Three.js clip-plane trick, which has no glTF equivalent.
phase_labels = (
    ["Fondations"]
    + [f"Etage {i}" for i in range(1, FLOORS + 1)]
    + ["Charpente et toiture", "Second oeuvre (facades, menuiseries)", "Finitions (amenagements exterieurs)"]
)
phase_empties = []
for label in phase_labels:
    empty = bpy.data.objects.new(f"Phase_{label}", None)
    bpy.context.collection.objects.link(empty)
    phase_empties.append(empty)


def assign_phase(obj, phase_index):
    obj.parent = phase_empties[phase_index]


ROOF_PHASE = 1 + FLOORS
SECOND_OEUVRE_PHASE = ROOF_PHASE + 1
FINITIONS_PHASE = ROOF_PHASE + 2


# ---- ground (always visible — not part of any construction phase) ----
bpy.ops.mesh.primitive_plane_add(size=max(LENGTH, WIDTH) * 6)
ground = bpy.context.active_object
ground.data.materials.append(make_material("Ground", (0.55, 0.62, 0.42), roughness=1.0))

# ---- foundation slab (phase 0) ----
foundation_mat = make_material("Foundation", (0.58, 0.58, 0.55), roughness=1.0)
foundation = new_box((LENGTH * 1.06, WIDTH * 1.06, 0.18), (0, 0, 0.09), foundation_mat)
assign_phase(foundation, 0)

wall_mat = make_material("Wall", style["wall"])

# ---- pilotis (moderniste): part of the foundation phase, like massing_3d.py's
# foundationObjects list — they support the structure from the ground up ----
if style["pilotis"]:
    pilotis_mat = make_material("Pilotis", (0.88, 0.87, 0.86), roughness=0.4)
    col_count = max(4, round(LENGTH / 2.5))
    for side in (WIDTH / 2 - 0.4, -WIDTH / 2 + 0.4):
        for i in range(col_count):
            x = -LENGTH / 2 + (LENGTH / max(1, col_count - 1)) * i
            bpy.ops.mesh.primitive_cylinder_add(radius=0.17, depth=BASE_Y, location=(x, side, BASE_Y / 2))
            col = bpy.context.active_object
            col.data.materials.append(pilotis_mat)
            assign_phase(col, 0)

# ---- building body, one slice per floor (phases 1..FLOORS), with real
# recessed window openings (and a ground-floor door) cut into the two faces
# actually visible from the camera — the back and far side stay plain, a
# known limitation now that the model is orbitable (glTF/model-viewer),
# unlike the original fixed-camera Three.js hero shot. ----
glass_mat = make_material("Glass", (0.75, 0.85, 0.90), roughness=0.05)
glass_mat.node_tree.nodes["Principled BSDF"].inputs["Transmission Weight"].default_value = 0.9
door_mat = make_material("Door", (0.30, 0.20, 0.14), roughness=0.6)

for i in range(FLOORS):
    floor_base_z = BASE_Y + i * FLOOR_H
    floor_obj = new_box((LENGTH, WIDTH, FLOOR_H), (0, 0, floor_base_z + FLOOR_H / 2), wall_mat)
    assign_phase(floor_obj, 1 + i)
    cut_windows(floor_obj, LENGTH, "x", -WIDTH / 2, floor_base_z, has_door=(i == 0), glass_mat=glass_mat, door_mat=door_mat)
    cut_windows(floor_obj, WIDTH, "y", LENGTH / 2, floor_base_z, has_door=False, glass_mat=glass_mat, door_mat=door_mat)

# ---- roof (phase ROOF_PHASE) ----
roof_mat = make_material("Roof", style["roof"], roughness=0.6)
roof_y = BASE_Y + TOTAL_H

if "plat" in ROOF_TYPE:
    parapet_h = FLOOR_H * 0.22
    parapet_t = min(LENGTH, WIDTH) * 0.04
    outer_l, outer_w = LENGTH * 1.03, WIDTH * 1.03

    deck = new_box((outer_l, outer_w, 0.06), (0, 0, roof_y + 0.03), make_material("RoofDeck", (0.55, 0.55, 0.53), roughness=0.9))
    assign_phase(deck, ROOF_PHASE)

    for w, d, x, y in (
        (outer_l, parapet_t, 0, outer_w / 2 - parapet_t / 2),
        (outer_l, parapet_t, 0, -outer_w / 2 + parapet_t / 2),
        (parapet_t, outer_w, outer_l / 2 - parapet_t / 2, 0),
        (parapet_t, outer_w, -outer_l / 2 + parapet_t / 2, 0),
    ):
        wall = new_box((w, d, parapet_h), (x, y, roof_y + parapet_h / 2), roof_mat)
        assign_phase(wall, ROOF_PHASE)

elif "quatre" in ROOF_TYPE:
    max_dim = max(LENGTH, WIDTH)
    bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=max_dim * 0.62, depth=FLOOR_H * 1.1, location=(0, 0, roof_y + FLOOR_H * 0.55))
    roof = bpy.context.active_object
    # Order matters: bake the 45deg rotation (diamond -> axis-aligned square)
    # BEFORE the non-uniform length/width scale, otherwise transform_apply's
    # scale-then-rotate composition stretches the still-diamond-oriented mesh
    # diagonally instead of along length/width, producing a distorted roof.
    roof.rotation_euler = (0, 0, math.radians(45))
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    roof.scale = (LENGTH / max_dim, WIDTH / max_dim, 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    roof.data.materials.append(roof_mat)
    assign_phase(roof, ROOF_PHASE)

else:  # "deux pans" — gable roof, a triangular prism running along LENGTH
    peak_h = FLOOR_H * 1.1
    bm = bmesh.new()
    verts = [
        bm.verts.new((-LENGTH / 2, -WIDTH / 2, roof_y)),
        bm.verts.new((-LENGTH / 2, 0, roof_y + peak_h)),
        bm.verts.new((-LENGTH / 2, WIDTH / 2, roof_y)),
        bm.verts.new((LENGTH / 2, -WIDTH / 2, roof_y)),
        bm.verts.new((LENGTH / 2, 0, roof_y + peak_h)),
        bm.verts.new((LENGTH / 2, WIDTH / 2, roof_y)),
    ]
    bm.faces.new((verts[0], verts[1], verts[4], verts[3]))  # slope A
    bm.faces.new((verts[1], verts[2], verts[5], verts[4]))  # slope B
    bm.faces.new((verts[0], verts[3], verts[5], verts[2]))  # underside
    bm.faces.new((verts[0], verts[2], verts[1]))  # front gable end
    bm.faces.new((verts[3], verts[4], verts[5]))  # back gable end
    mesh = bpy.data.meshes.new("GableRoof")
    bm.to_mesh(mesh)
    bm.free()
    roof = bpy.data.objects.new("GableRoof", mesh)
    bpy.context.collection.objects.link(roof)
    roof.data.materials.append(roof_mat)
    assign_phase(roof, ROOF_PHASE)

# ---- garden (finitions phase): entrance path + a few trees + hedges, on the
# front side (-Y) where the door is ----
path_mat = make_material("Path", (0.79, 0.76, 0.69), roughness=0.95)
path_depth = max(LENGTH, WIDTH) * 0.8
path = new_box((LENGTH * 0.18, path_depth, 0.05), (0, -WIDTH / 2 - path_depth / 2, 0.025), path_mat)
assign_phase(path, FINITIONS_PHASE)

hedge_mat = make_material("Hedge", (0.25, 0.42, 0.20), roughness=1.0)
hedge_y = -WIDTH / 2 - path_depth * 0.3
for side in (1, -1):
    hedge = new_box((0.5, path_depth * 0.5, 0.55), (side * (LENGTH * 0.09 + 0.4), hedge_y, 0.275), hedge_mat)
    assign_phase(hedge, FINITIONS_PHASE)

trunk_mat = make_material("Trunk", (0.42, 0.29, 0.20), roughness=1.0)
canopy_mat = make_material("Canopy", (0.29, 0.49, 0.25), roughness=0.9)
tree_scale = max(0.9, min(LENGTH, WIDTH) * 0.12)
tree_positions = (
    (LENGTH / 2 + tree_scale * 2.2, -tree_scale * 1.8),
    (-LENGTH / 2 - tree_scale * 2.0, tree_scale * 1.5),
)
for tx, ty in tree_positions:
    bpy.ops.mesh.primitive_cylinder_add(radius=0.12 * tree_scale, depth=1.4 * tree_scale, location=(tx, ty, 0.7 * tree_scale))
    trunk = bpy.context.active_object
    trunk.data.materials.append(trunk_mat)
    assign_phase(trunk, FINITIONS_PHASE)
    for j in range(3):
        bpy.ops.mesh.primitive_cone_add(
            radius1=(1.1 - j * 0.18) * tree_scale, depth=1.3 * tree_scale, location=(tx, ty, (1.5 + j * 0.85) * tree_scale)
        )
        canopy = bpy.context.active_object
        canopy.data.materials.append(canopy_mat)
        assign_phase(canopy, FINITIONS_PHASE)

# ---- bake the phase reveal animation onto each phase Empty's scale ----
# CONSTANT interpolation set as the default for new keyframes (not fixed up
# afterward via action.fcurves): Blender 4.4+'s reworked "layered actions"
# data model no longer exposes a flat action.fcurves list directly.
bpy.context.preferences.edit.keyframe_new_interpolation_type = "CONSTANT"
scene.frame_start = 0
scene.frame_end = FRAMES_PER_PHASE * len(phase_empties)
for i, empty in enumerate(phase_empties):
    reveal_frame = i * FRAMES_PER_PHASE
    empty.scale = (0.0001, 0.0001, 0.0001)  # not exactly 0: some glTF viewers treat a literal 0 scale as invalid
    empty.keyframe_insert(data_path="scale", frame=max(0, reveal_frame - 1))
    empty.scale = (1, 1, 1)
    empty.keyframe_insert(data_path="scale", frame=reveal_frame)

# ---- world background: real HDRI environment (replaces the flat sky color
# from step 2) for realistic ambient light and reflections on glass/metal ----
world = bpy.data.worlds.new("Sky")
world.use_nodes = True
nodes = world.node_tree.nodes
env_tex = nodes.new("ShaderNodeTexEnvironment")
hdri_path = os.environ.get("EXTERIOR_HDRI_PATH", "/opt/assets/sky.hdr")
env_tex.image = bpy.data.images.load(hdri_path)
mapping = nodes.new("ShaderNodeMapping")
# Rotate the HDRI so its own bright sun disc lines up with our raking-light
# azimuth below — otherwise the HDRI's real sun and our Sun lamp fight each
# other and the shading reads flat again (same failure mode as step 2's
# front-lit bug, just from a second light source this time).
mapping.inputs["Rotation"].default_value = (0, 0, math.radians(125))
tex_coord = nodes.new("ShaderNodeTexCoord")
world.node_tree.links.new(tex_coord.outputs["Generated"], mapping.inputs["Vector"])
world.node_tree.links.new(mapping.outputs["Vector"], env_tex.inputs["Vector"])
world.node_tree.links.new(env_tex.outputs["Color"], nodes["Background"].inputs["Color"])
nodes["Background"].inputs["Strength"].default_value = 0.8
scene.world = world

# ---- sun (in addition to the HDRI's own sky light, for crisp cast shadows —
# HDRI alone at 1k resolution gives soft/noisy shadows) ----
sun_data = bpy.data.lights.new(name="Sun", type="SUN")
sun_data.energy = 3.0
sun_obj = bpy.data.objects.new(name="Sun", object_data=sun_data)
bpy.context.collection.objects.link(sun_obj)
# Azimuth deliberately offset ~90deg from the camera's own azimuth (see camera
# setup below) for clear side/raking light — sun nearly behind the camera
# produces flat, shadowless faces that made a correctly-built hip roof read
# as a sunken hole instead of a raised peak (diagnosed by comparing renders).
sun_obj.rotation_euler = (math.radians(50), 0, math.radians(125))

# ---- camera: 3/4 angled view, framed on an empty at the building's center ----
target = bpy.data.objects.new("Target", None)
target.location = (0, 0, BASE_Y + TOTAL_H / 2)
bpy.context.collection.objects.link(target)

max_dim = max(LENGTH, WIDTH, BASE_Y + TOTAL_H) * 2.3
cam_data = bpy.data.cameras.new("Camera")
cam_obj = bpy.data.objects.new("Camera", cam_data)
bpy.context.collection.objects.link(cam_obj)
cam_obj.location = (max_dim, -max_dim, max_dim * 0.7)
constraint = cam_obj.constraints.new(type="TRACK_TO")
constraint.target = target
constraint.track_axis = "TRACK_NEGATIVE_Z"
constraint.up_axis = "UP_Y"
scene.camera = cam_obj

# ---- render a static Cycles hero shot of the COMPLETED building ----
scene.frame_set(scene.frame_end)

# Keep Blender's default AgX view transform: a strong outdoor sun (physically
# realistic) blows highlights out to flat white under "Standard" (no highlight
# rolloff at all) — AgX compresses that gracefully instead, which is why
# archviz renders use it rather than because it looks "nicer".
scene.render.engine = "CYCLES"
scene.cycles.samples = 128
scene.cycles.use_denoising = True
scene.render.resolution_x = 1024
scene.render.resolution_y = 768
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = output_png_path

device_used = "CPU (fallback)"
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for device_type in ("OPTIX", "CUDA"):
        prefs.compute_device_type = device_type
        prefs.get_devices()
        gpu_devices = [d for d in prefs.devices if d.type == device_type]
        if gpu_devices:
            for d in prefs.devices:
                d.use = d.type == device_type
            scene.cycles.device = "GPU"
            device_used = f"GPU ({device_type}, {len(gpu_devices)} device(s))"
            break
    else:
        scene.cycles.device = "CPU"
except Exception as exc:
    print(f"GPU_SETUP_ERROR: {exc}")
    scene.cycles.device = "CPU"

print(f"CYCLES_DEVICE: {device_used}")
bpy.ops.render.render(write_still=True)
print("RENDER_OK")

# ---- export the full animated model as glTF for <model-viewer> ----
# export_animation_mode="SCENE" (not the default "ACTIONS") is required here:
# each phase Empty has its own separate Action, and the default mode exports
# one glTF animation PER action — model-viewer only plays the first one by
# default, silently dropping every other phase. "SCENE" bakes every action in
# the scene's frame range into a single combined, scrubbable animation.
bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(
    filepath=output_glb_path,
    export_format="GLB",
    use_selection=True,
    export_animations=True,
    export_animation_mode="SCENE",
    # SCENE mode still splits into one animation per object unless this is
    # off — found by introspecting the operator's RNA properties after
    # export_animation_mode alone produced 5 separate animations instead of
    # one combined, scrubbable timeline.
    export_anim_scene_split_object=False,
)
print(f"PHASE_LABELS: {json.dumps(phase_labels)}")
print(f"ANIMATION_FPS: {scene.render.fps}")
print(f"ANIMATION_END_FRAME: {scene.frame_end}")
print("EXPORT_OK")
