import os
import sys
import time
import numpy as np
import open3d as o3d

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import PLY_DIR, UNION_PLY_DIR, RAW_PLY_DIR,PATIENTS
from matching.icp import match_pointclouds

def load_database(patients=None, ply_dir=None, mode="segmentation", verbose=True):
    """
    Load all preprocessed point clouds into memory as the matching database.
    mode: "segmentation" → loads from UNION_PLY_DIR
          "ct_threshold" → loads from RAW_PLY_DIR
    """
    patients = patients or PATIENTS
    if ply_dir is None:
        ply_dir = UNION_PLY_DIR if mode == "segmentation" else RAW_PLY_DIR

    database = {}

    if verbose:
        print(f"Loading database ({len(patients)} patients)...")

    for pid in patients:
        path = os.path.join(ply_dir, f"{pid}.ply")
        if not os.path.exists(path):
            print(f"  WARNING: {path} not found, skipping")
            continue
        pcd = o3d.io.read_point_cloud(path)
        database[pid] = pcd
        if verbose:
            print(f"  Loaded {pid}: {len(pcd.points)} points")

    return database


def match_against_database(real_pcd, database, voxel_size=10.0, verbose=True):
    """
    Match a real patient point cloud against all entries in the database.

    Args:
        real_pcd : open3d PointCloud of real patient scan
        database : dict of patient_id → open3d PointCloud
        voxel_size: ICP voxel size in mm
        verbose  : print progress

    Returns:
        list of dicts sorted by fitness (best first):
        [
            {
                "patient_id": "s1388",
                "fitness": 0.91,
                "rmse": 12.3,
                "confidence": 91.0,   # fitness as percentage
                "transform": np.array(...)
            },
            ...
        ]
    """
    results = []

    for pid, target_pcd in database.items():
        if verbose:
            print(f"\n  Matching against {pid}...")
        t0 = time.time()

        try:
            result = match_pointclouds(real_pcd, target_pcd,
                                       voxel_size=voxel_size,
                                       verbose=verbose)
            elapsed = time.time() - t0
            result["patient_id"]  = pid
            result["confidence"]  = round(result["fitness"] * 100, 2)
            result["time_sec"]    = round(elapsed, 2)
            results.append(result)

            if verbose:
                print(f"    ✓ fitness={result['fitness']:.4f} "
                      f"rmse={result['rmse']:.2f}mm "
                      f"({elapsed:.1f}s)")

        except Exception as e:
            print(f"    ERROR matching {pid}: {e}")

    # Sort by fitness descending (best match first)
    results.sort(key=lambda x: x["fitness"], reverse=True)
    return results


def find_best_match(real_pcd, database,
                    threshold=0.55,
                    max_retries=3,
                    voxel_size=5.0,
                    verbose=True):
    """
    Find best matching patient with retry logic and fallback.
    Only retries if best match is below threshold — doesn't re-run all matches.
    """
    if verbose:
        print(f"\n── Running match ──────────────────────────────")

    results = match_against_database(real_pcd, database,
                                     voxel_size=voxel_size,
                                     verbose=verbose)
    if not results:
        return {
            "patient_id": list(database.keys())[0],
            "confidence": 0.0,
            "fitness": 0.0,
            "rmse": 0.0,
            "transform": np.eye(4),
            "fallback": True,
            "attempts": 1
        }

    best = results[0]
    attempt = 1

    # Only retry if below threshold
    while best["fitness"] < threshold and attempt < max_retries:
        attempt += 1
        if verbose:
            print(f"\n── Retry {attempt}/{max_retries} "
                  f"(best so far: {best['patient_id']} {best['confidence']}%) ──")
        new_results = match_against_database(real_pcd, database,
                                             voxel_size=voxel_size,
                                             verbose=verbose)
        if new_results and new_results[0]["fitness"] > best["fitness"]:
            best = new_results[0]

    fallback = best["fitness"] < threshold
    if fallback and verbose:
        print(f"\n  Below threshold after {attempt} attempts. Using best available: {best['patient_id']}")

    best["fallback"] = fallback
    best["attempts"] = attempt
    return best