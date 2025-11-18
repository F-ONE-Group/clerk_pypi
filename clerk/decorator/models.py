from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class File(BaseModel):
    name: str
    url: str


class Document(BaseModel):
    id: str
    message_subject: Optional[str] = None
    message_content: Optional[str] = None
    files: List[File] = []
    upload_date: datetime | None = None  # TODO: make mandatory after 24.11.2025


class ClerkCodePayload(BaseModel):
    document: Document
    structured_data: Dict[str, Any]
    run_id: Optional[str] = None
