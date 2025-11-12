import bpy, json, mathutils, os, random
from math import isfinite

# --- helpers -----------------------------------------------------------------

def _clamp01(x):
    try:
        x = float(x)
    except Exception:
        return 0.0
    if not isfinite(x):
        return 0.0
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)

def _round_rgb(rgb, ndigits=6):
    r, g, b = rgb
    return (round(_clamp01(r), ndigits),
            round(_clamp01(g), ndigits),
            round(_clamp01(b), ndigits))

def _color_from_principled(mat):
    # Try to read the Principled BSDF "Base Color"
    if not mat or not getattr(mat, "use_nodes", False) or not mat.node_tree:
        return None
    # Find first Principled BSDF
    for node in mat.node_tree.nodes:
        if node.bl_idname == "ShaderNodeBsdfPrincipled":
            base = node.inputs.get("Base Color")
            if base and base.default_value is not None:
                # default_value is RGBA
                col = tuple(base.default_value)
                if len(col) >= 3:
                    return col[0], col[1], col[2]
    return None

def _color_from_diffuse(mat):
    # Legacy / non-node materials or viewport-ish color on material
    if not mat:
        return None
    dc = getattr(mat, "diffuse_color", None)
    if dc is None:
        return None
    # diffuse_color is RGBA in modern Blender; use RGB part
    if len(dc) >= 3:
        return dc[0], dc[1], dc[2]
    return None

def _color_from_object(obj):
    # Fallback to object viewport color if present
    oc = getattr(obj, "color", None) or getattr(obj, "display_color", None)
    if oc and len(oc) >= 3:
        return oc[0], oc[1], oc[2]
    return None

def get_solid_rgb_for_object(obj):
    """
    Returns (r,g,b) in 0–1 for an object that you guarantee is a single color.
    Priority:
      1) first material slot with Principled Base Color
      2) first material slot diffuse_color
      3) object viewport color
      4) fallback white
    """
    # 1/2) Try materials in order
    if hasattr(obj, "material_slots"):
        for slot in obj.material_slots:
            mat = slot.material
            if not mat:
                continue
            c = _color_from_principled(mat)
            if c is not None:
                return _round_rgb(c)
            c = _color_from_diffuse(mat)
            if c is not None:
                return _round_rgb(c)

    # 3) Object color
    c = _color_from_object(obj)
    if c is not None:
        return _round_rgb(c)

    # 4) Fallback white
    return (1.0, 1.0, 1.0)

# --- export ------------------------------------------------------------------

output = []

for obj in bpy.data.objects:
    if obj.type != 'MESH':
        continue

    world = obj.matrix_world
    loc = world.translation
    rot = world.to_quaternion()
    scale = world.to_scale()

    # Pull the object's solid color (0–1 RGB)
    r, g, b = get_solid_rgb_for_object(obj)

    node = {
        "levelNodeStatic": {
            "shape": 1004,
            "material": 8,
            "position": {
                "x": -loc[0],
                "y": loc[2],
                "z": loc[1]
            },
            "scale": {
                "x": -scale[0],
                "y": scale[2] / 100,
                "z": scale[1]
            },
            "rotation": {
                "x": -rot[1],
                "y": rot[3],
                "z": rot[2],
                "w": rot[0]
            },
            "color1": {
                "r": r,
                "g": g,
                "b": b
            }
        }
    }

    output.append(node)

# Write JSON
filepath = os.path.join(bpy.path.abspath("//"), "export_nodes.json")
with open(filepath, 'w') as f:
    json.dump({
        "formatVersion": 17,
        "title": "New Level",
        "creators": ".index-editor",
        "description": ".index modding - grab-tools.live",
        "tags": [],
        "maxCheckpointCount": 10,
        "ambienceSettings": {
            "skyZenithColor": {"r": 0.28, "g": 0.476, "b": 0.73, "a": 1},
            "skyHorizonColor": {"r": 0.916, "g": 0.9574, "b": 0.9574, "a": 1},
            "sunAltitude": 45,
            "sunAzimuth": 315,
            "sunSize": 1,
            "fogDensity": 0
        },
        "levelNodes": output
    }, f, indent=4)

print(f"✅ Export complete: {filepath}")
