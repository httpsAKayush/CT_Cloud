#!/usr/bin/env bash
# Run this ONCE on PC2, from inside the OLD ct_pipeline/ directory,
# BEFORE dropping in the new code. It moves real data into the new
# io_data/ layout. Safe to re-run (uses mv, skips if already moved).
#
# Usage:
#   cd ~/ct_pipeline          # old project root
#   bash migrate.sh /path/to/new_ct_pipeline_root
#
# Adjust OLD_WHOLEBODY below if your dataset lives somewhere else
# (it currently points at the path from your config.py's DATASET_DIR).

set -euo pipefail

NEW_ROOT="${1:?Usage: bash migrate.sh /path/to/new_ct_pipeline_root}"
OLD_WHOLEBODY="$HOME/Downloads/Totalsegmentator_dataset_small_v201/wholebody"

IO_DATA="$NEW_ROOT/io_data"
I_CT_DATA="$IO_DATA/i_data/ct_data"
REF_DIR="$IO_DATA/i_data/reference_data"
O_PLY="$IO_DATA/o_data/pointclouds"
O_MODELS="$IO_DATA/o_data/models"

mkdir -p "$I_CT_DATA/nii_gz" "$I_CT_DATA/ima" "$REF_DIR"
mkdir -p "$O_PLY/raw" "$O_PLY/union"
mkdir -p "$O_MODELS/raw" "$O_MODELS/union" "$O_MODELS/merged"

echo "── 1. Migrating input CT dataset (nii_gz) ──────────────────────────"
if [ -d "$OLD_WHOLEBODY" ]; then
    for pdir in "$OLD_WHOLEBODY"/*/; do
        pid=$(basename "$pdir")
        dest="$I_CT_DATA/nii_gz/$pid"
        if [ -d "$dest" ]; then
            echo "  [$pid] already migrated, skipping"
        else
            echo "  [$pid] -> $dest"
            cp -r "$pdir" "$dest"
        fi
    done
else
    echo "  WARNING: $OLD_WHOLEBODY not found — skipping. Point OLD_WHOLEBODY at your dataset and re-run."
fi

echo ""
echo "── 2. Migrating existing point clouds ───────────────────────────────"
# old layout: data/pointclouds/unionclouds/*.ply, data/pointclouds/rawclouds/*.ply, data/pointclouds/real_scan.ply
if [ -d "data/pointclouds/unionclouds" ]; then
    cp -n data/pointclouds/unionclouds/*.ply "$O_PLY/union/" 2>/dev/null || true
    echo "  union clouds -> $O_PLY/union/"
fi
if [ -d "data/pointclouds/rawclouds" ]; then
    cp -n data/pointclouds/rawclouds/*.ply "$O_PLY/raw/" 2>/dev/null || true
    echo "  raw clouds -> $O_PLY/raw/"
fi
if [ -f "data/pointclouds/real_scan.ply" ]; then
    cp -n data/pointclouds/real_scan.ply "$REF_DIR/reference.ply"
    echo "  real_scan.ply -> $REF_DIR/reference.ply"
fi

echo ""
echo "── 3. Migrating existing models ─────────────────────────────────────"
# old layout: data/models/unionmodels/*.glb, data/models/rawmodels/*.glb
if [ -d "data/models/unionmodels" ]; then
    cp -n data/models/unionmodels/*.glb "$O_MODELS/union/" 2>/dev/null || true
    echo "  union models -> $O_MODELS/union/"
fi
if [ -d "data/models/rawmodels" ]; then
    cp -n data/models/rawmodels/*.glb "$O_MODELS/raw/" 2>/dev/null || true
    echo "  raw models -> $O_MODELS/raw/"
fi

echo ""
echo "── Done. Verify with: find '$IO_DATA' -maxdepth 4 | sort ──────────"
echo "Nothing was deleted from the old project — this only copies."
echo "Once you've verified the new layout, you can remove the old data/ and wholebody/ copies yourself."
