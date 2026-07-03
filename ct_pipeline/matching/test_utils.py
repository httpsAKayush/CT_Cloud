"""Testing helpers — generate a fake scan by perturbing an existing point cloud."""
import os
import numpy as np
import open3d as o3d

from ct_pipeline.config import RAW_PLY_DIR, UNION_PLY_DIR


def make_fake_scan(patient_id, mode="raw", noise_mm=5.0, rotation_deg=15.0, dropout=0.3, verbose=True):
    """
    Generate a fake real-world scan by perturbing an existing database point cloud.
    Used for testing the matching pipeline without a real depth camera / reference scan.
    """
    ply_dir = RAW_PLY_DIR if mode == "raw" else UNION_PLY_DIR
    path = os.path.join(ply_dir, f"{patient_id}.ply")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Point cloud not found: {path}")

    pcd    = o3d.io.read_point_cloud(path)
    points = np.asarray(pcd.points).copy()

    points += np.random.normal(0, noise_mm, points.shape)

    angle = np.radians(rotation_deg)
    R = o3d.geometry.get_rotation_matrix_from_axis_angle([angle * 0.3, angle, angle * 0.1])
    pcd_fake = o3d.geometry.PointCloud()
    pcd_fake.points = o3d.utility.Vector3dVector(points)
    pcd_fake.rotate(R, center=np.zeros(3))

    n_keep = int(len(points) * (1.0 - dropout))
    indices = np.random.choice(len(points), n_keep, replace=False)
    pcd_fake = pcd_fake.select_by_index(indices)

    if verbose:
        print(f"Fake scan from {patient_id}: {len(pcd_fake.points)} points, "
              f"noise={noise_mm}mm, rotation={rotation_deg}°, dropout={dropout*100:.0f}%")
    return pcd_fake
