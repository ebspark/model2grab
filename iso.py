import pymeshlab
import argparse, os

def remesh_isotropic(input_file, output_file, target_edge_length, simplify_ratio=0.6, max_error=0.003):
    if not os.path.exists(input_file):
        print(f"❌ Error: Input file not found at {input_file}")
        return

    print(f"📂 Loading mesh: {input_file}")
    ms = pymeshlab.MeshSet()
    ms.load_new_mesh(input_file)

    v0, f0 = ms.current_mesh().vertex_number(), ms.current_mesh().face_number()
    print(f"✅ Loaded mesh: {v0} verts, {f0} faces")

    # --- Pre-clean ---
    for f in [
        'meshing_remove_duplicate_vertices',
        'meshing_remove_unreferenced_vertices',
        'meshing_remove_duplicate_faces',
        'meshing_repair_non_manifold_edges',
        'meshing_repair_non_manifold_vertices'
    ]:
        try: ms.apply_filter(f)
        except: pass

    print(f"🔧 Isotropic remeshing (edge ≈ {target_edge_length})")
    ms.apply_filter(
        'meshing_isotropic_explicit_remeshing',
        targetlen=pymeshlab.PureValue(target_edge_length),
        iterations=24,
        adaptive=False
    )

    print("🧹 Cleanup before simplify ...")
    for f in [
        'meshing_remove_t_vertices',
        'meshing_remove_folded_faces'
    ]:
        try: ms.apply_filter(f)
        except: pass

    # --- Simplify isotropically ---
    print(f"⚙️ Simplifying topology (≈{int(simplify_ratio*100)}% target)...")
    try:
        ms.apply_filter(
            'meshing_decimation_quadric_edge_collapse',
            targetfacenum=pymeshlab.PureValue(int(f0 * simplify_ratio)),
            qualitythr=pymeshlab.PureValue(0.3),
            preservenormal=True,
            planarquadric=True,
            optimalplacement=True,
            preservetopology=True
        )
    except Exception as e:
        print(f"⚠️ Simplify skipped: {e}")

    print("🔺 Triangulating + hole fix ...")
    for f in ['meshing_poly_to_tri', 'meshing_close_holes']:
        try: ms.apply_filter(f)
        except: pass

    try: ms.apply_filter('compute_normal_per_vertex')
    except: pass

    ms.save_current_mesh(output_file)
    v1, f1 = ms.current_mesh().vertex_number(), ms.current_mesh().face_number()
    print(f"💾 Saved → {output_file}")
    print(f"📊 Result: {v1} verts, {f1} faces (↓ {(1 - f1/f0)*100:.1f}% fewer)")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input_file")
    ap.add_argument("output_file")
    ap.add_argument("--length", type=float, required=True)
    ap.add_argument("--simplify", type=float, default=0.6, help="0.6 = keep 60% faces (default)")
    ap.add_argument("--error", type=float, default=0.003, help="max geometric deviation")
    args = ap.parse_args()
    remesh_isotropic(args.input_file, args.output_file, args.length, args.simplify, args.error)

if __name__ == "__main__":
    main()

