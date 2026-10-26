"""Small shared input primitives for the standalone CLI and package API."""

import re
from typing import Optional


def format_mac_address(value: str) -> Optional[str]:
    """Validate and normalize supported MAC spellings, including optional masks."""
    if not value:
        return None
    parts = re.split(r"[/\s]+", value.strip())
    if len(parts) > 2:
        return None
    compact = re.sub(r"[.:-]", "", parts[0]).lower()
    if not re.fullmatch(r"[0-9a-f]{12}", compact):
        return None
    if len(parts) == 2:
        mask = parts[1]
        if not (mask.isascii() and mask.isdigit() and 0 <= int(mask) <= 48):
            if not re.fullmatch(r"[0-9a-fA-F]{12}", re.sub(r"[.:-]", "", mask)):
                return None
    return ":".join(compact[i:i + 2] for i in range(0, 12, 2))


def is_mac_address(value: str) -> bool:
    return format_mac_address(value) is not None


def read_opening_lines(stream):
    """Inspect the first two nonblank lines without consuming input records."""
    lines = (line.strip() for line in stream if line.strip())
    first, second = next(lines, ""), next(lines, "")
    stream.seek(0)
    return first, second
