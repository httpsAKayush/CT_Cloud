"""
nii_gz-specific: build a colored, per-organ .glb from a patient's
segmentations/ folder. This is the "union" model path for nii_gz patients.

For IMA patients (no organ segmentation until totalseg.py lands), the union
model is instead produced by raw_export.py — see model/builder.py dispatch.
"""
import os
import numpy as np
import nibabel as nib
from skimage import measure
import trimesh

from ct_pipeline.config import (
    MODEL_DECIMATE_FACE_COUNT, MODEL_MIN_VOXELS,
    MODEL_SKELETON_DECIMATE_MULTIPLIER, MODEL_SCALE_FACTOR,
    SMALL_STRUCTURE_KEYWORDS, SMALL_STRUCTURE_MIN_VOXELS,
    SMALL_STRUCTURE_DECIMATE_FACTOR,
)

DECIMATE_FACE_COUNT = MODEL_DECIMATE_FACE_COUNT
MIN_VOXELS           = MODEL_MIN_VOXELS

ORGAN_COLORS = {
    "liver":                    (194, 100,  60, 180),
    "spleen":                   (160,  60, 120, 180),
    "kidney_left":              (210, 140,  80, 180),
    "kidney_right":             (210, 140,  80, 180),
    "pancreas":                 (220, 180, 100, 180),
    "stomach":                  (180, 160, 120, 180),
    "gallbladder":              (180, 200,  80, 180),
    "heart":                    (200,  60,  60, 200),
    "small_bowel":              (200, 160, 140, 160),
    "colon":                    (180, 130, 100, 160),
    "duodenum":                 (190, 150, 110, 160),
    "urinary_bladder":          (100, 160, 200, 160),
    "esophagus":                (160, 100, 100, 160),
    "trachea":                  (140, 180, 200, 160),
    "spinal_cord":              (220, 220, 160, 180),
    "lung_upper_lobe_left":     (140, 180, 220, 150),
    "lung_lower_lobe_left":     (140, 180, 220, 150),
    "lung_upper_lobe_right":    (140, 180, 220, 150),
    "lung_lower_lobe_right":    (140, 180, 220, 150),
    "lung_middle_lobe_right":   (140, 180, 220, 150),
    "aorta":                    (220,  60,  60, 200),
    "inferior_vena_cava":       ( 60,  60, 220, 200),
    "portal_vein_and_splenic_vein": ( 80, 100, 200, 180),
    "pulmonary_vein":           (100, 100, 220, 180),
    "adrenal_gland_left":       (180, 200, 140, 160),
    "adrenal_gland_right":      (180, 200, 140, 160),
    "__default__":              (200, 200, 200, 160),
}

MERGE_GROUPS = {
    "skeleton": [
        "vertebrae_L1", "vertebrae_L2", "vertebrae_L3", "vertebrae_L4", "vertebrae_L5",
        "vertebrae_S1", "sacrum",
        "vertebrae_T1", "vertebrae_T2", "vertebrae_T3", "vertebrae_T4",
        "vertebrae_T5", "vertebrae_T6", "vertebrae_T7", "vertebrae_T8",
        "vertebrae_T9", "vertebrae_T10", "vertebrae_T11", "vertebrae_T12",
        "vertebrae_C1", "vertebrae_C2", "vertebrae_C3", "vertebrae_C4",
        "vertebrae_C5", "vertebrae_C6", "vertebrae_C7",
        "rib_left_1",  "rib_left_2",  "rib_left_3",  "rib_left_4",
        "rib_left_5",  "rib_left_6",  "rib_left_7",  "rib_left_8",
        "rib_left_9",  "rib_left_10", "rib_left_11", "rib_left_12",
        "rib_right_1", "rib_right_2", "rib_right_3", "rib_right_4",
        "rib_right_5", "rib_right_6", "rib_right_7", "rib_right_8",
        "rib_right_9", "rib_right_10","rib_right_11","rib_right_12",
        "sternum", "costal_cartilages",
        "hip_left", "hip_right",
        "humerus_left", "humerus_right",
        "femur_left", "femur_right",
        "scapula_left", "scapula_right",
        "clavicula_left", "clavicula_right",
        "skull",
    ],
    "left_lung": ["lung_upper_lobe_left", "lung_lower_lobe_left"],
    "right_lung": ["lung_upper_lobe_right", "lung_lower_lobe_right", "lung_middle_lobe_right"],
    "muscles": [
        "gluteus_maximus_left",  "gluteus_maximus_right",
        "gluteus_medius_left",   "gluteus_medius_right",
        "gluteus_minimus_left",  "gluteus_minimus_right",
        "iliopsoas_left",        "iliopsoas_right",
        "autochthon_left",       "autochthon_right",
    ],
}

ORGAN_COLORS["skeleton"]  = (220, 210, 180, 200)
ORGAN_COLORS["left_lung"] = (140, 180, 220, 150)
ORGAN_COLORS["right_lung"] = (140, 180, 220, 150)
ORGAN_COLORS["muscles"]   = (180, 120, 100, 140)


