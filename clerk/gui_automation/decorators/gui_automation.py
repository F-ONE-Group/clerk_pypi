import asyncio
import functools
import os
from typing import Callable, Union

from websockets.asyncio.client import connect, ClientConnection
from websockets.protocol import State

from clerk.gui_automation.client import RPAClerk
from clerk.models.remote_device import RemoteDevice
from clerk.decorator.models import ClerkCodePayload
from ..exceptions.websocket import WebSocketConnectionFailed


# Global handle to the live connection (if any)
global_ws: Union[ClientConnection, None] = None

clerk_client = RPAClerk()
wss_uri = "wss://agent-manager.f-one.group/action"


def _allocate_remote_device(
    clerk_client: RPAClerk, group_name: str, run_id: str
) -> RemoteDevice:
    remote_device = clerk_client.allocate_remote_device(
        group_name=group_name, run_id=run_id
    )
    return remote_device


def _deallocate_target(
    clerk_client: RPAClerk, remote_device: RemoteDevice, run_id: str
):
    clerk_client.deallocate_remote_device(remote_device=remote_device, run_id=run_id)


def gui_automation(group_name: str):
    """
    Decorator that:
      • Allocates a remote device,
      • Opens a WebSocket to the agent manager,
      • Passes control to the wrapped function,
      • Cleans everything up afterwards.
    """

    async def connect_to_ws(uri: str) -> ClientConnection:
        # Same knobs as before, just via the new connect()
        return await connect(uri, max_size=2**23, ping_timeout=3600)

    async def close_ws_connection(ws_conn: ClientConnection):
        await ws_conn.close()

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(payload: ClerkCodePayload, *args, **kwargs):
            global global_ws
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
                    print("WebSocket connection established.")
                    func_ret = func(payload, *args, **kwargs)
                else:
                    global_ws = None
                    raise WebSocketConnectionFailed()

            except Exception:
                raise  # unchanged
            finally:
                _deallocate_target(clerk_client, remote_device, payload.run_id)

                if global_ws and global_ws.state is State.OPEN:
                    close_task = event_loop.create_task(close_ws_connection(global_ws))
                    event_loop.run_until_complete(close_task)
                    print("WebSocket connection closed.")

                event_loop.run_until_complete(event_loop.shutdown_asyncgens())
                event_loop.close()

            return func_ret

        return wrapper

    return decorator
