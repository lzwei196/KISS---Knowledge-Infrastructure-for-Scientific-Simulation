#!/usr/bin/env python3
"""
create_batch_file.py - Creates a DSSAT batch file (DSSBatch.v48).

The batch file controls which experiment files and treatments DSSAT runs.
DSSAT reads the batch file to locate FileX experiments and specific treatments.

Batch File Format (from CSM.for source):
    $BATCH(CROP_NAME)
    !
    @FILEX                                                                                        TRTNO     RP     SQ     OP     CO
    <path_to_filex padded to 92 chars>                                                            TRTNO     RP     SQ     OP     CO

Critical format details from Fortran source (CSM.for:268-272):
    - FileX path occupies columns 1-92 (right-justified 12-char filename)
    - TRTNO starts at column 93, format 3(1X,I6) for TRTNO, TRTREP, ROTNUM
    - RP (replication), SQ (sequence), OP (option), CO (control) follow

Exit codes:
    0 = success
    1 = input error
    2 = processing error
    3 = output error
"""

import sys
import os
import logging
import json

# ---------------------------------------------------------------------------
# INPUT VARIABLES (agent sets these before invocation)
# ---------------------------------------------------------------------------
FILEX_TREATMENTS = []       # List of (filex_path, treatment_numbers) tuples
                            # treatment_numbers can be int or list of ints
CROP_NAME = ""              # Crop name for $BATCH header (e.g., "MAIZE")
OUTPUT_PATH = ""            # Path to write batch file (default: DSSBatch.v48 in cwd)
VALIDATE_FILEX = True       # If True, check that FileX paths exist
RP_DEFAULT = 1              # Default replication number
SQ_DEFAULT = 0              # Default sequence number
OP_DEFAULT = 0              # Default option number
CO_DEFAULT = 0              # Default control number
OUTPUT_JSON = True          # If True, print JSON summary to stdout

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(message)s"
)
logger = logging.getLogger("create_batch_file")

# ---------------------------------------------------------------------------
# DSSAT BATCH FILE CONSTANTS
# ---------------------------------------------------------------------------
# From CSM.for: FileX path is read from columns 1 to END_POS-1 where
# END_POS is the position after the trimmed path. The path field is 92 chars wide.
FILEX_FIELD_WIDTH = 92

# Column header line format (matching official DSSAT batch files)
BATCH_HEADER_TEMPLATE = "@FILEX{spaces}TRTNO     RP     SQ     OP     CO"

# Data line: path padded to FILEX_FIELD_WIDTH, then treatment fields
# Format from Fortran: 3(1X,I6) starting at column 93
# Full format: columns 93-99 = 1X+I6 for TRTNO, 100-106 = 1X+I6 for RP, etc.
DATA_FORMAT = "{filex:<{width}s}{trtno:>6d}{rp:>6d}{sq:>6d}{op:>6d}{co:>6d}"


def normalize_treatments(filex_treatments):
    """Normalize the input treatment list to a flat list of (path, trtno) tuples.

    Args:
        filex_treatments: List where each element is either:
            - (filex_path, treatment_number) where treatment_number is int
            - (filex_path, [list_of_treatment_numbers])
            - (filex_path, treatment_number, rp, sq, op, co) extended format

    Returns:
        List of dicts with keys: filex, trtno, rp, sq, op, co.
    """
    records = []

    for entry in filex_treatments:
        if not isinstance(entry, (list, tuple)):
            raise ValueError(
                f"Each entry must be a tuple/list, got {type(entry)}: {entry}"
            )

        if len(entry) < 2:
            raise ValueError(
                f"Each entry must have at least (filex_path, treatment_number), "
                f"got {len(entry)} elements: {entry}"
            )

        filex_path = str(entry[0])
        trt_spec = entry[1]

        # Default values for optional fields
        rp = entry[2] if len(entry) > 2 else RP_DEFAULT
        sq = entry[3] if len(entry) > 3 else SQ_DEFAULT
        op = entry[4] if len(entry) > 4 else OP_DEFAULT
        co = entry[5] if len(entry) > 5 else CO_DEFAULT

        # Handle treatment_numbers as int or list
        if isinstance(trt_spec, (list, tuple)):
            for trtno in trt_spec:
                records.append({
                    "filex": filex_path,
                    "trtno": int(trtno),
                    "rp": int(rp),
                    "sq": int(sq),
                    "op": int(op),
                    "co": int(co),
                })
        else:
            records.append({
                "filex": filex_path,
                "trtno": int(trt_spec),
                "rp": int(rp),
                "sq": int(sq),
                "op": int(op),
                "co": int(co),
            })

    return records


