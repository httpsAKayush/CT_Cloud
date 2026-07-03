"""Convert a phantom .stl scan into a reference .ply for the matching pipeline."""
import os
import sys
import numpy as np
import open3d as o3d

from ct_pipeline.config import N_POINTS, REFERENCE_DIR


def stl_to_ply(stl_path, output_path=None, n_points=N_POINTS):
    mesh = o3d.io.read_triangle_mesh(stl_path)
    if not mesh.has_vertices():
        raise ValueError(f"Failed to load STL: {stl_path}")

    print(f"Mesh: {len(mesh.vertices)} vertices, {len(mesh.triangles)} triangles")

    pcd = mesh.sample_points_uniformly(number_of_points=n_points)

    # Convert mm -> metres (STL files are typically in mm)
    pts = np.asarray(pcd.points) * 0.001
    pcd.points = o3d.utility.Vector3dVector(pts)

    if output_path is None:
        output_path = os.path.join(REFERENCE_DIR, "reference.ply")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    o3d.io.write_point_cloud(output_path, pcd)
    print(f"Saved {len(pcd.points)} points -> {output_path}")
    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m ct_pipeline.converters.stl_to_ply /path/to/phantom.stl [output.ply]")
        sys.exit(1)

    stl_path = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else None
    saved = stl_to_ply(stl_path, out)
    print("\nVisualize:")
    print(f"  python -m ct_pipeline.cli view --ply {saved}")
