"""
Cross-platform replacement for pin_requirements.sh (works on Windows, Linux, macOS
without needing a bash shell / WSL / Git Bash).

Usage:
    python pin_requirements.py requirements_compile.in requirements.txt
"""
import re
import subprocess
import sys


def pip_freeze():
    out = subprocess.run(
        [sys.executable, "-m", "pip", "freeze"],
        capture_output=True, text=True, check=True,
    ).stdout
    return out.splitlines()


def bare_name(line):
    # strip extras/version specifiers, e.g. "open3d[extra]>=0.19" -> "open3d"
    name = re.split(r"[><=!\[]", line, maxsplit=1)[0].strip()
    return name


def main():
    in_path = sys.argv[1] if len(sys.argv) > 1 else "requirements.in"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "requirements.txt"

    try:
        with open(in_path, "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: {in_path} not found")
        sys.exit(1)

    frozen = pip_freeze()
    # index frozen packages by lowercase, hyphen/underscore-normalized name
    freeze_index = {}
    for fline in frozen:
        if "==" not in fline:
            continue
        fname = fline.split("==", 1)[0]
        key = fname.lower().replace("_", "-")
        freeze_index[key] = fline

    resolved = []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        pkg = bare_name(line)
        key = pkg.lower().replace("_", "-")
        match = freeze_index.get(key)
        if match:
            resolved.append(match)
        else:
            print(f"WARNING: {pkg} not found in environment, skipping")

    with open(out_path, "w") as f:
        f.write("\n".join(resolved) + ("\n" if resolved else ""))

    print(f"Done -> {out_path}")


if __name__ == "__main__":
    main()