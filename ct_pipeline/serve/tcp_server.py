import os
import json
import socket
import threading

from ct_pipeline.config import (
    RAW_PLY_DIR, UNION_PLY_DIR, RAW_MODEL_DIR, UNION_MODEL_DIR,
    REFERENCE_DIR, CT_TCP_PORT, MERGED_MODEL_DIR
)
from ct_pipeline.ingest.reference import find_reference_ply
from ct_pipeline.pointcloud.alignment import pca_align, normalize_scale
# from ct_pipeline.matching.matcher import load_database, find_best_match
# from ct_pipeline.ingest.ply_loader import load_database
# from ct_pipeline.matching.matcher import find_best_match
from ct_pipeline.matching.run_match import run_matching


def _model_dir_for(send):
    return {"raw": RAW_MODEL_DIR, "union": UNION_MODEL_DIR, "merged": MERGED_MODEL_DIR}[send]

# def run_matching(reference_ply_path, mode="raw", threshold=0.55, verbose=True):
#     """Run the matching pipeline and return the result dict."""
    
#     import open3d as o3d

#     print(f"\n── Loading database [{mode}]...")
#     database = load_database(mode=mode, verbose=verbose)

#     print(f"\n── Loading reference scan: {reference_ply_path}")
#     if not os.path.exists(reference_ply_path):
#         raise FileNotFoundError(f"Reference scan not found: {reference_ply_path}")

#     pcd = o3d.io.read_point_cloud(reference_ply_path)
#     pcd = pca_align(pcd, verbose=verbose)
#     pcd = normalize_scale(pcd, verbose=verbose)

#     print(f"\n── Matching...")
#     result = find_best_match(pcd, database, threshold=threshold, verbose=verbose)

#     print(f"\n── Best match: {result['patient_id']} ({result['confidence']}%)")
#     return result


# def handle_quest_connection(conn, addr, mode, threshold, verbose):
def handle_quest_connection(conn, addr, ref_ply, ref_dir, mode, send, threshold, verbose):
    """Handle a single TCP request from Quest."""
    try:
        data = conn.recv(4096).decode("utf-8").strip()
        print(f"\n  [TCP] Received from {addr}: {data}")

        request = json.loads(data) if data.startswith("{") else {"command": data}
        command = request.get("command", "match")

        if command == "match":
            # reference_ply_path = discover_reference_ply(REFERENCE_DIR, verbose=verbose)
            reference_ply_path = find_reference_ply(ref_ply=ref_ply, ref_dir=ref_dir, verbose=verbose)
            if not os.path.exists(reference_ply_path):
                raise FileNotFoundError(f"Reference scan not found: {reference_ply_path}")

            
            result = run_matching(reference_ply_path, mode=mode, threshold=threshold, verbose=verbose)

            model_dir = _model_dir_for(send)
            glb_path = os.path.join(model_dir, f"{result['patient_id']}.glb")
            if not os.path.exists(glb_path):
                raise FileNotFoundError(f"Model not found: {glb_path}")

            glb_size = os.path.getsize(glb_path)

            header = {
                "status":     "ok",
                "patient_id": result["patient_id"],
                "confidence": result["confidence"],
                "fallback":   result["fallback"],
                "glb_size":   glb_size
            }
            header_bytes = (json.dumps(header) + "\n").encode("utf-8")
            conn.sendall(header_bytes)
            print(f"  [TCP] Sent header: {header}")

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


# def start_tcp_server(port=CT_TCP_PORT, mode="raw", threshold=0.55, verbose=True):
def start_tcp_server(port=CT_TCP_PORT, ref_ply=None, ref_dir=None, mode="raw", send="union", threshold=0.55, verbose=True):
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
            args=(conn, addr, ref_ply, ref_dir, mode, send, threshold, verbose),
            # args=(conn, addr, mode,threshold, verbose),
            daemon=True
        )
        thread.start()


# def interactive_mode(mode="raw", threshold=0.55, ref_dir=None, ref_ply=None):
#     """Manual testing mode — trigger matching from keyboard."""
#     print(f"\n── Interactive mode ─────────────────────────────")
#     print(f"   Press Enter to trigger a match run, or type 'quit' to exit")

#     while True:
#         try:
#             cmd = input("\n  [Enter to match] > ").strip()
#             if cmd.lower() in ("quit", "exit", "q"):
#                 break           

#             reference_ply_path = find_reference_ply_(ref_ply=ref_ply, ref_dir=ref_dir, verbose=True)
#             # reference_ply_path = discover_reference_ply(REFERENCE_DIR, verbose=True)
#             result = run_matching(reference_ply_path, mode=mode, threshold=threshold, verbose=True)
#             print(f"\n  Result: {result['patient_id']} ({result['confidence']}%)")
#         except KeyboardInterrupt:
#             break
#         except Exception as e:
#             print(f"  ERROR: {e}")

#     print("\n  Exiting interactive mode.")
