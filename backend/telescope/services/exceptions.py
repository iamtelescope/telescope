class SerializerValidationError(Exception):
    def __init__(self, serializer):
        self.serializer = serializer


class ConnectionInUseError(Exception):
    """Raised when attempting to delete a connection that is being used by sources"""

    def __init__(self, connection_id, source_count):
        self.connection_id = connection_id
        self.source_count = source_count
        message = f"Cannot delete connection {connection_id}: it is being used by {source_count} source(s)"
        super().__init__(message)
        self.message = message
