"""
Single CLI entrypoint for the CT pipeline. Subcommands:

  build-ply       Build .ply point cloud(s) for patients
  build-glb       Build raw/union .glb model(s) for patients, straight from
                   the source volume — no .ply involved
  merge-glb       Merge an existing raw.glb + union.glb into one merged.glb
                   — no CT data, .ply, or format involved
  match-and-send  Run the Quest-facing TCP server (matches reference scan -> sends .glb)
  test-match      Run matching locally against a fake scan (no Quest/reference needed)
  view            Visualize .ply point clouds

build-ply, build-glb, and merge-glb are fully independent stages — each
only imports the module tree it actually needs (pointcloud/, model/,
model/ minus merge_export respectively), so you can build/rebuild any one
of them without touching the others. Chain them yourself when you want
the old "everything" behavior, e.g.:

  python -m ct_pipeline.cli build-ply  --format nii_gz
  python -m ct_pipeline.cli build-glb  --format nii_gz
  python -m ct_pipeline.cli merge-glb  --patients p001 p002

Every path argument (--db-dir, --ref-dir, --out-dir, etc.) has a default
pulled from config.py's io_data layout, and can be overridden per-call.

Usage:
  python -m ct_pipeline.cli build-ply --format nii_gz
  python -m ct_pipeline.cli build-glb --format ima --patients p001 --mode raw
  python -m ct_pipeline.cli merge-glb --patients p001
  python -m ct_pipeline.cli merge-glb --raw-glb /path/raw.glb --union-glb /path/union.glb --out /path/merged.glb
  python -m ct_pipeline.cli match-and-send --mode raw
  python -m ct_pipeline.cli match-and-send --mode raw --send union --apply-scale
  python -m ct_pipeline.cli match-and-send --send merged --apply-scale --scale-factor 0.0025
  python -m ct_pipeline.cli test-match --fake s1388
  python -m ct_pipeline.cli test-match --real-ply /path/to/scan.ply
  python -m ct_pipeline.cli view --all --source union --save
"""
import argparse
import sys

from ct_pipeline import config


def cmd_build_ply(args):
    from ct_pipeline.pipeline import build_pointcloud
    config.ensure_dirs()
    build_pointcloud.run(
        patients=args.patients,
        fmt=args.format,
        db_dir=args.db_dir,
        mode=args.mode,
        overwrite=args.overwrite,
        verbose=True,
    )


def cmd_build_glb(args):
    from ct_pipeline.pipeline import build_model
    config.ensure_dirs()
    build_model.run(
        patients=args.patients,
        fmt=args.format,
        db_dir=args.db_dir,
        mode=args.mode,
        overwrite=args.overwrite,
        verbose=True,
    )


def cmd_merge_glb(args):
    from ct_pipeline.pipeline import merge_model
    config.ensure_dirs()
    merge_model.run(
        patients=args.patients,
        raw_glb=args.raw_glb,
        union_glb=args.union_glb,
        out=args.out,
        overwrite=args.overwrite,
        verbose=True,
    )


def cmd_match_and_send(args):
    from ct_pipeline.pipeline import run_match_and_serve
    config.ensure_dirs()
    run_match_and_serve.run(
        mode=args.mode,
        send=args.send,
        threshold=args.threshold,
        tcp_port=args.tcp_port,
        ref_ply=args.ref_ply,
        ref_dir=args.ref_dir,
        apply_scale=args.apply_scale,
        scale_factor=args.scale_factor,
        verbose=True,
    )


def cmd_test_match(args):
    from ct_pipeline.pipeline import run_test_match
    run_test_match.run(
        fake_patient=args.fake,
        real_ply=args.real_ply,
        mode=args.mode,
        threshold=args.threshold,
        retries=args.retries,
        voxel_size=args.voxel_size,
        noise=args.noise,
        rotation=args.rotation,
        dropout=args.dropout,
        verbose=True,
    )


def cmd_view(args):
    from ct_pipeline.pipeline import run_view
    run_view.run(
        patients=args.patients,
        all_patients=args.all,
        ply_paths=args.ply,
        seg_paths=args.seg,
        dir_path=args.dir,
        source=args.source,
        save=args.save,
        save_dir=args.save_dir,
        stats=True,
    )


