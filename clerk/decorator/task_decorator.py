import pickle
import traceback
from typing import Callable, Optional
from functools import wraps

from clerk.exceptions.exceptions import ApplicationException
from .models import ClerkCodePayload

input_pkl: str = "/app/data/input/input.pkl"
output_pkl: str = "/app/data/output/output.pkl"


def clerk_code():
    def decorator(func: Callable[[ClerkCodePayload], ClerkCodePayload]):
        @wraps(func)
        def wrapper(
            payload: Optional[ClerkCodePayload] = None,
        ) -> ClerkCodePayload | None:
            # 1. Load payload from file if not provided
            use_pickle = False
            output: ClerkCodePayload | BaseException | None = None
            error_occurred = False
            error_info = None
            if payload is None:
                use_pickle = True
                # Write a placeholder output file in case of early failure
                with open(output_pkl, "wb") as f:
                    pickle.dump({"error": "Early failure"}, f)
                try:
                    with open(input_pkl, "rb") as f:
                        raw_data = pickle.load(f)
                    payload = (
                        ClerkCodePayload.model_validate(raw_data)
                        if not isinstance(raw_data, ClerkCodePayload)
                        else raw_data
                    )
                except Exception as e:
                    error_occurred = True
                    error_info = ApplicationException(
                        type_=str(type(e)),
                        message=f"Failed to load and parse input pickle: {e}",
                        traceback=traceback.format_exc(),
                    )

            assert payload is not None

            # 2. Execute function
            if not error_occurred:
                try:
                    output = func(payload)
                    if not isinstance(output, ClerkCodePayload):  # type: ignore
                        raise TypeError(
                            "Function must return a ClerkCodePayload instance."
                        )
                except Exception as e:
                    error_occurred = True
                    error_info = ApplicationException(
                        type_=str(type(e)),
                        message=str(e),
                        traceback=traceback.format_exc(),
                    )
                    output = error_info

            # 3. write to output.pkl
            try:
                if use_pickle and output is not None:
                    with open(output_pkl, "wb") as f:
                        if error_occurred:
                            pickle.dump(error_info, f)
                        elif isinstance(output, Exception):
                            pickle.dump(output, f)
                        else:
                            pickle.dump(output.model_dump(mode="json"), f)

            except Exception as e:
                # If writing output.pkl fails, try to write a minimal error
                try:
                    with open(output_pkl, "wb") as f:
                        pickle.dump(
                            ApplicationException(
                                type_=str(type(e)),
                                message=f"Failed to write output pickle: {str(e)}",
                                traceback=traceback.format_exc(),
                            ),
                            f,
                        )
                except Exception:
                    pass  # Last resort: do nothing if even this fails

            # 4. Raise if error or return result
            if isinstance(output, Exception):
                raise output

            return output

        return wrapper

    return decorator
