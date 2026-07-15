"""
CLI-facing entrypoint for Stage 4 — .glb model export ONLY (raw/union).
Independent of .ply (pipeline/build_pointcloud.py) and of merging
(pipeline/merge_model.py) — building a model never reads or writes .ply
files, and never touches a merged output.
"""
from ct_pipeline.config import CT_DATA_DIR
from ct_pipeline.ingest import discovery
from ct_pipeline.model import builder


def run(patients, fmt, db_dir=None, mode="both", overwrite=False, verbose=True):
    base_dir = db_dir or CT_DATA_DIR
    patient_ids = patients or discovery.list_patients(base_dir, fmt)

    if verbose:
        print(f"Building .glb model(s) for {len(patient_ids)} patient(s) [{fmt}] mode={mode}")

    return builder.build_all(patient_ids, fmt, base_dir, mode=mode,
                              overwrite=overwrite, verbose=verbose)