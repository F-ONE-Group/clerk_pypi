from typing import Dict
from pydantic import BaseModel


class ClerkCodePayload(BaseModel):
    document_id: str
    instance_id: str
    data: Dict
