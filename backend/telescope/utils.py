import re
from datetime import datetime
from datetime import timezone
from datetime import timedelta


HUMAN_RELATED_TIME_REGEX = re.compile(r"^now(?:-(?P<value>[0-9]+)(?P<unit>[dhms]))?$")
UNIT_TO_SECONDS = {
    "d": 24 * 60 * 60,
    "h": 60 * 60,
    "m": 60,
    "s": 1,
}


def get_source_database_conn_kwargs(source):
    return {
        "host": source.connection.host,
        "port": source.connection.port,
        "user": source.connection.user,
        "password": source.connection.password,
        "secure": source.connection.ssl,
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
            if value == "now":
                timestamp = int(datetime.now(timezone.utc).timestamp()) * 1000
            else:
                count = int(match.group("value"))
                seconds = UNIT_TO_SECONDS[match.group("unit")]
                timestamp = int(
                    (datetime.utcnow() - timedelta(seconds=count * seconds)).timestamp()
                    * 1000
                )
    return timestamp, error
