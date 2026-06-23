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
    Extract discriminative anthropometric features from point cloud.
    Uses width profile at multiple heights + shape ratios.
    Returns 46-dimensional feature vector.
    """
    pts = np.asarray(pcd.points)
    height = pts[:, 1].max() - pts[:, 1].min()
    y_norm = (pts[:, 1] - pts[:, 1].min()) / height

    def width_at(y_low, y_high, axis=0):
        band = pts[(y_norm >= y_low) & (y_norm < y_high)]
        if len(band) < 5:
            return 0.0
        return float(band[:, axis].max() - band[:, axis].min())

    def depth_at(y_low, y_high):
        return width_at(y_low, y_high, axis=2)

    # ── Width profile at 20 height slices (every 5%) ─────────────────────────
    width_profile = np.array([
        width_at(i * 0.05, (i + 1) * 0.05) for i in range(20)
    ])

    # ── Depth profile at 10 height slices (every 10%) ────────────────────────
    depth_profile = np.array([
        depth_at(i * 0.10, (i + 1) * 0.10) for i in range(10)
    ])

    # ── Key anatomical measurements ───────────────────────────────────────────
    shoulder_w   = width_at(0.72, 0.82)
    chest_w      = width_at(0.60, 0.72)
    waist_w      = width_at(0.50, 0.60)
    hip_w        = width_at(0.38, 0.50)
    thigh_w      = width_at(0.20, 0.35)
    ankle_w      = width_at(0.05, 0.15)
    chest_d      = depth_at(0.60, 0.72)
    abdomen_d    = depth_at(0.45, 0.60)

    # ── Shape ratios (scale invariant) ───────────────────────────────────────
    waist_hip_ratio    = waist_w   / (hip_w      + 1e-8)
    shoulder_hip_ratio = shoulder_w / (hip_w     + 1e-8)
    chest_waist_ratio  = chest_w   / (waist_w    + 1e-8)
    depth_width_ratio  = chest_d   / (chest_w    + 1e-8)
    thigh_hip_ratio    = thigh_w   / (hip_w      + 1e-8)

    # ── Waist definition ─────────────────────────────────────────────────────
    waist_definition = 1.0 - (waist_w / (max(shoulder_w, hip_w) + 1e-8))

    # ── Width variance ───────────────────────────────────────────────────────
    width_variance = float(np.std(width_profile))
    width_skew     = float(np.mean(width_profile[:10]) /
                           (np.mean(width_profile[10:]) + 1e-8))

    # ── Scalar features ───────────────────────────────────────────────────────
    scalar_features = np.array([
        shoulder_w, chest_w, waist_w, hip_w, thigh_w, ankle_w,
        chest_d, abdomen_d,
        waist_hip_ratio, shoulder_hip_ratio, chest_waist_ratio,
        depth_width_ratio, thigh_hip_ratio,
        waist_definition, width_variance, width_skew
    ])

    # ── Normalize profiles by height (scale invariant) ───────────────────────
    # width_profile_norm = width_profile / (height + 1e-8)
    # depth_profile_norm = depth_profile / (height + 1e-8)

    # ── Final 46-dim vector: 16 scalars + 20 width + 10 depth ────────────────
    #return np.concatenate([scalar_features, width_profile_norm, depth_profile_norm])
    # Weight width profile 3x more — it's the most discriminative feature
    #return np.concatenate([scalar_features, width_profile_norm * 3.0, depth_profile_norm * 1.5])

# ── Zone-weighted width profile ───────────────────────────────────────────
    # Amplify most discriminative zones (waist/hip/shoulder)
    ZONE_WEIGHTS = np.array([
        1.0, 1.0, 1.5, 1.5, 2.0,   # 0-25%  feet/ankles/knees
        2.5, 2.5, 2.0, 2.0, 2.5,   # 25-50% thighs/hips
        3.0, 3.0, 2.5, 2.5, 2.0,   # 50-75% waist/chest (most discriminative)
        3.0, 3.0, 2.5, 1.5, 1.0,   # 75-100% shoulders/arms/head
    ])

    width_profile_weighted = width_profile * ZONE_WEIGHTS
    width_profile_norm     = width_profile_weighted / (height + 1e-8)
    depth_profile_norm     = depth_profile / (height + 1e-8)

    return np.concatenate([scalar_features, width_profile_norm, depth_profile_norm])


def feature_similarity(feat_source, feat_target):
    eps = 1e-8
    
    # Split features
    scalars_s = feat_source[:16]
    scalars_t = feat_target[:16]
    width_s   = feat_source[16:36]
    width_t   = feat_target[16:36]
    depth_s   = feat_source[36:46]
    depth_t   = feat_target[36:46]

    # ── Width profile similarity (most discriminative) ────────────────────────
    # Use L2 distance normalized by profile magnitude — penalizes shape differences
    width_diff  = np.abs(width_s - width_t)
    width_scale = np.maximum(np.abs(width_t), eps)
    width_rel   = width_diff / width_scale
    width_score = float(np.exp(-width_rel.mean() * 3.0))  # exponential penalty

    # ── Depth profile similarity ──────────────────────────────────────────────
    depth_diff  = np.abs(depth_s - depth_t)
    depth_scale = np.maximum(np.abs(depth_t), eps)
    depth_rel   = depth_diff / depth_scale
    depth_score = float(np.exp(-depth_rel.mean() * 3.0))

    # ── Scalar ratios similarity ──────────────────────────────────────────────
    # Focus on ratios (indices 8-15) which are scale-invariant
    ratios_s = scalars_s[8:]
    ratios_t = scalars_t[8:]
    ratio_diff  = np.abs(ratios_s - ratios_t)
    ratio_scale = np.maximum(np.abs(ratios_t), eps)
    ratio_score = float(np.exp(-( ratio_diff / ratio_scale).mean() * 2.0))

    # ── Flip detection ────────────────────────────────────────────────────────
    width_flipped     = width_s[::-1]
    width_diff_flip   = np.abs(width_flipped - width_t)
    width_score_flip  = float(np.exp(-(width_diff_flip / width_scale).mean() * 3.0))
    if width_score_flip > width_score + 0.05:
        width_score = max(0, width_score - (width_score_flip - width_score) * 0.5)

    # ── Combined (width profile carries most weight) ──────────────────────────
    combined = 0.60 * width_score + 0.25 * depth_score + 0.15 * ratio_score

    return float(combined)

def match_pointclouds(source_pcd, target_pcd, voxel_size=5.0, verbose=True):
    """
    Full matching pipeline:
    60% anthropometric features + 40% ICP geometric matching.
    """
    # ── Feature-based matching ────────────────────────────────────────────────
    if verbose:
        print(f"    Extracting body features...")
    feat_src   = extract_body_features(source_pcd)
    feat_tgt   = extract_body_features(target_pcd)
    feat_score = feature_similarity(feat_src, feat_tgt)

    if verbose:
        print(f"    Feature similarity: {feat_score:.4f}")
        print(f"    Source: h={feat_src[0]+feat_src[1]:.0f} "
              f"sw={feat_src[0]:.0f} hw={feat_src[3]:.0f} "
              f"ww={feat_src[2]:.0f} whr={feat_src[8]:.2f}")
        print(f"    Target: h={feat_tgt[0]+feat_tgt[1]:.0f} "
              f"sw={feat_tgt[0]:.0f} hw={feat_tgt[3]:.0f} "
              f"ww={feat_tgt[2]:.0f} whr={feat_tgt[8]:.2f}")

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
    #combined = 0.6 * feat_score + 0.4 * icp_score
    # Only trust ICP if it found good correspondences (fitness > 0.05)
    icp_weight = 0.4 if icp_score > 0.05 else 0.1
    feat_weight = 1.0 - icp_weight
    combined = feat_weight * feat_score + icp_weight * icp_score
    #

    if verbose:
        print(f"    Combined: {combined:.4f} "
              f"(feat={feat_score:.3f}×0.6 + icp={icp_score:.3f}×0.4)")

    return {
        "fitness":    combined,
        "feat_score": feat_score,
        "icp_score":  icp_score,
        "rmse":       icp_result.inlier_rmse,
        "transform":  icp_result.transformation
    }