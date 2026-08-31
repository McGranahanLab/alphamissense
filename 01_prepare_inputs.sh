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

mkdir -p "${VEP_INPUT_DIR}" "${VEP_OUTPUT_DIR}"

if [[ ! -d "${SPLIT_INPUT_DIR}" ]]; then
  echo "SPLIT_INPUT_DIR does not exist: ${SPLIT_INPUT_DIR}" >&2
  echo "Run 00_split_mutation_table.sh first" >&2
  exit 1
fi

echo "Preparing VCFs from split muttables: ${SPLIT_INPUT_DIR}"

for muttable_source_path in "${SPLIT_INPUT_DIR}"/${TUMOUR_GLOB}_muttable.tsv*; do
  [[ -f "${muttable_source_path}" ]] || continue

  tumour_id="$(basename "${muttable_source_path}")"
  tumour_id="${tumour_id%%_muttable.tsv*}"

  tumour_input_dir="${VEP_INPUT_DIR}/${tumour_id}"
  tumour_output_dir="${VEP_OUTPUT_DIR}/${tumour_id}"
  mkdir -p "${tumour_input_dir}" "${tumour_output_dir}"

  muttable_dest_path="${tumour_input_dir}/${tumour_id}_muttable.tsv.gz"
  vcf_dest_path="${tumour_input_dir}/${tumour_id}_muttable.vcf"

  if [[ "${OVERWRITE_EXISTING}" == "true" || ! -f "${muttable_dest_path}" ]]; then
    cp "${muttable_source_path}" "${muttable_dest_path}"
  fi

  if [[ "${OVERWRITE_EXISTING}" == "true" || ! -f "${vcf_dest_path}" ]]; then
    "${PYTHON_BIN}" "${MUTTABLE_TO_VCF_SCRIPT}" --input "${muttable_dest_path}" --output "${vcf_dest_path}"
  fi

  echo "Prepared ${tumour_id}"
done

echo "Input preparation complete"
