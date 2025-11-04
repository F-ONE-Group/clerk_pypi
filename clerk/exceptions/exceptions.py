from typing import Any, Optional


class AppBaseException(Exception):
    def __init__(
        self,
        *args: Any,
        type_: Optional[str] = None,
        message: Optional[str] = None,
        traceback: Optional[str] = None,
    ):
        # If called with positional args (e.g., during unpickling or raise("msg")),
        # treat args[0] as the message.
        if args and message is None:
            message = args[0]

        # Always call base Exception with just the message so .args == (message,)
        super().__init__(message)

        # Store structured fields
        self.type = type_ or self.__class__.__name__
        self.message = message or ""
        self.traceback = traceback

    # (Optional) make pickling round-trip the extra fields explicitly
    def __reduce__(self):  # type: ignore
        # Reconstruct with message-only (what Exception expects) and restore extras via state
        return (
            self.__class__,
            (self.message,),
            {"type": self.type, "traceback": self.traceback},
        )  # type: ignore

    def __setstate__(self, state):  # type: ignore
        for k, v in state.items():  # type: ignore
            setattr(self, k, v)  # type: ignore


class ApplicationException(AppBaseException):
    pass
