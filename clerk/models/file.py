import base64
from typing import Optional
from pydantic import BaseModel, Field


class ParsedFile(BaseModel):
    name: str
    mimetype: Optional[str] = None
    content: str = Field(..., description="Base64-encoded file content")

    @property
    def decoded_content(self) -> bytes:
        try:
            return base64.b64decode(self.content.encode("utf-8"))
        except Exception as e:
            raise ValueError(f"Invalid base64 content: {e}")
