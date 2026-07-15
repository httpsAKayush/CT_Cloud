"""
Stage 5 orchestration — merged .glb ONLY. Fully decoupled from stages 1-4:
this module has no idea nii_gz/ima/.ply/volumes/segmentations exist. Its
only inputs are an already-built raw.glb + union.glb (default locations
from config, keyed by patient_id) — or, for total flexibility, explicit
paths to ANY two .glb files plus an explicit output path.

Because of that, merging can be re-run for a patient at any time —
retuned, redone, whatever — without touching CT data, segmentation, or
point clouds at all, as long as raw.glb + union.glb already exist
somewhere on disk. This module is the only thing that imports
model/merge_export.py.
"""
import os

from ct_pipeline.config import RAW_MODEL_DIR, UNION_MODEL_DIR, MERGED_MODEL_DIR
from ct_pipeline.model import merge_export


def build_patient(patient_id=None, raw_glb_path=None, union_glb_path=None,
                   out_path=None, overwrite=False, verbose=True):
    """
    Build the merged .glb for one patient.

    Two ways to call this:
      - build_patient(patient_id="p001")
            uses default raw/union/merged locations from config.
      - build_patient(raw_glb_path=..., union_glb_path=..., out_path=...)
            merges two arbitrary .glb files, no patient_id/config needed.

    You can mix the two — any path you supply explicitly overrides the
    patient_id-derived default for that one path only.
    """
    if raw_glb_path is None:
        if patient_id is None:
            raise ValueError("merge needs patient_id, or an explicit raw_glb_path")
        raw_glb_path = os.path.join(RAW_MODEL_DIR, f"{patient_id}.glb")
    if union_glb_path is None:
        if patient_id is None:
            raise ValueError("merge needs patient_id, or an explicit union_glb_path")
        union_glb_path = os.path.join(UNION_MODEL_DIR, f"{patient_id}.glb")
    if out_path is None:
        if patient_id is None:
            raise ValueError("merge needs patient_id, or an explicit out_path")
        out_path = os.path.join(MERGED_MODEL_DIR, f"{patient_id}.glb")

    label = patient_id or os.path.splitext(os.path.basename(out_path))[0]

    if os.path.exists(out_path) and not overwrite:
        if verbose:
            print(f"  [merged model] Already exists, skipping: {out_path}")
        return out_path

    return merge_export.build_merged_glb(label, raw_glb_path, union_glb_path, out_path, verbose=verbose)


def build_all(patient_ids, overwrite=False, verbose=True):
    """Merge raw+union .glb for a list of patients, using default config locations."""
    results = {}
    for pid in patient_ids:
        try:
            results[pid] = build_patient(patient_id=pid, overwrite=overwrite, verbose=verbose)
        except Exception as e:
            print(f"  ERROR merging model for {pid}: {e}")
            results[pid] = None
    return results