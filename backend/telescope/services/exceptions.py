class SerializerValidationError(Exception):
    def __init__(self, serializer):
        self.serializer = serializer
