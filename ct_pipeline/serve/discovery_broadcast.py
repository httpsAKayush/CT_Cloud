import json
import socket
import threading

from ct_pipeline.config import MULTICAST_GROUP, CT_BROADCAST_PORT


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


def start_udp_broadcaster(tcp_port, interval=2.0, broadcast_port=CT_BROADCAST_PORT):
    """Multicast-broadcast this server's presence so the Quest can auto-discover it."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)

    local_ip = get_local_ip()
    message = json.dumps({
        "service": "ct_pipeline_server",
        "ip": local_ip,
        "tcp_port": tcp_port
    }).encode("utf-8")

    def broadcast_loop():
        while True:
            try:
                sock.sendto(message, (MULTICAST_GROUP, broadcast_port))
            except Exception as e:
                print(f"  [UDP] Multicast error: {e}")
            threading.Event().wait(interval)

    thread = threading.Thread(target=broadcast_loop, daemon=True)
    thread.start()
    print(f"  [Multicast] Broadcasting 'ct_pipeline_server' → {MULTICAST_GROUP}:{broadcast_port}")
    return thread
