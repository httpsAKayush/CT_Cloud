import numpy as np
import pydicom
from pathlib import Path
from ct_pipeline.config import IMA_DIR


def load_ima_volume(folder):
    """
    Load a folder of .IMA slice files into a 3D HU volume.
    Returns (volume, spacing) where spacing is (slice_thickness, row_spacing, col_spacing) in mm.
    """
    folder = folder if folder else IMA_DIR
    files = sorted(Path(folder).glob("*.IMA"))
    if not files:
        files = sorted(Path(folder).glob("*.ima"))
    if not files:
        raise FileNotFoundError(f"No .IMA files found in {folder}")

    print(f"  Found {len(files)} slices")

    slices = [pydicom.dcmread(str(f)) for f in files]

    # Sort by ImagePositionPatient Z
    slices.sort(key=lambda s: float(s.ImagePositionPatient[2]))

    volume = np.stack([s.pixel_array.astype(np.float32) for s in slices], axis=0)

    ds0 = slices[0]
    slope = float(getattr(ds0, "RescaleSlope", 1))
    intercept = float(getattr(ds0, "RescaleIntercept", 0))
    volume = volume * slope + intercept

    row_sp, col_sp = map(float, ds0.PixelSpacing)
    slice_th = float(getattr(ds0, "SliceThickness", 1.0))
    spacing = np.array([slice_th, row_sp, col_sp])  # mm

    print(f"  Volume shape: {volume.shape}, spacing: {spacing} mm")
    print(f"  HU range: {volume.min():.0f} to {volume.max():.0f}")

    return volume, spacing
