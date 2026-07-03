# CT Pipeline

Restructured, format-agnostic pipeline: CT scan data (`.nii.gz` segmentation
folders or `.IMA` slice folders) → aligned `.ply` point clouds (raw + union)
→ optional `.glb` models → match against a reference scan → send to Quest.

## Directory layout

```
ct_pipeline/                     # installable package — all code lives here
  config.py                      # single source of truth for every path/constant
  cli.py                         # entrypoint: python -m ct_pipeline.cli <command>
  ingest/        # Stage 1 — locate + normalize input (format dispatch lives ONLY here)
  extract/       # Stage 2 — volume -> binary surface (raw / union)
  pointcloud/    # Stage 3 — surface -> aligned, scaled .ply
  model/         # Stage 4 — .ply/volume -> .glb
  matching/      # Stage 5 — reference vs database (ICP + anthropometric features)
  serve/         # Stage 6 — TCP + multicast, sends matched .glb to Quest
  view/          # Stage 7 — visualize .ply
  pipeline/      # Orchestration only — chains the stages above, no algorithm logic
  converters/    # One-off scan -> reference.ply converters (STL phantom, raw IMA folder)

io_data/
  i_data/
    ct_data/
      nii_gz/<patient>/segmentations/*.nii.gz, ct.nii.gz
      ima/<patient>/*.IMA
    reference_data/*.ply           # auto-discovered (see rule below)
  o_data/
    pointclouds/{raw,union}/<patient>.ply
    models/{raw,union,merged}/<patient>.glb
```

## Setup

```bash
conda create -n ct_pipeline python=3.12
conda activate ct_pipeline
pip install -r requirements.txt
```

<!-- ## Migrating existing data (PC2, one-time)

Run **on PC2**, from your *old* `ct_pipeline/` directory, before swapping in this new code:

```bash
bash migrate.sh /path/to/new_ct_pipeline_root
```

Copies (never deletes) your existing `wholebody/` dataset and generated `.ply`/`.glb`
files into the new `io_data/` layout. See comments in `migrate.sh` — it doesn't
know about any existing `.IMA` folders since none existed in the old layout;
drop those under `io_data/i_data/ct_data/ima/<patient>/` manually. -->

## CLI

Single entrypoint, replaces the old `run_preprocess.py` / `run_matching.py` /
`export_models.py` / `glbsender.py` / `view/visualize.py` scripts.

```bash
# Build point clouds (raw + union) for all discovered nii_gz patients
python -m ct_pipeline.cli create-model --format nii_gz

# One patient, raw only, also export .glb
python -m ct_pipeline.cli create-model --format nii_gz --patients s1388 --mode raw --with-glb

# IMA patient — same command, format is the only thing that changes
python -m ct_pipeline.cli create-model --format ima --patients p001 --with-glb

# Also produce a combined raw+union .glb
python -m ct_pipeline.cli create-model --patients s1388 --with-glb --merge

# Force reprocess
python -m ct_pipeline.cli create-model --overwrite

# Test matching locally (no Quest, no real reference scan needed)
python -m ct_pipeline.cli test-match --fake s1388
python -m ct_pipeline.cli test-match --fake s1388 --noise 20 --rotation 30 --dropout 0.4
python -m ct_pipeline.cli test-match --mode union --fake s1371

# Run the Quest-facing server (auto-discovers reference.ply from reference_data/)
python -m ct_pipeline.cli match-and-send --mode raw
python -m ct_pipeline.cli match-and-send --mode raw --interactive   # manual trigger, no Quest needed

# View
python -m ct_pipeline.cli view -p s1388 --source union
python -m ct_pipeline.cli view --all --source both --save
python -m ct_pipeline.cli view --ply /path/to/file.ply
python -m ct_pipeline.cli view --seg /path/to/s1388   # generate + view on the fly, no .ply needed
```

Every path flag (`--db-dir`, `--save-dir`, etc.) defaults to the `io_data/`
layout in `config.py` and can be overridden per-call — nothing is hardcoded
to one directory.

## Reference `.ply` discovery rule (`ingest/reference.py`)

- 0 files in `reference_data/` → error
- 1 file → use it
- \>1 files → use `reference.ply` if present, else the most-recently-modified `.ply`
- Always prints what was picked and what else was found — never silent.

Override anytime with `--ref-ply /explicit/path.ply` (skips discovery entirely).

## Format extensibility (IMA + TotalSegmentator, later)

`ingest/discovery.py:resolve_extractor()` is the **only** place that knows
which extraction function to use per format. Today:

- `nii_gz` → real per-organ union (`extract/segmentation.py`) + HU-threshold raw
- `ima` → both raw and union come from the same threshold surface
  (`extract/ima_surface.py`) — no organ separation yet

When TotalSegmentator support for `.IMA` is added (`extract/totalseg.py`,
currently a stub), only `resolve_extractor()`'s `ima` branch changes.
`pointcloud/`, `model/`, and `matching/` need zero changes — they only ever
see "a binary volume + affine", never a format.

## What's algorithmically unchanged

PCA alignment, scale normalization, marching cubes, organ mesh
decimation/coloring, the 46-dim anthropometric feature vector + weights,
ICP registration, the 60/40 (or 90/10 fallback) combined scoring, multicast
discovery, and the TCP header+bytes protocol are all byte-for-byte the same
logic as before — only file location and import paths changed.

One pre-existing inconsistency was **preserved, not fixed**: the raw model
export never applied `MODEL_SCALE_FACTOR` (only the union/segmentation
export did) — see the note in `model/raw_export.py`. Flagging in case you
want it fixed now that it's visible.


# making requirements.txt
```
touch requirements_compile.in                                               # put name of libraries that you installed after after making virtual env 
pip-compile requirements_compile.in                                         # create requirements_compile.txt   # autogenerated one

bash pin_requirements.sh requirements_compile.in requirements.txt           # to make requirements.txt
```
