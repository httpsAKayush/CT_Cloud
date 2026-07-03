import pyrealsense2 as rs
import numpy as np
import cv2, os
import open3d as o3d
import copy
import os
os.environ["QT_QPA_PLATFORM"] = "xcb"
os.environ["XDG_SESSION_TYPE"] = "x11"  # sometimes needed for GLFW/GLEW too
from ct_pipeline.config import REFERENCE_DIR

# direc = os.path.expanduser('~/ct_pipeline')
# exp_ID = '1'
direc = REFERENCE_DIR
# direc = os.path.join(direc, exp_ID)
os.makedirs(direc, exist_ok=True)

pipeline = rs.pipeline()
config = rs.config()

config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

pipeline.start(config)

depth_sensor = pipeline.get_active_profile().get_device().first_depth_sensor()
depth_scale = depth_sensor.get_depth_scale()
print(f"Depth Scale: {depth_scale} meters")

align_to = rs.stream.color
align = rs.align(align_to)

# ---- Trackbar window ----
WIN = 'Segmentation Tuner'
cv2.namedWindow(WIN, cv2.WINDOW_NORMAL)
cv2.resizeWindow(WIN, 1600, 900)

cv2.createTrackbar('Near (cm)', WIN, 40, 100, lambda x: None)
cv2.createTrackbar('Far (cm)', WIN, 70, 100, lambda x: None)

cv2.createTrackbar('H min', WIN, 0, 179, lambda x: None)
cv2.createTrackbar('H max', WIN, 25, 179, lambda x: None)
cv2.createTrackbar('S min', WIN, 20, 255, lambda x: None)
cv2.createTrackbar('S max', WIN, 150, 255, lambda x: None)
cv2.createTrackbar('V min', WIN, 70, 255, lambda x: None)
cv2.createTrackbar('V max', WIN, 255, 255, lambda x: None)

cv2.createTrackbar('Mode (0=D,1=C,2=D&C)', WIN, 2, 2, lambda x: None)


def segment_by_depth(depth_image, depth_scale, near_m, far_m):
    depth_m = depth_image.astype(np.float32) * depth_scale
    mask = ((depth_m > near_m) & (depth_m < far_m)).astype(np.uint8) * 255
    return mask


def segment_by_color(color_image, h_min, h_max, s_min, s_max, v_min, v_max):
    hsv_image = cv2.cvtColor(color_image, cv2.COLOR_BGR2HSV)
    lower = np.array([h_min, s_min, v_min])
    upper = np.array([h_max, s_max, v_max])
    return cv2.inRange(hsv_image, lower, upper)


def mask_to_point_cloud(depth_frame, color_frame, mask, depth_scale):
    """Convert a single masked frame into an Open3D point cloud."""
    depth_image = np.asanyarray(depth_frame.get_data())
    color_image = np.asanyarray(color_frame.get_data())
    color_intrinsics = color_frame.profile.as_video_stream_profile().intrinsics

    ys, xs = np.where(mask == 255)
    points = []
    colors = []

    for y, x in zip(ys, xs):
        depth = depth_image[y, x] * depth_scale
        if depth > 0:
            point = rs.rs2_deproject_pixel_to_point(color_intrinsics, [float(x), float(y)], float(depth))
            points.append(point)
            colors.append(color_image[y, x][::-1] / 255.0)  # BGR -> RGB

    pcd = o3d.geometry.PointCloud()
    if len(points) > 0:
        pcd.points = o3d.utility.Vector3dVector(np.array(points))
        pcd.colors = o3d.utility.Vector3dVector(np.array(colors))
    return pcd


def preprocess_for_icp(pcd, voxel_size=0.003):
    """Downsample + estimate normals, needed for point-to-plane ICP."""
    down = pcd.voxel_down_sample(voxel_size)
    down.estimate_normals(
        o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 2, max_nn=30)
    )
    return down


def preprocess_for_global_reg(pcd, voxel_size):
    down = pcd.voxel_down_sample(voxel_size)
    down.estimate_normals(
        o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 2, max_nn=30)
    )
    fpfh = o3d.pipelines.registration.compute_fpfh_feature(
        down,
        o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 5, max_nn=100)
    )
    return down, fpfh


def global_registration(source_down, target_down, source_fpfh, target_fpfh, voxel_size):
    distance_threshold = voxel_size * 1.5
    result = o3d.pipelines.registration.registration_ransac_based_on_feature_matching(
        source_down, target_down, source_fpfh, target_fpfh, True,
        distance_threshold,
        o3d.pipelines.registration.TransformationEstimationPointToPoint(False),
        3,
        [
            o3d.pipelines.registration.CorrespondenceCheckerBasedOnEdgeLength(0.9),
            o3d.pipelines.registration.CorrespondenceCheckerBasedOnDistance(distance_threshold)
        ],
        o3d.pipelines.registration.RANSACConvergenceCriteria(4000000, 500)
    )
    return result


