import re
import json
from datetime import datetime
from datetime import timezone
from datetime import timedelta
from typing import List


from rest_framework.renderers import JSONRenderer
from rest_framework.compat import INDENT_SEPARATORS, LONG_SEPARATORS, SHORT_SEPARATORS

CLICKHOUSE_TYPES: List[str] = [
    "aggregatefunction",
    "array",
    "bool",
    "date",
    "date32",
    "datetime",
    "datetime32",
    "datetime64",
    "decimal",
    "decimal128",
    "decimal256",
    "decimal32",
    "decimal64",
    "dynamic",
    "enum",
    "enum16",
    "enum8",
    "fixedstring",
    "float32",
    "float64",
    "ipv4",
    "ipv6",
    "int128",
    "int16",
    "int256",
    "int32",
    "int64",
    "int8",
    "intervalday",
    "intervalhour",
    "intervalmicrosecond",
    "intervalmillisecond",
    "intervalminute",
    "intervalmonth",
    "intervalnanosecond",
    "intervalquarter",
    "intervalsecond",
    "intervalweek",
    "intervalyear",
    "json",
    "linestring",
    "lowcardinality",
    "map",
    "multipolygon",
    "nested",
    "nothing",
    "nullable",
    "object",
    "point",
    "polygon",
    "ring",
    "simpleaggregatefunction",
    "string",
    "tuple",
    "uint128",
    "uint16",
    "uint256",
    "uint32",
    "uint64",
    "uint8",
    "uuid",
    "variant",
    "bigint",
    "bigint signed",
    "bigint unsigned",
    "binary",
    "binary large object",
    "binary varying",
    "bit",
    "blob",
    "byte",
    "bytea",
    "char",
    "char large object",
    "char varying",
    "character",
    "character large object",
    "character varying",
    "clob",
    "dec",
    "double",
    "double precision",
    "enum",
    "fixed",
    "float",
    "geometry",
    "inet4",
    "inet6",
    "int",
    "int signed",
    "int unsigned",
    "int1",
    "int1 signed",
    "int1 unsigned",
    "integer",
    "integer signed",
    "integer unsigned",
    "longblob",
    "longtext",
    "mediumblob",
    "mediumint",
    "mediumint signed",
    "mediumint unsigned",
    "mediumtext",
    "national char",
    "national char varying",
    "national character",
    "national character large object",
    "national character varying",
    "nchar",
    "nchar large object",
    "nchar varying",
    "numeric",
    "nvarchar",
    "real",
    "set",
    "signed",
    "single",
    "smallint",
    "smallint signed",
    "smallint unsigned",
    "text",
    "time",
    "timestamp",
    "tinyblob",
    "tinyint",
    "tinyint signed",
    "tinyint unsigned",
    "tinytext",
    "unsigned",
    "varbinary",
    "varchar",
    "varchar2",
    "year",
    "bool",
    "boolean",
]

ALLOWED_TIME_FIELD_TYPES: List[str] = [
    "datetime",
    "datetime64",
    "uint64",
    "int64",
    "timestamp",
]


ALLOWED_DATE_FIELD_TYPES: List[str] = [
    "date",
    "date32",
]


class DefaultJSONRenderer(JSONRenderer):
    # copied from https://github.com/encode/django-rest-framework/blob/28d0261afcd6702900512e00c37f4e264c117d83/rest_framework/renderers.py#L85
    # to save same behaivour
    # added default=str to json.dumps
    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        Render `data` into JSON, returning a bytestring.
        """
        if data is None:
            return b""

        renderer_context = renderer_context or {}
        indent = self.get_indent(accepted_media_type, renderer_context)

        if indent is None:
            separators = SHORT_SEPARATORS if self.compact else LONG_SEPARATORS
        else:
            separators = INDENT_SEPARATORS

        ret = json.dumps(
            data,
            cls=self.encoder_class,
            indent=indent,
            ensure_ascii=self.ensure_ascii,
            allow_nan=not self.strict,
            separators=separators,
            default=str,  # the only change for telescope
        )

        # We always fully escape \u2028 and \u2029 to ensure we output JSON
        # that is a strict javascript subset.
        # See: https://gist.github.com/damncabbage/623b879af56f850a6ddc
        ret = ret.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
        return ret.encode()


HUMAN_RELATED_TIME_REGEX = re.compile(r"^now(?:-(?P<value>[0-9]+)(?P<unit>[dhms]))?$")
UNIT_TO_SECONDS = {
    "d": 24 * 60 * 60,
    "h": 60 * 60,
    "m": 60,
    "s": 1,
}


def get_source_database_conn_kwargs(source):
    return {
        "host": source.conn.data["host"],
        "port": source.conn.data["port"],
        "user": source.conn.data["user"],
        "password": source.conn.data["password"],
        "secure": source.conn.data["ssl"],
    }


def parse_time(value):
    timestamp = None
    error = None
    try:
        timestamp = int(value)
    except ValueError:
        match = HUMAN_RELATED_TIME_REGEX.match(value)
        if not match:
            error = "Invalid value given. Expect int timestamp or related str"
        else:
            now = datetime.now(timezone.utc)
            if value == "now":
                timestamp = int(now.timestamp()) * 1000
            else:
                count = int(match.group("value"))
                seconds = UNIT_TO_SECONDS[match.group("unit")]
                timestamp = int(
                    (now - timedelta(seconds=count * seconds)).timestamp() * 1000
                )
    return timestamp, error


def convert_to_base_ch(full_type: str) -> str:
    """Finds the longest matching ClickHouse type in the given full type string."""
    res: str = ""
    for t in CLICKHOUSE_TYPES:
        if t in full_type and len(t) > len(res):
            res = t
    return res


def get_telescope_field(name, _type, **kwargs):
    data = {
        "name": name,
        "display_name": "",
        "values": "",
        "type": _type,
        "jsonstring": False,
        "autocomplete": True,
        "suggest": True,
        "group_by": True,
    }
    for key, value in kwargs.items():
        if key not in data:
            raise ValueError
        data[key] = value

    if "datetime" in _type.lower():
        data["autocomplete"] = False
        data["group_by"] = False
    elif _type.startswith("Enum"):
        try:
            data["values"] = ",".join(
                [
                    x.split(" = ")[0].strip().replace("'", "")
                    for x in _type.split("(")[1].split(")")[0].split(",")
                ]
            )
        except Exception:
            pass

    return data
