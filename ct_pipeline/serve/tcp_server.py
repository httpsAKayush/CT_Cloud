"""
Socket layer only. Owns the connection lifecycle and command dispatch —
delegates MATCH to matching.matcher.run_reference_match() and SEND to
serve.model_sender.send_glb(). Doesn't know how matching works or how a
.glb gets built; just wires the two together per request.
"""
import json
import socket
import threading

from ct_pipeline.config import CT_TCP_PORT
from ct_pipeline.matching.matcher import run_reference_match
from ct_pipeline.serve.model_sender import send_glb


def handle_match_command(conn, ref_ply, ref_dir, mode, send, threshold,
                          apply_scale, scale_factor, verbose):
    """command == 'match': run a fresh match, then send the matched patient's model."""
    result = run_reference_match(ref_ply=ref_ply, ref_dir=ref_dir,
                                  mode=mode, threshold=threshold, verbose=verbose)
    send_glb(
        conn, result["patient_id"], send=send,
        extra_header_fields={"confidence": result["confidence"], "fallback": result["fallback"]},
        apply_scale=apply_scale, scale_factor=scale_factor,
        verbose=verbose,
    )


def handle_send_command(conn, request, send, apply_scale, scale_factor, verbose):
    """command == 'send': skip matching entirely, send a specific patient_id directly."""
    patient_id = request.get("patient_id")
    if not patient_id:
        raise ValueError("'send' command requires a 'patient_id' field")
    send_glb(conn, patient_id, send=send,
             apply_scale=apply_scale, scale_factor=scale_factor, verbose=verbose)


def handle_quest_connection(conn, addr, ref_ply, ref_dir, mode, send, threshold,
                             apply_scale, scale_factor, verbose):
    """Handle a single TCP request from Quest."""
    try:
        data = conn.recv(4096).decode("utf-8").strip()
        print(f"\n  [TCP] Received from {addr}: {data}")

        request = json.loads(data) if data.startswith("{") else {"command": data}
        command = request.get("command", "match")

        if command == "match":
            handle_match_command(conn, ref_ply, ref_dir, mode, send, threshold,
                                  apply_scale, scale_factor, verbose)
        elif command == "send":
            handle_send_command(conn, request, send, apply_scale, scale_factor, verbose)
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


def start_tcp_server(port=CT_TCP_PORT, ref_ply=None, ref_dir=None, mode="raw", send="union",
                      threshold=0.55, apply_scale=False, scale_factor=None, verbose=True):
    """
    TCP server that listens for requests from Quest.
    'match' requests trigger a fresh match + send; 'send' requests (with an
    explicit patient_id) skip matching and send directly — useful for manual
    testing/overrides.

    apply_scale/scale_factor: applied to every .glb this server sends, for
    the lifetime of this server run — set this when the models in `send`'s
    folder weren't produced by this pipeline's own scaled export path. See
    serve/model_sender.py for how the scaling itself is done.
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("0.0.0.0", port))
    server_socket.listen(5)
    print(f"  [TCP] Listening for requests on port {port}")
    if apply_scale:
        print(f"  [TCP] Send-time scaling ENABLED (factor={scale_factor if scale_factor is not None else 'config default'})")

    while True:
        conn, addr = server_socket.accept()
        thread = threading.Thread(
            target=handle_quest_connection,
            args=(conn, addr, ref_ply, ref_dir, mode, send, threshold,
                  apply_scale, scale_factor, verbose),
            daemon=True
        )
        thread.start()