def validate_records(records):
    """Validate batch file records.

    Args:
        records: List of record dicts from normalize_treatments().

    Returns:
        tuple of (errors_list, warnings_list).
    """
    errors = []
    warnings = []

    if not records:
        errors.append("No treatment records provided.")
        return errors, warnings

    seen_paths = set()

    for i, rec in enumerate(records):
        filex = rec["filex"]
        trtno = rec["trtno"]

        # Check treatment number is positive
        if trtno <= 0:
            errors.append(
                f"Record {i + 1}: treatment number {trtno} must be a positive integer."
            )

        # Check FileX path exists (if validation enabled)
        if VALIDATE_FILEX and filex not in seen_paths:
            if not os.path.isfile(filex):
                errors.append(
                    f"Record {i + 1}: FileX path does not exist: '{filex}'"
                )
            seen_paths.add(filex)

        # Check path length fits in field width
        if len(filex) > FILEX_FIELD_WIDTH:
            errors.append(
                f"Record {i + 1}: FileX path length ({len(filex)}) exceeds "
                f"maximum field width ({FILEX_FIELD_WIDTH}): '{filex}'"
            )

        # Check FileX has valid extension (should be .XXX where X is crop code letter)
        basename = os.path.basename(filex)
        if "." in basename:
            ext = basename.rsplit(".", 1)[1]
            if len(ext) != 3:
                warnings.append(
                    f"Record {i + 1}: FileX extension '{ext}' is not 3 characters. "
                    f"DSSAT expects extensions like .MZX, .RIX, .WHX, etc."
                )
            elif not ext[2].upper() == "X":
                warnings.append(
                    f"Record {i + 1}: FileX extension '{ext}' does not end with 'X'. "
                    f"Standard DSSAT experiment files use extensions ending in 'X'."
                )

        # Validate RP, SQ, OP, CO are non-negative
        for field in ["rp", "sq", "op", "co"]:
            if rec[field] < 0:
                errors.append(
                    f"Record {i + 1}: {field.upper()} = {rec[field]} must be >= 0."
                )

    return errors, warnings


def generate_batch_content(records, crop_name):
    """Generate the batch file content string.

    Args:
        records: List of validated record dicts.
        crop_name: Crop name for the $BATCH header.

    Returns:
        String containing the complete batch file content.
    """
    lines = []

    # $BATCH header
    lines.append(f"$BATCH({crop_name.upper()})")
    lines.append("!")

    # Column header line
    # The @FILEX header needs spacing to match FILEX_FIELD_WIDTH
    filex_header = "@FILEX"
    spaces_needed = FILEX_FIELD_WIDTH - len(filex_header)
    header_line = f"{filex_header}{' ' * spaces_needed} TRTNO     RP     SQ     OP     CO"
    lines.append(header_line)

    # Data lines
    for rec in records:
        data_line = DATA_FORMAT.format(
            filex=rec["filex"],
            width=FILEX_FIELD_WIDTH,
            trtno=rec["trtno"],
            rp=rec["rp"],
            sq=rec["sq"],
            op=rec["op"],
            co=rec["co"],
        )
        lines.append(data_line)

    return "\n".join(lines) + "\n"


