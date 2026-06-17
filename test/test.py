import nibabel as nib
import numpy as np
from skimage import measure, morphology
import open3d as o3d
import matplotlib.pyplot as plt
from scipy import ndimage

# Load raw CT
ct = nib.load('/home/zer0/Downloads/Totalsegmentator_dataset_small_v201/wholebody/s1388/ct.nii.gz')
data = ct.get_fdata()
affine = ct.affine

print(f"CT shape: {data.shape}")
print(f"HU range: {data.min():.0f} to {data.max():.0f}")

# Threshold at -200 HU
binary = (data > -200).astype(np.uint8)

# Remove CT table — keep only largest connected component (the body)
print("Removing table (keeping largest connected component)...")
labeled, num_features = ndimage.label(binary)
print(f"Found {num_features} connected components")
sizes = ndimage.sum(binary, labeled, range(1, num_features + 1))
largest = np.argmax(sizes) + 1
binary_clean = (labeled == largest).astype(np.uint8)
print(f"Kept component size: {sizes[largest-1]:.0f} voxels")

# Marching cubes
print("Running marching cubes...")
verts, faces, _, _ = measure.marching_cubes(binary_clean, level=0.5)

# World space
verts_h = np.hstack([verts, np.ones((len(verts), 1))])
verts_world = (affine @ verts_h.T).T[:, :3]
verts_world -= verts_world.mean(axis=0)

# Sample point cloud
mesh = o3d.geometry.TriangleMesh()
mesh.vertices = o3d.utility.Vector3dVector(verts_world)
mesh.triangles = o3d.utility.Vector3iVector(faces)
pcd = mesh.sample_points_uniformly(number_of_points=10000)

# PCA alignment
print("Aligning via PCA...")
points = np.asarray(pcd.points)
cov = np.cov(points.T)
eigenvalues, eigenvectors = np.linalg.eigh(cov)
principal = eigenvectors[:, np.argmax(eigenvalues)]
target = np.array([0, 1, 0])
axis = np.cross(principal, target)
axis_norm = np.linalg.norm(axis)
if axis_norm > 1e-6:
    axis = axis / axis_norm
    angle = np.arccos(np.clip(np.dot(principal, target), -1, 1))
    R = o3d.geometry.get_rotation_matrix_from_axis_angle(axis * angle)
    pcd.rotate(R, center=np.zeros(3))
    print(f"Rotated {np.degrees(angle):.1f} degrees")

# Visualize
pts = np.asarray(pcd.points)
fig, axes = plt.subplots(1, 2, figsize=(12, 6))
axes[0].scatter(pts[:,0], pts[:,1], s=0.3, c=pts[:,1], cmap='viridis')
axes[0].set_title('Front (X-Y) - CT threshold fixed')
axes[0].set_aspect('equal')
axes[1].scatter(pts[:,2], pts[:,1], s=0.3, c=pts[:,1], cmap='viridis')
axes[1].set_title('Side (Z-Y) - CT threshold fixed')
axes[1].set_aspect('equal')

plt.savefig('/home/zer0/ct_pipeline/test/s1388_ct_fixed.png', dpi=150, bbox_inches='tight')
print('Saved to ~/ct_pipeline/test/s1388_ct_fixed.png')
