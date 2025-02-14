import re
import json
from datetime import datetime
from datetime import timezone
from datetime import timedelta


from rest_framework.renderers import JSONRenderer
from rest_framework.compat import INDENT_SEPARATORS, LONG_SEPARATORS, SHORT_SEPARATORS


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
        "host": source.connection["host"],
        "port": source.connection["port"],
        "user": source.connection["user"],
        "password": source.connection["password"],
        "secure": source.connection["ssl"],
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
