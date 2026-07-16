"""
The SEND step, decoupled from matching: given a patient_id and which model
folder to pull from, transmit the .glb over an already-open connection.

Has zero knowledge of matching, reference scans, or how patient_id was chosen —
that's matching/matcher.py's job (run_reference_match). This module can be
called with any patient_id from anywhere: a real match result, a manual
override for testing, or a future "send this specific patient" command.

Optional send-time scaling: if a .glb was produced outside this pipeline
(or by an older export path) and never had MODEL_SCALE_FACTOR baked in,
pass apply_scale=True to scale it in memory before sending — the file on
disk is never modified. This is deliberately a *send-time* concern, not
baked into model export, since whether a given .glb needs it depends on
how it was built, not on this module.
"""
import io
import os
import json

from ct_pipeline.config import RAW_MODEL_DIR, UNION_MODEL_DIR, MERGED_MODEL_DIR, MODEL_SCALE_FACTOR


def model_dir_for(send):
    return {"raw": RAW_MODEL_DIR, "union": UNION_MODEL_DIR, "merged": MERGED_MODEL_DIR}[send]


def _scaled_glb_bytes(glb_path, scale_factor, verbose=True):
    """
    Load glb_path, multiply every mesh's vertices by scale_factor, re-export
    to an in-memory .glb. Never writes back to glb_path.
    """
    import trimesh  # lazy import — keep this module's baseline import cheap for pure network use

    loaded = trimesh.load(glb_path)

    if isinstance(loaded, trimesh.Scene):
        for geom in loaded.geometry.values():
            geom.vertices = geom.vertices * scale_factor
    else:
        loaded.vertices = loaded.vertices * scale_factor

    buf = io.BytesIO()
    loaded.export(file_obj=buf, file_type="glb")
    data = buf.getvalue()

    if verbose:
        print(f"  [scale] Applied scale factor {scale_factor} to {os.path.basename(glb_path)} "
              f"before sending (in-memory only, file on disk unchanged)")
    return data


def send_glb(conn, patient_id, send="union", extra_header_fields=None,
             apply_scale=False, scale_factor=None, verbose=True):
    """
    Send the header (JSON + newline) then the .glb bytes for patient_id
    over conn. extra_header_fields lets callers merge in match-specific info
    (confidence, fallback, etc.) without this module needing to know what
    matching produced.

    apply_scale: if True, scale the .glb in memory before sending (see
    _scaled_glb_bytes). scale_factor defaults to config.MODEL_SCALE_FACTOR
    when not given.
    """
    model_dir = model_dir_for(send)
    glb_path = os.path.join(model_dir, f"{patient_id}.glb")
    if not os.path.exists(glb_path):
        raise FileNotFoundError(f"Model not found: {glb_path}")

    if apply_scale:
        factor = scale_factor if scale_factor is not None else MODEL_SCALE_FACTOR
        glb_data = _scaled_glb_bytes(glb_path, factor, verbose=verbose)
    else:
        factor = None
        with open(glb_path, "rb") as f:
            glb_data = f.read()

    glb_size = len(glb_data)

    header = {
        "status": "ok",
        "patient_id": patient_id,
        "glb_size": glb_size,
        "scaled": bool(apply_scale),
    }
    if apply_scale:
        header["scale_factor"] = factor
    if extra_header_fields:
        header.update(extra_header_fields)

    header_bytes = (json.dumps(header) + "\n").encode("utf-8")
    conn.sendall(header_bytes)
    if verbose:
        print(f"  [TCP] Sent header: {header}")

    conn.sendall(glb_data)
    if verbose:
        print(f"  [TCP] Sent GLB: {glb_size} bytes")

    return glb_path