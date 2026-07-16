import numpy as np


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

    width_profile = np.array([
        width_at(i * 0.05, (i + 1) * 0.05) for i in range(20)
    ])
    depth_profile = np.array([
        depth_at(i * 0.10, (i + 1) * 0.10) for i in range(10)
    ])

    shoulder_w   = width_at(0.72, 0.82)
    chest_w      = width_at(0.60, 0.72)
    waist_w      = width_at(0.50, 0.60)
    hip_w        = width_at(0.38, 0.50)
    thigh_w      = width_at(0.20, 0.35)
    ankle_w      = width_at(0.05, 0.15)
    chest_d      = depth_at(0.60, 0.72)
    abdomen_d    = depth_at(0.45, 0.60)

    waist_hip_ratio    = waist_w   / (hip_w      + 1e-8)
    shoulder_hip_ratio = shoulder_w / (hip_w     + 1e-8)
    chest_waist_ratio  = chest_w   / (waist_w    + 1e-8)
    depth_width_ratio  = chest_d   / (chest_w    + 1e-8)
    thigh_hip_ratio    = thigh_w   / (hip_w      + 1e-8)

    waist_definition = 1.0 - (waist_w / (max(shoulder_w, hip_w) + 1e-8))

    width_variance = float(np.std(width_profile))
    width_skew     = float(np.mean(width_profile[:10]) /
                           (np.mean(width_profile[10:]) + 1e-8))

    scalar_features = np.array([
        shoulder_w, chest_w, waist_w, hip_w, thigh_w, ankle_w,
        chest_d, abdomen_d,
        waist_hip_ratio, shoulder_hip_ratio, chest_waist_ratio,
        depth_width_ratio, thigh_hip_ratio,
        waist_definition, width_variance, width_skew
    ])

    # Zone-weighted width profile — amplify most discriminative zones (waist/hip/shoulder)
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

    scalars_s = feat_source[:16]
    scalars_t = feat_target[:16]
    width_s   = feat_source[16:36]
    width_t   = feat_target[16:36]
    depth_s   = feat_source[36:46]
    depth_t   = feat_target[36:46]

    width_diff  = np.abs(width_s - width_t)
    width_scale = np.maximum(np.abs(width_t), eps)
    width_rel   = width_diff / width_scale
    width_score = float(np.exp(-width_rel.mean() * 3.0))

    depth_diff  = np.abs(depth_s - depth_t)
    depth_scale = np.maximum(np.abs(depth_t), eps)
    depth_rel   = depth_diff / depth_scale
    depth_score = float(np.exp(-depth_rel.mean() * 3.0))

    ratios_s = scalars_s[8:]
    ratios_t = scalars_t[8:]
    ratio_diff  = np.abs(ratios_s - ratios_t)
    ratio_scale = np.maximum(np.abs(ratios_t), eps)
    ratio_score = float(np.exp(-(ratio_diff / ratio_scale).mean() * 2.0))

    # Flip detection
    width_flipped     = width_s[::-1]
    width_diff_flip   = np.abs(width_flipped - width_t)
    width_score_flip  = float(np.exp(-(width_diff_flip / width_scale).mean() * 3.0))
    if width_score_flip > width_score + 0.05:
        width_score = max(0, width_score - (width_score_flip - width_score) * 0.5)

    combined = 0.60 * width_score + 0.25 * depth_score + 0.15 * ratio_score
    return float(combined)
