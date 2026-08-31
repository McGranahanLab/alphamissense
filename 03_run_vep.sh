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

if [[ ! -d "${VEP_INPUT_DIR}" ]]; then
  echo "Input directory missing: ${VEP_INPUT_DIR}" >&2
  exit 1
fi

image_ref="${APPTAINER_IMAGE}"
if [[ -n "${APPTAINER_IMAGE_SIF}" ]]; then
  image_ref="${APPTAINER_IMAGE_SIF}"
fi

for tumour_input_dir in "${VEP_INPUT_DIR}"/${TUMOUR_GLOB}; do
  [[ -d "${tumour_input_dir}" ]] || continue

  tumour_id="$(basename "${tumour_input_dir}")"
  muttable_vcf="${tumour_input_dir}/${tumour_id}_muttable.vcf"
  tumour_output_dir="${VEP_OUTPUT_DIR}/${tumour_id}"
  vep_output="${tumour_output_dir}/${tumour_id}_muttable_annotated.tsv"

  if [[ ! -f "${muttable_vcf}" ]]; then
    echo "Skipping ${tumour_id}: missing VCF ${muttable_vcf}"
    continue
  fi

  mkdir -p "${tumour_output_dir}"

  if [[ "${OVERWRITE_EXISTING}" != "true" && -f "${vep_output}" ]]; then
    echo "Skipping ${tumour_id}: output exists (${vep_output})"
    continue
  fi

  echo "Running VEP for ${tumour_id}"
  "${APPTAINER_BIN}" exec \
    --bind "${WORK_ROOT}:${CONTAINER_WORKDIR}" \
    "${image_ref}" \
    vep \
      -i "${CONTAINER_WORKDIR}/input/vep/${WORK_COHORT_NAME}/${tumour_id}/${tumour_id}_muttable.vcf" \
      -o "${CONTAINER_WORKDIR}/output/vep/${WORK_COHORT_NAME}/${tumour_id}/${tumour_id}_muttable_annotated.tsv" \
      --cache --offline \
      --cache_version "${VEP_CACHE_VERSION}" \
      --dir_cache "${CONTAINER_WORKDIR}/_assets" \
      --assembly "${VEP_ASSEMBLY}" \
      --tab \
      --plugin "AlphaMissense,file=${CONTAINER_WORKDIR}/_assets/AlphaMissense_hg19.tsv.gz" \
      --force_overwrite
done

echo "VEP annotation complete"
