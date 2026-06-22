import os
import open3d as o3d
from . import segmentation, surface, alignment
from config import (
    DATASET_DIR, PLY_DIR,
    CT_THRESHOLD_HU, UNION_PLY_DIR, RAW_PLY_DIR,
    N_POINTS, MARCHING_CUBES_LEVEL,
    TARGET_UP_AXIS
)


def process_patient(patient_id, overwrite=False, verbose=True, surface_mode="segmentation"):
    """
    Full preprocessing pipeline for one patient.
    Returns path to saved .ply file.
    """
    #out_path = os.path.join(PLY_DIR, f"{patient_id}.ply")
    union_out_path = os.path.join(UNION_PLY_DIR, f"{patient_id}.ply")
    raw_out_path = os.path.join(RAW_PLY_DIR, f"{patient_id}.ply")

    # if os.path.exists(out_path) and not overwrite:
    #     if verbose:
    #         print(f"  [{patient_id}] Already exists, skipping. (use overwrite=True to redo)")
    #     return out_path

    if surface_mode == "segmentation":
        if os.path.exists(union_out_path) and not overwrite:
            if verbose:
                print(f"  [{patient_id}] Union cloud already exists, skipping. (use overwrite=True to redo)")
            return union_out_path

    elif surface_mode == "ct_threshold":
        if os.path.exists(raw_out_path) and not overwrite:
            if verbose:
                print(f"  [{patient_id}] Raw cloud already exists, skipping. (use overwrite=True to redo)")
            return raw_out_path

    patient_dir = os.path.join(DATASET_DIR, patient_id)
    if not os.path.exists(patient_dir):
        raise FileNotFoundError(f"Patient directory not found: {patient_dir}")

    if verbose:
        print(f"\n{'='*50}")
        print(f"  Processing {patient_id} [{surface_mode} mode]")

    # Step 1 — extract binary volume
    if surface_mode == "segmentation":
        volume, affine = segmentation.merge_segmentations(patient_dir, verbose)
        out_path = union_out_path

    elif surface_mode == "ct_threshold":
        volume, affine = segmentation.threshold_ct(
            patient_dir,
            CT_THRESHOLD_HU,
            verbose
        )
        out_path = raw_out_path

    else:
        raise ValueError(f"Unknown mode: {surface_mode}")

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


def process_all(patients, overwrite=False, verbose=True, surface_mode="segmentation"):
    """Process all patients. Returns dict of patient_id → ply_path."""
    results = {}
    for pid in patients:
        try:
            path = process_patient(pid, overwrite=overwrite, verbose=verbose, surface_mode=surface_mode)
            results[pid] = path
        except Exception as e:
            print(f"  ERROR processing {pid}: {e}")
            results[pid] = None
    return results