import os

# ── PATHS ────────────────────────────────────────────────────────────────────
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR  = os.path.expanduser("~/Downloads/Totalsegmentator_dataset_small_v201/wholebody")
OUTPUT_DIR   = os.path.join(BASE_DIR, "data")
PLY_DIR      = os.path.join(OUTPUT_DIR, "pointclouds")
MODEL_DIR    = os.path.join(OUTPUT_DIR, "models")

# ── PATIENTS ─────────────────────────────────────────────────────────────────
PATIENTS = ["s1369", "s1371", "s1384", "s1388", "s1397"]

# ── POINT CLOUD ──────────────────────────────────────────────────────────────
N_POINTS          = 10000   # points per cloud
MARCHING_CUBES_LEVEL = 0.5

# ── SURFACE EXTRACTION MODE ──────────────────────────────────────────────────
# "segmentation" → merge all organ/bone masks (recommended)
# "ct_threshold" → threshold raw CT volume (experimental)
SURFACE_MODE      = "segmentation"
CT_THRESHOLD_HU   = -200    # only used in ct_threshold mode

# ── ALIGNMENT ────────────────────────────────────────────────────────────────
TARGET_UP_AXIS    = [0, 1, 0]   # Y up (Unity convention)