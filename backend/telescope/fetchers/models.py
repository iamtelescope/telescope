import json
from typing import List, Dict, Any, Sequence
from zoneinfo import ZoneInfo

from telescope.models import Source
from telescope.constants import (
    UTC_ZONE,
    SOURCE_CAPABILITY_SEVERITY_RULES,
    SOURCE_CAPABILITY_NORMALIZE_BODY,
    SOURCE_BODY_COL_NAME,
    SOURCE_SEVERITY_COL_NAME,
)
from telescope.fetchers.utils import extract_severity_with_rules, normalize_body_to_dict

import logging

logger = logging.getLogger("telescope.models")


class Row:
    def __init__(
        self,
        source: Source,
        selected_columns: List[str],
        values: Sequence[Any],
        tz: ZoneInfo = UTC_ZONE,
        severity: str = None,
    ):
        self.source = source

        self.data = {}
        for key, value in zip(selected_columns, values):
            self.data[key] = value

        if (
            source.has_capability(SOURCE_CAPABILITY_SEVERITY_RULES)
            and SOURCE_BODY_COL_NAME in self.data
            and source.severity_rules
        ):
            severity = extract_severity_with_rules(
                self.data[SOURCE_BODY_COL_NAME], source.severity_rules
            )

        if (
            source.has_capability(SOURCE_CAPABILITY_NORMALIZE_BODY)
            and SOURCE_BODY_COL_NAME in self.data
            and isinstance(self.data[SOURCE_BODY_COL_NAME], str)
        ):
            self.data[SOURCE_BODY_COL_NAME] = normalize_body_to_dict(
                self.data[SOURCE_BODY_COL_NAME]
            )

        self.record_id = self.data.get(source.uniq_column) or self.data.get(
            source._record_pseudo_id_column
        )
        dt = self.data[source.time_column]
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz)
        self.time = {
            "unixtime": int(dt.timestamp() * 1000),
            "datetime": dt.strftime("%Y-%m-%d %H:%M:%S"),
            "microseconds": dt.strftime("%f"),
        }
        if (
            source.has_capability(SOURCE_CAPABILITY_SEVERITY_RULES)
            and SOURCE_BODY_COL_NAME in self.data
        ):
            if not severity:
                severity = "UNKNOWN"
            self.data[SOURCE_SEVERITY_COL_NAME] = severity

        self.severity = severity if severity is not None else self.calculate_severity()

    def calculate_severity(self) -> str:
        if self.source.severity_column:
            return self.data.get(self.source.severity_column, "")
        return ""

    @property
    def as_json(self) -> str:
        return json.dumps(self.as_dict(), default=str)

    def is_propbably_jsonstring(self, value):
        if not isinstance(value, str):
            return False
        if value.startswith("{") and value.endswith("}"):
            return True
        if value.startswith("[") and value.endswith("["):
            return True

        return False

    def as_dict(self) -> Dict:
        data = {}
        for name, source_column in self.source._columns.items():
            if source_column.jsonstring and self.is_propbably_jsonstring(
                self.data[name]
            ):
                try:
                    value = json.loads(self.data[name])
                except Exception:
                    value = self.data[name]
                    logger.error(
                        "Failed to json.loads(value) for JSON-treated column '%s', %s",
                        name,
                        type(self.data[name]),
                    )
            else:
                value = self.data[name]
            data[name] = value
        return {
            "time": self.time,
            SOURCE_SEVERITY_COL_NAME: self.severity,
            "data": data,
        }
