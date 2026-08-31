#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

bash "${SCRIPT_DIR}/00_split_mutation_table.sh"
bash "${SCRIPT_DIR}/01_prepare_inputs.sh"
bash "${SCRIPT_DIR}/02_prepare_assets.sh"
bash "${SCRIPT_DIR}/03_run_vep.sh"
bash "${SCRIPT_DIR}/04_project_scores.sh"
