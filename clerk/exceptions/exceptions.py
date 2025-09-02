from typing import Optional


class AppBaseException(Exception):
    def __init__(
        self,
        *args,
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
    def __reduce__(self):
        # Reconstruct with message-only (what Exception expects) and restore extras via state
        return (
            self.__class__,
            (self.message,),
            {"type": self.type, "traceback": self.traceback},
        )

    def __setstate__(self, state):
        for k, v in state.items():
            setattr(self, k, v)


class ApplicationException(AppBaseException):
    pass
