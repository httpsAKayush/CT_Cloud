
import os
import time
import numpy as np
import open3d as o3d

from ct_pipeline.config import RAW_PLY_DIR, UNION_PLY_DIR
from ct_pipeline.matching.icp import match_pointclouds


def discover_available_patients(ply_dir):
    """List patient IDs that actually have a .ply in ply_dir."""
    if not os.path.exists(ply_dir):
        return []
    return sorted(
        os.path.splitext(f)[0] for f in os.listdir(ply_dir) if f.endswith(".ply")
    )


def load_database(patients=None, ply_dir=None, mode="raw", verbose=True):
    """
    Load all preprocessed point clouds into memory as the matching database.
    mode: "raw" -> RAW_PLY_DIR, "union" -> UNION_PLY_DIR
    patients: explicit list, or None -> auto-discover every .ply present in ply_dir
              (NOT config.PATIENTS — that's just a stale fallback name list, not
              a source of truth; the disk is the source of truth for scalability).
    """
    if ply_dir is None:
        ply_dir = RAW_PLY_DIR if mode == "raw" else UNION_PLY_DIR

    if patients is None:
        patients = discover_available_patients(ply_dir)
        if verbose:
            print(f"Auto-discovered {len(patients)} patients in {ply_dir}: {patients}")

    database = {}
    if verbose:
        print(f"Loading database ({len(patients)} patients) from {ply_dir} ...")

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
    Returns list of dicts sorted by fitness (best first).
    """
    results = []

    for pid, target_pcd in database.items():
        if verbose:
            print(f"\n  Matching against {pid}...")
        t0 = time.time()
        try:
            result = match_pointclouds(real_pcd, target_pcd, voxel_size=voxel_size, verbose=verbose)
            elapsed = time.time() - t0
            result["patient_id"] = pid
            result["confidence"] = round(result["fitness"] * 100, 2)
            result["time_sec"]   = round(elapsed, 2)
            results.append(result)
            if verbose:
                print(f"    ✓ fitness={result['fitness']:.4f} "
                      f"rmse={result['rmse']:.2f}mm ({elapsed:.1f}s)")
        except Exception as e:
            print(f"    ERROR matching {pid}: {e}")

    results.sort(key=lambda x: x["fitness"], reverse=True)
    return results


def find_best_match(real_pcd, database, threshold=0.55, max_retries=3, voxel_size=5.0, verbose=True):
    """
    Find best matching patient with retry logic and fallback.
    Only retries if best match is below threshold.
    """
    if verbose:
        print(f"\n── Running match ──────────────────────────────")

    results = match_against_database(real_pcd, database, voxel_size=voxel_size, verbose=verbose)
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

    while best["fitness"] < threshold and attempt < max_retries:
        attempt += 1
        if verbose:
            print(f"\n── Retry {attempt}/{max_retries} "
                  f"(best so far: {best['patient_id']} {best['confidence']}%) ──")
        new_results = match_against_database(real_pcd, database, voxel_size=voxel_size, verbose=verbose)
        if new_results and new_results[0]["fitness"] > best["fitness"]:
            best = new_results[0]

    fallback = best["fitness"] < threshold
    if fallback and verbose:
        print(f"\n  Below threshold after {attempt} attempts. Using best available: {best['patient_id']}")

    best["fallback"] = fallback
    best["attempts"] = attempt
    return best


def match_reference_file(reference_ply_path, mode="raw", threshold=0.55, verbose=True):
    """
    Single shared entrypoint for matching a REAL reference scan (loaded from disk)
    against the database. Used by matcher.run_reference_match() and anywhere else
    that has a .ply *path* rather than an in-memory pcd.

    Not used by test-match — fake scans are perturbed copies of already-aligned
    database clouds, so they must NOT be re-aligned/re-normalized here (doing so
    degrades matching). test_match calls match_against_database/find_best_match
    directly with its already-prepared fake pcd instead.
    """
    import open3d as o3d
    from ct_pipeline.pointcloud.alignment import pca_align, normalize_scale

    if verbose:
        print(f"\n── Loading database [{mode}]...")
    database = load_database(mode=mode, verbose=verbose)
    if not database:
        raise RuntimeError(f"No point clouds found for mode={mode}. Run create-model first.")

    if verbose:
        print(f"\n── Loading reference scan: {reference_ply_path}")
    if not os.path.exists(reference_ply_path):
        raise FileNotFoundError(f"Reference scan not found: {reference_ply_path}")

    pcd = o3d.io.read_point_cloud(reference_ply_path)
    pcd = pca_align(pcd, verbose=verbose)
    pcd = normalize_scale(pcd, verbose=verbose)

    if verbose:
        print(f"\n── Matching...")
    result = find_best_match(pcd, database, threshold=threshold, verbose=verbose)

    if verbose:
        print(f"\n── Best match: {result['patient_id']} ({result['confidence']}%)")
    return result


def run_reference_match(ref_ply=None, ref_dir=None, mode="raw", threshold=0.55, verbose=True):
    """
    The full MATCH step, decoupled from sending: discover which reference .ply
    to use, then match it against the database. Returns the result dict only —
    no knowledge of models/.glb/sockets here at all. serve/model_sender.py is
    the one place that turns a result into bytes on the wire.
    """
    from ct_pipeline.ingest.reference import find_reference_ply

    reference_ply_path = find_reference_ply(ref_ply=ref_ply, ref_dir=ref_dir, verbose=verbose)
    return match_reference_file(reference_ply_path, mode=mode, threshold=threshold, verbose=verbose)
