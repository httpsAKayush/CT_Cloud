# Quick Setup
```
conda create -n ct_pipeline python=3.12
conda activate ct_pipeline
pip install -r requirements.txt
```

# CLI - Cmd line Interface
```
conda activate ct_pipeline
python run_preprocess.py                          # all patients 
python run_preprocess.py --patients s1388        # one patient
python run_preprocess.py --overwrite             # force redo
pyhton run_preprocess.py --raw                   # all raw patients
```



# ── MATCHING ─────────────────────────────────────────────────────────────────
# Test with fake scan from s1388 (should match itself)
python run_matching.py --fake s1388

# Test with different source patient
python run_matching.py --fake s1371

# Stress test with heavy noise/rotation/dropout
python run_matching.py --fake s1388 --noise 20 --rotation 30 --dropout 0.4

# Use raw CT threshold database instead
python run_matching.py --fake s1388 --mode ct_threshold

# Match against a real depth camera scan
python run_matching.py --real /path/to/real_scan.ply

# Tune threshold and retries
python run_matching.py --fake s1388 --threshold 0.80 --retries 5

# Tune ICP voxel size (smaller = more precise but slower)
python run_matching.py --fake s1388 --voxel-size 5.0