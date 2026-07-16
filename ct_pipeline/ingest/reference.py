"""
Reference .ply auto-discovery.

Rule (confirmed):
  0 files  -> error
  1 file   -> use it
  >1 files -> look for a file literally named REFERENCE_PREFERRED_NAME;
              if not present, fall back to most-recently-modified .ply.
  Always print what was picked and what else was found, so it's never silent.
"""
import os
from ct_pipeline.config import REFERENCE_PREFERRED_NAME, REFERENCE_DIR


def discover_reference_ply(reference_dir, explicit_path=None, preferred_name=None, verbose=True):
    """
    Resolve the reference .ply to match against.
    explicit_path always wins and skips discovery entirely.
    """
    if explicit_path:
        if not os.path.exists(explicit_path):
            raise FileNotFoundError(f"--ref-ply given but not found: {explicit_path}")
        if verbose:
            print(f"  [reference] Using explicit path: {explicit_path}")
        return explicit_path

    if not os.path.exists(reference_dir):
        raise FileNotFoundError(f"Reference directory not found: {reference_dir}")

    candidates = sorted([
        os.path.join(reference_dir, f)
        for f in os.listdir(reference_dir)
        if f.endswith(".ply")
    ])

    if not candidates:
        raise FileNotFoundError(f"No .ply files found in {reference_dir}")

    if len(candidates) == 1:
        chosen = candidates[0]
        if verbose:
            print(f"  [reference] Single candidate found: {chosen}")
        return chosen

    # Multiple candidates
    preferred_name = preferred_name if preferred_name else REFERENCE_PREFERRED_NAME
    preferred = os.path.join(reference_dir, preferred_name)
    if preferred in candidates:
        chosen = preferred
        rule = f"found preferred name '{preferred_name}'"
    else:
        chosen = max(candidates, key=os.path.getmtime)
        rule = "no preferred-name match, fell back to most-recently-modified"

    if verbose:
        print(f"  [reference] Multiple candidates in {reference_dir}:")
        for c in candidates:
            marker = " ◄ chosen" if c == chosen else ""
            print(f"    - {os.path.basename(c)}{marker}")
        print(f"  [reference] Rule applied: {rule}")

    return chosen


def find_reference_ply(ref_ply=None, ref_dir=None, verbose=True):
    """
    Return the path to the reference .ply file to use.
    If explicit_path is given, it is used directly.
    Otherwise, discover_reference_ply() is called to find the best candidate.
    """
    reference_dir = ref_dir if ref_dir else REFERENCE_DIR
    # if ref_ply looks like an existing path, treat as explicit override;
    # otherwise treat as a preferred filename to search for
    if ref_ply and os.path.exists(ref_ply):
        return discover_reference_ply(reference_dir, explicit_path=ref_ply, verbose=verbose)
    return discover_reference_ply(reference_dir, preferred_name=ref_ply, verbose=verbose)