def main():
    """Entry point: create DSSAT batch file."""
    # -----------------------------------------------------------------------
    # PRECONDITIONS
    # -----------------------------------------------------------------------
    if not FILEX_TREATMENTS:
        logger.error("FILEX_TREATMENTS must be set (non-empty list of tuples).")
        sys.exit(1)

    if not CROP_NAME:
        logger.error("CROP_NAME must be set (e.g., 'MAIZE', 'RICE').")
        sys.exit(1)

    output_path = OUTPUT_PATH if OUTPUT_PATH else os.path.join(os.getcwd(), "DSSBatch.v48")

    # Verify output directory exists
    output_dir = os.path.dirname(os.path.abspath(output_path))
    if not os.path.isdir(output_dir):
        logger.error("Output directory does not exist: %s", output_dir)
        sys.exit(1)

    # -----------------------------------------------------------------------
    # CORE PROCESSING
    # -----------------------------------------------------------------------
    try:
        records = normalize_treatments(FILEX_TREATMENTS)
    except ValueError as e:
        logger.error("Input normalization error: %s", e)
        sys.exit(1)

    errors, warnings = validate_records(records)

    if warnings:
        for w in warnings:
            logger.warning(w)

    if errors:
        for e in errors:
            logger.error(e)
        logger.error(
            "Batch file creation aborted due to %d validation error(s).", len(errors)
        )
        if OUTPUT_JSON:
            print(json.dumps({
                "success": False,
                "errors": errors,
                "warnings": warnings,
            }, indent=2))
        sys.exit(1)

    try:
        content = generate_batch_content(records, CROP_NAME)
    except Exception as e:
        logger.error("Error generating batch file content: %s", e, exc_info=True)
        sys.exit(2)

    # -----------------------------------------------------------------------
    # WRITE OUTPUT FILE
    # -----------------------------------------------------------------------
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
    except IOError as e:
        logger.error("Failed to write batch file: %s", e)
        sys.exit(2)

    # -----------------------------------------------------------------------
    # POSTCONDITIONS
    # -----------------------------------------------------------------------
    # Verify the file was written correctly
    if not os.path.isfile(output_path):
        logger.error("Output file was not created: %s", output_path)
        sys.exit(3)

    # Re-read and verify structure
    try:
        with open(output_path, "r", encoding="utf-8") as f:
            written_content = f.read()
    except IOError as e:
        logger.error("Cannot re-read output file for verification: %s", e)
        sys.exit(3)

    # Verify $BATCH header is present
    if "$BATCH" not in written_content:
        logger.error("Output file missing $BATCH header (postcondition failure).")
        sys.exit(3)

    # Verify @FILEX header is present
    if "@FILEX" not in written_content:
        logger.error("Output file missing @FILEX header (postcondition failure).")
        sys.exit(3)

    # Count data lines (non-comment, non-header, non-blank)
    data_line_count = 0
    for wline in written_content.split("\n"):
        ws = wline.strip()
        if ws and not ws.startswith("$") and not ws.startswith("!") and not ws.startswith("@"):
            data_line_count += 1

    if data_line_count != len(records):
        logger.error(
            "Output file has %d data lines but expected %d (postcondition failure).",
            data_line_count, len(records)
        )
        sys.exit(3)

    # -----------------------------------------------------------------------
    # OUTPUT
    # -----------------------------------------------------------------------
    file_size = os.path.getsize(output_path)
    logger.info(
        "Created batch file: %s (%d records, %d bytes)",
        output_path, len(records), file_size
    )

    if OUTPUT_JSON:
        result = {
            "success": True,
            "output_path": os.path.abspath(output_path),
            "crop_name": CROP_NAME.upper(),
            "record_count": len(records),
            "file_size_bytes": file_size,
            "warnings": warnings,
            "records": [
                {
                    "filex": rec["filex"],
                    "trtno": rec["trtno"],
                    "rp": rec["rp"],
                    "sq": rec["sq"],
                    "op": rec["op"],
                    "co": rec["co"],
                }
                for rec in records
            ],
        }
        print(json.dumps(result, indent=2))

    sys.exit(0)


if __name__ == "__main__":
    main()
