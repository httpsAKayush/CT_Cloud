import os
import sys
import argparse
import numpy as np
import open3d as o3d

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import PLY_DIR,UNION_PLY_DIR,RAW_PLY_DIR, PATIENTS
from matching.matcher import load_database, find_best_match
from preprocess.alignment import pca_align, normalize_scale


def make_fake_scan(patient_id, noise_mm=5.0, rotation_deg=15.0, dropout=0.3, verbose=True, mode="segmentation"):
    """
    Generate a fake real-world scan by perturbing an existing point cloud.
    Used for testing without a real depth camera.
    """
    if mode == "segmentation":
        path = os.path.join(UNION_PLY_DIR, f"{patient_id}.ply")

    elif mode == "ct_threshold":
         path = os.path.join(RAW_PLY_DIR, f"{patient_id}.ply")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Point cloud not found: {path}")

    pcd    = o3d.io.read_point_cloud(path)
    points = np.asarray(pcd.points).copy()

    # Add Gaussian noise
    points += np.random.normal(0, noise_mm, points.shape)

    # Random rotation
    angle  = np.radians(rotation_deg)
    R      = o3d.geometry.get_rotation_matrix_from_axis_angle(
                 [angle * 0.3, angle, angle * 0.1])
    pcd_fake        = o3d.geometry.PointCloud()
    pcd_fake.points = o3d.utility.Vector3dVector(points)
    pcd_fake.rotate(R, center=np.zeros(3))

    # Random dropout (simulate partial occlusion)
    n_keep  = int(len(points) * (1.0 - dropout))
    indices = np.random.choice(len(points), n_keep, replace=False)
    pcd_fake = pcd_fake.select_by_index(indices)

    if verbose:
        print(f"Fake scan from {patient_id}: "
              f"{len(pcd_fake.points)} points, "
              f"noise={noise_mm}mm, "
              f"rotation={rotation_deg}°, "
              f"dropout={dropout*100:.0f}%")
    return pcd_fake


def load_real_scan(ply_path, verbose=True):
    """
    Load a real depth camera scan from a .ply file.
    Applies PCA alignment + scale normalization to match database format.
    """
    
    if not os.path.exists(ply_path):
        raise FileNotFoundError(f"Scan file not found: {ply_path}")

    pcd = o3d.io.read_point_cloud(ply_path)
    if verbose:
        print(f"Loaded real scan: {len(pcd.points)} points from {ply_path}")

    pcd = pca_align(pcd, verbose=verbose)
    pcd = normalize_scale(pcd, verbose=verbose)
    return pcd


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


def main():
    parser = argparse.ArgumentParser(description="CT Patient Matching")
    parser.add_argument("--mode", default="segmentation",
                    choices=["segmentation", "ct_threshold"],
                    help="Which point cloud database to use (default: segmentation)")
    parser.add_argument("--fake", default="s1388",
                        help="Generate fake scan from this patient ID (default: s1388)")
    parser.add_argument("--real", default=None,
                        help="Path to real depth camera .ply scan")
    parser.add_argument("--threshold", type=float, default=0.55,
                        help="Match confidence threshold 0.0-1.0 ")
    parser.add_argument("--retries", type=int, default=3,
                        help="Max retries before fallback (default: 3)")
    parser.add_argument("--voxel-size", type=float, default=10.0,
                        help="ICP voxel size in mm (default: 10.0)")
    parser.add_argument("--noise", type=float, default=5.0,
                        help="Noise in mm for fake scan (default: 5.0)")
    parser.add_argument("--rotation", type=float, default=15.0,
                        help="Rotation in degrees for fake scan (default: 15.0)")
    parser.add_argument("--dropout", type=float, default=0.3,
                        help="Point dropout 0.0-1.0 for fake scan (default: 0.3)")
    parser.add_argument("--verbose", action="store_true", default=True)
    args = parser.parse_args()

    # Load database
    database = load_database(verbose=args.verbose,mode=args.mode)
    if not database:
        print("ERROR: No point clouds in database. Run run_preprocess.py first.")
        return

    # Get scan to match
    if args.real:
        print(f"\nUsing real scan: {args.real}")
        real_pcd = load_real_scan(args.real, verbose=args.verbose)
    else:
        print(f"\nGenerating fake scan from {args.fake}...")
        real_pcd = make_fake_scan(
            args.fake,
            noise_mm=args.noise,
            rotation_deg=args.rotation,
            dropout=args.dropout,
            verbose=args.verbose,
            mode = args.mode
        )

    # Run matching
    from matching.matcher import match_against_database
    print(f"\nRunning matching against {len(database)} patients...")
    all_results = match_against_database(real_pcd, database,
                                          voxel_size=args.voxel_size,
                                          verbose=args.verbose)

    result = find_best_match(real_pcd, database,
                             threshold=args.threshold,
                             max_retries=args.retries,
                             voxel_size=args.voxel_size,
                             verbose=False)

    print_results(result, all_results)


if __name__ == "__main__":
    main()