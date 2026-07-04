"""
Single CLI entrypoint for the CT pipeline. Subcommands:

  create-model    Build point cloud(s) + optionally .glb model(s) for patients
  match-and-send  Run the Quest-facing TCP server (matches reference scan -> sends .glb)
  test-match      Run matching locally against a fake scan (no Quest/reference needed)
  view            Visualize .ply point clouds

Every path argument (--db-dir, --ref-dir, --out-dir, etc.) has a default
pulled from config.py's io_data layout, and can be overridden per-call.

Usage:
  python -m ct_pipeline.cli create-model --format nii_gz
  python -m ct_pipeline.cli create-model --format ima --patients p001 --mode raw
  python -m ct_pipeline.cli match-and-send --mode raw
  python -m ct_pipeline.cli test-match --fake s1388
  python -m ct_pipeline.cli test-match --real-ply /path/to/scan.ply
  python -m ct_pipeline.cli view --all --source union --save
"""
import argparse
import sys

from ct_pipeline import config


def cmd_create_model(args):
    from ct_pipeline.pipeline import create_model
    config.ensure_dirs()
    create_model.run(
        patients=args.patients,
        fmt=args.format,
        db_dir=args.db_dir,
        mode=args.mode,
        with_glb=args.with_glb,
        make_merged=args.merge,
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


def build_parser():
    parser = argparse.ArgumentParser(prog="ct-pipeline", description="CT Pipeline CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # ── create-model ──────────────────────────────────────────────────────
    p = sub.add_parser("create-model", help="Build point cloud(s) + optional .glb model(s)")
    p.add_argument("--format", choices=["nii_gz", "ima"], default="nii_gz",
                    help="Source CT format (default: nii_gz)")
    p.add_argument("--db-dir", default=None,
                    help="Path to ct_data/ root (default: io_data/i_data/ct_data)")
    p.add_argument("--patients", nargs="+", default=None,
                    help="Patient IDs (default: auto-discover all under db-dir/format/)")
    p.add_argument("--mode", choices=["raw", "union", "both"], default="both",
                    help="Which point cloud(s)/model(s) to build (default: both)")
    p.add_argument("--with-glb", action="store_true",
                    help="Also export .glb model(s), not just .ply")
    p.add_argument("--merge", action="store_true",
                    help="Also build a merged raw+union .glb (requires --with-glb --mode both)")
    p.add_argument("--overwrite", action="store_true",
                    help="Reprocess even if output already exists")
    p.set_defaults(func=cmd_create_model)

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