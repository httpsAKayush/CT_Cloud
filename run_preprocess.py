import os
import sys
import argparse

# Make sure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import PATIENTS, PLY_DIR, MODEL_DIR
from preprocess.pipeline import process_all, process_patient

def main():
    parser = argparse.ArgumentParser(description="CT Pipeline Preprocessor")
    parser.add_argument("--patients", nargs="+", default=PATIENTS,
                        help="Patient IDs to process (default: all)")
    parser.add_argument("--overwrite", action="store_true",
                        help="Reprocess even if output already exists")
    parser.add_argument("--verbose", action="store_true", default=True)
    args = parser.parse_args()

    os.makedirs(PLY_DIR, exist_ok=True)
    os.makedirs(MODEL_DIR, exist_ok=True)

    print(f"Processing {len(args.patients)} patients: {args.patients}")
    results = process_all(args.patients, overwrite=args.overwrite, verbose=args.verbose)

    print(f"\n{'='*50}")
    print("Summary:")
    for pid, path in results.items():
        status = "✓" if path else "✗"
        print(f"  {status} {pid}: {path or 'FAILED'}")

if __name__ == "__main__":
    main()