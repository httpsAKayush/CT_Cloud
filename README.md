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