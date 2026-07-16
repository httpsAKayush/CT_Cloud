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
  model/         # Stage 4 — .ply/volume -> .glb (builder.py: raw+union from volume)
                 #   + Stage 5 — merge_builder.py: raw.glb+union.glb -> merged.glb,
                 #   fully decoupled from everything above it (see below)
  matching/      # Stage 6 — reference vs database (ICP + anthropometric features);
                 #   matcher.py also owns run_reference_match() (discover + match)
  serve/         # Stage 7 — model_sender.py (send_glb: patient_id -> bytes) +
                 #   tcp_server.py (socket/dispatch only) + multicast broadcast
  view/          # Stage 8 — visualize .ply
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

```bash for conda
conda create -n ct_pipeline python=3.12
conda activate ct_pipeline
pip install -r requirements.txt
```
```bash for venv
python3.12 -m venv ct_pipeline
source ct_pipeline/bin/activate
pip install -r requirements.txt
```

<!-- multi

  ######

comment-->

## CLI

Single entrypoint, replaces the old `run_preprocess.py` / `run_matching.py` /
`export_models.py` / `glbsender.py` / `view/visualize.py` scripts.

`.ply` point clouds, `.glb` raw/union models, and merged `.glb` are three
**independent** commands now — not one `create-model` with a pile of flags.
Each only touches the input it actually needs:

| command      | needs                          | never touches                     |
|--------------|---------------------------------|------------------------------------|
| `build-ply`  | source volume (nii_gz/ima)      | anything in `model/`               |
| `build-glb`  | source volume (nii_gz/ima)      | `.ply` files                       |
| `merge-glb`  | an existing raw.glb + union.glb | source volume, `.ply`, format/db-dir |

Run them independently, or chain them yourself when you want the old
"do everything" behavior:

```bash

#depth scan 
python -m ct_pipeline.converters.camera_to_ply


# Build point clouds (raw + union) for all discovered nii_gz patients
python -m ct_pipeline.cli build-ply --format nii_gz

# One patient, raw point cloud only
python -m ct_pipeline.cli build-ply --format nii_gz --patients s1388 --mode raw

# Build raw+union .glb for the same patient — independent call, no .ply touched
python -m ct_pipeline.cli build-glb --format nii_gz --patients s1388

# IMA patient — same commands, format is the only thing that changes
python -m ct_pipeline.cli build-ply --format ima --patients p001
python -m ct_pipeline.cli build-glb --format ima --patients p001

# Merge raw+union .glb for a patient — only reads the two .glb files already
# on disk at their default config locations, nothing else
python -m ct_pipeline.cli merge-glb --patients s1388

# Merge two arbitrary .glb files directly — no patient_id, no format, no
# db-dir, works even on files that never went through this pipeline
python -m ct_pipeline.cli merge-glb --raw-glb /path/raw.glb --union-glb /path/union.glb --out /path/merged.glb

# Force reprocess (same --overwrite flag on all three)
python -m ct_pipeline.cli build-ply --overwrite
python -m ct_pipeline.cli build-glb --overwrite
python -m ct_pipeline.cli merge-glb --patients s1388 --overwrite



# Test matching locally, no Quest and no socket involved — two scan sources:
# a) fake scan: perturbed copy of a database cloud (tests the algorithm/thresholds)
python -m ct_pipeline.cli test-match --fake s1388
python -m ct_pipeline.cli test-match --fake s1388 --noise 20 --rotation 30 --dropout 0.4
python -m ct_pipeline.cli test-match --mode union --fake s1371
# b) real .ply from disk (tests the real capture pipeline: camera/STL/IMA
#    conversion, alignment, everything up to the socket layer)
python -m ct_pipeline.cli test-match --real-ply /path/to/scan.ply




# Run the Quest-facing server (auto-discovers reference.ply from reference_data/)
python -m ct_pipeline.cli match-and-send --mode raw --send union

# Point at an explicit reference file instead of auto-discovery
python -m ct_pipeline.cli match-and-send --ref-ply /path/to/scan.ply



# View
python -m ct_pipeline.cli view -p s1388 --source union
python -m ct_pipeline.cli view --all --source both --save
python -m ct_pipeline.cli view --ply /path/to/file.ply
python -m ct_pipeline.cli view --seg /path/to/s1388   # generate + view on the fly, no .ply needed



```


