import asyncio
import json
import os
from typing import Any, Dict, Union

import pydantic
import requests


from .model import (
    ExecutePayload,
    DeleteFilesExecutePayload,
    ApplicationExecutePayload,
    SaveFilesExecutePayload,
    WindowExecutePayload,
    GetFileExecutePayload,
)
import backoff

from .model import PerformActionResponse, ActionStates
from .exception import PerformActionException, GetScreenError


async def _perform_action_ws(payload: Dict) -> PerformActionResponse:
    """Perform an action over a WebSocket connection.

    Args:
        payload (Dict): The payload request to be sent.

    Returns:
        PerformActionResponse: The response of performing the action.

    Raises:
        RuntimeError: If the ACK message is not received within the specified timeout.
    """

    from ..decorators.gui_automation import global_ws

    # 1. Send the payload request
    if global_ws:
        await global_ws.send(json.dumps(payload))

        # 2. wait for ack message
        try:
            ack = await asyncio.wait_for(global_ws.recv(), 90)
            if ack == "OK":
                action_info = await asyncio.wait_for(global_ws.recv(), 90)
                return PerformActionResponse(**json.loads(action_info))
            else:
                raise RuntimeError("Received ACK != OK")
        except asyncio.TimeoutError:
            raise RuntimeError("The ack message did not arrive.")
    else:
        raise RuntimeError("The Websocket has not been initiated.")


async def _get_screen_async() -> str:
    """
    Asynchronously retrieves a screen using a WebSocket connection.

    Returns:
        str: The base64 encoded screen image.

    Note:
        This function sends a request to perform a screenshot action over a WebSocket connection
        and returns the base64 encoded image of the screen captured.
    """
    payload = {
        "proc_inst_id": os.getenv("_run_id"),
        "client_name": os.getenv("REMOTE_DEVICE_NAME"),
        "headless": True,
        "action": {"action_type": "screenshot"},
    }
    try:
        action_info = await _perform_action_ws(payload)
    except Exception as e:
        if str(e) in (
            "The ack message did not arrive.",
            "Received ACK != OK",
        ):
            raise GetScreenError("The ack message did not arrive.")
        raise  # else raise the error

    if action_info.screen_b64 is not None:
        return action_info.screen_b64
    raise GetScreenError()


@backoff.on_exception(
    backoff.expo,
    (requests.RequestException, pydantic.ValidationError, GetScreenError),
    max_time=120,
)
def get_screen() -> str:
    """
    Request the VDI screen and return the base64 representation of the screenshot.

    Returns:
        str: The base64 representation of the screenshot.

    Raises:
        RuntimeError: If the request to the VDI screen fails.
    """

    loop = asyncio.get_event_loop()
    # asyncio.set_event_loop(loop)
    task = loop.create_task(_get_screen_async())
    res = loop.run_until_complete(task)
    return res


async def _perform_action_async(
    payload: Union[
        ExecutePayload,
        ApplicationExecutePayload,
        WindowExecutePayload,
        SaveFilesExecutePayload,
        DeleteFilesExecutePayload,
        GetFileExecutePayload,
    ],
) -> Any:
    """
    Perform an asynchronous action based on the provided payload.

    Args:
        payload (Union[ExecutePayload, ApplicationExecutePayload, WindowExecutePayload, SaveFilesExecutePayload, DeleteFilesExecutePayload, GetFileExecutePayload]): The payload containing information about the action to be performed.

    Returns:
        Any: The return value of the action.

    Raises:
        PerformActionException: If the action fails with an error message.
    """
    req_payload: Dict = {
        "proc_inst_id": os.getenv("_run_id"),
        "client_name": os.getenv("REMOTE_DEVICE_NAME"),
        "headless": (
            True if os.getenv("HEADLESS", "True").lower() == "true" else False
        ),
        "action": payload.model_dump(),
    }
    action_info = await _perform_action_ws(req_payload)

    if action_info.state == ActionStates.failed:
        raise PerformActionException(action_info.message)
    return action_info.return_value


def perform_action(
    payload: Union[
        ExecutePayload,
        ApplicationExecutePayload,
        WindowExecutePayload,
        SaveFilesExecutePayload,
        DeleteFilesExecutePayload,
        GetFileExecutePayload,
    ],
) -> Any:
    """
    Perform an action on the VDI client.

    Args:
        payload (Union[ExecutePayload, ApplicationExecutePayload, WindowExecutePayload]): The payload containing the details of the action to be performed.

    Raises:
        PerformActionException: If the action fails.
        RuntimeError: If the request to perform the action fails.

    Returns:
        Any
    """

    loop = asyncio.get_event_loop()
    task = loop.create_task(_perform_action_async(payload))
    res = loop.run_until_complete(task)
    return res
