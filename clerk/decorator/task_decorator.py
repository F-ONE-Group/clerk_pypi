import pickle
from typing import Callable, Optional
from functools import wraps
from .models import ClerkCodePayload

input_pkl: str = "/app/data/input/input.pkl"
output_pkl: str = "/app/data/output/output.pkl"


def clerk_code():
    def decorator(func: Callable[[ClerkCodePayload], ClerkCodePayload]):
        @wraps(func)
        def wrapper(payload: Optional[ClerkCodePayload] = None) -> ClerkCodePayload:
            # 1. Load payload from file if not provided
            if payload is None:
                try:
                    with open(input_pkl, "rb") as f:
                        raw_data = pickle.load(f)
                    payload = (
                        ClerkCodePayload.model_validate(raw_data)
                        if not isinstance(raw_data, ClerkCodePayload)
                        else raw_data
                    )
                except Exception as e:
                    raise RuntimeError(
                        f"Failed to load and parse input pickle: {e}"
                    ) from e

            # 2. Execute function
            try:
                output = func(payload)
                if not isinstance(output, ClerkCodePayload):
                    raise TypeError("Function must return a ClerkCodePayload instance.")
            except Exception as e:
                output = e

            # 3. Always write to output.pkl
            try:
                with open(output_pkl, "wb") as f:
                    pickle.dump(output, f)
            except Exception as e:
                raise RuntimeError(f"Failed to write output pickle: {e}") from e

            # 4. Raise if error or return result
            if isinstance(output, Exception):
                raise output
            return output

        return wrapper

    return decorator
