"""Utilities for converting muttable CSV files into VCF format."""

from __future__ import annotations

import argparse
import csv
import logging
import gzip
from pathlib import Path
from typing import Iterable, Sequence

DEFAULT_INFO_FIELDS: Sequence[str] = (
    "sample_name_hash",
    "patient_tumour",
    "func_refgene",
    "exonicfunc_refgene",
    "mutation_cluster",
    "phylo_ccf",
    "clone",
    "mutcpn",
    "major_cn",
    "minor_cn",
)


def parse_mutation_id(mutation_id: str) -> tuple[str, str, str, str, str]:
    """Split ``mutation_id`` (``SAMPLE:CHR:POS:REF:ALT``) into VCF fields."""

    parts = mutation_id.strip().split(":", maxsplit=4)
    if len(parts) != 5:
        raise ValueError(
            "mutation_id must contain SAMPLE:CHR:POS:REF:ALT, "
            f"but got {mutation_id!r}"
        )

    tid, chrom, pos_raw, ref, alt = parts
    if not pos_raw:
        raise ValueError("POS component is empty")

    try:
        pos = str(int(float(pos_raw)))
    except ValueError as exc:
        raise ValueError(f"POS component is not numeric ({pos_raw!r})") from exc

    if not ref or not alt:
        raise ValueError("REF and ALT components cannot be empty")

    return tid, chrom, pos, ref, alt


def build_info_field(row: dict[str, str], info_fields: Iterable[str]) -> str:
    """Create a semicolon-separated INFO field from selected columns."""

    parts: list[str] = []
    for field in info_fields:
        value = row.get(field)
        if value is None or value == "":
            continue
        sanitized = str(value).replace(";", ",")
        parts.append(f"{field.upper()}={sanitized}")

    return ";".join(parts) if parts else "."


def write_vcf_header(handle) -> None:
    """Write the minimal VCF header required by downstream tooling."""

    handle.write("##fileformat=VCFv4.2\n")
    handle.write("##source=muttable_to_vcf\n")
    handle.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n")


def _open_text_file(path: Path):
    """Return a text handle that transparently reads plain or gzipped files."""

    if str(path).endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("r", encoding="utf-8")


def _detect_delimiter(handle) -> str:
    """Best-effort delimiter detection between comma and tab."""

    sample = handle.read(4096)
    handle.seek(0)
    if sample.count("\t") > sample.count(","):
        return "\t"
    return ","


def _chrom_sort_key(chrom: str) -> tuple[int, int | str]:
    value = chrom.strip()
    if value.lower().startswith("chr"):
        value = value[3:]
    upper = value.upper()

    if upper == "X":
        return (0, 23)
    if upper == "Y":
        return (0, 24)
    if upper in {"M", "MT"}:
        return (0, 25)
    if value.isdigit():
        return (0, int(value))
    return (1, upper)


def convert_to_vcf(
    input_file: Path,
    output_file: Path,
    info_fields: Sequence[str] | None = None,
) -> int:
    """Convert ``input_file`` muttable CSV into ``output_file`` VCF.

    Returns the number of emitted variants.
    """

    fields_to_use = info_fields if info_fields is not None else DEFAULT_INFO_FIELDS
    records: list[tuple[str, int, str]] = []

    with _open_text_file(input_file) as infile, output_file.open(
        "w", encoding="utf-8"
    ) as outfile:
        delimiter = _detect_delimiter(infile)
        reader = csv.DictReader(infile, delimiter=delimiter)
        write_vcf_header(outfile)

        for idx, row in enumerate(reader, start=1):
            mutation_id = (row.get("mutation_id") or "").strip()
            if not mutation_id:
                logging.warning("Row %s missing mutation_id; skipping", idx)
                continue

            try:
                tid, chrom, pos, ref, alt = parse_mutation_id(mutation_id)
            except ValueError as exc:
                logging.warning("Row %s has invalid mutation_id %r: %s", idx, mutation_id, exc)
                continue

            info_field = build_info_field(row, fields_to_use)
            pos_int = int(pos)
            line = f"{chrom}\t{pos}\t{tid}\t{ref}\t{alt}\t.\tPASS\t{info_field}\n"
            records.append((chrom, pos_int, line))

        records.sort(key=lambda x: (_chrom_sort_key(x[0]), x[1]))
        for _, __, line in records:
            outfile.write(line)

    return len(records)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a muttable CSV (mutation table) into a VCF file."
    )
    parser.add_argument("--input", type=Path, help="Path to the muttable CSV file")
    parser.add_argument("--output", type=Path, help="Destination path for the VCF file")
    parser.add_argument(
        "--info-fields",
        nargs="*",
        default=None,
        metavar="COLUMN",
        help=(
            "Optional list of CSV column names to include in the INFO column. "
            "Defaults to: " + ", ".join(DEFAULT_INFO_FIELDS)
        ),
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase logging verbosity (can be passed multiple times)",
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

    emitted = convert_to_vcf(args.input, args.output, args.info_fields)
    logging.info("Wrote %s variants to %s", emitted, args.output)


if __name__ == "__main__":
    main()