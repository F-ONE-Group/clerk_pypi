from typing import List
from xml.dom.minidom import Document

from clerk.base import BaseClerk
from .models.file import ParsedFile


class Clerk(BaseClerk):
    def get_document(self, document_id: str) -> Document:
        endpoint = f"/document/{document_id}"
        res = self.get_request(endpoint=endpoint)
        return Document(**res.data[0])

    def get_files_document(self, document_id: str) -> List[ParsedFile]:
        endpoint = f"/document/{document_id}/files"
        res = self.get_request(endpoint=endpoint)
        return [ParsedFile(**d) for d in res.data]
