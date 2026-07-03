"""Orchestration only — chains serve.tcp_server + serve.discovery_broadcast."""
from ct_pipeline.config import UNION_MODEL_DIR, RAW_MODEL_DIR, CT_TCP_PORT
from ct_pipeline.serve import tcp_server, discovery_broadcast
from ct_pipeline.ingest.reference import find_reference_ply
from ct_pipeline.matching.run_match import run_matching

def interactive_mode(mode="raw", threshold=0.55, ref_dir=None, ref_ply=None):
    """Manual testing mode — trigger matching from keyboard."""
    print(f"\n── Interactive mode ─────────────────────────────")
    print(f"   Press Enter to trigger a match run, or type 'quit' to exit")

    while True:
        try:
            cmd = input("\n  [Enter to match] > ").strip()
            if cmd.lower() in ("quit", "exit", "q"):
                break           

            reference_ply_path = find_reference_ply(ref_ply=ref_ply, ref_dir=ref_dir, verbose=True)
            # reference_ply_path = discover_reference_ply(REFERENCE_DIR, verbose=True)
            result = run_matching(reference_ply_path, mode=mode, threshold=threshold, verbose=True)
            print(f"\n  Result: {result['patient_id']} ({result['confidence']}%)")
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"  ERROR: {e}")

    print("\n  Exiting interactive mode.")

# def run(mode="raw", threshold=0.55, tcp_port=CT_TCP_PORT, interactive=False, verbose=True):
def run(mode="raw", send="union", threshold=0.55, tcp_port=CT_TCP_PORT, interactive=False, ref_ply=None, ref_dir=None, verbose=True):
    # model_dir = RAW_MODEL_DIR if mode == "raw" else UNION_MODEL_DIR
    model_dir = UNION_MODEL_DIR if send == "union" else RAW_MODEL_DIR

    print(f"\n{'='*50}")
    print(f"CT Pipeline Server")
    print(f"{'='*50}")

    local_ip = discovery_broadcast.get_local_ip()
    discovery_broadcast.start_udp_broadcaster(tcp_port)

    print(f"  Local IP   : {local_ip}")
    print(f"  TCP port   : {tcp_port}")
    print(f"  Models dir : {model_dir}")
    # print(f"  Match mode : {mode}")
    print(f"  Match mode : {mode}")

    if interactive:
        # tcp_server.interactive_mode(mode=mode, threshold=threshold)
        interactive_mode(mode=mode, threshold=threshold, ref_dir=ref_dir, ref_ply=ref_ply)

    else:
        print(f"\n  Waiting for Quest to send match requests...")
        print(f"  (Quest connects to {local_ip}:{tcp_port} and sends {{\"command\": \"match\"}})")
        try:
            # tcp_server.start_tcp_server(port=tcp_port, mode=mode, threshold=threshold, verbose=verbose)
            tcp_server.start_tcp_server(port=tcp_port, ref_ply=ref_ply, ref_dir=ref_dir, mode=mode, send=send, threshold=threshold, verbose=verbose)
        except KeyboardInterrupt:
            print("\n  Shutting down.")
