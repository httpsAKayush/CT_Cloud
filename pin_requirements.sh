#!/bin/bash
# Usage: bash pin_requirements.sh requirements.in requirements.txt

IN=${1:-requirements.in}
OUT=${2:-requirements.txt}

if [ ! -f "$IN" ]; then
  echo "Error: $IN not found"
  exit 1
fi

> "$OUT"

while IFS= read -r line || [ -n "$line" ]; do
  # skip empty lines and comments
  [[ -z "$line" || "$line" == \#* ]] && continue

  # strip extras/version specifiers to get bare package name
  pkg=$(echo "$line" | sed 's/[>=<!].*//' | sed 's/\[.*//' | xargs)

  # grep pip freeze for this package (case-insensitive, treat - and _ as same)
  match=$(pip freeze 2>/dev/null | grep -iE "^${pkg}==|^$(echo $pkg | tr '-' '_')==|^$(echo $pkg | tr '_' '-')==" | head -1)

  if [ -n "$match" ]; then
    echo "$match" >> "$OUT"
  else
    echo "WARNING: $pkg not found in environment, skipping"
  fi
done < "$IN"

echo "Done → $OUT"