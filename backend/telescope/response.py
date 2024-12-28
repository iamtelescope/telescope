class UIResponse:
    def __init__(self):
        self.result = True
        self.data = {}
        self.messages = []
        self.errors = []
        self.validation = {
            "result": True,
            "fields": {},
            "non_field": [],
        }

    def add_msg(self, message):
        if message:
            self.messages.append(message)

    def add_err(self, error):
        if error:
            self.errors.append(error)

    def mark_failed(self, error):
        self.add_err(error)
        self.result = False

    def mark_ok(self, message):
        self.add_msg(message)
        self.result = True

    def as_dict(self):
        return {
            "result": self.result,
            "data": self.data,
            "messages": self.messages,
            "errors": self.errors,
            "validation": self.validation,
        }
