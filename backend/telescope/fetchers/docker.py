import json
import logging

from dateutil import parser as duparser
import docker

from flyql.core.parser import parse, ParserError
from flyql.core.exceptions import FlyqlError
from flyql.matcher.evaluator import Evaluator
from flyql.matcher.record import Record

from telescope.utils import get_telescope_field

from telescope.fetchers.request import (
    AutocompleteRequest,
    DataRequest,
    GraphDataRequest,
)
from telescope.fetchers.response import (
    AutocompleteResponse,
    DataResponse,
    GraphDataResponse,
)
from telescope.fetchers.fetcher import BaseFetcher
from telescope.fetchers.models import Row, UTC_ZONE


logger = logging.getLogger("telescope.fetchers.docker")


STATUS_TO_INT = {
    "runnig": 0,
    "restarting": 1,
    "removing": 2,
    "paused": 3,
    "dead": 4,
    "exited": 5,
    "created": 6,
}


class ConnectionTestResponseNg:
    def __init__(
        self,
    ):
        self.result = False
        self.error = ""

    def as_dict(self) -> dict:
        return {
            "result": self.result,
            "error": self.error,
        }


class ConnectionTestResponse:
    def __init__(
        self,
    ):
        self.reachability = {
            "result": False,
            "error": "",
        }
        self.schema = {
            "result": False,
            "error": "",
            "data": [],
        }

    def as_dict(self) -> dict:
        return {
            "reachability": self.reachability,
            "schema": self.schema,
        }


