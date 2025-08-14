from typing import Optional


class AppBaseException(Exception):
    def __init__(self, type_: str, message: str, traceback: Optional[str] = None):
        super().__init__(message)
        self.type = type_
        self.message = message
        self.traceback = traceback


class ApplicationException(AppBaseException):
    pass
