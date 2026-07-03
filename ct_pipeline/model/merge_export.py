"""
Combine an existing raw .glb and union .glb for a patient into one merged
.glb scene (two node groups: "raw_surface" and organ/union geometry).

New module — no equivalent existed before. Only runs on demand (--merge
flag), never implicitly, since raw and union are usually viewed separately.
"""
import os
import trimesh


def build_merged_glb(patient_id, raw_glb_path, union_glb_path, out_path, verbose=True):
    if not os.path.exists(raw_glb_path):
        raise FileNotFoundError(f"Raw glb not found: {raw_glb_path}")
    if not os.path.exists(union_glb_path):
        raise FileNotFoundError(f"Union glb not found: {union_glb_path}")

    if verbose:
        print(f"  Merging raw + union glb for {patient_id}...")

    raw_scene   = trimesh.load(raw_glb_path)
    union_scene = trimesh.load(union_glb_path)

    merged = trimesh.Scene()

    def _add(scene_or_mesh, prefix):
        if isinstance(scene_or_mesh, trimesh.Scene):
            for name, geom in scene_or_mesh.geometry.items():
                merged.add_geometry(geom, node_name=f"{prefix}_{name}")
        else:
            merged.add_geometry(scene_or_mesh, node_name=prefix)

    _add(raw_scene, "raw")
    _add(union_scene, "union")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    merged.export(out_path)

    if verbose:
        print(f"  Exported merged: {out_path}")
    return out_path
