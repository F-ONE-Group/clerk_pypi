import base64
from typing import Optional, Tuple
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


class UploadFile(BaseModel):
    name: str
    mimetype: str | None
    content: bytes

    def to_multipart_format(
        self, key: str = "files"
    ) -> Tuple[str, Tuple[str, bytes, str | None]]:
        return (key, (self.name, self.content, self.mimetype))
