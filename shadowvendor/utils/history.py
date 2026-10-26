"""Archive summary/metadata pairs without replacing an earlier run."""

from datetime import datetime, timezone
from itertools import count
import json
from pathlib import Path


def archive_vendor_summary(summary_src, history_dir, *, site=None, change_ticket=None):
    """Return the two written paths; reserve both names with exclusive creation.

    The first run keeps the legacy filename. Collisions append an ordered suffix.
    Callers still need separate report directories for concurrent analysis jobs.
    """
    contents = Path(summary_src).read_bytes()
    history_dir = Path(history_dir)
    history_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now().astimezone()
    timestamp = now.strftime("%Y%m%d-%H%M%S")
    metadata = json.dumps({
        "run_timestamp": now.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "site": site,
        "change_ticket_id": change_ticket,
    }, indent=2)

    for sequence in count():
        suffix = f"-{sequence:06d}" if sequence else ""
        summary_dst = history_dir / f"vendor_summary-{timestamp}{suffix}.txt"
        metadata_path = history_dir / f"{summary_dst.stem}.metadata.json"
        summary_created = metadata_created = False
        try:
            with summary_dst.open("xb") as summary:
                summary_created = True
                with metadata_path.open("x", encoding="utf-8") as companion:
                    metadata_created = True
                    summary.write(contents)
                    companion.write(metadata)
        except BaseException as error:
            # Handles write/close failures too, after files are closed on Windows.
            # Only remove files this attempt created, never a pre-existing pair.
            if metadata_created:
                metadata_path.unlink()
            if summary_created:
                summary_dst.unlink()
            if isinstance(error, FileExistsError):
                continue
            raise
        return summary_dst, metadata_path
