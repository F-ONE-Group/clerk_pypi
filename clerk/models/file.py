import base64
from typing import Optional
from pydantic import BaseModel


class ParsedFile(BaseModel):
    name: str
    mimetype: Optional[str] = None
    content: str

    def decode_content(self) -> bytes:
        return base64.b64decode(self.content.encode("utf-8"))
