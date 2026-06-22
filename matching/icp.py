import numpy as np
import open3d as o3d


def preprocess_pointcloud(pcd, voxel_size=5.0):
    """Downsample + compute FPFH features."""
    pcd_down = pcd.voxel_down_sample(voxel_size)
    pcd_down.estimate_normals(
        o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 2, max_nn=30)
    )
    fpfh = o3d.pipelines.registration.compute_fpfh_feature(
        pcd_down,
        o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 5, max_nn=100)
    )
    return pcd_down, fpfh


def global_registration(source_down, target_down, source_fpfh, target_fpfh, voxel_size=5.0):
    """RANSAC global registration."""
    distance_threshold = voxel_size * 1.5
    result = o3d.pipelines.registration.registration_ransac_based_on_feature_matching(
        source_down, target_down,
        source_fpfh, target_fpfh,
        mutual_filter=True,
        max_correspondence_distance=distance_threshold,
        estimation_method=o3d.pipelines.registration.TransformationEstimationPointToPoint(False),
        ransac_n=4,
        checkers=[
            o3d.pipelines.registration.CorrespondenceCheckerBasedOnEdgeLength(0.9),
            o3d.pipelines.registration.CorrespondenceCheckerBasedOnDistance(distance_threshold),
        ],
        criteria=o3d.pipelines.registration.RANSACConvergenceCriteria(4000000, 500)
    )
    return result


def refine_icp(source, target, initial_transform, voxel_size=5.0):
    """ICP refinement after global registration."""
    distance_threshold = voxel_size * 0.4
    result = o3d.pipelines.registration.registration_icp(
        source, target,
        distance_threshold,
        initial_transform,
        o3d.pipelines.registration.TransformationEstimationPointToPlane(),
        o3d.pipelines.registration.ICPConvergenceCriteria(
            max_iteration=200,
            relative_fitness=1e-7,
            relative_rmse=1e-7
        )
    )
    return result


def extract_body_features(pcd):
    """
    Extract anthropometric features from point cloud.
    These are body measurements that distinguish patients:
    height, shoulder width, hip width, torso depth, waist width.
    These work even when ICP fails on sparse skeletal clouds.
    """
    pts = np.asarray(pcd.points)
    height = pts[:, 1].max() - pts[:, 1].min()

    # Normalize Y to 0-1 for relative measurements
    y_norm = (pts[:, 1] - pts[:, 1].min()) / height

    # Shoulder region (70-85% height)
    shoulder_pts = pts[(y_norm > 0.70) & (y_norm < 0.85)]
    shoulder_width = shoulder_pts[:, 0].max() - shoulder_pts[:, 0].min() \
        if len(shoulder_pts) > 10 else 0

    # Hip region (35-50% height)
    hip_pts = pts[(y_norm > 0.35) & (y_norm < 0.50)]
    hip_width = hip_pts[:, 0].max() - hip_pts[:, 0].min() \
        if len(hip_pts) > 10 else 0

    # Waist region (55-65% height)
    waist_pts = pts[(y_norm > 0.55) & (y_norm < 0.65)]
    waist_width = waist_pts[:, 0].max() - waist_pts[:, 0].min() \
        if len(waist_pts) > 10 else 0

    # Torso depth (front-back, Z axis) at chest level
    chest_pts = pts[(y_norm > 0.65) & (y_norm < 0.80)]
    chest_depth = chest_pts[:, 2].max() - chest_pts[:, 2].min() \
        if len(chest_pts) > 10 else 0

    # Overall body width
    body_width = pts[:, 0].max() - pts[:, 0].min()

    return np.array([
        height,
        shoulder_width,
        hip_width,
        waist_width,
        chest_depth,
        body_width,
        shoulder_width / height if height > 0 else 0,   # shoulder ratio
        hip_width / height if height > 0 else 0,        # hip ratio
        waist_width / hip_width if hip_width > 0 else 0 # waist-hip ratio
    ])


def feature_similarity(feat_source, feat_target):
    """
    Compute similarity between two feature vectors.
    Returns 0.0-1.0 (higher = more similar).
    """
    # Normalize features
    eps = 1e-8
    norm_s = feat_source / (np.linalg.norm(feat_source) + eps)
    norm_t = feat_target / (np.linalg.norm(feat_target) + eps)

    # Cosine similarity
    cosine = np.dot(norm_s, norm_t)

    # Also compute relative difference per feature
    rel_diff = np.abs(feat_source - feat_target) / (np.abs(feat_target) + eps)
    rel_score = 1.0 - np.clip(rel_diff.mean(), 0, 1)

    # Combine both
    return float((cosine + rel_score) / 2.0)


def match_pointclouds(source_pcd, target_pcd, voxel_size=5.0, verbose=True):
    """
    Full matching pipeline combining:
    1. Anthropometric feature matching (robust to sparse clouds)
    2. ICP geometric matching (refines alignment)

    Returns combined score weighted 60% features + 40% ICP.
    """
    # ── Feature-based matching ────────────────────────────────────────────────
    if verbose:
        print(f"    Extracting body features...")
    feat_src = extract_body_features(source_pcd)
    feat_tgt = extract_body_features(target_pcd)
    feat_score = feature_similarity(feat_src, feat_tgt)

    if verbose:
        print(f"    Feature similarity: {feat_score:.4f}")
        print(f"    Source features: h={feat_src[0]:.0f} sw={feat_src[1]:.0f} "
              f"hw={feat_src[2]:.0f} ww={feat_src[3]:.0f}")
        print(f"    Target features: h={feat_tgt[0]:.0f} sw={feat_tgt[1]:.0f} "
              f"hw={feat_tgt[2]:.0f} ww={feat_tgt[3]:.0f}")

    # ── ICP geometric matching ────────────────────────────────────────────────
    if verbose:
        print(f"    Preprocessing for ICP...")
    src_down, src_fpfh = preprocess_pointcloud(source_pcd, voxel_size)
    tgt_down, tgt_fpfh = preprocess_pointcloud(target_pcd, voxel_size)

    if verbose:
        print(f"    Global registration (RANSAC)...")
    global_result = global_registration(src_down, tgt_down,
                                        src_fpfh, tgt_fpfh, voxel_size)

    if verbose:
        print(f"    ICP refinement...")
    icp_result = refine_icp(source_pcd, target_pcd,
                             global_result.transformation, voxel_size)

    icp_score = icp_result.fitness

    if verbose:
        print(f"    ICP fitness: {icp_score:.4f}")

    # ── Combined score ────────────────────────────────────────────────────────
    combined = 0.6 * feat_score + 0.4 * icp_score

    if verbose:
        print(f"    Combined score: {combined:.4f} "
              f"(feat={feat_score:.3f} × 0.6 + icp={icp_score:.3f} × 0.4)")

    return {
        "fitness":       combined,
        "feat_score":    feat_score,
        "icp_score":     icp_score,
        "rmse":          icp_result.inlier_rmse,
        "transform":     icp_result.transformation
    }