import numpy as np
import open3d as o3d


def pca_align(pcd, target_up=(0, 1, 0), verbose=True):
    """
    Rotate point cloud so its principal (longest) axis aligns
    with target_up. Default: Y up (Unity convention).
    Returns aligned PointCloud.
    """
    points    = np.asarray(pcd.points)
    cov       = np.cov(points.T)
    eigvals, eigvecs = np.linalg.eigh(cov)

    principal = eigvecs[:, np.argmax(eigvals)]
    target    = np.array(target_up, dtype=float)
    target   /= np.linalg.norm(target)

    axis      = np.cross(principal, target)
    axis_norm = np.linalg.norm(axis)

    if axis_norm < 1e-6:
        if verbose:
            print("  Already aligned, no rotation needed")
        return pcd

    axis  = axis / axis_norm
    angle = np.arccos(np.clip(np.dot(principal, target), -1.0, 1.0))
    R     = o3d.geometry.get_rotation_matrix_from_axis_angle(axis * angle)

    aligned = o3d.geometry.PointCloud(pcd)
    aligned.rotate(R, center=np.zeros(3))

    if verbose:
        print(f"  PCA aligned: rotated {np.degrees(angle):.1f}° to Y-up")
    return aligned


def normalize_scale(pcd, target_height=1000, verbose=True):
    """
    Scale point cloud so its Y extent equals target_height (mm).
    Makes matching scale-invariant across different patient heights.
    """
    points = np.asarray(pcd.points)
    height = points[:, 1].max() - points[:, 1].min()
    if height < 1e-6:
        return pcd
    scale  = target_height / height
    scaled = o3d.geometry.PointCloud(pcd)
    scaled.points = o3d.utility.Vector3dVector(points * scale)
    if verbose:
        print(f"  Scale normalized: {height:.1f}mm → {target_height}mm (factor {scale:.3f})")
    return scaled