# patients related flags, changable
Every path flag (`--db-dir`, `--save-dir`, `--ref-dir`, etc.) defaults to the
`io_data/` layout in `config.py` and can be overridden per-call — nothing is
hardcoded to one directory.


# real-ply test
`match-and-send` has no `--interactive` flag anymore — 
that mode was doing
the exact same thing as `test-match --real-ply` (match a real file, print
the result, don't send anything), 
just under a different name. Use
`test-match --real-ply <path>` instead when you want to sanity-check a real
scan without a Quest connected.



## Why `merge-glb` is a separate command

Merging only ever reads two already-built `.glb` files and writes a third —

it was never actually a part of the volume → surface → mesh pipeline, it
just used to be *bundled into* `create-model` behind a `--merge` flag that
still demanded `--format`/`--db-dir`/patient discovery it didn't use. 
Now,
`model/merge_builder.py` is the only module that imports `merge_export.py`,
and it takes either a `patient_id` (default raw/union/merged paths from
config) or fully explicit `--raw-glb`/`--union-glb`/`--out` paths — so you
can re-run or retune a merge at any time without the source CT data,
segmentations, or point clouds existing anywhere.


## Reference `.ply` discovery rule (`ingest/reference.py`)

- 0 files in `reference_data/` → error
- 1 file → use it
- \>1 files → use `reference.ply` if present, else the most-recently-modified `.ply`
- Always prints what was picked and what else was found — never silent.

Override with `--ref-ply`, which accepts either:
- an explicit path (`/path/to/scan.ply`) → skips discovery entirely, used as-is
- a filename (`scan_b.ply`) → used as the *preferred* candidate when multiple
  files exist in `--ref-dir`, instead of the mtime fallback


## Matching and sending are separate, decoupled steps

```
matching/matcher.py       → run_reference_match()   discover ref + match, returns a result dict
                                                       (no knowledge of .glb, models, or sockets)
serve/model_sender.py     → send_glb()               patient_id -> bytes on the wire
                                                       (no knowledge of how patient_id was chosen)
serve/tcp_server.py       → dispatch only            wires the two together per request
pipeline/run_match_and_serve.py → starts the broadcaster + tcp_server, no logic of its own
```

The TCP server (`match-and-send`) understands two JSON commands:

```jsonc
{"command": "match"}                          // discover ref, match, send matched patient's .glb
{"command": "send", "patient_id": "s1388"}    // skip matching entirely, send this patient directly
                                                // (manual override / testing without waiting on ICP)
```

`--mode` controls which point cloud database (`raw`/`union`) matching runs
against; `--send` controls which `.glb` folder (`raw`/`union`/`merged`) gets
sent once a patient is chosen — these are independent, e.g. match against
`raw` clouds but send the colored `union` model.


## Format extensibility (IMA + TotalSegmentator, later)

`ingest/discovery.py:resolve_extractor()` is the **only** place that knows
which extraction function to use per format. Today:

- `nii_gz` → real per-organ union (`extract/segmentation.py`) + HU-threshold raw
- `ima` → both raw and union come from the same threshold surface
  (`extract/ima_surface.py`) — no organ separation yet

When TotalSegmentator support for `.IMA` is added (`extract/totalseg.py`,
currently a stub), only `resolve_extractor()`'s `ima` branch changes.
`pointcloud/`, `model/`, and `matching/` need zero changes — they only ever
see "a binary volume + affine", never a format. `merge-glb` needs zero
changes regardless — it never sees a format at all.

## What's algorithmically unchanged

PCA alignment, scale normalization, marching cubes, organ mesh
decimation/coloring, the 46-dim anthropometric feature vector + weights,
ICP registration, the 60/40 (or 90/10 fallback) combined scoring, multicast
discovery, and the TCP header+bytes protocol are all byte-for-byte the same
logic as before — only file location, import paths, and how the three
`model/` outputs (raw, union, merged) get orchestrated from the CLI changed.

One pre-existing inconsistency was **preserved, not fixed**: the raw model
export never applied `MODEL_SCALE_FACTOR` (only the union/segmentation
export did) — see the note in `model/raw_export.py`. Flagging in case you
want it fixed now that it's visible.


# making requirements.txt
```
New-Item requirements_compile.in                                            # put name of libraries that you installed after making virtual env
pip-compile requirements_compile.in                                         # create requirements_compile.txt   # autogenerated one

python pin_requirements.py requirements_compile.in requirements.txt         # to make requirements.txt
```