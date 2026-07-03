import os

# ── ROOT ─────────────────────────────────────────────────────────────────────
PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(PACKAGE_DIR)
IO_DATA_DIR = os.path.join(PROJECT_ROOT, "io_data")

# ── INPUT (i_data) ───────────────────────────────────────────────────────────
I_DATA_DIR       = os.path.join(IO_DATA_DIR, "i_data")
CT_DATA_DIR      = os.path.join(I_DATA_DIR, "ct_data")
NII_GZ_DIR       = os.path.join(CT_DATA_DIR, "nii_gz")
IMA_DIR          = os.path.join(CT_DATA_DIR, "ima")
REFERENCE_DIR    = os.path.join(I_DATA_DIR, "reference_data")

# ── OUTPUT (o_data) ──────────────────────────────────────────────────────────
O_DATA_DIR       = os.path.join(IO_DATA_DIR, "o_data")

PLY_DIR          = os.path.join(O_DATA_DIR, "pointclouds")
RAW_PLY_DIR      = os.path.join(PLY_DIR, "raw")
UNION_PLY_DIR    = os.path.join(PLY_DIR, "union")

MODEL_DIR        = os.path.join(O_DATA_DIR, "models")
RAW_MODEL_DIR    = os.path.join(MODEL_DIR, "raw")
UNION_MODEL_DIR  = os.path.join(MODEL_DIR, "union")
MERGED_MODEL_DIR = os.path.join(MODEL_DIR, "merged")

ALL_OUTPUT_DIRS = [
    RAW_PLY_DIR, UNION_PLY_DIR,
    RAW_MODEL_DIR, UNION_MODEL_DIR, MERGED_MODEL_DIR,
]

ALL_INPUT_DIRS = [NII_GZ_DIR, IMA_DIR, REFERENCE_DIR]


def ensure_dirs():
    """Create the full io_data tree if it doesn't exist yet. Safe to call anytime."""
    for d in ALL_INPUT_DIRS + ALL_OUTPUT_DIRS:
        os.makedirs(d, exist_ok=True)


# NOTE: no hardcoded PATIENTS list — every stage auto-discovers patients from
# disk (ingest.discovery.list_patients for input, matcher.discover_available_patients
# / view._discover_all_patient_ids for output), so adding a new patient folder
# is enough; nothing needs to be edited here. Use --patients on the CLI to
# restrict to a subset.

# ── POINT CLOUD ──────────────────────────────────────────────────────────────
N_POINTS              = 10000   # points per cloud
MARCHING_CUBES_LEVEL  = 0.5

# ── SURFACE EXTRACTION ────────────────────────────────────────────────────────
CT_THRESHOLD_HU   = -200    # HU threshold for raw/outer-surface extraction

# ── ALIGNMENT ────────────────────────────────────────────────────────────────
TARGET_UP_AXIS    = [0, 1, 0]   # Y up (Unity convention)

# ── MODEL EXPORT ─────────────────────────────────────────────────────────────
MODEL_DECIMATE_FACE_COUNT          = 10000
MODEL_MIN_VOXELS                   = 100
MODEL_SKELETON_DECIMATE_MULTIPLIER = 3
MODEL_RAW_DECIMATE_MULTIPLIER      = 5
MODEL_SCALE_FACTOR                 = 0.0025   # mm → Unity units (tune per dataset)

# ── SMALL STRUCTURE HANDLING ─────────────────────────────────────────────────
SMALL_STRUCTURE_KEYWORDS = [
    "artery", "vein", "vessel", "nerve", "trunk", "cava", "aorta",
    "thyroid", "adrenal", "gallbladder", "appendage"
]
SMALL_STRUCTURE_MIN_VOXELS      = 20
SMALL_STRUCTURE_DECIMATE_FACTOR = 1.5

# ── REFERENCE PLY DISCOVERY ───────────────────────────────────────────────────
# Rule (ingest/reference.py):
#   0 files  -> error
#   1 file   -> use it
#   >1 files -> look for a file literally named this; else fall back to most-recent mtime
REFERENCE_PREFERRED_NAME = "reference.ply"

# ── NETWORK (serve stage) ─────────────────────────────────────────────────────
MULTICAST_GROUP    = "239.255.42.42"
CT_BROADCAST_PORT   = 5013
CT_TCP_PORT          = 5012
