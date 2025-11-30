import asyncio
import functools
import os
import time
from typing import Any, Callable, Dict, Sequence, Union

from websockets.asyncio.client import connect, ClientConnection
from websockets.protocol import State

from clerk.gui_automation.client import RPAClerk
from clerk.gui_automation.exceptions.agent_manager import (
    ClientAvailabilityTimeout,
    NoClientsAvailable,
)
from clerk.models.remote_device import RemoteDevice
from clerk.decorator.models import ClerkCodePayload
from clerk.utils import logger
from ..exceptions.websocket import WebSocketConnectionFailed


# Global handle to the live connection (if any)
global_ws: Union[ClientConnection, None] = None

clerk_client = RPAClerk()
wss_uri = "wss://agent-manager.f-one.group/action"


async def connect_to_ws(uri: str) -> ClientConnection:
    # Same knobs as before, just via the new connect()
    return await connect(uri, max_size=2**23, ping_timeout=3600)


async def close_ws_connection(ws_conn: ClientConnection):
    await ws_conn.close()


async def reconnect_ws():
    global global_ws

    remote_device_name = os.getenv("REMOTE_DEVICE_NAME")
    if not remote_device_name:
        raise RuntimeError(
            "REMOTE_DEVICE_NAME environmental variable is required for reconnecting WebSocket."
        )
    wss_token = clerk_client.get_wss_token()
    uri = f"{wss_uri}/{remote_device_name}/publisher?token={wss_token}"
    global_ws = await connect_to_ws(uri)


def gui_automation():
    """
    Decorator that:
      • Allocates a remote device,
      • Opens a WebSocket to the agent manager,
      • Passes control to the wrapped function,
      • Cleans everything up afterwards.
    """
    remote_device_name: str | None = os.getenv("REMOTE_DEVICE_NAME")

    if not remote_device_name:
        raise ValueError("REMOTE_DEVICE_NAME environmental variable is required.")

    wss_token = clerk_client.get_wss_token()

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(
            payload: ClerkCodePayload, *args: Sequence[Any], **kwargs: Dict[str, Any]
        ):
            global global_ws

            os.environ["_document_id"] = payload.document.id
            os.environ["_run_id"] = payload.run_id or ""

            # Create a dedicated loop for the WebSocket work
            event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(event_loop)

            try:
                task = event_loop.create_task(
                    connect_to_ws(
                        f"{wss_uri}/{remote_device_name}/publisher"
                        f"?token={wss_token}"
                    )
                )
                global_ws = event_loop.run_until_complete(task)

                if global_ws and global_ws.state is State.OPEN:
                    logger.debug("WebSocket connection established.")
                    func_ret = func(payload, *args, **kwargs)
                else:
                    global_ws = None
                    raise WebSocketConnectionFailed()

            except Exception:
                raise
            finally:
                os.environ.pop("_run_id", None)
                os.environ.pop("_document_id", None)

                if global_ws and global_ws.state is State.OPEN:
                    close_task = event_loop.create_task(close_ws_connection(global_ws))
                    event_loop.run_until_complete(close_task)
                    logger.debug("WebSocket connection closed.")

                event_loop.run_until_complete(event_loop.shutdown_asyncgens())
                event_loop.close()

            return func_ret

        return wrapper

    return decorator
