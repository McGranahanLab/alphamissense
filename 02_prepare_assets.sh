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

if [[ "${LOAD_CONTAINER_MODULE:-false}" == "true" ]] && ! command -v "${APPTAINER_BIN}" >/dev/null 2>&1; then
  if command -v ml >/dev/null 2>&1; then
    ml "${CONTAINER_MODULE}"
  else
    if ! command -v module >/dev/null 2>&1 && [[ -f /etc/profile.d/modules.sh ]]; then
      # shellcheck source=/dev/null
      source /etc/profile.d/modules.sh
    fi
    if command -v module >/dev/null 2>&1; then
      module load "${CONTAINER_MODULE}"
    fi
  fi
fi

if ! command -v "${APPTAINER_BIN}" >/dev/null 2>&1; then
  echo "Container runtime not found: ${APPTAINER_BIN}" >&2
  echo "Tried module load: ${CONTAINER_MODULE}" >&2
  exit 1
fi

mkdir -p "${WORK_ASSETS_DIR}"

image_ref="${APPTAINER_IMAGE}"
if [[ -n "${APPTAINER_IMAGE_SIF}" ]]; then
  image_ref="${APPTAINER_IMAGE_SIF}"
elif [[ "${APPTAINER_IMAGE}" == docker://* ]]; then
  echo "Using docker URI directly: ${APPTAINER_IMAGE}"
fi

if [[ -n "${APPTAINER_IMAGE_SIF}" ]]; then
  image_dir="$(dirname "${APPTAINER_IMAGE_SIF}")"
  mkdir -p "${image_dir}"
  if [[ ! -f "${APPTAINER_IMAGE_SIF}" ]]; then
    echo "Pulling SIF image to ${APPTAINER_IMAGE_SIF}"
    "${APPTAINER_BIN}" pull "${APPTAINER_IMAGE_SIF}" "${APPTAINER_IMAGE}"
  fi
fi

if [[ ! -f "${ALPHAMISSENSE_FILE}" ]]; then
  echo "Downloading AlphaMissense asset"
  wget -O "${ALPHAMISSENSE_FILE}" "${ALPHAMISSENSE_URL}"
fi

if [[ ! -f "${ALPHAMISSENSE_FILE}.tbi" ]]; then
  echo "Indexing AlphaMissense asset with tabix"
  tabix -s 1 -b 2 -e 2 -S 1 -f "${ALPHAMISSENSE_FILE}"
fi

cache_dir_a="${WORK_ASSETS_DIR}/${VEP_SPECIES}/${VEP_CACHE_VERSION}_${VEP_ASSEMBLY}"
cache_dir_b="${WORK_ASSETS_DIR}/${VEP_SPECIES}_vep_${VEP_CACHE_VERSION}_${VEP_ASSEMBLY}"

if [[ ! -d "${cache_dir_a}" && ! -d "${cache_dir_b}" ]]; then
  echo "Downloading VEP cache into ${WORK_ASSETS_DIR}"
  "${APPTAINER_BIN}" exec \
    --env "HOME=${CONTAINER_WORKDIR}" \
    --bind "${WORK_ROOT}:${CONTAINER_WORKDIR}" \
    "${image_ref}" \
    perl /opt/vep/src/ensembl-vep/INSTALL.pl \
      -a c \
      -s "${VEP_SPECIES}" \
      -y "${VEP_ASSEMBLY}" \
      -c "${CONTAINER_WORKDIR}/_assets" \
      -d "${CONTAINER_WORKDIR}/_assets" \
      --CACHE_VERSION "${VEP_CACHE_VERSION}"
else
  echo "Found VEP cache for ${VEP_SPECIES} ${VEP_CACHE_VERSION} ${VEP_ASSEMBLY}"
fi

echo "Asset preparation complete"