def _add_patient_source_args(p):
    """Shared --format/--db-dir/--patients/--mode args for build-ply and build-glb."""
    p.add_argument("--format", choices=["nii_gz", "ima"], default="nii_gz",
                    help="Source CT format (default: nii_gz)")
    p.add_argument("--db-dir", default=None,
                    help="Path to ct_data/ root (default: io_data/i_data/ct_data)")
    p.add_argument("--patients", nargs="+", default=None,
                    help="Patient IDs (default: auto-discover all under db-dir/format/)")
    p.add_argument("--mode", choices=["raw", "union", "both"], default="both",
                    help="Which raw/union output(s) to build (default: both)")
    p.add_argument("--overwrite", action="store_true",
                    help="Reprocess even if output already exists")


def build_parser():
    parser = argparse.ArgumentParser(prog="ct-pipeline", description="CT Pipeline CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # ── build-ply ─────────────────────────────────────────────────────────
    p = sub.add_parser("build-ply", help="Build .ply point cloud(s) — independent of .glb")
    _add_patient_source_args(p)
    p.set_defaults(func=cmd_build_ply)

    # ── build-glb ─────────────────────────────────────────────────────────
    p = sub.add_parser("build-glb", help="Build raw/union .glb model(s) — independent of .ply")
    _add_patient_source_args(p)
    p.set_defaults(func=cmd_build_glb)

    # ── merge-glb ─────────────────────────────────────────────────────────
    p = sub.add_parser("merge-glb", help="Merge existing raw.glb + union.glb — needs nothing else")
    p.add_argument("--patients", nargs="+", default=None,
                    help="Patient IDs — merges each one's raw/union .glb from default "
                         "config locations. Omit when using --raw-glb/--union-glb/--out.")
    p.add_argument("--raw-glb", default=None,
                    help="Explicit path to a raw .glb (overrides the patient_id default)")
    p.add_argument("--union-glb", default=None,
                    help="Explicit path to a union .glb (overrides the patient_id default)")
    p.add_argument("--out", default=None,
                    help="Explicit output path (overrides the patient_id default)")
    p.add_argument("--overwrite", action="store_true",
                    help="Reprocess even if output already exists")
    p.set_defaults(func=cmd_merge_glb)

    # ── match-and-send ────────────────────────────────────────────────────
    p = sub.add_parser("match-and-send", help="Run the Quest-facing TCP match+send server")
    p.add_argument("--mode", choices=["raw", "union"], default="raw",
                    help="Which point cloud database to match against (default: raw). "
                         "No 'merged' here — only .glb models have a merged variant, not point clouds.")
    p.add_argument("--send", choices=["raw", "union", "merged"], default="union",
                    help="Which .glb model folder to send once matched (default: union)")
    p.add_argument("--threshold", type=float, default=0.55)
    p.add_argument("--tcp-port", type=int, default=config.CT_TCP_PORT)
    p.add_argument("--ref-ply", default=None,
                    help="Explicit path to a reference .ply, OR a filename to prefer "
                         "when multiple candidates exist in --ref-dir (default: auto-discover)")
    p.add_argument("--ref-dir", default=None,
                    help="Path to reference_data/ root (default: io_data/i_data/reference_data)")
    p.add_argument("--apply-scale", action="store_true",
                    help="Scale every .glb this server sends by MODEL_SCALE_FACTOR (or "
                         "--scale-factor) in memory before sending, without touching the "
                         "file on disk. Use this when the models in --send's folder weren't "
                         "produced by this pipeline's own scaled export path.")
    p.add_argument("--scale-factor", type=float, default=None,
                    help="Override the scale factor used with --apply-scale "
                         "(default: config.MODEL_SCALE_FACTOR). Ignored without --apply-scale.")
    p.set_defaults(func=cmd_match_and_send)

    # ── test-match ────────────────────────────────────────────────────────
    p = sub.add_parser("test-match", help="Test matching locally, no Quest needed")
    p.add_argument("--fake", default=None,
                    help="Generate a fake scan from this patient ID (perturbed copy of a "
                         "database cloud — tests the algorithm). Default source if "
                         "--real-ply is not given.")
    p.add_argument("--real-ply", default=None,
                    help="Path to a real .ply (camera/STL/IMA capture) to match instead of "
                         "a fake scan — tests the real capture pipeline, incl. discovery + "
                         "alignment. Replaces the old `match-and-send --interactive` mode.")
    p.add_argument("--mode", choices=["raw", "union"], default="raw")
    p.add_argument("--threshold", type=float, default=0.55)
    p.add_argument("--retries", type=int, default=3)
    p.add_argument("--voxel-size", type=float, default=10.0)
    p.add_argument("--noise", type=float, default=5.0)
    p.add_argument("--rotation", type=float, default=15.0)
    p.add_argument("--dropout", type=float, default=0.3)
    p.set_defaults(func=cmd_test_match)

    # ── view ──────────────────────────────────────────────────────────────
    p = sub.add_parser("view", help="Visualize .ply point clouds")
    p.add_argument("-p", "--patients", nargs="+", default=None)
    p.add_argument("--source", choices=["union", "raw", "both"], default="union")
    p.add_argument("--ply", nargs="+", default=None, help="Direct paths to .ply files")
    p.add_argument("--seg", nargs="+", default=None, help="Direct paths to segmentation folders")
    p.add_argument("--dir", default=None, help="Directory containing .ply files")
    p.add_argument("--all", action="store_true", help="Visualize all patients discovered in the ply output dirs")
    p.add_argument("--save", action="store_true")
    p.add_argument("--save-dir", default=None)
    p.set_defaults(func=cmd_view)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "view" and not any([args.patients, args.ply, args.seg, args.dir, args.all]):
        print("No input specified — showing all patients. Use -h for options.")
        args.all = True

    args.func(args)


if __name__ == "__main__":
    sys.exit(main() or 0)
# """
# Single CLI entrypoint for the CT pipeline. Subcommands:

#   create-model    Build point cloud(s) + optionally .glb model(s) for patients
#   match-and-send  Run the Quest-facing TCP server (matches reference scan -> sends .glb)
#   test-match      Run matching locally against a fake scan (no Quest/reference needed)
#   view            Visualize .ply point clouds

# Every path argument (--db-dir, --ref-dir, --out-dir, etc.) has a default
# pulled from config.py's io_data layout, and can be overridden per-call.

# Usage:
#   python -m ct_pipeline.cli create-model --format nii_gz
#   python -m ct_pipeline.cli create-model --format ima --patients p001 --mode raw
#   python -m ct_pipeline.cli match-and-send --mode raw
#   python -m ct_pipeline.cli test-match --fake s1388
#   python -m ct_pipeline.cli test-match --real-ply /path/to/scan.ply
#   python -m ct_pipeline.cli view --all --source union --save
# """
# import argparse
# import sys

# from ct_pipeline import config


# def cmd_create_model(args):
#     from ct_pipeline.pipeline import create_model
#     config.ensure_dirs()
#     create_model.run(
#         patients=args.patients,
#         fmt=args.format,
#         db_dir=args.db_dir,
#         mode=args.mode,
#         with_glb=args.with_glb,
#         make_merged=args.merge,
#         overwrite=args.overwrite,
#         verbose=True,
#     )


# def cmd_match_and_send(args):
#     from ct_pipeline.pipeline import run_match_and_serve
#     config.ensure_dirs()
#     run_match_and_serve.run(
#         mode=args.mode,
#         send=args.send,
#         threshold=args.threshold,
#         tcp_port=args.tcp_port,
#         ref_ply=args.ref_ply,
#         ref_dir=args.ref_dir,
#         verbose=True,
#     )


# def cmd_test_match(args):
#     from ct_pipeline.pipeline import run_test_match
#     run_test_match.run(
#         fake_patient=args.fake,
#         real_ply=args.real_ply,
#         mode=args.mode,
#         threshold=args.threshold,
#         retries=args.retries,
#         voxel_size=args.voxel_size,
#         noise=args.noise,
#         rotation=args.rotation,
#         dropout=args.dropout,
#         verbose=True,
#     )


# def cmd_view(args):
#     from ct_pipeline.pipeline import run_view
#     run_view.run(
#         patients=args.patients,
#         all_patients=args.all,
#         ply_paths=args.ply,
#         seg_paths=args.seg,
#         dir_path=args.dir,
#         source=args.source,
#         save=args.save,
#         save_dir=args.save_dir,
#         stats=True,
#     )


# def build_parser():
#     parser = argparse.ArgumentParser(prog="ct-pipeline", description="CT Pipeline CLI")
#     sub = parser.add_subparsers(dest="command", required=True)

#     # ── create-model ──────────────────────────────────────────────────────
#     p = sub.add_parser("create-model", help="Build point cloud(s) + optional .glb model(s)")
#     p.add_argument("--format", choices=["nii_gz", "ima"], default="nii_gz",
#                     help="Source CT format (default: nii_gz)")
#     p.add_argument("--db-dir", default=None,
#                     help="Path to ct_data/ root (default: io_data/i_data/ct_data)")
#     p.add_argument("--patients", nargs="+", default=None,
#                     help="Patient IDs (default: auto-discover all under db-dir/format/)")
#     p.add_argument("--mode", choices=["raw", "union", "both"], default="both",
#                     help="Which point cloud(s)/model(s) to build (default: both)")
#     p.add_argument("--with-glb", action="store_true",
#                     help="Also export .glb model(s), not just .ply")
#     p.add_argument("--merge", action="store_true",
#                     help="Also build a merged raw+union .glb (requires --with-glb --mode both)")
#     p.add_argument("--overwrite", action="store_true",
#                     help="Reprocess even if output already exists")
#     p.set_defaults(func=cmd_create_model)

#     # ── match-and-send ────────────────────────────────────────────────────
#     p = sub.add_parser("match-and-send", help="Run the Quest-facing TCP match+send server")
#     p.add_argument("--mode", choices=["raw", "union"], default="raw",
#                     help="Which point cloud database to match against (default: raw). "
#                          "No 'merged' here — only .glb models have a merged variant, not point clouds.")
#     p.add_argument("--send", choices=["raw", "union", "merged"], default="union",
#                     help="Which .glb model folder to send once matched (default: union)")
#     p.add_argument("--threshold", type=float, default=0.55)
#     p.add_argument("--tcp-port", type=int, default=config.CT_TCP_PORT)
#     p.add_argument("--ref-ply", default=None,
#                     help="Explicit path to a reference .ply, OR a filename to prefer "
#                          "when multiple candidates exist in --ref-dir (default: auto-discover)")
#     p.add_argument("--ref-dir", default=None,
#                     help="Path to reference_data/ root (default: io_data/i_data/reference_data)")
#     p.set_defaults(func=cmd_match_and_send)

#     # ── test-match ────────────────────────────────────────────────────────
#     p = sub.add_parser("test-match", help="Test matching locally, no Quest needed")
#     p.add_argument("--fake", default=None,
#                     help="Generate a fake scan from this patient ID (perturbed copy of a "
#                          "database cloud — tests the algorithm). Default source if "
#                          "--real-ply is not given.")
#     p.add_argument("--real-ply", default=None,
#                     help="Path to a real .ply (camera/STL/IMA capture) to match instead of "
#                          "a fake scan — tests the real capture pipeline, incl. discovery + "
#                          "alignment. Replaces the old `match-and-send --interactive` mode.")
#     p.add_argument("--mode", choices=["raw", "union"], default="raw")
#     p.add_argument("--threshold", type=float, default=0.55)
#     p.add_argument("--retries", type=int, default=3)
#     p.add_argument("--voxel-size", type=float, default=10.0)
#     p.add_argument("--noise", type=float, default=5.0)
#     p.add_argument("--rotation", type=float, default=15.0)
#     p.add_argument("--dropout", type=float, default=0.3)
#     p.set_defaults(func=cmd_test_match)

#     # ── view ──────────────────────────────────────────────────────────────
#     p = sub.add_parser("view", help="Visualize .ply point clouds")
#     p.add_argument("-p", "--patients", nargs="+", default=None)
#     p.add_argument("--source", choices=["union", "raw", "both"], default="union")
#     p.add_argument("--ply", nargs="+", default=None, help="Direct paths to .ply files")
#     p.add_argument("--seg", nargs="+", default=None, help="Direct paths to segmentation folders")
#     p.add_argument("--dir", default=None, help="Directory containing .ply files")
#     p.add_argument("--all", action="store_true", help="Visualize all patients discovered in the ply output dirs")
#     p.add_argument("--save", action="store_true")
#     p.add_argument("--save-dir", default=None)
#     p.set_defaults(func=cmd_view)

#     return parser


# def main():
#     parser = build_parser()
#     args = parser.parse_args()

#     if args.command == "view" and not any([args.patients, args.ply, args.seg, args.dir, args.all]):
#         print("No input specified — showing all patients. Use -h for options.")
#         args.all = True

#     args.func(args)


# if __name__ == "__main__":
#     sys.exit(main() or 0)