"""Orchestration only — chains matching.test_utils + matching.matcher for local testing."""
# from ct_pipeline.matching.matcher import load_database, find_best_match, match_against_database
from ct_pipeline.ingest.ply_loader import load_database
from ct_pipeline.matching.matcher import find_best_match, match_against_database
from ct_pipeline.matching.test_utils import make_fake_scan


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


def run(fake_patient="s1388", mode="raw", threshold=0.55, retries=3, voxel_size=10.0,
        noise=5.0, rotation=15.0, dropout=0.3, verbose=True):

    database = load_database(verbose=verbose, mode=mode)
    if not database:
        print("ERROR: No point clouds in database. Run `ct-pipeline create-model` first.")
        return

    print(f"\nGenerating fake scan from {fake_patient}...")
    real_pcd = make_fake_scan(fake_patient, mode=mode, noise_mm=noise,
                               rotation_deg=rotation, dropout=dropout, verbose=verbose)

    print(f"\nRunning matching against {len(database)} patients...")
    all_results = match_against_database(real_pcd, database, voxel_size=voxel_size, verbose=verbose)

    result = find_best_match(real_pcd, database, threshold=threshold,
                              max_retries=retries, voxel_size=voxel_size, verbose=False)

    print_results(result, all_results)
    return result
