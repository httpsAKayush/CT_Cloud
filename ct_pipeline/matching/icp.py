import open3d as o3d
from ct_pipeline.matching.features import extract_body_features, feature_similarity


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


def match_pointclouds(source_pcd, target_pcd, voxel_size=5.0, verbose=True):
    """
    Full matching pipeline: 60% anthropometric features + 40% ICP geometric matching
    (ICP weight drops to 10% if ICP fitness is too low to trust, e.g. < 0.05).
    """
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

    if verbose:
        print(f"    Preprocessing for ICP...")
    src_down, src_fpfh = preprocess_pointcloud(source_pcd, voxel_size)
    tgt_down, tgt_fpfh = preprocess_pointcloud(target_pcd, voxel_size)

    if verbose:
        print(f"    Global registration (RANSAC)...")
    global_result = global_registration(src_down, tgt_down, src_fpfh, tgt_fpfh, voxel_size)

    if verbose:
        print(f"    ICP refinement...")
    icp_result = refine_icp(source_pcd, target_pcd, global_result.transformation, voxel_size)

    icp_score = icp_result.fitness
    if verbose:
        print(f"    ICP fitness: {icp_score:.4f}")

    # Only trust ICP if it found good correspondences (fitness > 0.05)
    icp_weight = 0.4 if icp_score > 0.05 else 0.1
    feat_weight = 1.0 - icp_weight
    combined = feat_weight * feat_score + icp_weight * icp_score

    if verbose:
        print(f"    Combined: {combined:.4f} "
              f"(feat={feat_score:.3f}×{feat_weight} + icp={icp_score:.3f}×{icp_weight})")

    return {
        "fitness":    combined,
        "feat_score": feat_score,
        "icp_score":  icp_score,
        "rmse":       icp_result.inlier_rmse,
        "transform":  icp_result.transformation
    }
