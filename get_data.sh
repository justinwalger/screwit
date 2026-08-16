#!/usr/bin/env bash
# Script to download MVTec AD data to ./data for categories specified as parameters.
# Defaults to: screw
#
# Usage: ./get_data.sh [category ...]
#   e.g. ./get_data.sh bottle cable

set -euo pipefail

VALID_CATEGORIES=(bottle cable capsule carpet grid hazelnut leather metal_nut pill screw tile toothbrush transistor wood zipper)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${SCRIPT_DIR}/data"
CACHE_DIR="${SCRIPT_DIR}/.cache"
ARCHIVE="${CACHE_DIR}/mvtec_anomaly_detection.tar.xz"
URL="https://www.mydrive.ch/shares/150996/b52ecdcbf521176e9db9c731f2304b27/download/420938113-1629960298/mvtec_anomaly_detection.tar.xz"

categories=("$@")
if [ ${#categories[@]} -eq 0 ]; then
    categories=(screw)
fi

for category in "${categories[@]}"; do
    if [[ ! " ${VALID_CATEGORIES[*]} " == *" ${category} "* ]]; then
        echo "Unknown category '${category}'. Valid categories: ${VALID_CATEGORIES[*]}" >&2
        exit 1
    fi
done

mkdir -p "$DATA_DIR" "$CACHE_DIR"

missing=()
for category in "${categories[@]}"; do
    if [ ! -d "${DATA_DIR}/${category}" ]; then
        missing+=("$category")
    fi
done

if [ ${#missing[@]} -eq 0 ]; then
    echo "All requested categories already present in ${DATA_DIR}: ${categories[*]}"
    exit 0
fi

echo "Missing categories: ${missing[*]}"

echo "Downloading MVTec AD archive (~4.9 GB) to ${ARCHIVE}..."
curl -L --fail --retry 5 --retry-delay 5 --retry-connrefused -C - -o "$ARCHIVE" "$URL"

echo "Verifying archive integrity..."
if ! tar -tf "$ARCHIVE" > /dev/null; then
    echo "Archive ${ARCHIVE} is not a valid tar.xz file (corrupted or incomplete download)." >&2
    rm -f "$ARCHIVE"
    exit 1
fi

echo "Extracting: ${missing[*]}"
tar -xf "$ARCHIVE" -C "$DATA_DIR" "${missing[@]}"

echo "Done. Data available at:"
for category in "${categories[@]}"; do
    echo "  ${DATA_DIR}/${category}"
done
