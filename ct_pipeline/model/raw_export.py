"""
Format-agnostic single-surface .glb export — builds one mesh from a binary
volume (already produced by an extract/ function), decimates, colors, and
centers it.

Used for:
  - the "raw" model, for both nii_gz and ima patients
  - the "union" model for ima patients specifically, since there's no organ
    segmentation to color individually yet (see model/builder.py dispatch)
"""
import os
import numpy as np
from skimage import measure
import trimesh

from ct_pipeline.config import MODEL_DECIMATE_FACE_COUNT, MODEL_RAW_DECIMATE_MULTIPLIER
# NOTE: original export_models.py's process_patient_raw() did NOT apply
# MODEL_SCALE_FACTOR (only the union/segmentation export did). That looks
# like an inconsistency in the original code (raw glb ends up ~400x larger
# in world units than union glb), but per "keep logic exactly the same"
# it's preserved as-is here rather than silently fixed. Flagging below.

SKIN_COLOR = (210, 180, 140, 200)


def build_surface_glb(volume, affine, out_path, verbose=True, node_name="body_surface"):
    """
    volume, affine: binary volume + affine, as returned by an extract/ function
    (segmentation.threshold_ct or ima_surface.threshold_ima).
    """
    if verbose:
        print(f"  Running marching cubes...")
    verts, faces, _, _ = measure.marching_cubes(volume, level=0.5)

    verts_h     = np.hstack([verts, np.ones((len(verts), 1))])
    verts_world = (affine @ verts_h.T).T[:, :3]

    mesh = trimesh.Trimesh(vertices=verts_world, faces=faces, process=False)

    if verbose:
        print(f"  Faces before decimation: {len(mesh.faces)}")

    target = MODEL_DECIMATE_FACE_COUNT * MODEL_RAW_DECIMATE_MULTIPLIER
    if len(mesh.faces) > target:
        mesh = mesh.simplify_quadric_decimation(face_count=target)

    if verbose:
        print(f"  Faces after decimation: {len(mesh.faces)}")

    mesh.visual = trimesh.visual.ColorVisuals(
        mesh=mesh, vertex_colors=np.tile(SKIN_COLOR, (len(mesh.vertices), 1))
    )

    # Center only — no MODEL_SCALE_FACTOR here, matching original behavior exactly.
    center = mesh.vertices.mean(axis=0)
    mesh.vertices = mesh.vertices - center
    if verbose:
        print(f"  Centered mesh (offset: {center.round(1)})")

    scene = trimesh.Scene()
    scene.add_geometry(mesh, node_name=node_name)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    scene.export(out_path)

    if verbose:
        size = os.path.getsize(out_path) / (1024 * 1024)
        print(f"  Exported: {out_path} ({size:.1f} MB)")

    return out_path
