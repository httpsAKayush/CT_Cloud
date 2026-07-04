

"""
Orchestration only — chains serve.tcp_server + serve.discovery_broadcast +
matching.matcher.match_reference_file.

No interactive/keyboard mode here anymore — that behavior (match a real
reference file, print the result, don't send anything) is now
`ct-pipeline test-match --real-ply <path>`, since it was doing the exact same
thing as test-match's fake-scan path minus the send step. Fewer code paths
to keep in sync.
"""
from ct_pipeline.config import UNION_MODEL_DIR, RAW_MODEL_DIR, MERGED_MODEL_DIR, CT_TCP_PORT
from ct_pipeline.serve import tcp_server, discovery_broadcast


def _model_dir_for(send):
    return {"raw": RAW_MODEL_DIR, "union": UNION_MODEL_DIR, "merged": MERGED_MODEL_DIR}[send]


def run(mode="raw", send="union", threshold=0.55, tcp_port=CT_TCP_PORT,
        ref_ply=None, ref_dir=None, verbose=True):
    model_dir = _model_dir_for(send)

    print(f"\n{'='*50}")
    print(f"CT Pipeline Server")
    print(f"{'='*50}")

    local_ip = discovery_broadcast.get_local_ip()
    discovery_broadcast.start_udp_broadcaster(tcp_port)

    print(f"  Local IP   : {local_ip}")
    print(f"  TCP port   : {tcp_port}")
    print(f"  Models dir : {model_dir}")
    print(f"  Match mode : {mode}")
    print(f"  Send mode  : {send}")
    print(f"\n  Waiting for Quest to send match requests...")
    print(f"  (Quest connects to {local_ip}:{tcp_port} and sends {{\"command\": \"match\"}})")
    try:
        tcp_server.start_tcp_server(port=tcp_port, ref_ply=ref_ply, ref_dir=ref_dir,
                                     mode=mode, send=send, threshold=threshold, verbose=verbose)
    except KeyboardInterrupt:
        print("\n  Shutting down.")