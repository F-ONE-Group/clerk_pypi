from typing import Any, Callable, overload, TypeVar

from pydantic import Field

_T = TypeVar("_T")

@overload
def ClerkVariable(*, id: str, default: _T) -> _T: ...
@overload
def ClerkVariable(*, id: str, default_factory: Callable[[], _T]) -> _T: ...
@overload
def ClerkVariable(*, id: str) -> Any: ...

def ClerkVariable(*, id: str, **kwargs: Any) -> Any:
    """Create a Pydantic Field with a Clerk variable ID attached."""
    json_schema_extra = kwargs.pop("json_schema_extra", {}) or {}
    json_schema_extra["clerk_var_id"] = id
    return Field(**kwargs, json_schema_extra=json_schema_extra)