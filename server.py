import os
import sys
import json
import socket
import threading
import http.server
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import UNION_MODEL_DIR, REAL_SCAN_PATH

# ── CONFIG ───────────────────────────────────────────────────────────────────

TCP_PORT  = 5012   # Quest sends "match" trigger here, receives result here
# ─────────────────────────────────────────────────────────────────────────────


class ModelHTTPHandler(http.server.SimpleHTTPRequestHandler):
    """Serves files from UNION_MODEL_DIR."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=UNION_MODEL_DIR, **kwargs)

    def log_message(self, format, *args):
        print(f"  [HTTP] {self.address_string()} - {format % args}")


# def start_http_server(port=HTTP_PORT):
#     server = http.server.HTTPServer(("0.0.0.0", port), ModelHTTPHandler)
#     thread = threading.Thread(target=server.serve_forever, daemon=True)
#     thread.start()
#     print(f"  [HTTP] Serving models from {UNION_MODEL_DIR} on port {port}")
#     return server


def run_matching(real_scan_path, mode="ct_threshold", threshold=0.55, verbose=True):
    """Run the matching pipeline and return result dict."""
    from matching.matcher import load_database, find_best_match
    from preprocess.alignment import pca_align, normalize_scale
    import open3d as o3d

    print(f"\n── Loading database [{mode}]...")
    database = load_database(mode=mode, verbose=verbose)

    print(f"\n── Loading real scan: {real_scan_path}")
    if not os.path.exists(real_scan_path):
        raise FileNotFoundError(f"Real scan not found: {real_scan_path}")

    pcd = o3d.io.read_point_cloud(real_scan_path)
    pcd = pca_align(pcd, verbose=verbose)
    pcd = normalize_scale(pcd, verbose=verbose)

    print(f"\n── Matching...")
    result = find_best_match(pcd, database, threshold=threshold, verbose=verbose)

    print(f"\n── Best match: {result['patient_id']} ({result['confidence']}%)")
    return result


def handle_quest_connection(conn, addr, http_port, mode, threshold, verbose):
    """Handle a single TCP request from Quest."""
    try:
        data = conn.recv(4096).decode("utf-8").strip()
        print(f"\n  [TCP] Received from {addr}: {data}")

        request = json.loads(data) if data.startswith("{") else {"command": data}
        command = request.get("command", "match")

        if command == "match":
            result = run_matching(REAL_SCAN_PATH, mode=mode,
                                  threshold=threshold, verbose=verbose)

            glb_path = os.path.join(UNION_MODEL_DIR, f"{result['patient_id']}.glb")
            if not os.path.exists(glb_path):
                raise FileNotFoundError(f"Model not found: {glb_path}")

            glb_size = os.path.getsize(glb_path)

            # Send header first (JSON + newline delimiter)
            header = {
                "status":      "ok",
                "patient_id":  result["patient_id"],
                "confidence":  result["confidence"],
                "fallback":    result["fallback"],
                "glb_size":    glb_size
            }
            header_bytes = (json.dumps(header) + "\n").encode("utf-8")
            conn.sendall(header_bytes)
            print(f"  [TCP] Sent header: {header}")

            # Send GLB file bytes
            with open(glb_path, "rb") as f:
                glb_data = f.read()
            conn.sendall(glb_data)
            print(f"  [TCP] Sent GLB: {glb_size} bytes")

        else:
            error_response = {"status": "error", "message": f"Unknown command: {command}"}
            conn.sendall((json.dumps(error_response) + "\n").encode("utf-8"))

    except Exception as e:
        print(f"  [TCP] ERROR: {e}")
        try:
            error_response = {"status": "error", "message": str(e)}
            conn.sendall((json.dumps(error_response) + "\n").encode("utf-8"))
        except Exception:
            pass
    finally:
        conn.close()

def get_local_ip():
    """Get the PC's local network IP."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def start_tcp_server(port, http_port, mode, threshold, verbose):
    """
    TCP server that listens for match requests from Quest.
    Each connection triggers a matching run and sends back the result.
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("0.0.0.0", port))
    server_socket.listen(5)
    print(f"  [TCP] Listening for match requests on port {port}")

    while True:
        conn, addr = server_socket.accept()
        thread = threading.Thread(
            target=handle_quest_connection,
            args=(conn, addr, http_port, mode, threshold, verbose),
            daemon=True
        )
        thread.start()


def interactive_mode(http_port, tcp_port):
    """Manual testing mode — trigger matching from keyboard."""
    print(f"\n── Interactive mode ─────────────────────────────")
    print(f"   Press Enter to trigger a match run, or type 'quit' to exit")

    while True:
        try:
            cmd = input("\n  [Enter to match] > ").strip()
            if cmd.lower() in ("quit", "exit", "q"):
                break

            result = run_matching(REAL_SCAN_PATH, mode="ct_threshold", verbose=True)
            print(f"\n  Result: {result['patient_id']} ({result['confidence']}%)")
            print(f"  Model URL: http://{get_local_ip()}:{http_port}/{result['patient_id']}.glb")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"  ERROR: {e}")

    print("\n  Exiting interactive mode.")

def start_udp_broadcaster(tcp_port, interval=2.0):
    """
    Periodically broadcast this server's presence on the local network.
    Quest listens for this to auto-discover the PC's IP.
    """
    BROADCAST_PORT = 5013
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    local_ip = get_local_ip()
    message = json.dumps({
        "service": "ct_pipeline_server",
        "ip": local_ip,
        "tcp_port": tcp_port
    }).encode("utf-8")

    def broadcast_loop():
        while True:
            try:
                sock.sendto(message, ("255.255.255.255", BROADCAST_PORT))
            except Exception as e:
                print(f"  [UDP] Broadcast error: {e}")
            threading.Event().wait(interval)

    thread = threading.Thread(target=broadcast_loop, daemon=True)
    thread.start()
    print(f"  [UDP] Broadcasting presence on port {BROADCAST_PORT} every {interval}s")
    return thread


def main():
    parser = argparse.ArgumentParser(description="CT Pipeline Server")
    
    parser.add_argument("--tcp-port", type=int, default=TCP_PORT)
    parser.add_argument("--mode", default="ct_threshold",
                        choices=["segmentation", "ct_threshold"],
                        help="Point cloud database to match against (default: ct_threshold)")
    parser.add_argument("--threshold", type=float, default=0.55)
    parser.add_argument("--interactive", action="store_true",
                        help="Test mode: press Enter to trigger matching manually")
    parser.add_argument("--verbose", action="store_true", default=True)
    args = parser.parse_args()

    print(f"\n{'='*50}")
    print(f"CT Pipeline Server")
    print(f"{'='*50}")

    local_ip = get_local_ip()
    
    start_udp_broadcaster(args.tcp_port)

    print(f"  Local IP   : {local_ip}")
    
    print(f"  TCP port   : {args.tcp_port}")
    print(f"  Models dir : {UNION_MODEL_DIR}")
    print(f"  Real scan  : {REAL_SCAN_PATH}")
    print(f"  Match mode : {args.mode}")
    print(f"  Models available:")
    for f in sorted(os.listdir(UNION_MODEL_DIR)):
        if f.endswith(".glb"):
            size = os.path.getsize(os.path.join(UNION_MODEL_DIR, f)) / (1024*1024)
            print(f"    {f} ({size:.1f} MB)")

    if args.interactive:
        interactive_mode(args.http_port, args.tcp_port)
    else:
        print(f"\n  Waiting for Quest to send match requests...")
        print(f"  (Quest connects to {local_ip}:{args.tcp_port} and sends {{\"command\": \"match\"}})")
        try:
            start_tcp_server(args.tcp_port, args.http_port,
                            args.mode, args.threshold, args.verbose)
        except KeyboardInterrupt:
            print("\n  Shutting down.")


if __name__ == "__main__":
    main()