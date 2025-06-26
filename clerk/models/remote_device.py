from pydantic import BaseModel


class RemoteDevice(BaseModel):
    id: str
    name: str
    wss_token: str
