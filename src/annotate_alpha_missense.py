"""Annotate muttable rows with AlphaMissense pathogenicity scores."""

from __future__ import annotations

import argparse
import csv
import gzip
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pandas as pd 
import numpy as np

DEFAULT_ALPHA_VALUE = np.nan
# this value will be assigned to all variantes not found in the AlphaMissense output
# for example non exonic variants



def _open_text_file(path: Path):
    """Return a text handle that supports plain and gzipped inputs."""

    if str(path).endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="ignore")
    return path.open("r", encoding="utf-8", errors="ignore")


def detect_delimiter(path: Path) -> str:
    """Detect whether the file is tab- or comma-delimited (default comma)."""

    with _open_text_file(path) as handle:
        sample = handle.readline()

    if sample.count("\t") >= sample.count(",") and sample.count("\t") > 0:
        return "\t"
    return ","


def normalize_header(field: str) -> str:
    return field.lstrip("#").strip()


def mutation_key_candidates(identifier: str) -> Tuple[str, ...]:
    ident = identifier.strip()
    if not ident:
        return tuple()

    keys = [ident]
    if ":" in ident:
        prefix = ident.split(":", 1)[0].strip()
        if prefix and prefix != ident:
            keys.append(prefix)

    # Preserve order but drop duplicates
    seen = set()
    ordered: List[str] = []
    for key in keys:
        if key not in seen:
            ordered.append(key)
            seen.add(key)
    return tuple(ordered)


def load_alpha_scores(vcf_path: Path) -> Dict[str, Optional[str]]:
    """Read AlphaMissense VEP output, returning a map of variant ID to score."""
    mapping: Dict[str, Optional[str]] = {}
    
    df = pd.read_csv(vcf_path, sep='\t', comment='#', dtype=str)
    header: Optional[List[str]] = ['Uploaded_variation','Location','Allele','Gene','Feature','Feature_type','Consequence','cDNA_position','CDS_position','Protein_position','Amino_acids','Codons','Existing_variation','IMPACT','DISTANCE','STRAND','FLAGS','am_class','am_pathogenicity']
    df.columns = header
    # drop rows without am_pathogenicity
    df = df[df['am_pathogenicity'] != '-']
    df_am_max = df.groupby('Location')['am_pathogenicity'].max().reset_index()
    
    mapping = dict(zip(df_am_max['Location'], df_am_max['am_pathogenicity']))
    return mapping


def annotate_muttable_with_alpha(
    muttable_path: Path,
    vcf_path: Path,
    output_path: Path,
    default_value: str = DEFAULT_ALPHA_VALUE,
) -> Tuple[int, int, int]:
    """Annotate ``muttable_path`` rows and write them (with a new column) to ``output_path``.

    Returns a tuple ``(total_rows, matched_with_scores, defaulted_rows)``.
    """

    alpha_scores = load_alpha_scores(vcf_path)
    delimiter = detect_delimiter(muttable_path)

    total_rows = 0
    matched_with_scores = 0
    defaulted_rows = 0

    with _open_text_file(muttable_path) as infile, output_path.open(
        "w", encoding="utf-8", newline=""
    ) as outfile:
        reader = csv.DictReader(infile, delimiter=delimiter)
        if reader.fieldnames is None:
            raise ValueError("Muttable file is missing a header row")

        fieldnames = list(reader.fieldnames)
        if "alpha_missense" not in fieldnames:
            fieldnames.append("alpha_missense")
        if "am_class" not in fieldnames:
            fieldnames.append("am_class")

        writer = csv.DictWriter(outfile, fieldnames=fieldnames, delimiter=delimiter, lineterminator="\n")
        writer.writeheader()

        for row in reader:
            if not row:
                continue
            total_rows += 1
            mutation_id = (row.get("mutation_id") or "").strip()
            if not mutation_id:
                logging.warning("Row %s missing mutation_id; defaulting value", total_rows)
                row["alpha_missense"] = default_value
                defaulted_rows += 1
                writer.writerow(row)
                continue

            score: Optional[str] = None
            matched = False
            for key in mutation_key_candidates(mutation_id):
                try:
                    location = key.split(':')[1] + ':' + key.split(':')[2]  # extract chrom:pos
                except IndexError:
                    continue
                if location in alpha_scores:
                    matched = True
                    score = alpha_scores[location]
                    if score is not None:
                        break

            if matched and score is not None:
                row["alpha_missense"] = score
                matched_with_scores += 1
            else:
                row["alpha_missense"] = default_value
                defaulted_rows += 1
            # annotate with am_class
            row["am_class"] = 'Likely benign' if float(row["alpha_missense"]) < 0.34 else ('Likely pathogenic' if float(row["alpha_missense"]) > 0.564 else 'ambiguous')
            # if am value is nan, overwrite am_class to 'not_classified'
            if pd.isna(float(row["alpha_missense"])):
                row["am_class"] = 'not_classified'
            writer.writerow(row)

    return total_rows, matched_with_scores, defaulted_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Annotate a muttable TSV/CSV with AlphaMissense pathogenicity scores derived from "
            "a tab-delimited VEP output file."
        )
    )
    parser.add_argument("--muttable", required=True, type=Path, help="Path to the muttable TSV/CSV file")
    parser.add_argument("--vcf", required=True, type=Path, help="Path to the AlphaMissense VCF/TSV file")
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Destination file for the annotated muttable (will be overwritten if it exists)",
    )
    parser.add_argument(
        "--default-value",
        default=DEFAULT_ALPHA_VALUE,
        help="Value to use when AlphaMissense does not provide a pathogenicity score",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase logging verbosity (can be specified multiple times)",
    )
    return parser.parse_args()


def configure_logging(verbosity: int) -> None:
    level = logging.WARNING
    if verbosity == 1:
        level = logging.INFO
    elif verbosity >= 2:
        level = logging.DEBUG

    logging.basicConfig(level=level, format="[%(levelname)s] %(message)s")


def main() -> None:
    args = parse_args()
    configure_logging(args.verbose)

    total, matched, defaulted = annotate_muttable_with_alpha(
        args.muttable, args.vcf, args.output, args.default_value
    )
    logging.info(
        "Annotated %s rows (%s matched scores, %s defaulted to %s)",
        total,
        matched,
        defaulted,
        args.default_value,
    )


if __name__ == "__main__":
    main()