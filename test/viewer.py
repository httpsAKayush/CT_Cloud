import open3d as o3d
import numpy as np
import matplotlib.pyplot as plt

pcd = o3d.io.read_point_cloud('/home/zer0/ct_pipeline/pointclouds/s1388.ply')
pts = np.asarray(pcd.points)
print('X range:', pts[:,0].min(), pts[:,0].max())
print('Y range:', pts[:,1].min(), pts[:,1].max())
print('Z range:', pts[:,2].min(), pts[:,2].max())

# Show from front (X-Y plane) and side (Z-Y plane)
fig, axes = plt.subplots(1, 3, figsize=(15, 6))

axes[0].scatter(pts[:,0], pts[:,1], s=0.3, c=pts[:,1], cmap='viridis')
axes[0].set_title('Front (X-Y)')
axes[0].set_aspect('equal')

axes[1].scatter(pts[:,2], pts[:,1], s=0.3, c=pts[:,1], cmap='viridis')
axes[1].set_title('Side (Z-Y)')
axes[1].set_aspect('equal')

axes[2].scatter(pts[:,0], pts[:,2], s=0.3, c=pts[:,2], cmap='viridis')
axes[2].set_title('Top (X-Z)')
axes[2].set_aspect('equal')

plt.savefig('/home/zer0/ct_pipeline/s1388_views.png', dpi=150, bbox_inches='tight')
print('Saved to ~/ct_pipeline/s1388_views.png')
