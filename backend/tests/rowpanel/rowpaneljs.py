"""Runs ui/.../sections/rowpanel.js in node, so the tests check the exact values the row panel shows."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROWPANEL_JS = (
    Path(__file__).resolve().parents[3]
    / "ui/src/components/explorer/results/sections/rowpanel.js"
)

SCRIPT = """
import * as p from './rowpanel.mjs'
const { fn, args } = JSON.parse(process.argv[2])
const out = typeof p[fn] === 'function' ? p[fn](...args) : p[fn]
console.log(JSON.stringify(out === undefined ? null : out))
"""


def call(tmp_path, fn, *args):
    """The JSON result of rowpanel.js export `fn` called with `args` (or the export itself)."""
    node = shutil.which("node")
    if not node:
        pytest.skip("node not found")
    if not (tmp_path / "run.mjs").exists():
        shutil.copy(ROWPANEL_JS, tmp_path / "rowpanel.mjs")
        (tmp_path / "run.mjs").write_text(SCRIPT)
    out = subprocess.run(
        [node, str(tmp_path / "run.mjs"), json.dumps({"fn": fn, "args": args})],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(out.stdout)


def ui_source(kind, otel, columns=None):
    """The fields of the UI Source model that rowpanel.js reads."""
    return {"kind": kind, "columns": columns or {}, "data": {"otel": otel}}
