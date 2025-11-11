import json
from typing import List, Dict, Any
from zoneinfo import ZoneInfo

from telescope.models import Source
from telescope.constants import UTC_ZONE

import logging

logger = logging.getLogger("telescope.models")


class Row:
    def __init__(
        self,
        source: Source,
        selected_fields: List[str],
        values: List[Any],
        tz: ZoneInfo = UTC_ZONE,
    ):
        self.source = source
        self.data = {}
        for key, value in zip(selected_fields, values):
            self.data[key] = value

        self.record_id = self.data.get(source.uniq_field) or self.data.get(
            source._record_pseudo_id_field
        )
        dt = self.data[source.time_field]
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz)
        self.time = {
            "unixtime": int(dt.timestamp() * 1000),
            "datetime": dt.strftime("%Y-%m-%d %H:%M:%S"),
            "microseconds": dt.strftime("%f"),
        }

    @property
    def as_json(self) -> str:
        return json.dumps(self.as_dict(), default=str)

    def is_propbably_jsonstring(self, value):
        # check before attempting json.load
        if not isinstance(value, str):
            return False
        if value.startswith("{") and value.endswith("}"):
            return True
        if value.startswith("[") and value.endswith("["):
            return True

        return False

    def as_dict(self) -> Dict:
        data = {}
        for name, source_field in self.source._fields.items():
            if source_field.jsonstring and self.is_propbably_jsonstring(
                self.data[name]
            ):
                try:
                    value = json.loads(self.data[name])
                except Exception:
                    value = self.data[name]
                    logger.error(
                        "Failed to json.loads(value) for JSON-treated field '%s', %s",
                        name,
                        type(self.data[name]),
                    )
            else:
                value = self.data[name]
            data[name] = value
        return {"time": self.time, "data": data}
