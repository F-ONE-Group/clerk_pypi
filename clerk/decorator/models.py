from typing import Dict, List, Optional
from pydantic import BaseModel


class File(BaseModel):
    name: str
    url: str


class Document(BaseModel):
    id: str
    message_subject: Optional[str] = None
    message_content: Optional[str] = None
    files: List[File] = []


class ClerkCodePayload(BaseModel):
    document: Document
    structured_data: Dict
