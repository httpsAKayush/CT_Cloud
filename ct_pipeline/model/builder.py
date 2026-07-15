# """
# Stage 4 orchestration — .ply data isn't actually needed here, models are
# built straight from the volume (mirrors pointcloud/builder.py's approach:
# extract -> mesh, rather than round-tripping through the saved .ply).

# Union model dispatch (the one place format still matters, since IMA has no
# organ segmentation yet):
#   nii_gz -> mesh_export.build_union_glb   (real per-organ colored mesh)
#   ima    -> raw_export.build_surface_glb  (single surface, same as raw —
#             once extract/totalseg.py lands, swap this branch only)
# """
# import os

# from ct_pipeline.config import RAW_MODEL_DIR, UNION_MODEL_DIR, MERGED_MODEL_DIR
# from ct_pipeline.ingest import discovery
# from ct_pipeline.model import mesh_export, raw_export, merge_export


# def build_patient(patient_id, fmt, base_dir, mode="both", make_merged=False,
#                    overwrite=False, verbose=True):
#     """
#     Build .glb model(s) for one patient.
#     mode: "raw" | "union" | "both"
#     Returns dict: {"raw": path_or_None, "union": path_or_None, "merged": path_or_None}
#     """
#     patient_dir = discovery.patient_dir(base_dir, fmt, patient_id)
#     raw_fn, _ = discovery.resolve_extractor(fmt)

#     results = {"raw": None, "union": None, "merged": None}

#     if mode in ("raw", "both"):
#         out_path = os.path.join(RAW_MODEL_DIR, f"{patient_id}.glb")
#         if os.path.exists(out_path) and not overwrite:
#             if verbose:
#                 print(f"  [raw model] Already exists, skipping: {out_path}")
#             results["raw"] = out_path
#         else:
#             volume, affine = raw_fn(patient_dir, verbose=verbose)
#             results["raw"] = raw_export.build_surface_glb(volume, affine, out_path, verbose=verbose)

#     if mode in ("union", "both"):
#         out_path = os.path.join(UNION_MODEL_DIR, f"{patient_id}.glb")
#         if os.path.exists(out_path) and not overwrite:
#             if verbose:
#                 print(f"  [union model] Already exists, skipping: {out_path}")
#             results["union"] = out_path
#         elif fmt == discovery.FORMAT_NII_GZ:
#             results["union"] = mesh_export.build_union_glb(patient_id, patient_dir, out_path, verbose=verbose)
#         else:
#             # ima: no organ segmentation yet -> union model == raw surface
#             volume, affine = raw_fn(patient_dir, verbose=verbose)
#             results["union"] = raw_export.build_surface_glb(volume, affine, out_path, verbose=verbose)

#     if make_merged and results["raw"] and results["union"]:
#         out_path = os.path.join(MERGED_MODEL_DIR, f"{patient_id}.glb")
#         if os.path.exists(out_path) and not overwrite:
#             if verbose:
#                 print(f"  [merged model] Already exists, skipping: {out_path}")
#             results["merged"] = out_path
#         else:
#             results["merged"] = merge_export.build_merged_glb(
#                 patient_id, results["raw"], results["union"], out_path, verbose=verbose)

#     return results


# def build_all(patient_ids, fmt, base_dir, mode="both", make_merged=False,
#                overwrite=False, verbose=True):
#     results = {}
#     for pid in patient_ids:
#         try:
#             results[pid] = build_patient(pid, fmt, base_dir, mode=mode,
#                                           make_merged=make_merged,
#                                           overwrite=overwrite, verbose=verbose)
#         except Exception as e:
#             print(f"  ERROR exporting model for {pid}: {e}")
#             results[pid] = None
#     return results
"""
Stage 4 orchestration — .glb model export ONLY (raw + union). Builds
straight from the source volume (mirrors pointcloud/builder.py's approach:
extract -> mesh, rather than round-tripping through a saved .ply). Never
imports or knows about .ply code, and never imports merge_export — merging
is a fully separate stage, see model/merge_builder.py.

Union model dispatch (the one place format still matters, since IMA has no
organ segmentation yet):
  nii_gz -> mesh_export.build_union_glb   (real per-organ colored mesh)
  ima    -> raw_export.build_surface_glb  (single surface, same as raw —
            once extract/totalseg.py lands, swap this branch only)
"""
import os

from ct_pipeline.config import RAW_MODEL_DIR, UNION_MODEL_DIR
from ct_pipeline.ingest import discovery
from ct_pipeline.model import mesh_export, raw_export


def build_patient(patient_id, fmt, base_dir, mode="both", overwrite=False, verbose=True):
    """
    Build .glb model(s) for one patient.
    mode: "raw" | "union" | "both"
    Returns dict: {"raw": path_or_None, "union": path_or_None}
    """
    patient_dir = discovery.patient_dir(base_dir, fmt, patient_id)
    raw_fn, _ = discovery.resolve_extractor(fmt)

    results = {"raw": None, "union": None}

    if mode in ("raw", "both"):
        out_path = os.path.join(RAW_MODEL_DIR, f"{patient_id}.glb")
        if os.path.exists(out_path) and not overwrite:
            if verbose:
                print(f"  [raw model] Already exists, skipping: {out_path}")
            results["raw"] = out_path
        else:
            volume, affine = raw_fn(patient_dir, verbose=verbose)
            results["raw"] = raw_export.build_surface_glb(volume, affine, out_path, verbose=verbose)

    if mode in ("union", "both"):
        out_path = os.path.join(UNION_MODEL_DIR, f"{patient_id}.glb")
        if os.path.exists(out_path) and not overwrite:
            if verbose:
                print(f"  [union model] Already exists, skipping: {out_path}")
            results["union"] = out_path
        elif fmt == discovery.FORMAT_NII_GZ:
            results["union"] = mesh_export.build_union_glb(patient_id, patient_dir, out_path, verbose=verbose)
        else:
            # ima: no organ segmentation yet -> union model == raw surface
            volume, affine = raw_fn(patient_dir, verbose=verbose)
            results["union"] = raw_export.build_surface_glb(volume, affine, out_path, verbose=verbose)

    return results


def build_all(patient_ids, fmt, base_dir, mode="both", overwrite=False, verbose=True):
    results = {}
    for pid in patient_ids:
        try:
            results[pid] = build_patient(pid, fmt, base_dir, mode=mode,
                                          overwrite=overwrite, verbose=verbose)
        except Exception as e:
            print(f"  ERROR exporting model for {pid}: {e}")
            results[pid] = None
    return results