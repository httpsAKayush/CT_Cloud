"""
Orchestration only — no algorithm logic lives here. Chains:
  ingest.discovery -> pointcloud.builder -> (optional) model.builder
"""
from ct_pipeline.config import CT_DATA_DIR
from ct_pipeline.ingest import discovery
from ct_pipeline.pointcloud import builder as ply_builder
from ct_pipeline.model import builder as model_builder


def _base_dir_for(db_dir_override=None):
    # db_dir_override, when given, points at the ct_data/ level (containing nii_gz/ and ima/).
    return db_dir_override or CT_DATA_DIR


def run(patients=None, fmt="nii_gz", db_dir=None, mode="both",
        with_glb=False, make_merged=False, overwrite=False, verbose=True):
    """
    patients: list of patient IDs, or None -> auto-discover all under db_dir/fmt/
    db_dir:   path to the ct_data/ root (containing nii_gz/ and ima/ subfolders);
              defaults to config.CT_DATA_DIR
    mode:     "raw" | "union" | "both"
    """
    base_dir = _base_dir_for(db_dir)

    if patients is None:
        patients = discovery.list_patients(base_dir, fmt)
        if verbose:
            print(f"Auto-discovered {len(patients)} patients: {patients}")

    print(f"\n{'='*50}")
    print(f"Building point clouds — {len(patients)} patients, format={fmt}, mode={mode}")
    ply_results = ply_builder.build_all(patients, fmt, base_dir, mode=mode,
                                         overwrite=overwrite, verbose=verbose)

    model_results = None
    if with_glb:
        print(f"\n{'='*50}")
        print(f"Building .glb models — {len(patients)} patients")
        model_results = model_builder.build_all(patients, fmt, base_dir, mode=mode,
                                                  make_merged=make_merged,
                                                  overwrite=overwrite, verbose=verbose)

    print(f"\n{'='*50}")
    print("Summary:")
    for pid in patients:
        ply_ok = "✓" if ply_results.get(pid) else "✗"
        line = f"  {ply_ok} {pid}: ply={ply_results.get(pid)}"
        if model_results is not None:
            m_ok = "✓" if model_results.get(pid) else "✗"
            line += f"  |  {m_ok} glb={model_results.get(pid)}"
        print(line)

    return ply_results, model_results
