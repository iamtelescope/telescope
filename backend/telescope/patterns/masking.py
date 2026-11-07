"""Body normalization before Drain: ANSI codes removed, whitespace collapsed and hex ids masked."""

import re

ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
SPACE_RE = re.compile(r"\s+")
MASK = "<HEX>"
# UUIDs and hex runs of 8+ chars with a digit, the ids that make every message unique.
HEX_RE = re.compile(
    r"\b(?:[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
    r"|(?=[0-9a-fA-F]*\d)[0-9a-fA-F]{8,})\b"
)


def normalize(body) -> str:
    if body is None:
        return ""
    text = SPACE_RE.sub(" ", ANSI_RE.sub("", str(body))).strip()
    return HEX_RE.sub(MASK, text)
