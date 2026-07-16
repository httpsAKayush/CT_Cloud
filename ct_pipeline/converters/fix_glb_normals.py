"""
Standalone utility to fix inward-facing normals on externally-sourced .glb
files (e.g. downloaded models, models from other tools) before they're
served to Quest. Unlike our own pipeline's mesh_export.py / raw_surface.py
(which already produce correct normals at generation time), these files
come from outside our control and may have inconsistent winding.

Usage:
    python fix_glb_normals.py /path/to/model.glb
    python fix_glb_normals.py /path/to/folder/          # fixes every .glb in the folder
    python fix_glb_normals.py /path/to/folder/ --dry-run  # report only, don't overwrite
"""
import sys
import os
import argparse
import trimesh


def fix_glb(path, dry_run=False):
    """
    Load a .glb, check each geometry's winding via signed volume, invert any
    that are inward-facing, and re-export in place (unless dry_run).
    Returns the number of geometries that were flipped.
    """
    scene = trimesh.load(path, process=False)

    # trimesh.load on a .glb with multiple nodes returns a Scene;
    # a single-mesh .glb can load as a bare Trimesh — normalize both cases
    # into a dict of {name: mesh} to handle uniformly.
    if isinstance(scene, trimesh.Trimesh):
        geoms = {"mesh": scene}
    else:
        geoms = dict(scene.geometry)

    flipped_count = 0
    new_geoms = {}

    for name, mesh in geoms.items():
        if not isinstance(mesh, trimesh.Trimesh):
            new_geoms[name] = mesh
            continue

        if mesh.volume < 0:
            mesh.invert()
            flipped_count += 1
            print(f"    Flipped: '{name}' (was inward-facing)")

        new_geoms[name] = mesh

    if flipped_count == 0:
        print(f"  {os.path.basename(path)}: no inverted normals found, skipping")
        return 0

    print(f"  {os.path.basename(path)}: fixed {flipped_count} geometr{'y' if flipped_count == 1 else 'ies'}")

    if not dry_run:
        if isinstance(scene, trimesh.Trimesh):
            new_geoms["mesh"].export(path)
        else:
            fixed_scene = trimesh.Scene()
            for name, mesh in new_geoms.items():
                fixed_scene.add_geometry(mesh, node_name=name)
            fixed_scene.export(path)

    return flipped_count


def main():
    parser = argparse.ArgumentParser(description="Fix inward-facing normals in .glb files")
    parser.add_argument("path", help="Path to a .glb file or a folder containing .glb files")
    parser.add_argument("--dry-run", action="store_true", help="Report issues without modifying files")
    args = parser.parse_args()

    if os.path.isdir(args.path):
        glb_files = [
            os.path.join(args.path, f)
            for f in sorted(os.listdir(args.path))
            if f.lower().endswith(".glb")
        ]
        if not glb_files:
            print(f"No .glb files found in {args.path}")
            return
        print(f"Checking {len(glb_files)} .glb file(s) in {args.path}\n")
    else:
        glb_files = [args.path]

    total_flipped = 0
    for f in glb_files:
        total_flipped += fix_glb(f, dry_run=args.dry_run)

    print(f"\nDone. {total_flipped} geometr{'y' if total_flipped == 1 else 'ies'} fixed"
          f"{' (dry run — no files modified)' if args.dry_run else ''}.")


if __name__ == "__main__":
    main()