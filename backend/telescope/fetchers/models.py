import json
from typing import List, Dict, Any
from datetime import datetime

from zoneinfo import ZoneInfo

from telescope.models import Source
from telescope.constants import UTC_ZONE


class Row:
    def __init__(
        self,
        source: Source,
        selected_fields: List[str],
        values: List[Any],
        timezone: ZoneInfo = UTC_ZONE,
    ):
        self.source = source
        self.data = {}
        for key, value in zip(selected_fields, values):
            self.data[key] = value

        self.record_id = self.data.get(source.uniq_field) or self.data.get(
            source._record_pseudo_id_field
        )
        self.time = {
            "unixtime": int(self.data[source.time_field].timestamp() * 1000),
            "datetime": datetime.strftime(
                self.data[source.time_field], "%Y-%m-%d %H:%M:%S"
            ),
            "microseconds": datetime.strftime(self.data[source.time_field], "%f"),
        }

    @property
    def as_json(self) -> str:
        return json.dumps(self.as_dict(), default=str)

    def as_dict(self) -> Dict:
        data = {}
        for name, source_field in self.source._fields.items():
            if source_field.jsonstring:
                try:
                    value = json.loads(self.data[name])
                except Exception as err:
                    value = self.data[name]
                    logger.error(
                        "Failed to json.loads(value) for JSON-treated field '%s'", name
                    )
            else:
                value = self.data[name]
            data[name] = value
        return {"time": self.time, "data": data}
