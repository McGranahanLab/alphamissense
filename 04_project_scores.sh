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

if [[ ! -d "${VEP_OUTPUT_DIR}" ]]; then
  echo "VEP output directory missing: ${VEP_OUTPUT_DIR}" >&2
  exit 1
fi

mkdir -p "${ANNOTATED_OUTPUT_DIR}"

for tumour_vep_out_dir in "${VEP_OUTPUT_DIR}"/${TUMOUR_GLOB}; do
  [[ -d "${tumour_vep_out_dir}" ]] || continue

  tumour_id="$(basename "${tumour_vep_out_dir}")"
  muttable="${VEP_INPUT_DIR}/${tumour_id}/${tumour_id}_muttable.tsv.gz"
  muttable_with_alphascores="${VEP_OUTPUT_DIR}/${tumour_id}/${tumour_id}_muttable_annotated.tsv"
  output_file="${ANNOTATED_OUTPUT_DIR}/${tumour_id}_muttable_alpha.csv"

  if [[ ! -f "${muttable}" ]]; then
    echo "Skipping ${tumour_id}: missing muttable ${muttable}"
    continue
  fi
  if [[ ! -f "${muttable_with_alphascores}" ]]; then
    echo "Skipping ${tumour_id}: missing VEP output ${muttable_with_alphascores}"
    continue
  fi

  if [[ "${OVERWRITE_EXISTING}" != "true" && -f "${output_file}" ]]; then
    echo "Skipping ${tumour_id}: output exists (${output_file})"
    continue
  fi

  echo "Projecting AlphaMissense scores for ${tumour_id}"
  "${PYTHON_BIN}" "${ANNOTATE_ALPHA_SCRIPT}" \
    --muttable "${muttable}" \
    --vcf "${muttable_with_alphascores}" \
    --output "${output_file}"
done

echo "AlphaMissense projection complete"
