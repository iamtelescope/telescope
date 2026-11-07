"""Helpers shared by the SQL fetchers for keyset paging and bare-text search."""

from typing import Dict, Optional, Sequence

from telescope.models import Source

BODY_COLUMN_NAMES = ["body", "message", "msg", "log"]


def body_column(source: Source) -> Optional[str]:
    """The column bare text is searched in: the OTel body role, else a body-like column name."""
    otel = (source.data or {}).get("otel") or {}
    role = (otel.get("roles") or {}).get("body") or otel.get("body")
    if role and role in source.columns:
        return role
    by_lower = {name.lower(): name for name in source.columns}
    for candidate in BODY_COLUMN_NAMES:
        if candidate in by_lower:
            return by_lower[candidate]
    return None


def next_cursor(
    source: Source,
    keys: Sequence[tuple],
    limit: int,
    before: Optional[Dict],
) -> Optional[Dict]:
    """Cursor for the page after rows whose (time, uniq) keys are given, or None at the end."""
    if not keys or len(keys) < limit:
        return None
    last_time, last_uniq = keys[-1]
    if source.uniq_column:
        return {"time": str(last_time), "uniq": str(last_uniq)}
    # Without a uniq column, rows sharing the last time are skipped by count on the next page.
    skip = sum(1 for t, _ in keys if t == last_time)
    if before and str(before.get("time")) == str(last_time):
        skip += int(before.get("skip") or 0)
    return {"time": str(last_time), "skip": skip}
