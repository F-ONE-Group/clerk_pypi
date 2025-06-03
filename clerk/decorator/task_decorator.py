import pickle
from typing import Callable
from functools import wraps
from .models import ClerkCodePayload

input_pkl: str = "/app/data/input/input.pkl"
output_pkl: str = "/app/data/output/output.pkl"


def clerk_code():
    def decorator(func: Callable[[ClerkCodePayload], ClerkCodePayload]):
        @wraps(func)
        def wrapper():
            # Step 1: Load and parse input
            try:
                with open(input_pkl, "rb") as f:
                    raw_data = pickle.load(f)
                parsed = (
                    ClerkCodePayload.model_validate(raw_data)
                    if not isinstance(raw_data, ClerkCodePayload)
                    else raw_data
                )
            except Exception as e:
                raise RuntimeError(f"Failed to load and parse input pickle: {e}") from e

            # Step 2: Call the function and validate output
            try:
                output = func(parsed)
                if not isinstance(output, ClerkCodePayload):
                    raise TypeError("Function must return a ClerkCodePayload instance.")
            except Exception as e:
                output = e  # Save exception to output file for later debugging

            # Step 3: Write output or exception to pickle
            try:
                with open(output_pkl, "wb") as f:
                    pickle.dump(output, f)
            except Exception as e:
                raise RuntimeError(f"Failed to write output pickle: {e}") from e

        return wrapper

    return decorator
