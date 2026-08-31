# AlphaMissense on HPC with Apptainer (Singularity)

This directory ports the Docker-based AlphaMissense workflow to HPC environments
that provide Apptainer/Singularity.

Apptainer can run Docker images directly (via `docker://...`) or from a local
`.sif` image, so the `ensemblorg/ensembl-vep` workflow is portable.

## What this workflow does

1. Splits one large mutation table into one per-tumour muttable by `tumour_id`.
2. Converts each per-tumour muttable to VCF using `src/muttable_to_vcf.py`.
3. Downloads AlphaMissense assets and VEP cache into this workflow workspace.
4. Runs VEP + AlphaMissense plugin through Apptainer for each tumour.
5. Projects AlphaMissense values back onto muttables using
   `src/annotate_alpha_missense.py`.

All paths are configured in one file: `config.env`.

This folder is self-contained and can be copied to HPC without the parent
`plausibility_index` repository.

## Files

- `config.env`: Single source of truth for all paths and runtime settings.
- `input/`: Local input workspace (split muttables and VCF-ready folders).
- `output/`: Local outputs (VEP tables and final annotated muttables).
- `src/`: Local helper scripts used by this workflow.
- `00_split_mutation_table.sh`: Split one large mutation table by `tumour_id`.
- `01_prepare_inputs.sh`: Build VEP input folders and create VCFs.
- `02_prepare_assets.sh`: Pull image (optional), download AlphaMissense, build tabix index, download VEP cache.
- `03_run_vep.sh`: Run VEP in Apptainer over all input VCFs.
- `04_project_scores.sh`: Merge AlphaMissense scores back into cohort muttables.
- `run_all.sh`: Convenience wrapper to run all steps in order.

## Quick start

1. Edit `config.env`.
2. Ensure your Python environment has repository requirements installed.
3. Run:

```bash
cd hpc_apptainer_alphamissense
bash run_all.sh
```

Or run each step separately:

```bash
bash 00_split_mutation_table.sh
bash 01_prepare_inputs.sh
bash 02_prepare_assets.sh
bash 03_run_vep.sh
bash 04_project_scores.sh
```

## Notes for HPC

- If compute nodes do not have internet, run `02_prepare_assets.sh` on a login
  node first, then execute step 3 on compute.
- If your HPC already has a prepared `.sif`, set `APPTAINER_IMAGE` accordingly.
- If your cluster uses `singularity` instead of `apptainer`, set
  `APPTAINER_BIN=singularity` in `config.env`.
