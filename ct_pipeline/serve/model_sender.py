"""
The SEND step, decoupled from matching: given a patient_id and which model
folder to pull from, transmit the .glb over an already-open connection.

Has zero knowledge of matching, reference scans, or how patient_id was chosen —
that's matching/matcher.py's job (run_reference_match). This module can be
called with any patient_id from anywhere: a real match result, a manual
override for testing, or a future "send this specific patient" command.
"""
import os
import json

from ct_pipeline.config import RAW_MODEL_DIR, UNION_MODEL_DIR, MERGED_MODEL_DIR


def model_dir_for(send):
    return {"raw": RAW_MODEL_DIR, "union": UNION_MODEL_DIR, "merged": MERGED_MODEL_DIR}[send]


def send_glb(conn, patient_id, send="union", extra_header_fields=None, verbose=True):
    """
    Send the header (JSON + newline) then the raw .glb bytes for patient_id
    over conn. extra_header_fields lets callers merge in match-specific info
    (confidence, fallback, etc.) without this module needing to know what
    matching produced.
    """
    model_dir = model_dir_for(send)
    glb_path = os.path.join(model_dir, f"{patient_id}.glb")
    if not os.path.exists(glb_path):
        raise FileNotFoundError(f"Model not found: {glb_path}")

    glb_size = os.path.getsize(glb_path)

    header = {"status": "ok", "patient_id": patient_id, "glb_size": glb_size}
    if extra_header_fields:
        header.update(extra_header_fields)

    header_bytes = (json.dumps(header) + "\n").encode("utf-8")
    conn.sendall(header_bytes)
    if verbose:
        print(f"  [TCP] Sent header: {header}")

    with open(glb_path, "rb") as f:
        glb_data = f.read()
    conn.sendall(glb_data)
    if verbose:
        print(f"  [TCP] Sent GLB: {glb_size} bytes")

    return glb_path