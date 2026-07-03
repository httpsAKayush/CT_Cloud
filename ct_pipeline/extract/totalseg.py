"""
PLACEHOLDER — not implemented yet.

Planned flow, when added:
  1. Convert .IMA slices -> a single ct.nii.gz volume (reuse ingest/ima_loader.py
     for reading, write out with nibabel).
  2. Run TotalSegmentator CLI on that nii.gz to produce a segmentations/ folder,
     giving IMA patients real per-organ masks instead of raw==union.
  3. Store the converted nii.gz + generated segmentations under
     i_data/ct_data/nii_gz/<patient>/ (per the confirmed "option A" — treat
     converted IMA patients as ordinary nii_gz patients from here on), so every
     downstream stage (pointcloud/, model/, matching/) needs zero changes.
  4. Swap ingest/discovery.py's resolve_extractor() IMA branch to call this
     module's union function instead of ima_surface.threshold_ima for union.

Not wired in yet — ingest/discovery.py currently routes all IMA patients
through extract/ima_surface.py for both raw and union.
"""

raise NotImplementedError(
    "TotalSegmentator support for .IMA patients is not implemented yet. "
    "See module docstring for the planned integration point."
)
