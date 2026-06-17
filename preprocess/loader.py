import os
import nibabel as nib
import numpy as np


def load_nifti(filepath):
    """Load a .nii or .nii.gz file. Returns (data, affine)."""
    img = nib.load(filepath)
    return img.get_fdata(), img.affine


def get_segmentation_files(patient_dir):
    """Return sorted list of all .nii.gz files in segmentations/."""
    seg_dir = os.path.join(patient_dir, "segmentations")
    if not os.path.exists(seg_dir):
        raise FileNotFoundError(f"Segmentation dir not found: {seg_dir}")
    files = sorted([
        os.path.join(seg_dir, f)
        for f in os.listdir(seg_dir)
        if f.endswith(".nii.gz")
    ])
    if not files:
        raise ValueError(f"No segmentation files found in {seg_dir}")
    return files


def get_ct_file(patient_dir):
    """Return path to ct.nii.gz for a patient."""
    path = os.path.join(patient_dir, "ct.nii.gz")
    if not os.path.exists(path):
        raise FileNotFoundError(f"CT file not found: {path}")
    return path