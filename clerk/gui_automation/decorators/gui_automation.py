import asyncio
import functools
import os
import time
from typing import Callable, Union

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

REMOTE_DEVICE_ALLOCATION_TIMEOUT = int(
    os.getenv("REMOTE_DEVICE_ALLOCATION_TIMEOUT", 60)
)
REMOTE_DEVICE_ALLOCATION_MAX_TRIES = int(
    os.getenv("REMOTE_DEVICE_ALLOCATION_MAX_TRIES", 60)
)


def _allocate_remote_device(
    clerk_client: RPAClerk, group_name: str, run_id: str
) -> RemoteDevice:
    remote_device = None
    retries = 0

    while True:
        try:
            remote_device = clerk_client.allocate_remote_device(
                group_name=group_name, run_id=run_id
            )
            os.environ["REMOTE_DEVICE_ID"] = remote_device.id
            os.environ["REMOTE_DEVICE_NAME"] = remote_device.name
            logger.debug(f"Remote device allocated: {remote_device.name}")
            return remote_device

        except NoClientsAvailable:
            logger.warning(
                f"No clients are available for {group_name} group. Initiating a {REMOTE_DEVICE_ALLOCATION_TIMEOUT} seconds wait. Retry count: {retries}"
            )
            if retries >= REMOTE_DEVICE_ALLOCATION_MAX_TRIES:
                raise ClientAvailabilityTimeout(
                    f"No clients available for {group_name} group after {REMOTE_DEVICE_ALLOCATION_TIMEOUT * REMOTE_DEVICE_ALLOCATION_MAX_TRIES} seconds"
                )
            time.sleep(REMOTE_DEVICE_ALLOCATION_TIMEOUT)
            retries += 1


def _deallocate_target(
    clerk_client: RPAClerk, remote_device: RemoteDevice, run_id: str
):
    clerk_client.deallocate_remote_device(remote_device=remote_device, run_id=run_id)
    logger.debug("Remote device deallocated")
    os.environ.pop("REMOTE_DEVICE_ID", None)
    os.environ.pop("REMOTE_DEVICE_NAME", None)


def gui_automation(
    reserve_client: bool = False,
):
    """
    Decorator that:
      • Allocates a remote device,
      • Opens a WebSocket to the agent manager,
      • Passes control to the wrapped function,
      • Cleans everything up afterwards.
    """
    group_name: str = os.getenv("REMOTE_DEVICE_GROUP")
    if not group_name:
        raise ValueError("REMOTE_DEVICE_GROUP environmental variable is required.")

    async def connect_to_ws(uri: str) -> ClientConnection:
        # Same knobs as before, just via the new connect()
        return await connect(uri, max_size=2**23, ping_timeout=3600)

    async def close_ws_connection(ws_conn: ClientConnection):
        await ws_conn.close()

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(payload: ClerkCodePayload, *args, **kwargs):
            global global_ws
            force_deallocate = False
            os.environ["_document_id"] = payload.document.id
            os.environ["_run_id"] = payload.run_id

            remote_device = _allocate_remote_device(
                clerk_client, group_name, payload.run_id
            )

            # Create a dedicated loop for the WebSocket work
            event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(event_loop)

            try:
                task = event_loop.create_task(
                    connect_to_ws(
                        f"{wss_uri}/{remote_device.name}/publisher"
                        f"?token={remote_device.wss_token}"
                    )
                )
                global_ws = event_loop.run_until_complete(task)

                if global_ws and global_ws.state is State.OPEN:
                    logger.debug("WebSocket connection established.")
                    func_ret = func(payload, *args, **kwargs)
                else:
                    global_ws = None
                    raise WebSocketConnectionFailed()

            except Exception as e:
                force_deallocate = True
                raise
            finally:
                os.environ.pop("_run_id", None)
                os.environ.pop("_document_id", None)
                if not reserve_client or force_deallocate:
                    _deallocate_target(clerk_client, remote_device, payload.run_id)
                else:
                    logger.warning(
                        f"The client stayed reserved for the this run id: {payload.run_id}"
                    )

                if global_ws and global_ws.state is State.OPEN:
                    close_task = event_loop.create_task(close_ws_connection(global_ws))
                    event_loop.run_until_complete(close_task)
                    logger.debug("WebSocket connection closed.")

                event_loop.run_until_complete(event_loop.shutdown_asyncgens())
                event_loop.close()

            return func_ret

        return wrapper

    return decorator
