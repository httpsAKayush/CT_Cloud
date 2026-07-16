"""
Stage 1 entry point — locate patients under a db-dir for a given format,
and hand back a uniform description of what's available for each patient.

This is the single place that knows "nii_gz" vs "ima" as directory layouts.
Everything downstream (extract/, pointcloud/, model/) only ever sees a
patient_id + a resolved surface-producing function — it never branches on
format again.

When TotalSegmentator support for IMA is added later, the only change needed
is inside resolve_extractor() below — nothing in extract/, pointcloud/, or
model/ has to change.
"""
import os
from ct_pipeline.extract import segmentation, ima_surface

FORMAT_NII_GZ = "nii_gz"
FORMAT_IMA = "ima"
SUPPORTED_FORMATS = (FORMAT_NII_GZ, FORMAT_IMA)


def format_dir(base_dir, fmt):
    if fmt not in SUPPORTED_FORMATS:
        raise ValueError(f"Unknown format '{fmt}'. Supported: {SUPPORTED_FORMATS}")
    return os.path.join(base_dir, fmt)


def list_patients(base_dir, fmt):
    """List patient IDs available under base_dir/<fmt>/."""
    fdir = format_dir(base_dir, fmt)
    if not os.path.exists(fdir):
        raise FileNotFoundError(f"Format directory not found: {fdir}")
    patients = sorted([
        d for d in os.listdir(fdir)
        if os.path.isdir(os.path.join(fdir, d))
    ])
    if not patients:
        raise ValueError(f"No patient folders found in {fdir}")
    return patients


def patient_dir(base_dir, fmt, patient_id):
    """Path to a single patient's folder for a given format."""
    pdir = os.path.join(format_dir(base_dir, fmt), patient_id)
    if not os.path.exists(pdir):
        raise FileNotFoundError(f"Patient directory not found: {pdir}")
    return pdir


def resolve_extractor(fmt):
    """
    Return the (raw_fn, union_fn) pair used by pointcloud/builder.py for a
    given format. Both take (patient_dir) and return a binary volume + affine
    suitable for pointcloud/surface.py.

    nii_gz  -> real segmentation-derived union, HU-threshold raw
    ima     -> today: both raw and union derived from the same threshold
               volume (no organ separation available yet).
               later: swap union_fn here for extract/totalseg.py's output
               once TotalSegmentator is wired in — no other file changes.
    """
    from ct_pipeline.extract import segmentation, ima_surface

    if fmt == FORMAT_NII_GZ:
        return segmentation.threshold_ct, segmentation.merge_segmentations

    if fmt == FORMAT_IMA:
        # union == raw for now (see docstring above)
        return ima_surface.threshold_ima, ima_surface.threshold_ima

    raise ValueError(f"Unknown format '{fmt}'. Supported: {SUPPORTED_FORMATS}")
