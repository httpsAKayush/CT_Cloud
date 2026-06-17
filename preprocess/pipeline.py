import os
import open3d as o3d
from . import segmentation, surface, alignment
from config import (
    DATASET_DIR, PLY_DIR,
    SURFACE_MODE, CT_THRESHOLD_HU,
    N_POINTS, MARCHING_CUBES_LEVEL,
    TARGET_UP_AXIS
)


def process_patient(patient_id, overwrite=False, verbose=True):
    """
    Full preprocessing pipeline for one patient.
    Returns path to saved .ply file.
    """
    out_path = os.path.join(PLY_DIR, f"{patient_id}.ply")

    if os.path.exists(out_path) and not overwrite:
        if verbose:
            print(f"  [{patient_id}] Already exists, skipping. (use overwrite=True to redo)")
        return out_path

    patient_dir = os.path.join(DATASET_DIR, patient_id)
    if not os.path.exists(patient_dir):
        raise FileNotFoundError(f"Patient directory not found: {patient_dir}")

    if verbose:
        print(f"\n{'='*50}")
        print(f"  Processing {patient_id} [{SURFACE_MODE} mode]")

    # Step 1 — extract binary volume
    if SURFACE_MODE == "segmentation":
        volume, affine = segmentation.merge_segmentations(patient_dir, verbose)
    elif SURFACE_MODE == "ct_threshold":
        volume, affine = segmentation.threshold_ct(patient_dir, CT_THRESHOLD_HU, verbose)
    else:
        raise ValueError(f"Unknown SURFACE_MODE: {SURFACE_MODE}")

    # Step 2 — surface extraction + point cloud
    pcd = surface.volume_to_pointcloud(
        volume, affine,
        n_points=N_POINTS,
        level=MARCHING_CUBES_LEVEL,
        verbose=verbose
    )

    # Step 3 — PCA alignment
    pcd = alignment.pca_align(pcd, target_up=TARGET_UP_AXIS, verbose=verbose)

    # Step 4 — normalize scale
    pcd = alignment.normalize_scale(pcd, verbose=verbose)

    # Step 5 — save
    os.makedirs(PLY_DIR, exist_ok=True)
    o3d.io.write_point_cloud(out_path, pcd)
    if verbose:
        print(f"  Saved: {out_path}")

    return out_path


def process_all(patients, overwrite=False, verbose=True):
    """Process all patients. Returns dict of patient_id → ply_path."""
    results = {}
    for pid in patients:
        try:
            path = process_patient(pid, overwrite=overwrite, verbose=verbose)
            results[pid] = path
        except Exception as e:
            print(f"  ERROR processing {pid}: {e}")
            results[pid] = None
    return results