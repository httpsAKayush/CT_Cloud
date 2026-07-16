"""
CLI-facing entrypoint for Stage 3 — .ply point clouds ONLY. Independent of
.glb model export (pipeline/build_model.py) and of merging
(pipeline/merge_model.py); this call never touches model/ code at all.
"""
from ct_pipeline.config import CT_DATA_DIR
from ct_pipeline.ingest import discovery
from ct_pipeline.pointcloud import builder


def run(patients, fmt, db_dir=None, mode="both", overwrite=False, verbose=True):
    base_dir = db_dir or CT_DATA_DIR
    patient_ids = patients or discovery.list_patients(base_dir, fmt)

    if verbose:
        print(f"Building point cloud(s) for {len(patient_ids)} patient(s) [{fmt}] mode={mode}")

    return builder.build_all(patient_ids, fmt, base_dir, mode=mode,
                              overwrite=overwrite, verbose=verbose)