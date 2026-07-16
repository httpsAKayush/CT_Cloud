#!/usr/bin/env python3
"""
One-off converter that permanently decimates existing .glb models.

Unlike serve/model_sender.py, this is an offline preprocessing tool.
It overwrites the original .glb (keeping a .glb.bak backup) so models
are already optimized before the Quest server sends them.

Requires:
    pip install trimesh fast_simplification

Usage:
    # Single model
    python ct_pipeline/converters/decimate_glb.py \
        io_data/o_data/models/merged/phantom.glb

    # Entire directory
    python ct_pipeline/converters/decimate_glb.py \
        io_data/o_data/models/merged

    # All models
    python ct_pipeline/converters/decimate_glb.py \
        io_data/o_data/models

    # Custom face count
    python ct_pipeline/converters/decimate_glb.py \
        io_data/o_data/models/merged \
        --max-faces 10000

    # Overwrite an existing backup
    python ct_pipeline/converters/decimate_glb.py \
        io_data/o_data/models \
        --overwrite-backup
"""

import argparse
from pathlib import Path

import trimesh

DEFAULT_FACE_COUNT = 10000


def decimate_glb(glb_path: Path, max_faces: int, overwrite_backup: bool):
    print(f"\n{'=' * 60}")
    print(glb_path)

    scene = trimesh.load(glb_path, force="scene")

    new_scene = trimesh.Scene()
    changed = False

    for name, mesh in scene.geometry.items():
        if not isinstance(mesh, trimesh.Trimesh):
            new_scene.add_geometry(mesh, node_name=name)
            continue

        before = len(mesh.faces)

        if before > max_faces:
            simplified = mesh.simplify_quadric_decimation(face_count=max_faces)

            if simplified is not None:
                mesh = simplified
                changed = True

        after = len(mesh.faces)
        print(f"  {name}: {before} -> {after} faces")

        new_scene.add_geometry(mesh, node_name=name)

    if not changed:
        print("  Already below target face count.")
        return

    backup = glb_path.with_suffix(".glb.bak")

    if backup.exists():
        if overwrite_backup:
            backup.unlink()
        else:
            print(f"  Backup already exists: {backup}")
            print("  Skipping. Use --overwrite-backup to replace it.")
            return

    glb_path.rename(backup)
    new_scene.export(glb_path)

    old_size = backup.stat().st_size / (1024 * 1024)
    new_size = glb_path.stat().st_size / (1024 * 1024)

    print(f"\n✓ Saved      : {glb_path}")
    print(f"✓ Backup     : {backup}")
    print(f"✓ Size       : {old_size:.2f} MB -> {new_size:.2f} MB")


def main():
    parser = argparse.ArgumentParser(
        description="Offline GLB decimation tool"
    )

    parser.add_argument(
        "path",
        help="GLB file or directory containing GLBs"
    )

    parser.add_argument(
        "--max-faces",
        type=int,
        default=DEFAULT_FACE_COUNT,
        help=f"Target faces per mesh (default: {DEFAULT_FACE_COUNT})"
    )

    parser.add_argument(
        "--overwrite-backup",
        action="store_true",
        help="Replace an existing .glb.bak if present."
    )

    args = parser.parse_args()

    path = Path(args.path)

    if not path.exists():
        parser.error(f"{path} does not exist.")

    if path.is_file():
        if path.suffix.lower() != ".glb":
            parser.error("Input file must be a .glb")
        decimate_glb(path, args.max_faces, args.overwrite_backup)

    else:
        glbs = sorted(path.rglob("*.glb"))

        if not glbs:
            print("No .glb files found.")
            return

        print(f"Found {len(glbs)} GLB file(s).\n")

        for glb in glbs:
            decimate_glb(glb, args.max_faces, args.overwrite_backup)


if __name__ == "__main__":
    main()