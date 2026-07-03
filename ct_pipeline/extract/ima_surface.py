"""
Direct .IMA -> binary surface volume, no segmentation.

This is today's only IMA path (raw == union, see ingest/discovery.py).
Kept isolated so a future extract/totalseg.py (IMA -> nii.gz -> TotalSegmentator
-> real union) can be added later and swapped into discovery.resolve_extractor()
without touching this module, pointcloud/, or model/.
"""
import numpy as np
from ct_pipeline.ingest.ima_loader import load_ima_volume
from ct_pipeline.config import CT_THRESHOLD_HU


def _spacing_to_affine(spacing):
    """
    Build a 4x4 affine mapping marching-cubes verts (in Z,Y,X voxel-index
    order, since the volume is stacked slice-first) to world mm in X,Y,Z
    order. Mirrors the reorder+scale trick used previously in ima_to_ply.py,
    but stays in mm (not meters) to match the nii_gz pipeline's units —
    normalize_scale() rescales everything to a common height afterward anyway.
    """
    slice_th, row_sp, col_sp = spacing
    affine = np.array([
        [0.0,      0.0,     col_sp, 0.0],
        [0.0,      row_sp,  0.0,    0.0],
        [slice_th, 0.0,     0.0,    0.0],
        [0.0,      0.0,     0.0,    1.0],
    ])
    return affine


def threshold_ima(patient_dir, threshold_hu=CT_THRESHOLD_HU, verbose=True):
    """
    Load .IMA slices from patient_dir and threshold to a binary body-surface
    volume. Returns (volume, affine) — same interface as
    extract/segmentation.threshold_ct, so downstream stages are format-agnostic.
    """
    from scipy import ndimage

    volume, spacing = load_ima_volume(patient_dir)

    if verbose:
        print(f"  Thresholding at {threshold_hu} HU...")
    binary = (volume > threshold_hu).astype(np.uint8)

    if verbose:
        print(f"  Removing scan table (keeping largest component)...")
    labeled, n = ndimage.label(binary)
    sizes = ndimage.sum(binary, labeled, range(1, n + 1))
    largest = np.argmax(sizes) + 1
    binary_clean = (labeled == largest).astype(np.uint8)

    affine = _spacing_to_affine(spacing)

    if verbose:
        print(f"  Clean volume shape: {binary_clean.shape}")
    return binary_clean, affine
