"""Step 1 smoke test only: prove Blender + Cycles + GPU passthrough works in
this Docker/WSL2 environment before porting the real massing geometry.
Renders one red cube on a plane and writes a PNG to the path given after `--`.

Run via: blender --background --factory-startup --python blender_smoke_test.py -- <output_path>
"""

import math
import sys

import bpy

output_path = sys.argv[sys.argv.index("--") + 1]

bpy.ops.wm.read_factory_settings(use_empty=True)

bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 1))
cube = bpy.context.active_object
mat = bpy.data.materials.new(name="TestRed")
mat.use_nodes = True
mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.8, 0.1, 0.1, 1.0)
cube.data.materials.append(mat)

bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0))

sun_data = bpy.data.lights.new(name="Sun", type="SUN")
sun_data.energy = 3.0
sun_obj = bpy.data.objects.new(name="Sun", object_data=sun_data)
bpy.context.collection.objects.link(sun_obj)
sun_obj.rotation_euler = (math.radians(45), 0, math.radians(45))

cam_data = bpy.data.cameras.new("Camera")
cam_obj = bpy.data.objects.new("Camera", cam_data)
bpy.context.collection.objects.link(cam_obj)
cam_obj.location = (5, -5, 4)
cam_obj.rotation_euler = (math.radians(60), 0, math.radians(45))
bpy.context.scene.camera = cam_obj

scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = 64
scene.cycles.use_denoising = True
scene.render.resolution_x = 512
scene.render.resolution_y = 512
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = output_path

device_used = "CPU (fallback)"
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    found = False
    for device_type in ("OPTIX", "CUDA"):
        prefs.compute_device_type = device_type
        prefs.get_devices()
        gpu_devices = [d for d in prefs.devices if d.type == device_type]
        if gpu_devices:
            for d in prefs.devices:
                d.use = d.type == device_type
            scene.cycles.device = "GPU"
            device_used = f"GPU ({device_type}, {len(gpu_devices)} device(s))"
            found = True
            break
    if not found:
        scene.cycles.device = "CPU"
except Exception as exc:
    print(f"GPU_SETUP_ERROR: {exc}")
    scene.cycles.device = "CPU"

print(f"CYCLES_DEVICE: {device_used}")
bpy.ops.render.render(write_still=True)
print("RENDER_OK")
