"""
Stage 3 orchestration — always produces BOTH raw and union point clouds for
a patient, regardless of source format. Format is resolved once via
ingest.discovery.resolve_extractor(); this module never branches on format
itself.
"""
import os
import open3d as o3d

from ct_pipeline.config import (
    RAW_PLY_DIR, UNION_PLY_DIR, N_POINTS, MARCHING_CUBES_LEVEL, TARGET_UP_AXIS,
)
from ct_pipeline.ingest import discovery
from ct_pipeline.pointcloud import surface, alignment


def _build_one(extractor_fn, patient_dir, out_path, overwrite, verbose, label):
    if os.path.exists(out_path) and not overwrite:
        if verbose:
            print(f"  [{label}] Already exists, skipping (use overwrite=True to redo)")
        return out_path

    volume, affine = extractor_fn(patient_dir, verbose=verbose)

    pcd = surface.volume_to_pointcloud(
        volume, affine,
        n_points=N_POINTS,
        level=MARCHING_CUBES_LEVEL,
        verbose=verbose,
    )
    pcd = alignment.pca_align(pcd, target_up=TARGET_UP_AXIS, verbose=verbose)
    pcd = alignment.normalize_scale(pcd, verbose=verbose)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    o3d.io.write_point_cloud(out_path, pcd)
    if verbose:
        print(f"  [{label}] Saved: {out_path}")
    return out_path


def build_patient(patient_id, fmt, base_dir, mode="both", overwrite=False, verbose=True):
    """
    Build point cloud(s) for one patient.
    mode: "raw" | "union" | "both"
    Returns dict: {"raw": path_or_None, "union": path_or_None}
    """
    patient_dir = discovery.patient_dir(base_dir, fmt, patient_id)
    raw_fn, union_fn = discovery.resolve_extractor(fmt)

    results = {"raw": None, "union": None}

    if verbose:
        print(f"\n{'='*50}")
        print(f"  Building point cloud(s) for {patient_id} [{fmt}] mode={mode}")

    if mode in ("raw", "both"):
        out_path = os.path.join(RAW_PLY_DIR, f"{patient_id}.ply")
        results["raw"] = _build_one(raw_fn, patient_dir, out_path, overwrite, verbose, "raw")

    if mode in ("union", "both"):
        out_path = os.path.join(UNION_PLY_DIR, f"{patient_id}.ply")
        results["union"] = _build_one(union_fn, patient_dir, out_path, overwrite, verbose, "union")

    return results


def build_all(patient_ids, fmt, base_dir, mode="both", overwrite=False, verbose=True):
    """Build point clouds for a list of patients. Returns dict patient_id -> result dict."""
    results = {}
    for pid in patient_ids:
        try:
            results[pid] = build_patient(pid, fmt, base_dir, mode=mode,
                                          overwrite=overwrite, verbose=verbose)
        except Exception as e:
            print(f"  ERROR processing {pid}: {e}")
            results[pid] = None
    return results
