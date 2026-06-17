import os
import sys
import glob
import numpy as np
import nibabel as nib
from skimage import measure
import open3d as o3d

# ── CONFIG ───────────────────────────────────────────────────────────────────
DATASET_DIR = os.path.expanduser("~/Downloads/Totalsegmentator_dataset_small_v201/wholebody")
OUTPUT_DIR  = os.path.expanduser("~/ct_pipeline/test")
PATIENTS    = ["s1369", "s1371", "s1384", "s1388", "s1397"]
POINT_CLOUD_POINTS = 10000  # downsample to this many points per patient
# ─────────────────────────────────────────────────────────────────────────────

os.makedirs(os.path.join(OUTPUT_DIR, "pointclouds"), exist_ok=True)
os.makedirs(os.path.join(OUTPUT_DIR, "models"),      exist_ok=True)

def load_and_merge_segmentations(seg_dir):
    """Load all .nii.gz masks in seg_dir and merge into one binary volume."""
    files = glob.glob(os.path.join(seg_dir, "*.nii.gz"))
    if not files:
        print(f"  WARNING: no segmentation files found in {seg_dir}")
        return None, None

    print(f"  Loading {len(files)} segmentation masks...")
    ref = nib.load(files[0])
    affine = ref.affine
    merged = np.zeros(ref.shape, dtype=np.uint8)

    for f in files:
        data = nib.load(f).get_fdata()
        merged = np.logical_or(merged, data > 0).astype(np.uint8)

    print(f"  Merged volume shape: {merged.shape}")
    return merged, affine

def volume_to_pointcloud(volume, affine, n_points):
    """Extract surface mesh via marching cubes → sample points → return point cloud."""
    print(f"  Running marching cubes...")
    verts, faces, normals, _ = measure.marching_cubes(volume, level=0.5)

    # Transform verts from voxel space to world space (mm)
    verts_h = np.hstack([verts, np.ones((len(verts), 1))])
    verts_world = (affine @ verts_h.T).T[:, :3]

    # Normalize to zero mean
    verts_world -= verts_world.mean(axis=0)

    # Create Open3D mesh → sample point cloud
    mesh = o3d.geometry.TriangleMesh()
    mesh.vertices  = o3d.utility.Vector3dVector(verts_world)
    mesh.triangles = o3d.utility.Vector3iVector(faces)
    mesh.compute_vertex_normals()

    pcd = mesh.sample_points_uniformly(number_of_points=n_points)
    print(f"  Point cloud: {n_points} points")
    return pcd

def align_to_standing(pcd):
    """
    CT scans are acquired with patient lying down (superior-inferior along Z).
    Rotate so the long body axis aligns with Y (standing upright).
    Uses PCA to find principal axis and rotates it to Y.
    """
    points = np.asarray(pcd.points)

    # PCA
    cov = np.cov(points.T)
    eigenvalues, eigenvectors = np.linalg.eigh(cov)
    # Largest eigenvalue = principal axis (long body axis)
    principal = eigenvectors[:, np.argmax(eigenvalues)]

    # Rotation from principal axis to Y axis
    target = np.array([0, 1, 0])
    axis   = np.cross(principal, target)
    axis_norm = np.linalg.norm(axis)

    if axis_norm < 1e-6:
        return pcd  # already aligned

    axis   = axis / axis_norm
    angle  = np.arccos(np.clip(np.dot(principal, target), -1, 1))
    R_mat  = o3d.geometry.get_rotation_matrix_from_axis_angle(axis * angle)

    pcd_aligned = o3d.geometry.PointCloud(pcd)
    pcd_aligned.rotate(R_mat, center=np.zeros(3))
    print(f"  Aligned principal axis to Y (rotation angle: {np.degrees(angle):.1f}°)")
    return pcd_aligned

def process_patient(patient_id):
    print(f"\n{'='*50}")
    print(f"Processing {patient_id}...")

    seg_dir = os.path.join(DATASET_DIR, patient_id, "segmentations")
    if not os.path.exists(seg_dir):
        print(f"  ERROR: segmentation dir not found: {seg_dir}")
        return

    # Step 1 — merge all segmentation masks
    volume, affine = load_and_merge_segmentations(seg_dir)
    if volume is None:
        return

    # Step 2 — extract surface + build point cloud
    pcd = volume_to_pointcloud(volume, affine, POINT_CLOUD_POINTS)

    # Step 3 — align to standing orientation
    pcd = align_to_standing(pcd)

    # Step 4 — save point cloud
    out_ply = os.path.join(OUTPUT_DIR, "pointclouds", f"{patient_id}.ply")
    o3d.io.write_point_cloud(out_ply, pcd)
    print(f"  Saved point cloud: {out_ply}")

    print(f"  Done: {patient_id}")

# ── MAIN ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Installing dependencies if needed...")
    os.system(f"{sys.executable} -m pip install nibabel scikit-image open3d numpy --quiet")

    for patient in PATIENTS:
        process_patient(patient)

    print(f"\n{'='*50}")
    print(f"Preprocessing complete.")
    print(f"Point clouds saved to: {OUTPUT_DIR}/pointclouds/")
    print(f"  s1369.ply, s1371.ply, s1384.ply, s1388.ply, s1397.ply")
