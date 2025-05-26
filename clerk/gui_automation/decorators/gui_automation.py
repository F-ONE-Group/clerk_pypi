import asyncio
import functools
import os
from typing import Callable, Union

from websockets.asyncio.client import connect, ClientConnection
from websockets.protocol import State

from clerk import Clerk
from clerk.models.remote_device import RemoteDevice
from clerk.decorator.models import ClerkCodePayload
from ..exceptions.websocket import WebSocketConnectionFailed


# Global handle to the live connection (if any)
global_ws: Union[ClientConnection, None] = None

clerk_client = Clerk()
wss_uri = "wss://agent-manager.f-one.group/action"


def _allocate_remote_device(clerk_client: Clerk, group_name: str) -> RemoteDevice:
    remote_device = clerk_client.allocate_remote_device(organization_id=group_name)
    os.environ["REMOTE_DEVICE_ID"] = remote_device.id
    os.environ["REMOTE_DEVICE_NAME"] = remote_device.name
    return remote_device


def _deallocate_target(clerk_client: Clerk, group_name: str, remote_device_id: str):
    clerk_client.deallocate_remote_device(
        organization_id=group_name, remote_device_id=remote_device_id
    )
    os.environ.pop("REMOTE_DEVICE_ID", None)
    os.environ.pop("REMOTE_DEVICE_NAME", None)


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
        return await connect(uri, max_size=2**23, ping_timeout=3600)  # UPDATED

    async def close_ws_connection(ws_conn: ClientConnection):
        await ws_conn.close()

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(payload: ClerkCodePayload, *args, **kwargs):
            global global_ws
            os.environ["PROC_ID"] = payload.instance_id

            remote_device = _allocate_remote_device(clerk_client, group_name)

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

                if global_ws and global_ws.state is State.OPEN:  # UPDATED
                    print("WebSocket connection established.")
                    func_ret = func(payload, *args, **kwargs)
                else:
                    global_ws = None
                    raise WebSocketConnectionFailed()

            except Exception:
                raise  # unchanged
            finally:
                os.environ.pop("PROC_ID", None)
                _deallocate_target(clerk_client, group_name, remote_device.id)

                if global_ws and global_ws.state is State.OPEN:  # UPDATED
                    close_task = event_loop.create_task(close_ws_connection(global_ws))
                    event_loop.run_until_complete(close_task)
                    print("WebSocket connection closed.")

                event_loop.run_until_complete(event_loop.shutdown_asyncgens())
                event_loop.close()

            return func_ret

        return wrapper

    return decorator
