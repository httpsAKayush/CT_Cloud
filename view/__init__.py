import os
import sys
import argparse
import numpy as np
import matplotlib.pyplot as plt
import open3d as o3d

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import PLY_DIR, PATIENTS


def load_ply(path):
    pcd = o3d.io.read_point_cloud(path)
    return np.asarray(pcd.points)


def plot_patient(pts, patient_id, save_dir=None):
    fig, axes = plt.subplots(1, 3, figsize=(15, 6))
    fig.suptitle(f"Patient: {patient_id}", fontsize=14)

    views = [
        (0, 1, "Front (X-Y)"),
        (2, 1, "Side (Z-Y)"),
        (0, 2, "Top (X-Z)"),
    ]

    for ax, (xi, yi, title) in zip(axes, views):
        ax.scatter(pts[:, xi], pts[:, yi], s=0.3, c=pts[:, yi], cmap="viridis")
        ax.set_title(title)
        ax.set_aspect("equal")
        ax.set_xlabel(["X", "Y", "Z"][xi])
        ax.set_ylabel(["X", "Y", "Z"][yi])

    plt.tight_layout()

    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        out = os.path.join(save_dir, f"{patient_id}_views.png")
        plt.savefig(out, dpi=150, bbox_inches="tight")
        print(f"  Saved: {out}")
        plt.close()
    else:
        plt.show()


def print_stats(pts, patient_id):
    print(f"\n── {patient_id} ──────────────────────────")
    print(f"  Points : {len(pts)}")
    print(f"  X range: {pts[:,0].min():.1f} → {pts[:,0].max():.1f} mm")
    print(f"  Y range: {pts[:,1].min():.1f} → {pts[:,1].max():.1f} mm")
    print(f"  Z range: {pts[:,2].min():.1f} → {pts[:,2].max():.1f} mm")
    height = pts[:,1].max() - pts[:,1].min()
    width  = pts[:,0].max() - pts[:,0].min()
    depth  = pts[:,2].max() - pts[:,2].min()
    print(f"  Height : {height:.1f} mm")
    print(f"  Width  : {width:.1f} mm")
    print(f"  Depth  : {depth:.1f} mm")


def resolve_patients(args_patients, args_ply, args_all):
    """Resolve which .ply files to visualize based on CLI args."""
    targets = {}  # patient_id → ply_path

    if args_all:
        for pid in PATIENTS:
            path = os.path.join(PLY_DIR, f"{pid}.ply")
            if os.path.exists(path):
                targets[pid] = path
            else:
                print(f"  WARNING: {path} not found, skipping")
        return targets

    if args_ply:
        for p in args_ply:
            pid = os.path.splitext(os.path.basename(p))[0]
            targets[pid] = p
        return targets

    if args_patients:
        for pid in args_patients:
            path = os.path.join(PLY_DIR, f"{pid}.ply")
            if os.path.exists(path):
                targets[pid] = path
            else:
                print(f"  WARNING: {path} not found, skipping")
        return targets

    return targets


def main():
    parser = argparse.ArgumentParser(
        description="Visualize CT point clouds",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Examples:
  # View one patient
  python view/visualize.py -p s1388

  # View multiple patients
  python view/visualize.py -p s1388 s1371 s1369

  # View all patients
  python view/visualize.py --all

  # Point directly at a .ply file
  python view/visualize.py --ply /path/to/custom.ply

  # Save images instead of showing interactively
  python view/visualize.py --all --save

  # Save to custom folder
  python view/visualize.py -p s1388 --save --save-dir ~/Desktop/views
        """
    )

    parser.add_argument("-p", "--patients", nargs="+",
                        help="Patient IDs to visualize (e.g. s1388 s1371)")
    parser.add_argument("--ply", nargs="+",
                        help="Direct paths to .ply files")
    parser.add_argument("--all", action="store_true",
                        help="Visualize all patients in config")
    parser.add_argument("--save", action="store_true",
                        help="Save images instead of showing interactively")
    parser.add_argument("--save-dir", default=None,
                        help="Where to save images (default: ct_pipeline/view/output/)")
    parser.add_argument("--stats", action="store_true", default=True,
                        help="Print point cloud statistics (default: True)")

    args = parser.parse_args()

    # Default: show all if nothing specified
    if not args.patients and not args.ply and not args.all:
        print("No input specified — showing all patients. Use -h for options.")
        args.all = True

    targets = resolve_patients(args.patients, args.ply, args.all)

    if not targets:
        print("No valid point clouds found. Run run_preprocess.py first.")
        return

    save_dir = None
    if args.save:
        save_dir = args.save_dir or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "output"
        )

    for pid, path in targets.items():
        print(f"Loading {pid} from {path}...")
        pts = load_ply(path)
        if args.stats:
            print_stats(pts, pid)
        plot_patient(pts, pid, save_dir=save_dir)


if __name__ == "__main__":
    main()