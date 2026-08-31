#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/config.env"

if [[ ! -f "${CONFIG_FILE}" ]]; then
  echo "Missing config file: ${CONFIG_FILE}" >&2
  exit 1
fi

# shellcheck source=/dev/null
source "${CONFIG_FILE}"

if [[ ! -f "${MUTTABLE_TABLE}" ]]; then
  echo "MUTTABLE_TABLE does not exist: ${MUTTABLE_TABLE}" >&2
  exit 1
fi

mkdir -p "${SPLIT_INPUT_DIR}"

echo "Splitting mutation table by tumour_id"
"${PYTHON_BIN}" "${SPLIT_MUTTABLE_SCRIPT}" \
  --input "${MUTTABLE_TABLE}" \
  --output-dir "${SPLIT_INPUT_DIR}" \
  --tumour-column patient_tumour \
  --filename-template "{tumour_id}_muttable.tsv" \
  --gzip-output "${SPLIT_COMPRESS_GZIP}"

echo "Split complete"
