"""Helpers for turning flyql's structured errors/diagnostics into readable
user-facing messages.

``ParserError`` and ``Diagnostic`` carry a ``range`` with the offending span
when available; we lift that into the final string so the user can spot
which part of their query/columns expression broke.

Bare ``FlyqlError`` (raised from generators / transformer ``sql()``
implementations — e.g. UI-only transformers in ``flyql_registry``) has no
``range``. We fall back to scanning the source text for a quoted token
named in the error message so the user still gets a position. The fallback
uses word boundaries so a name like ``'chars'`` cannot accidentally match
inside ``chars_count``; if no boundary-clean match exists we drop the
position rather than mislead.
"""

import re
from typing import Any, Optional

# Match the first single-quoted token in the error message — flyql's
# convention for naming the offending transformer/renderer/column
# (e.g. "transformer 'chars' is UI-only…").
_QUOTED_NAME_RE = re.compile(r"'([^']+)'")


def format_flyql_error(text: Optional[str], err: Any) -> str:
    message = getattr(err, "message", None) or str(err) or "flyql error"
    rng = getattr(err, "range", None)
    if rng is None or text is None:
        return _format_without_range(message, text)
    start = getattr(rng, "start", None)
    end = getattr(rng, "end", None)
    if not isinstance(start, int) or start < 0 or start > len(text):
        return message
    if isinstance(end, int) and start < end <= len(text):
        span = text[start:end]
        if span:
            return f"{message} at position {start + 1}: {span!r}"
    if start < len(text):
        return f"{message} at position {start + 1}: {text[start]!r}"
    return f"{message} at position {start + 1}"


def _format_without_range(message: str, text: Optional[str]) -> str:
    if not text:
        return message
    match = _QUOTED_NAME_RE.search(message)
    if not match:
        return message
    name = match.group(1)
    # Word-boundary-safe lookup: re.escape so regex metacharacters in the
    # name don't blow up; \b on both sides so 'chars' doesn't match inside
    # 'chars_count'. If the name has no identifier-like chars (e.g. '|') the
    # boundary still works because \b is a transition from \w to \W.
    name_pattern = re.compile(rf"\b{re.escape(name)}\b")
    pos_match = name_pattern.search(text)
    if pos_match is None:
        return message
    pos = pos_match.start()
    return f"{message} at position {pos + 1}: {name!r}"
