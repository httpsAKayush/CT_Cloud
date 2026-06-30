import os

# ── PATHS ────────────────────────────────────────────────────────────────────
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR  = os.path.expanduser("~/Downloads/Totalsegmentator_dataset_small_v201/wholebody")
OUTPUT_DIR   = os.path.join(BASE_DIR, "data")
PLY_DIR      = os.path.join(OUTPUT_DIR, "pointclouds")
REAL_SCAN_PATH = os.path.join(PLY_DIR, "real_scan.ply")
UNION_PLY_DIR  = os.path.join(PLY_DIR, "unionclouds")
RAW_PLY_DIR  = os.path.join(PLY_DIR, "rawclouds")
MODEL_DIR    = os.path.join(OUTPUT_DIR, "models")
RAW_MODEL_DIR    = os.path.join(MODEL_DIR, "rawmodels")
UNION_MODEL_DIR    = os.path.join(MODEL_DIR, "unionmodels")

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


# ── MODEL EXPORT ─────────────────────────────────────────────────────────────
MODEL_DECIMATE_FACE_COUNT = 10000      # max faces per individual organ
MODEL_MIN_VOXELS          = 100        # skip organs smaller than this
MODEL_SKELETON_DECIMATE_MULTIPLIER = 3 # skeleton allowed 3x more faces (merged structure)
MODEL_RAW_DECIMATE_MULTIPLIER      = 5 # raw CT surface allowed 5x more faces
MODEL_SCALE_FACTOR        = 0.0025     # mm → Unity units (tune per dataset)

# ── SMALL STRUCTURE HANDLING ─────────────────────────────────────────────────
SMALL_STRUCTURE_KEYWORDS = [
    "artery", "vein", "vessel", "nerve", "trunk", "cava", "aorta",
    "thyroid", "adrenal", "gallbladder", "appendage"
]
SMALL_STRUCTURE_MIN_VOXELS       = 20     # much lower threshold — don't drop these
SMALL_STRUCTURE_DECIMATE_FACTOR  = 1.5    # allow 1.5x more faces (less aggressive decimation)