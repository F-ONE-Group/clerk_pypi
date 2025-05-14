import json
from typing import Dict
from prefect import flow
from functools import wraps
from prefect.states import Completed
from pydantic import BaseModel
from .models import ClerkCodePayload


def clerk_code():
    def wrapper(func):
        @wraps(func)
        @flow(persist_result=False, log_prints=True, result_serializer="json")
        def wrapped_flow(payload: Dict):
            payload = ClerkCodePayload(**payload)
            result = func(payload)
            if isinstance(result, BaseModel):
                result = result.model_dump()
            return Completed(message=json.dumps(result), data=result)

        return wrapped_flow

    return wrapper
