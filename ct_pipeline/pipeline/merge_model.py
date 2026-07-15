"""
CLI-facing entrypoint for Stage 5 — merged .glb ONLY. Needs an existing
raw.glb + union.glb (already produced by `build-glb`) and nothing else: no
--format, no --db-dir, no .ply, no nii_gz/ima. This is what lets merging
be re-run independently, any time, for any patient, without re-touching
CT data, segmentation, or point clouds.
"""
from ct_pipeline.model import merge_builder


def run(patients=None, raw_glb=None, union_glb=None, out=None, overwrite=False, verbose=True):
    # Explicit single-file override mode — merge two arbitrary .glb files,
    # no patient discovery / config defaults involved at all.
    if raw_glb or union_glb or out:
        if patients and len(patients) > 1:
            raise ValueError(
                "--raw-glb/--union-glb/--out are single-file overrides — pass at "
                "most one --patients ID with them (to fill in defaults for the "
                "paths you didn't override), or omit --patients entirely.")
        pid = (patients or [None])[0]
        path = merge_builder.build_patient(
            patient_id=pid, raw_glb_path=raw_glb, union_glb_path=union_glb,
            out_path=out, overwrite=overwrite, verbose=verbose)
        return {pid: path}

    if not patients:
        raise ValueError(
            "merge-glb needs --patients (batch mode, default raw/union/merged "
            "locations from config), or --raw-glb/--union-glb/--out for a single "
            "explicit merge.")

    if verbose:
        print(f"Merging raw+union .glb for {len(patients)} patient(s)")

    return merge_builder.build_all(patients, overwrite=overwrite, verbose=verbose)