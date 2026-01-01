from typing import Dict, List


class ConnectionTestResponseNg:
    def __init__(self):
        self.result = False
        self.error = ""
        self.matched_contexts: List[Dict] = []
        self.total_contexts = 0

    def as_dict(self) -> dict:
        return {
            "result": self.result,
            "error": self.error,
            "matched_contexts": self.matched_contexts,
            "total_contexts": self.total_contexts,
        }


class ConnectionTestResponse:
    def __init__(self):
        self.reachability = {"result": False, "error": ""}
        self.schema = {"result": False, "error": "", "data": []}

    def as_dict(self) -> dict:
        return {"reachability": self.reachability, "schema": self.schema}
