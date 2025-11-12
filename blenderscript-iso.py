import bpy
import mathutils

# ---------- helpers ----------
def apply_xforms(obj):
    mw = obj.matrix_world.copy()
    obj.matrix_world = mathutils.Matrix.Identity(4)
    for v in obj.data.vertices:
        v.co = mw @ v.co

# Build/fetch 1.0-edge equilateral ref triangle centered on centroid, lying in XY
ref_name = "reg_iso"
ref_obj = bpy.data.objects.get(ref_name)
if not ref_obj:
    h = 0.8660254037844386  # sqrt(3)/2 for unit side
    verts = [(-0.5, -h/3, 0.0),
             ( 0.5, -h/3, 0.0),
             ( 0.0,  2*h/3, 0.0)]
    faces = [(0, 1, 2)]
    me = bpy.data.meshes.new(ref_name + "_mesh")
    me.from_pydata(verts, [], faces)
    me.update()
    ref_obj = bpy.data.objects.new(ref_name, me)
    bpy.context.collection.objects.link(ref_obj)

# ensure ref clean
if (ref_obj.parent is not None
    or ref_obj.scale != mathutils.Vector((1,1,1))
    or ref_obj.rotation_euler != mathutils.Euler((0,0,0))):
    apply_xforms(ref_obj)
    ref_obj.parent = None
    ref_obj.scale = (1,1,1)
    ref_obj.rotation_euler = (0,0,0)

REF_BASE = 1.0

def get_poly_color(poly, mesh):
    # vertex colors (Blender 3.x attributes) → average loops
    if mesh.color_attributes:
        color_layer = mesh.color_attributes.active_color
        if color_layer:
            acc = mathutils.Vector((0,0,0,0))
            for li in poly.loop_indices:
                acc += mathutils.Vector(color_layer.data[li].color)
            return acc / len(poly.loop_indices)
    # fallback: mat diffuse
    if poly.material_index < len(mesh.materials):
        mat = mesh.materials[poly.material_index]
        if mat and mat.diffuse_color:
            return mat.diffuse_color
    return mathutils.Vector((1,1,1,1))

# ---------- main ----------
total = 0
for target_obj in bpy.context.selected_objects:
    if target_obj.type != "MESH":
        continue

    bpy.ops.object.mode_set(mode='OBJECT')
    mesh = target_obj.data
    mesh.update()

    placed = 0
    for poly in mesh.polygons:
        if len(poly.vertices) != 3:
            continue

        # world-space triangle vertices
        v = [target_obj.matrix_world @ mesh.vertices[i].co for i in poly.vertices]
        v0, v1, v2 = v

        # edges and normal
        e01 = v1 - v0
        e12 = v2 - v1
        e20 = v0 - v2
        n = e01.cross(v2 - v0)
        if n.length < 1e-12:
            continue
        normal = n.normalized()

        # local frame: x along e01, y = n × x
        x_axis = e01.normalized()
        y_axis = normal.cross(x_axis).normalized()
        R = mathutils.Matrix((x_axis, y_axis, normal)).transposed()
        Rq = R.to_quaternion()

        # uniform scale = average edge length / REF_BASE
        L01 = e01.length
        L12 = e12.length
        L20 = e20.length
        s = (L01 + L12 + L20) / 3.0 / REF_BASE
        if s < 1e-9:
            continue

        # centroid placement
        c = (v0 + v1 + v2) / 3.0

        # instance (link data, do NOT copy mesh to keep one prototype)
        inst = ref_obj.copy()
        inst.data = ref_obj.data           # link same mesh data
        bpy.context.collection.objects.link(inst)

        inst.location = c
        inst.rotation_mode = 'QUATERNION'
        inst.rotation_quaternion = Rq
        inst.scale = (s, s, 1.0)           # uniform in-plane scale (no anisotropy)

        # per-face color -> per-instance material
        col = get_poly_color(poly, mesh)
        mat = bpy.data.materials.new(name=f"tri_mat_{total}_{placed}")
        # Blender expects (r,g,b,a)
        mat.diffuse_color = (col[0], col[1], col[2], col[3] if len(col) > 3 else 1.0)
        if len(inst.data.materials):
            inst.data.materials[0] = mat
        else:
            inst.data.materials.append(mat)

        placed += 1

    total += placed
    print(f"✅ {target_obj.name}: {placed} triangles placed")

print(f"🎯 Total triangles placed: {total}")