def nii_to_mesh(nii_path, decimate=True, min_voxels=None, decimate_factor=1.0):
    img  = nib.load(nii_path)
    data = img.get_fdata()
    affine = img.affine

    threshold = min_voxels if min_voxels is not None else MIN_VOXELS
    if data.sum() < threshold:
        return None

    try:
        verts, faces, _, _ = measure.marching_cubes(data, level=0.5)
    except Exception:
        return None

    if len(faces) == 0:
        return None

    verts_h     = np.hstack([verts, np.ones((len(verts), 1))])
    verts_world = (affine @ verts_h.T).T[:, :3]

    result = trimesh.Trimesh(vertices=verts_world, faces=faces, process=False)

    target_faces = int(DECIMATE_FACE_COUNT * decimate_factor)
    if decimate and len(result.faces) > target_faces:
        result = result.simplify_quadric_decimation(face_count=target_faces)

    return result


def get_color(organ_name):
    for key, color in ORGAN_COLORS.items():
        if key in organ_name.lower():
            return color
    return ORGAN_COLORS["__default__"]


def is_small_structure(organ_name):
    return any(kw in organ_name.lower() for kw in SMALL_STRUCTURE_KEYWORDS)


def build_union_glb(patient_id, patient_dir, out_path, verbose=True):
    """
    Build the organ-colored union .glb for one nii_gz patient from its
    segmentations/ folder. Returns out_path.
    """
    seg_dir = os.path.join(patient_dir, "segmentations")
    if not os.path.exists(seg_dir):
        raise FileNotFoundError(f"segmentation dir not found: {seg_dir}")

    if verbose:
        print(f"\n{'='*50}")
        print(f"  Building union model for {patient_id}...")

    nii_files = sorted([f for f in os.listdir(seg_dir) if f.endswith(".nii.gz")])

    organ_to_group = {}
    for group, members in MERGE_GROUPS.items():
        for member in members:
            organ_to_group[member] = group

    group_meshes = {g: [] for g in MERGE_GROUPS}
    individual_meshes = {}

    for nii_file in nii_files:
        organ_name = nii_file.replace(".nii.gz", "")
        nii_path   = os.path.join(seg_dir, nii_file)

        if verbose:
            print(f"    {organ_name}...", end=" ", flush=True)

        min_voxels_for_this = SMALL_STRUCTURE_MIN_VOXELS if is_small_structure(organ_name) else MIN_VOXELS
        mesh = nii_to_mesh(
            nii_path, min_voxels=min_voxels_for_this,
            decimate_factor=(SMALL_STRUCTURE_DECIMATE_FACTOR if is_small_structure(organ_name) else 1.0),
        )

        if mesh is None:
            if verbose:
                print("skipped (too small)")
            continue
        if verbose:
            print(f"{len(mesh.faces)} faces")

        group = organ_to_group.get(organ_name)
        if group:
            group_meshes[group].append(mesh)
        else:
            individual_meshes[organ_name] = mesh

    scene = trimesh.Scene()

    for group_name, meshes in group_meshes.items():
        if not meshes:
            continue
        merged = trimesh.util.concatenate(meshes)

        if group_name == "skeleton" and len(merged.faces) > DECIMATE_FACE_COUNT * 3:
            merged = merged.simplify_quadric_decimation(
                face_count=DECIMATE_FACE_COUNT * MODEL_SKELETON_DECIMATE_MULTIPLIER)

        color = get_color(group_name)
        merged.visual = trimesh.visual.ColorVisuals(
            mesh=merged, vertex_colors=np.tile(color, (len(merged.vertices), 1))
        )
        scene.add_geometry(merged, node_name=group_name)
        if verbose:
            print(f"    Group '{group_name}': {len(merged.faces)} faces")

    for organ_name, mesh in individual_meshes.items():
        color = get_color(organ_name)
        mesh.visual = trimesh.visual.ColorVisuals(
            mesh=mesh, vertex_colors=np.tile(color, (len(mesh.vertices), 1))
        )
        scene.add_geometry(mesh, node_name=organ_name)

    # Center + scale
    all_verts = [np.array(geom.vertices) for geom in scene.geometry.values()]
    if all_verts:
        all_verts_np = np.vstack(all_verts)
        bbox_min = all_verts_np.min(axis=0)
        bbox_max = all_verts_np.max(axis=0)
        center   = (bbox_min + bbox_max) / 2.0

        if verbose:
            print(f"  Centering scene (bbox center: {center.round(1)})")

        centered_scene = trimesh.Scene()
        for name, geom in scene.geometry.items():
            new_verts = (np.array(geom.vertices) - center) * MODEL_SCALE_FACTOR
            centered_mesh = trimesh.Trimesh(vertices=new_verts, faces=np.array(geom.faces), process=False)
            centered_mesh.visual = geom.visual
            centered_scene.add_geometry(centered_mesh, node_name=name)
        scene = centered_scene

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    scene.export(out_path)

    if verbose:
        print(f"\n  Exported: {out_path}")
        print(f"  Total geometries: {len(scene.geometry)}")

    return out_path
