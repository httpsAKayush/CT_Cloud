import numpy as np
from .loader import load_nifti, get_segmentation_files


def merge_segmentations(patient_dir, verbose=True):
    """
    Load all segmentation masks for a patient and merge
    into a single binary volume. Returns (volume, affine).
    """
    files = get_segmentation_files(patient_dir)
    if verbose:
        print(f"  Loading {len(files)} segmentation masks...")

    ref_data, affine = load_nifti(files[0])
    merged = np.zeros(ref_data.shape, dtype=np.uint8)

    for f in files:
        data, _ = load_nifti(f)
        merged = np.logical_or(merged, data > 0).astype(np.uint8)

    if verbose:
        print(f"  Merged volume shape: {merged.shape}")
    return merged, affine


def threshold_ct(patient_dir, threshold_hu=-200, verbose=True):
    """
    Extract body surface from raw CT using HU threshold.
    Keeps only the largest connected component (removes scan table).
    Returns (volume, affine).
    """
    from .loader import get_ct_file, load_nifti
    from scipy import ndimage

    ct_path = get_ct_file(patient_dir)
    data, affine = load_nifti(ct_path)

    if verbose:
        print(f"  CT shape: {data.shape}, HU range: {data.min():.0f} to {data.max():.0f}")

    binary = (data > threshold_hu).astype(np.uint8)

    if verbose:
        print(f"  Removing CT table (keeping largest component)...")
    labeled, n = ndimage.label(binary)
    sizes = ndimage.sum(binary, labeled, range(1, n + 1))
    largest = np.argmax(sizes) + 1
    binary_clean = (labeled == largest).astype(np.uint8)

    if verbose:
        print(f"  Clean volume shape: {binary_clean.shape}")
    return binary_clean, affine