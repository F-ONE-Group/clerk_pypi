from typing import List, Literal
from xml.dom.minidom import Document

from clerk.base import BaseClerk
from .models.file import ParsedFile, UploadFile


class Clerk(BaseClerk):
    def get_document(self, document_id: str) -> Document:
        endpoint = f"/document/{document_id}"
        res = self.get_request(endpoint=endpoint)
        return Document(**res.data[0])

    def get_files_document(self, document_id: str) -> List[ParsedFile]:
        endpoint = f"/document/{document_id}/files"
        res = self.get_request(endpoint=endpoint)
        return [ParsedFile(**d) for d in res.data]

    def add_files_to_document(
        self,
        document_id: str,
        type: Literal["input", "output"],
        files: List[UploadFile],
    ):
        endpoint = f"/document/{document_id}/files/upload"
        params = {"type": type}
        files_data = []
        files_data.append(f.to_multipart_format() for f in files)
        self.post_request(endpoint, params=params)
