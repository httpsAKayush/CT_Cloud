import numpy as np
from skimage import measure
import open3d as o3d


def volume_to_pointcloud(volume, affine, n_points=10000, level=0.5, verbose=True):
    """
    Run marching cubes on binary volume -> sample point cloud.
    Returns open3d PointCloud in world space (mm), zero-centered.
    """
    if verbose:
        print(f"  Running marching cubes...")

    verts, faces, _, _ = measure.marching_cubes(volume, level=level)

    verts_h     = np.hstack([verts, np.ones((len(verts), 1))])
    verts_world = (affine @ verts_h.T).T[:, :3]
    verts_world -= verts_world.mean(axis=0)

    mesh           = o3d.geometry.TriangleMesh()
    mesh.vertices  = o3d.utility.Vector3dVector(verts_world)
    mesh.triangles = o3d.utility.Vector3iVector(faces)
    mesh.compute_vertex_normals()

    pcd = mesh.sample_points_uniformly(number_of_points=n_points)

    if verbose:
        print(f"  Point cloud: {n_points} points sampled")
    return pcd
