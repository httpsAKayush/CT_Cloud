import os
from ct_pipeline.config import RAW_PLY_DIR, UNION_PLY_DIR

def discover_available_patients(ply_dir):
    """List patient IDs that actually have a .ply in ply_dir."""
    if not os.path.exists(ply_dir):
        return []
    return sorted(
        os.path.splitext(f)[0] for f in os.listdir(ply_dir) if f.endswith(".ply")
    )

def load_database(patients=None, ply_dir=None, mode="raw", verbose=True):
    """
    Load all preprocessed point clouds into memory as the matching database.
    mode: "raw" -> RAW_PLY_DIR, "union" -> UNION_PLY_DIR
    patients: explicit list, or None -> auto-discover every .ply present in ply_dir
              (NOT config.PATIENTS — that's just a stale fallback name list, not
              a source of truth; the disk is the source of truth for scalability).
    """
    if ply_dir is None:
        ply_dir = RAW_PLY_DIR if mode == "raw" else UNION_PLY_DIR

    if patients is None:
        patients = discover_available_patients(ply_dir)
        if verbose:
            print(f"Auto-discovered {len(patients)} patients in {ply_dir}: {patients}")

    database = {}
    if verbose:
        print(f"Loading database ({len(patients)} patients) from {ply_dir} ...")

    for pid in patients:
        path = os.path.join(ply_dir, f"{pid}.ply")
        if not os.path.exists(path):
            print(f"  WARNING: {path} not found, skipping")
            continue
        pcd = o3d.io.read_point_cloud(path)
        database[pid] = pcd
        if verbose:
            print(f"  Loaded {pid}: {len(pcd.points)} points")

    return database