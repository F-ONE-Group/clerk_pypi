from typing import Any, Dict, List, Literal

from clerk.base import BaseClerk
from clerk.models.document import Document, UploadDocumentRequest
from .models.file import ParsedFile, UploadFile


class Clerk(BaseClerk):

    def upload_document(self, request: UploadDocumentRequest) -> Document:
        endpoint = "/document"
        res = self.post_request(
            endpoint=endpoint, data=request.data, files=request.files_
        )
        return Document(**res.data[0])

    def update_document_structured_data(
        self, document_id: str, updated_structured_data: Dict[str, Any]
    ) -> Document:
        endpoint = f"/document/{document_id}"
        payload = dict(structured_data=updated_structured_data)
        res = self.put_request(endpoint, json=payload)

        return Document(**res.data[0])

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
        files_data = [f.to_multipart_format() for f in files]
        self.post_request(endpoint, params=params, files=files_data)
