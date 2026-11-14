"""A thrown problem with a field: the message always names the key."""


class BirPdfError(Exception):
    def __init__(self, message: str, key: str | None = None):
        super().__init__(message)
        self.key = key
