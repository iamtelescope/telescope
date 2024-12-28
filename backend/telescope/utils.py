import re
from datetime import datetime
from datetime import timezone
from datetime import timedelta


HUMAN_RELATED_TIME_REGEX = re.compile("^now-(?P<value>[0-9]+)(?P<unit>[dhms])$")
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


def get_times(time_from, time_to):
    parsed_related = parse_related_time(time_from)
    if parsed_related:
        time_from = parsed_related
    else:
        time_from = int(time_from)

    if time_to == "now":
        time_to = int(datetime.now(timezone.utc).timestamp()) * 1000
    else:
        time_to = int(time_to)
    return time_from, time_to


def parse_related_time(related_time):
    m = HUMAN_RELATED_TIME_REGEX.match(related_time)
    if m:
        value = int(m.group("value"))
        seconds = UNIT_TO_SECONDS[m.group("unit")]
        time_from = datetime.utcnow() - timedelta(seconds=value * seconds)
        return int(time_from.timestamp()) * 1000
    else:
        return None
