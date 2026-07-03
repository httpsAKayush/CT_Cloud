import os
import numpy as np
import matplotlib.pyplot as plt
import open3d as o3d

from ct_pipeline.config import RAW_PLY_DIR, UNION_PLY_DIR


def load_ply(path):
    pcd = o3d.io.read_point_cloud(path)
    return np.asarray(pcd.points)


def plot_patient(pts, patient_id, save_dir=None, source_type="union"):
    fig, axes = plt.subplots(1, 3, figsize=(15, 6))
    fig.suptitle(f"Patient: {patient_id} [{source_type}]", fontsize=14)

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
        sub = os.path.join(save_dir, source_type if source_type in ("union", "raw") else "custom")
        os.makedirs(sub, exist_ok=True)
        out = os.path.join(sub, f"{patient_id}_views.png")
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


def _discover_all_patient_ids():
    """Union of patient IDs discovered from both raw/ and union/ ply dirs."""
    ids = set()
    for d in (RAW_PLY_DIR, UNION_PLY_DIR):
        if os.path.exists(d):
            ids.update(os.path.splitext(f)[0] for f in os.listdir(d) if f.endswith(".ply"))
    return sorted(ids)


def resolve_patients(args_patients, args_all, source):
    targets = {}

    if source == "union":
        dirs = [("union", UNION_PLY_DIR)]
    elif source == "raw":
        dirs = [("raw", RAW_PLY_DIR)]
    else:
        dirs = [("union", UNION_PLY_DIR), ("raw", RAW_PLY_DIR)]

    patient_list = _discover_all_patient_ids() if args_all else args_patients
    if not patient_list:
        return targets

    for pid in patient_list:
        for cloud_type, base_dir in dirs:
            path = os.path.join(base_dir, f"{pid}.ply")
            if os.path.exists(path):
                targets[f"{pid}_{cloud_type}"] = (pid, cloud_type, path)
            else:
                print(f"WARNING: {path} not found")

    return targets


def pointcloud_from_seg_folder(seg_folder, verbose=True):
    """Generate point cloud directly from a segmentation folder on the fly (nii_gz only)."""
    from ct_pipeline.extract.segmentation import merge_segmentations
    from ct_pipeline.pointcloud.surface import volume_to_pointcloud
    from ct_pipeline.pointcloud.alignment import pca_align, normalize_scale
    from ct_pipeline.config import N_POINTS, MARCHING_CUBES_LEVEL, TARGET_UP_AXIS

    if not seg_folder.endswith("segmentations") and not seg_folder.endswith("segmentations/"):
        candidate = os.path.join(seg_folder, "segmentations")
        patient_dir = seg_folder if os.path.exists(candidate) else os.path.dirname(seg_folder)
    else:
        patient_dir = os.path.dirname(seg_folder.rstrip("/"))

    if verbose:
        print(f"  Reading segmentations from: {os.path.join(patient_dir, 'segmentations')}")

    volume, affine = merge_segmentations(patient_dir, verbose=verbose)
    pcd = volume_to_pointcloud(volume, affine, n_points=N_POINTS,
                               level=MARCHING_CUBES_LEVEL, verbose=verbose)
    pcd = pca_align(pcd, target_up=TARGET_UP_AXIS, verbose=verbose)
    pcd = normalize_scale(pcd, verbose=verbose)
    return np.asarray(pcd.points)
