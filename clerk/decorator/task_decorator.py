import json
from prefect import flow
from functools import wraps
from prefect.states import Completed


def clerk_code(**custom_kwargs):
    def wrapper(func):
        @wraps(func)
        @flow(**custom_kwargs)
        def wrapped_flow(payload):

            result = func(payload)

            return Completed(message=json.dumps(result), data=result)

        return wrapped_flow

    return wrapper