def register_and_merge(clouds, voxel_size=0.003, icp_threshold=0.02, min_fitness=0.15):
    merged = copy.deepcopy(clouds[0])
    skipped = []

    for i in range(1, len(clouds)):
        source_down, source_fpfh = preprocess_for_global_reg(clouds[i], voxel_size)
        target_down, target_fpfh = preprocess_for_global_reg(merged, voxel_size)

        # Step 1: coarse global alignment (no identity assumption)
        global_result = global_registration(source_down, target_down, source_fpfh, target_fpfh, voxel_size)
        print(f"Cloud {i} global -> fitness: {global_result.fitness:.3f}")

        if global_result.fitness < 0.1:
            print(f"  SKIPPED cloud {i}: global registration failed to find any coarse alignment.")
            skipped.append(i)
            continue

        # Step 2: refine with ICP, starting from the global result instead of identity
        source = preprocess_for_icp(clouds[i], voxel_size)
        target = preprocess_for_icp(merged, voxel_size)

        reg = o3d.pipelines.registration.registration_icp(
            source, target, icp_threshold, global_result.transformation,
            o3d.pipelines.registration.TransformationEstimationPointToPlane(),
            o3d.pipelines.registration.ICPConvergenceCriteria(max_iteration=50)
        )
        print(f"Cloud {i} ICP refine -> fitness: {reg.fitness:.3f}, RMSE: {reg.inlier_rmse:.5f}")

        if reg.fitness < min_fitness:
            print(f"  SKIPPED cloud {i}: ICP fitness too low ({reg.fitness:.3f} < {min_fitness}).")
            skipped.append(i)
            continue

        clouds[i].transform(reg.transformation)
        merged += clouds[i]
        merged = merged.voxel_down_sample(voxel_size)

    if skipped:
        print(f"\n{len(skipped)} cloud(s) skipped: {skipped}. Recapture with more overlap.")

    return merged
    
captured_clouds = []

try:
    while True:
        frames = pipeline.wait_for_frames()
        aligned_frames = align.process(frames)
        depth_frame = aligned_frames.get_depth_frame()
        color_frame = aligned_frames.get_color_frame()

        if not depth_frame or not color_frame:
            continue

        depth_image = np.asanyarray(depth_frame.get_data())
        color_image = np.asanyarray(color_frame.get_data())

        near_m = cv2.getTrackbarPos('Near (cm)', WIN) / 100.0
        far_m = cv2.getTrackbarPos('Far (cm)', WIN) / 100.0

        h_min = cv2.getTrackbarPos('H min', WIN)
        h_max = cv2.getTrackbarPos('H max', WIN)
        s_min = cv2.getTrackbarPos('S min', WIN)
        s_max = cv2.getTrackbarPos('S max', WIN)
        v_min = cv2.getTrackbarPos('V min', WIN)
        v_max = cv2.getTrackbarPos('V max', WIN)

        mode = cv2.getTrackbarPos('Mode (0=D,1=C,2=D&C)', WIN)

        depth_mask = segment_by_depth(depth_image, depth_scale, near_m, far_m)
        color_mask = segment_by_color(color_image, h_min, h_max, s_min, s_max, v_min, v_max)

        if mode == 0:
            mask = depth_mask
        elif mode == 1:
            mask = color_mask
        else:
            mask = cv2.bitwise_and(depth_mask, color_mask)

        segmented_image = color_image.copy()
        segmented_image[mask == 255] = (0, 0, 255)
        segmented_image = cv2.addWeighted(color_image, 0.7, segmented_image, 0.3, 0)

        depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.03), cv2.COLORMAP_JET)

        cy, cx = depth_image.shape[0] // 2, depth_image.shape[1] // 2
        center_depth_cm = depth_image[cy, cx] * depth_scale * 100
        cv2.circle(segmented_image, (cx, cy), 4, (0, 255, 0), -1)

        images = np.hstack((segmented_image, depth_colormap))

        # ---- Readable text overlay of all current values ----
        overlay_lines = [
            f"Near:{near_m*100:.1f}cm  Far:{far_m*100:.1f}cm",
            f"H:[{h_min},{h_max}]  S:[{s_min},{s_max}]  V:[{v_min},{v_max}]",
            f"Mode:{mode} (0=Depth,1=Color,2=Both)  Captured:{len(captured_clouds)}",
            f"Center depth:{center_depth_cm:.1f}cm",
        ]

        y0 = 30
        for i, line in enumerate(overlay_lines):
            y = y0 + i * 28
            cv2.putText(images, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 4)
            cv2.putText(images, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 1)

        controls_y = y0 + len(overlay_lines) * 28
        cv2.putText(images, "c=capture  f=finish&fuse  q=quit", (10, controls_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 4)
        cv2.putText(images, "c=capture  f=finish&fuse  q=quit", (10, controls_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)

        cv2.imshow(WIN, images)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('c'):
            pcd = mask_to_point_cloud(depth_frame, color_frame, mask, depth_scale)
            if len(pcd.points) == 0:
                print("Empty mask — nothing captured. Adjust sliders and retry.")
                continue
            captured_clouds.append(pcd)
            print(f"Captured cloud #{len(captured_clouds)} ({len(pcd.points)} points). "
                  f"Move camera and press 'c' again, or 'f' to finish.")
        elif key == ord('f'):
            if len(captured_clouds) == 0:
                print("No clouds captured yet.")
                continue
            print(f"Fusing {len(captured_clouds)} captures...")
            fused = register_and_merge(captured_clouds)
            out_path = f"{direc}/phantom_pcd_fused.ply"
            o3d.io.write_point_cloud(out_path, fused)
            print(f"Fused point cloud saved as {out_path} ({len(fused.points)} points)")
            o3d.visualization.draw_geometries([fused], window_name="Fused Point Cloud")
            break

finally:
    pipeline.stop()
    cv2.destroyAllWindows()