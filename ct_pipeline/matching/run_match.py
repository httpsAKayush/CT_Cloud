from ct_pipeline.ingest.ply_loader import load_database
from ct_pipeline.matching.matcher import find_best_match

def run_matching(reference_ply_path, mode="raw", threshold=0.55, verbose=True):
    """Run the matching pipeline and return the result dict."""
    
    import open3d as o3d

    print(f"\n── Loading database [{mode}]...")
    database = load_database(mode=mode, verbose=verbose)

    print(f"\n── Loading reference scan: {reference_ply_path}")
    if not os.path.exists(reference_ply_path):
        raise FileNotFoundError(f"Reference scan not found: {reference_ply_path}")

    pcd = o3d.io.read_point_cloud(reference_ply_path)
    pcd = pca_align(pcd, verbose=verbose)
    pcd = normalize_scale(pcd, verbose=verbose)

    print(f"\n── Matching...")
    result = find_best_match(pcd, database, threshold=threshold, verbose=verbose)

    print(f"\n── Best match: {result['patient_id']} ({result['confidence']}%)")
    return result
