"""Runs ui/src/utils/context.js in node, so the tests send the exact query the CONTEXT tab builds."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

CONTEXT_JS = Path(__file__).resolve().parents[3] / "ui" / "src" / "utils" / "context.js"

SCRIPT = """
import * as c from './context.mjs'
const { source, row, preset, range } = JSON.parse(process.argv[2])
const filters = c.extractQuickFilters(source, row)
const selected = c.presetFilterIds(preset, filters, source)
console.log(JSON.stringify({
    filters,
    presets: c.availablePresets(filters, source).map((p) => p.value),
    query: c.buildContextQuery(selected, filters, ''),
    window: c.contextWindow(row, range),
}))
"""


def ui_source(source):
    """The fields of the UI Source model that context.js reads."""
    return {
        "kind": source.kind,
        "columns": source.columns,
        "timeColumn": source.time_column,
        "dateColumn": source.date_column,
        "data": getattr(source, "data", None) or {},
    }


def context_for(tmp_path, source, row, preset, range_ms):
    node = shutil.which("node")
    if not node:
        pytest.skip("node not found")
    shutil.copy(CONTEXT_JS, tmp_path / "context.mjs")
    (tmp_path / "run.mjs").write_text(SCRIPT)
    arg = json.dumps(
        {"source": ui_source(source), "row": row, "preset": preset, "range": range_ms}
    )
    out = subprocess.run(
        [node, str(tmp_path / "run.mjs"), arg],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(out.stdout)
