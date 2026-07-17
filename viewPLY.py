import os
os.environ.pop("WAYLAND_DISPLAY", None)  # forces XWayland fallback if on Wayland; no-op on X11-native systems

import open3d as o3d
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "output.ply"

pcd = o3d.io.read_point_cloud(path)

if len(pcd.points) == 0:
    print(f"ERROR: no points loaded from '{path}' — check the file exists and has a supported extension (.ply, .pcd, .xyz)")
    sys.exit(1)

print(pcd)

o3d.visualization.draw_geometries(
    [pcd],
    window_name="PLY Viewer",
    width=1280, height=720,
    point_show_normal=False
)