import os
import sys
import json
import socket
import threading
import http.server
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import MODEL_DIR

# ── CONFIG ───────────────────────────────────────────────────────────────────
HTTP_PORT = 8080   # Quest downloads models from here
TCP_PORT  = 5002   # Quest receives patient ID from here
# ─────────────────────────────────────────────────────────────────────────────


class ModelHTTPHandler(http.server.SimpleHTTPRequestHandler):
    """Serves files from MODEL_DIR."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=MODEL_DIR, **kwargs)

    def log_message(self, format, *args):
        print(f"  [HTTP] {self.address_string()} - {format % args}")


def start_http_server(port=HTTP_PORT):
    """Start HTTP file server in background thread."""
    server = http.server.HTTPServer(("0.0.0.0", port), ModelHTTPHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"  [HTTP] Serving models from {MODEL_DIR} on port {port}")
    return server


def send_patient_to_quest(patient_id, confidence, quest_ip, port=TCP_PORT):
    """Send matched patient ID to Quest over TCP."""
    payload = json.dumps({
        "patient_id": patient_id,
        "confidence": confidence,
        "model_url":  f"http://{{quest_ip}}:{HTTP_PORT}/{patient_id}.glb"
    }).replace("{quest_ip}", quest_ip)

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((quest_ip, port))
            s.sendall(payload.encode("utf-8"))
            print(f"  [TCP] Sent to Quest {quest_ip}:{port} → {payload}")
    except Exception as e:
        print(f"  [TCP] ERROR sending to Quest: {e}")


def run_matching_and_serve(real_scan_path, quest_ip,
                           mode="segmentation", threshold=0.55,
                           verbose=True):
    """
    Full pipeline:
    1. Load real scan
    2. Match against database
    3. Send result to Quest
    """
    from matching.matcher import load_database, find_best_match
    from preprocess.alignment import pca_align, normalize_scale
    import open3d as o3d

    print(f"\n── Loading database...")
    database = load_database(mode=mode, verbose=verbose)

    print(f"\n── Loading real scan: {real_scan_path}")
    pcd = o3d.io.read_point_cloud(real_scan_path)
    pcd = pca_align(pcd, verbose=verbose)
    pcd = normalize_scale(pcd, verbose=verbose)

    print(f"\n── Matching...")
    result = find_best_match(pcd, database,
                             threshold=threshold,
                             verbose=verbose)

    print(f"\n── Best match: {result['patient_id']} ({result['confidence']}%)")
    print(f"── Sending to Quest at {quest_ip}...")
    send_patient_to_quest(result["patient_id"],
                          result["confidence"],
                          quest_ip)
    return result


def interactive_mode(quest_ip, http_port=HTTP_PORT, tcp_port=TCP_PORT):
    """
    Manual mode — type patient ID to send to Quest directly.
    Useful for testing without running full matching pipeline.
    """
    print(f"\n── Interactive mode ─────────────────────────────")
    print(f"   Type a patient ID to send to Quest, or 'quit' to exit")
    print(f"   Available: {[f for f in os.listdir(MODEL_DIR) if f.endswith('.glb')]}")

    while True:
        try:
            cmd = input("\n  Patient ID > ").strip()
            if cmd.lower() in ("quit", "exit", "q"):
                break
            if not cmd:
                continue

            glb = os.path.join(MODEL_DIR, f"{cmd}.glb")
            if not os.path.exists(glb):
                print(f"  ERROR: {glb} not found")
                continue

            send_patient_to_quest(cmd, 100.0, quest_ip, tcp_port)

        except KeyboardInterrupt:
            break

    print("\n  Exiting interactive mode.")


def main():
    parser = argparse.ArgumentParser(description="CT Pipeline Server")
    parser.add_argument("--quest-ip", required=True,
                        help="Quest 3 IP address on local network")
    parser.add_argument("--http-port", type=int, default=HTTP_PORT,
                        help=f"HTTP port for model serving (default: {HTTP_PORT})")
    parser.add_argument("--tcp-port", type=int, default=TCP_PORT,
                        help=f"TCP port to send patient ID (default: {TCP_PORT})")
    parser.add_argument("--real-scan", default=None,
                        help="Path to real depth camera .ply scan")
    parser.add_argument("--mode", default="segmentation",
                        choices=["segmentation", "ct_threshold"],
                        help="Point cloud database to match against")
    parser.add_argument("--threshold", type=float, default=0.55,
                        help="Match confidence threshold (default: 0.55)")
    parser.add_argument("--interactive", action="store_true",
                        help="Manual mode: type patient ID to send to Quest")
    parser.add_argument("--verbose", action="store_true", default=True)
    args = parser.parse_args()

    # Start HTTP server
    print(f"\n{'='*50}")
    print(f"CT Pipeline Server")
    print(f"{'='*50}")
    start_http_server(args.http_port)
    print(f"  Quest IP   : {args.quest_ip}")
    print(f"  HTTP port  : {args.http_port}")
    print(f"  TCP port   : {args.tcp_port}")
    print(f"  Models dir : {MODEL_DIR}")
    print(f"  Models available:")
    for f in sorted(os.listdir(MODEL_DIR)):
        if f.endswith(".glb"):
            size = os.path.getsize(os.path.join(MODEL_DIR, f)) / (1024*1024)
            print(f"    {f} ({size:.1f} MB)")

    if args.interactive:
        interactive_mode(args.quest_ip, args.http_port, args.tcp_port)

    elif args.real_scan:
        run_matching_and_serve(
            args.real_scan,
            args.quest_ip,
            mode=args.mode,
            threshold=args.threshold,
            verbose=args.verbose
        )

    else:
        # Just keep HTTP server running, wait for manual trigger
        print(f"\n  HTTP server running. Press Ctrl+C to stop.")
        print(f"  Test: curl http://localhost:{args.http_port}/")
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            print("\n  Shutting down.")


if __name__ == "__main__":
    main()