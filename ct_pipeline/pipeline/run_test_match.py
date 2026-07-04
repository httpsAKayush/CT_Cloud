"""
Orchestration only — local matching tests, no Quest/socket involved.

Two scan sources, one shared matching path:
  --fake <patient_id>  : perturbed copy of an existing database cloud (tests the
                          algorithm/thresholds; must NOT be re-aligned, since
                          re-aligning an already-aligned cloud degrades matching)
  --real-ply <path>     : an actual captured/converted .ply from disk (tests the
                          real capture pipeline — camera/STL/IMA conversion,
                          discovery, alignment, everything up to the socket layer)

This replaces the old separate `match-and-send --interactive` mode — that was
the same "match a real file, print the result, don't send anything" operation
under a different name. One less code path to keep in sync.
"""
import os
from ct_pipeline.matching.matcher import load_database, find_best_match, match_against_database
from ct_pipeline.matching.test_utils import make_fake_scan
from ct_pipeline.pointcloud.alignment import pca_align, normalize_scale


def print_results(result, all_results=None):
    print(f"\n{'='*50}")
    print(f"MATCH RESULT")
    print(f"{'='*50}")
    print(f"  Patient ID  : {result['patient_id']}")
    print(f"  Confidence  : {result['confidence']}%")
    print(f"  Fitness     : {result['fitness']:.4f}")
    print(f"  Feat score  : {result.get('feat_score', 'N/A')}")
    print(f"  ICP score   : {result.get('icp_score', 'N/A')}")
    print(f"  RMSE        : {result['rmse']:.2f} mm")
    print(f"  Fallback    : {result['fallback']}")
    print(f"  Attempts    : {result['attempts']}")

    if all_results:
        print(f"\n  Full ranking:")
        for i, r in enumerate(all_results):
            marker = " ◄ BEST" if i == 0 else ""
            print(f"    {i+1}. {r['patient_id']:8s} "
                  f"combined={r['fitness']:.4f} "
                  f"feat={r.get('feat_score', 0):.3f} "
                  f"icp={r.get('icp_score', 0):.3f} "
                  f"conf={r['confidence']}%{marker}")
    print(f"{'='*50}")


def run(fake_patient=None, real_ply=None, mode="raw", threshold=0.55, retries=3,
        voxel_size=10.0, noise=5.0, rotation=15.0, dropout=0.3, verbose=True):
    """
    Exactly one of fake_patient / real_ply drives the scan source.
    fake_patient defaults to "s1388" only if real_ply is not given (preserves
    old default behavior for `test-match` with no args).
    """
    import open3d as o3d

    database = load_database(verbose=verbose, mode=mode)
    if not database:
        print("ERROR: No point clouds in database. Run `ct-pipeline create-model` first.")
        return

    if real_ply:
        print(f"\nLoading real scan: {real_ply}")
        if not os.path.exists(real_ply):
            print(f"ERROR: file not found: {real_ply}")
            return
        pcd = o3d.io.read_point_cloud(real_ply)
        pcd = pca_align(pcd, verbose=verbose)
        pcd = normalize_scale(pcd, verbose=verbose)
    else:
        fake_patient = fake_patient or "s1388"
        print(f"\nGenerating fake scan from {fake_patient}...")
        pcd = make_fake_scan(fake_patient, mode=mode, noise_mm=noise,
                              rotation_deg=rotation, dropout=dropout, verbose=verbose)

    print(f"\nRunning matching against {len(database)} patients...")
    all_results = match_against_database(pcd, database, voxel_size=voxel_size, verbose=verbose)

    result = find_best_match(pcd, database, threshold=threshold,
                              max_retries=retries, voxel_size=voxel_size, verbose=False)

    print_results(result, all_results)
    return result