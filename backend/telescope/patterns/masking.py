"""Body normalization before Drain: ANSI codes removed and whitespace collapsed, as HyperDX does."""

import re

ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
SPACE_RE = re.compile(r"\s+")


def normalize(body) -> str:
    if body is None:
        return ""
    return SPACE_RE.sub(" ", ANSI_RE.sub("", str(body))).strip()