class Fetcher(BaseFetcher):
    @classmethod
    def validate_query(cls, source, query):
        if not query:
            return True, None

        try:
            parser = parse(query)
        except ParserError as err:
            return False, err.message
        else:
            try:
                # row_match(parser.root, source._fields, None)
                return True, None
            except FlyqlError as err:
                return False, err.message

        return True, None

    @classmethod
    def get_all_context_fields_data(cls, source):
        client = docker.DockerClient(base_url=source.conn.data["address"])
        containers = []
        for container in client.containers.list(all=True):
            containers.append(
                {
                    "name": container.name,
                    "short_id": container.short_id,
                    "status": container.status,
                    "labels": container.labels,
                }
            )
        return {
            "containers": sorted(
                containers,
                key=lambda c: STATUS_TO_INT.get(c["status"], 10),
                reverse=True,
            ),
        }

    @classmethod
    def get_context_field_data(cls, source, field, params=None):
        if field == "container":
            client = docker.DockerClient(base_url=source.conn.data["address"])
            containers = []
            for container in client.containers.list(all=True):
                containers.append(
                    {
                        "name": container.name,
                        "short_id": container.short_id,
                        "status": container.status,
                        "labels": container.labels,
                    }
                )
            return sorted(
                containers,
                key=lambda c: STATUS_TO_INT.get(c["status"], 10),
                reverse=True,
            )
        else:
            raise ValueError

    @classmethod
    def test_connection_ng(cls, data: dict) -> ConnectionTestResponseNg:
        response = ConnectionTestResponseNg()
        try:
            client = docker.DockerClient(base_url=data["address"])
            client.containers.list()
        except Exception as err:
            response.error = str(err)
        else:
            response.result = True
        return response

    @classmethod
    def get_schema(cls, data: dict):
        """Get schema without testing connection"""
        return [
            get_telescope_field("time", "datetime"),
            get_telescope_field("container_id", "string"),
            get_telescope_field("container_name", "string"),
            get_telescope_field("container_short_id", "string"),
            get_telescope_field("message", "string"),
            get_telescope_field("status", "string"),
            get_telescope_field("stream", "string"),
            get_telescope_field("labels", "json"),
        ]

    @classmethod
    def test_connection(cls, data: dict) -> ConnectionTestResponse:
        response = ConnectionTestResponse()
        try:
            client = docker.DockerClient(base_url=data["address"])
            client.containers.list()
        except Exception as err:
            response.reachability["result"] = False
            response.reachability["error"] = str(err)
        else:
            response.reachability["result"] = True

        try:
            response.schema["result"] = True
            response.schema["data"] = cls.get_schema(data)
        except Exception as err:
            response.schema["result"] = False
            response.schema["error"] = str(err)
        return response

    @classmethod
    def autocomplete(cls, source, field, time_from, time_to, value):
        incomplete = False
        return AutocompleteResponse(items=[], incomplete=incomplete)

    @classmethod
    def fetch_graph_data(
        cls,
        request: GraphDataRequest,
    ):
        client = docker.DockerClient(base_url=request.source.conn.data["address"])
        since = request.time_from / 1000
        until = request.time_to / 1000

        evaluator = Evaluator()
        stats_by_ts = {}
        unique_ts = {request.time_from, request.time_to}
        stats_names = set()
        group_by = request.group_by[0] if request.group_by else None
        if not group_by:
            groupper = "Rows"
        else:
            groupper = None

        ts = None
        total = 0
        root = None
        if request.query:
            parser = parse(request.query)
            root = parser.root

        rows = []
        for stream_name in ["stdout", "stderr"]:
            stream_param = {
                "stdout": False,
                "stderr": False,
            }
            stream_param[stream_name] = True
            for container in client.containers.list(
                all=True,
                filters={"name": request.context_fields.get("container", [])},
            ):
                logs = container.logs(
                    timestamps=True, since=since, until=until, **stream_param
                )
                for line in logs.decode("utf-8").splitlines():
                    if not line:
                        continue
                    spl = line.split(" ")
                    try:
                        ts = duparser.isoparse(spl[0])
                    except Exception:
                        message = line
                    else:
                        message = " ".join(spl[1:])
                    message = cls.remove_ansi_escape_codes(message)
                    if ts and message:
                        row = Row(
                            source=request.source,
                            selected_fields=[
                                "time",
                                "stream",
                                "status",
                                "labels",
                                "container_id",
                                "container_short_id",
                                "container_name",
                                "message",
                            ],
                            values=[
                                ts,
                                stream_name,
                                container.status,
                                container.labels,
                                container.id,
                                container.short_id,
                                container.name,
                                message,
                            ],
                            tz=UTC_ZONE,
                        )
                        total += 1
                        if not root:
                            rows.append(row)
                        else:
                            if evaluator.evaluate(root, Record(data=row.data)):
                                rows.append(row)

        for row in rows:
            ts_key = int(row.time["unixtime"] / 1000) * 1000
            unique_ts.add(ts_key)
            if group_by:
                if ":" in group_by.name:
                    spl = group_by.name.split(":")
                    json_path = spl[1:]
                    data = json.loads(row.data[spl[0]])
                    for key in json_path:
                        data = data.get(key, {})
                    if not data:
                        groupper = "__none__"
                    else:
                        groupper = str(data)
                else:
                    groupper = str(row.data[group_by.name])

            if groupper not in stats_by_ts:
                stats_by_ts[groupper] = {}
            if ts_key not in stats_by_ts[groupper]:
                stats_by_ts[groupper][ts_key] = 1
            else:
                stats_by_ts[groupper][ts_key] += 1

        timestamps = sorted(unique_ts)
        data = {}
        for name in stats_by_ts.keys():
            data[name] = []

        for ts in timestamps:
            for name in stats_by_ts.keys():
                value = stats_by_ts.get(name, {}).get(ts, 0)
                data[name].append(value)

        return GraphDataResponse(
            timestamps=sorted(unique_ts),
            data=data,
            total=total,
        )

    def remove_ansi_escape_codes(text):
        import re

        ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        return ansi_escape.sub("", text)

    @classmethod
    def fetch_data(
        cls,
        request: DataRequest,
        tz,
    ):
        rows = []
        client = docker.DockerClient(base_url=request.source.conn.data["address"])
        since = request.time_from / 1000
        until = request.time_to / 1000
        ts = None
        root = None
        evaluator = Evaluator()
        if request.query:
            parser = parse(request.query)
            root = parser.root

        for stream_name in ["stdout", "stderr"]:
            stream_param = {
                "stdout": False,
                "stderr": False,
            }
            stream_param[stream_name] = True
            for container in client.containers.list(
                all=True,
                filters={"name": request.context_fields.get("container", [])},
            ):
                logs = container.logs(
                    timestamps=True, since=since, until=until, **stream_param
                )
                for line in logs.decode("utf-8").splitlines():
                    if not line:
                        continue
                    spl = line.split(" ")
                    try:
                        ts = duparser.isoparse(spl[0])
                    except Exception:
                        message = line
                    else:
                        message = " ".join(spl[1:])
                    message = cls.remove_ansi_escape_codes(message)
                    if ts and message:
                        row = Row(
                            source=request.source,
                            selected_fields=[
                                "time",
                                "stream",
                                "status",
                                "labels",
                                "container_id",
                                "container_short_id",
                                "container_name",
                                "message",
                            ],
                            values=[
                                ts,
                                stream_name,
                                container.status,
                                container.labels,
                                container.id,
                                container.short_id,
                                container.name,
                                message,
                            ],
                            tz=tz,
                        )
                        if not root:
                            rows.append(row)
                        else:
                            if evaluator.evaluate(root, Record(data=row.data)):
                                rows.append(row)
        rows = sorted(rows, key=lambda r: r.time["unixtime"], reverse=True)[
            : request.limit
        ]
        return DataResponse(rows=rows)

    @classmethod
    def fetch_data_and_graph(
        cls,
        request,
        tz,
    ):

        from telescope.fetchers.graph_utils import generate_graph_from_rows
        from telescope.fetchers.response import DataAndGraphDataResponse

        rows = []
        client = docker.DockerClient(base_url=request.source.conn.data["address"])
        since = request.time_from / 1000
        until = request.time_to / 1000
        ts = None
        root = None
        evaluator = Evaluator()
        if request.query:
            parser = parse(request.query)
            root = parser.root

        for stream_name in ["stdout", "stderr"]:
            stream_param = {
                "stdout": False,
                "stderr": False,
            }
            stream_param[stream_name] = True
            for container in client.containers.list(
                all=True,
                filters={"name": request.context_fields.get("container", [])},
            ):
                logs = container.logs(
                    timestamps=True, since=since, until=until, **stream_param
                )
                for line in logs.decode("utf-8").splitlines():
                    if not line:
                        continue
                    spl = line.split(" ")
                    try:
                        ts = duparser.isoparse(spl[0])
                    except Exception:
                        message = line
                    else:
                        message = " ".join(spl[1:])
                    message = cls.remove_ansi_escape_codes(message)
                    if ts and message:
                        row = Row(
                            source=request.source,
                            selected_fields=[
                                "time",
                                "stream",
                                "status",
                                "labels",
                                "container_id",
                                "container_short_id",
                                "container_name",
                                "message",
                            ],
                            values=[
                                ts,
                                stream_name,
                                container.status,
                                container.labels,
                                container.id,
                                container.short_id,
                                container.name,
                                message,
                            ],
                            tz=tz,
                        )
                        if not root:
                            rows.append(row)
                        else:
                            if evaluator.evaluate(root, Record(data=row.data)):
                                rows.append(row)

        group_by_field = request.group_by[0] if request.group_by else None
        graph_timestamps, graph_data, graph_total = generate_graph_from_rows(
            rows,
            request.time_from,
            request.time_to,
            group_by_field,
        )

        rows = sorted(rows, key=lambda r: r.time["unixtime"], reverse=True)
        limited_rows = rows[: request.limit]

        return DataAndGraphDataResponse(
            rows=limited_rows,
            graph_timestamps=graph_timestamps,
            graph_data=graph_data,
            graph_total=graph_total,
        )
