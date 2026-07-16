"""Orchestration only — chains view.visualize for the `view` CLI command."""
import os
from ct_pipeline.view import visualize as viz


def run(patients=None, all_patients=False, ply_paths=None, seg_paths=None, dir_path=None,
        source="union", save=False, save_dir=None, stats=True):

    resolved_save_dir = None
    if save:
        resolved_save_dir = save_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "view_output"
        )

    if seg_paths:
        for seg_path in seg_paths:
            base = os.path.basename(seg_path.rstrip("/\\"))
            pid = base if base != "segmentations" else os.path.basename(os.path.dirname(seg_path.rstrip("/\\")))
            print(f"\nGenerating point cloud from segmentation folder: {seg_path}")
            try:
                pts = viz.pointcloud_from_seg_folder(seg_path)
                if stats:
                    viz.print_stats(pts, pid)
                viz.plot_patient(pts, pid, save_dir=resolved_save_dir, source_type="union")
            except Exception as e:
                print(f"  ERROR for {pid}: {e}")

    if ply_paths:
        for ply_path in ply_paths:
            pid = os.path.splitext(os.path.basename(ply_path))[0]
            pts = viz.load_ply(ply_path)
            if stats:
                viz.print_stats(pts, pid)
            viz.plot_patient(pts, pid, save_dir=resolved_save_dir, source_type="custom")

    if dir_path:
        ply_files = sorted([
            os.path.join(dir_path, f) for f in os.listdir(dir_path) if f.endswith(".ply")
        ])
        for ply_path in ply_files:
            pid = os.path.splitext(os.path.basename(ply_path))[0]
            print(f"\nLoading {ply_path}")
            try:
                pts = viz.load_ply(ply_path)
                if stats:
                    viz.print_stats(pts, pid)
                viz.plot_patient(pts, pid, save_dir=resolved_save_dir, source_type="custom")
            except Exception as e:
                print(f"ERROR for {pid}: {e}")

    if ply_paths or dir_path or seg_paths:
        return

    targets = viz.resolve_patients(patients, all_patients, source)
    if not targets:
        print("No valid point clouds found. Run `ct-pipeline create-model` first.")
        return

    for _, (pid, source_type, path) in targets.items():
        print(f"\nLoading {pid} from {path}...")
        try:
            pts = viz.load_ply(path)
            if stats:
                viz.print_stats(pts, pid)
            viz.plot_patient(pts, pid, save_dir=resolved_save_dir, source_type=source_type)
        except Exception as e:
            print(f"  ERROR for {pid}: {e}")
