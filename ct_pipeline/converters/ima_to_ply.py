"""Convert a folder of .IMA slices directly into a reference .ply for the matching pipeline."""
import os
import sys
import numpy as np
import open3d as o3d
from skimage.measure import marching_cubes

from ct_pipeline.ingest.ima_loader import load_ima_volume
from ct_pipeline.config import REFERENCE_DIR


def volume_to_pointcloud(volume, spacing, hu_threshold=-200):
    """
    Threshold at hu_threshold to isolate body surface (air ~ -1000 HU,
    soft tissue -100 to +100 HU). -200 captures body outline cleanly.
    """
    binary = (volume > hu_threshold).astype(np.uint8)

    verts, faces, normals, _ = marching_cubes(binary, level=0.5, spacing=spacing)
    # verts are in (Z, Y, X) order from marching_cubes with spacing applied
    pts = verts[:, [2, 1, 0]] * 0.001  # mm -> metres, reorder to X,Y,Z

    print(f"Marching cubes produced {len(pts)} vertices")
    return pts, normals


def save_ply(pts, output_path=None):
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(pts)

    pcd = pcd.voxel_down_sample(voxel_size=0.005)
    print(f"After downsampling: {len(pcd.points)} points")

    if output_path is None:
        output_path = os.path.join(REFERENCE_DIR, "reference.ply")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    o3d.io.write_point_cloud(output_path, pcd)
    print(f"Saved: {output_path}")
    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m ct_pipeline.converters.ima_to_ply /path/to/IMA_folder [output.ply]")
        sys.exit(1)

    ima_folder = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else None

    volume, spacing = load_ima_volume(ima_folder)
    pts, _ = volume_to_pointcloud(volume, spacing, hu_threshold=-200)
    saved = save_ply(pts, out)

    print("\nDone. Run matching next:")
    print("  python -m ct_pipeline.cli test-match")
