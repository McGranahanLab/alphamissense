"""Split a large mutation table into one muttable per tumour_id."""

from __future__ import annotations

import argparse
import csv
import gzip
from pathlib import Path


def open_text(path: Path):
    if str(path).endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="ignore")
    return path.open("r", encoding="utf-8", errors="ignore")


def open_write(path: Path, gzip_output: bool):
    if gzip_output:
        if not str(path).endswith(".gz"):
            path = Path(f"{path}.gz")
        return gzip.open(path, "wt", encoding="utf-8", newline="")
    return path.open("w", encoding="utf-8", newline="")


def detect_delimiter(path: Path) -> str:
    with open_text(path) as handle:
        sample = handle.read(4096)
    if sample.count("\t") > sample.count(","):
        return "\t"
    return ","


def parse_bool(value: str) -> bool:
    lowered = value.strip().lower()
    if lowered in {"1", "true", "t", "yes", "y"}:
        return True
    if lowered in {"0", "false", "f", "no", "n"}:
        return False
    raise argparse.ArgumentTypeError(f"Invalid boolean value: {value}")


def split_table(
    input_path: Path,
    output_dir: Path,
    tumour_column: str,
    filename_template: str,
    gzip_output: bool,
) -> tuple[int, int]:
    delimiter = detect_delimiter(input_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    writers: dict[str, csv.DictWriter] = {}
    handles = {}
    n_rows = 0

    try:
        with open_text(input_path) as infile:
            reader = csv.DictReader(infile, delimiter=delimiter)
            if reader.fieldnames is None:
                raise ValueError("Input table has no header")
            if tumour_column not in reader.fieldnames:
                raise ValueError(
                    f"Required tumour column {tumour_column!r} not found in header"
                )

            for row in reader:
                if not row:
                    continue
                tumour_id = (row.get(tumour_column) or "").strip()
                if not tumour_id:
                    continue

                writer = writers.get(tumour_id)
                if writer is None:
                    out_name = filename_template.format(tumour_id=tumour_id)
                    out_path = output_dir / out_name
                    handle = open_write(out_path, gzip_output)
                    handles[tumour_id] = handle
                    writer = csv.DictWriter(
                        handle,
                        fieldnames=reader.fieldnames,
                        delimiter=delimiter,
                        lineterminator="\n",
                    )
                    writer.writeheader()
                    writers[tumour_id] = writer

                writer.writerow(row)
                n_rows += 1
    finally:
        for handle in handles.values():
            handle.close()

    return n_rows, len(writers)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Split one mutation table into per-tumour muttable files"
    )
    parser.add_argument("--input", required=True, type=Path, help="Input table path")
    parser.add_argument(
        "--output-dir", required=True, type=Path, help="Directory for split tables"
    )
    parser.add_argument(
        "--tumour-column",
        default="tumour_id",
        help="Column name containing tumour IDs",
    )
    parser.add_argument(
        "--filename-template",
        default="{tumour_id}_muttable.tsv",
        help="Output filename template; use {tumour_id}",
    )
    parser.add_argument(
        "--gzip-output",
        type=parse_bool,
        default=True,
        help="Whether to gzip per-tumour files (true/false)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows, tumours = split_table(
        input_path=args.input,
        output_dir=args.output_dir,
        tumour_column=args.tumour_column,
        filename_template=args.filename_template,
        gzip_output=args.gzip_output,
    )
    print(f"Wrote {tumours} tumour files with {rows} rows total")


if __name__ == "__main__":
    main()
