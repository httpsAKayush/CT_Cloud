# """
# Combine an existing raw .glb and union .glb for a patient into one merged
# .glb scene (two node groups: "raw_surface" and organ/union geometry).

# New module — no equivalent existed before. Only runs on demand (--merge
# flag), never implicitly, since raw and union are usually viewed separately.
# """
# import os
# import trimesh


# def build_merged_glb(patient_id, raw_glb_path, union_glb_path, out_path, verbose=True):
#     if not os.path.exists(raw_glb_path):
#         raise FileNotFoundError(f"Raw glb not found: {raw_glb_path}")
#     if not os.path.exists(union_glb_path):
#         raise FileNotFoundError(f"Union glb not found: {union_glb_path}")

#     if verbose:
#         print(f"  Merging raw + union glb for {patient_id}...")

#     raw_scene   = trimesh.load(raw_glb_path)
#     union_scene = trimesh.load(union_glb_path)

#     merged = trimesh.Scene()

#     def _add(scene_or_mesh, prefix):
#         if isinstance(scene_or_mesh, trimesh.Scene):
#             for name, geom in scene_or_mesh.geometry.items():
#                 merged.add_geometry(geom, node_name=f"{prefix}_{name}")
#         else:
#             merged.add_geometry(scene_or_mesh, node_name=prefix)

#     _add(raw_scene, "raw")
#     _add(union_scene, "union")

#     os.makedirs(os.path.dirname(out_path), exist_ok=True)
#     merged.export(out_path)

#     if verbose:
#         print(f"  Exported merged: {out_path}")
#     return out_path
"""
Combine an already-exported raw .glb and union .glb for a patient into one
merged .glb — built ONLY from those two files (no volume recomputation).
Requires both to already exist (built via mode="both" --with-glb, either in
the same create-model call or a previous one).

Each organ/group from the union scene stays its own node (liver, skeleton,
etc.) so Quest/Unity can toggle them individually. The raw layer is always
added under the SAME fixed node name (RAW_LAYER_NODE_NAME below), regardless
of whatever internal node name raw.glb happens to have — so Unity-side code
that references the raw layer by name never breaks, even if raw_export.py's
own internal naming changes later.
"""
import os
import trimesh

RAW_LAYER_NODE_NAME = "raw_body_surface"


def _geoms_by_node(scene):
    """
    Map real node/layer name -> geometry, for a loaded trimesh.Scene.
    NOT scene.geometry.items() — that dict is keyed by trimesh's internal
    auto-generated geometry name (e.g. "geometry_0"), not the node name you
    actually set with node_name=... when the file was built. Using it here
    would silently rename every organ layer to a meaningless generic name.
    """
    out = {}
    for node_name in scene.graph.nodes_geometry:
        _, geom_key = scene.graph[node_name]
        out[node_name] = scene.geometry[geom_key]
    return out


def build_merged_glb(patient_id, raw_glb_path, union_glb_path, out_path, verbose=True):
    if not os.path.exists(raw_glb_path):
        raise FileNotFoundError(f"Raw glb not found: {raw_glb_path}")
    if not os.path.exists(union_glb_path):
        raise FileNotFoundError(f"Union glb not found: {union_glb_path}")

    if verbose:
        print(f"  Merging raw + union glb for {patient_id}...")

    raw_scene   = trimesh.load(raw_glb_path)
    union_scene = trimesh.load(union_glb_path)

    raw_geoms   = _geoms_by_node(raw_scene)
    union_geoms = _geoms_by_node(union_scene)

    merged = trimesh.Scene()

    # Raw layer — always the same fixed name, regardless of raw.glb's own
    # internal node name(s). If raw.glb somehow has more than one node
    # (shouldn't happen given raw_export.py always produces exactly one),
    # combine them so there's still exactly one raw layer in the merged file.
    raw_meshes = list(raw_geoms.values())
    combined_raw = trimesh.util.concatenate(raw_meshes) if len(raw_meshes) > 1 else raw_meshes[0]
    merged.add_geometry(combined_raw, node_name=RAW_LAYER_NODE_NAME)

    # Union layer(s) — keep their real names (liver, skeleton, ...) so Quest
    # can toggle by organ. Guard against a name colliding with the raw
    # layer's fixed name (vanishingly unlikely with real organ names, but
    # fail loud rather than silently overwrite the raw layer if it happens).
    for name, geom in union_geoms.items():
        node_name = name
        if node_name == RAW_LAYER_NODE_NAME:
            node_name = f"union_{name}"
            if verbose:
                print(f"  WARNING: union layer named '{name}' collides with the "
                      f"raw layer's fixed name — renamed to '{node_name}'")
        merged.add_geometry(geom, node_name=node_name)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    merged.export(out_path)

    if verbose:
        print(f"  Exported merged: {out_path}")
        print(f"  Layers: {list(merged.graph.nodes_geometry)}")

    return out_path
