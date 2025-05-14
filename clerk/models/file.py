from typing import Optional
from pydantic import BaseModel


class ParsedFile(BaseModel):
    name: str
    mimetype: Optional[str] = None
    content: str
