import os
from typing import Dict, List, Optional, Self
from xml.dom.minidom import Document
from pydantic import BaseModel, model_validator, Field
import requests

from clerk.models.file import ParsedFile
from clerk.models.response_model import StandardResponse


base_url = "https://api.clerk-app.com"


class Clerk(BaseModel):
    api_key: Optional[str] = None
    headers: Dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_api_key(self) -> Self:
        if not self.api_key:
            # get the api key from the environment
            self.api_key = os.getenv("CLERK_API_KEY")

        if not self.api_key:
            raise ValueError("Api key has not been provided.")

        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    def get_request(
        self, endpoint, headers: Dict = {}, json: Dict = {}, params: Dict = {}
    ) -> StandardResponse:

        res = requests.get(
            url=f"{base_url}{endpoint}",
            headers=self.headers.update(headers),
            json=json,
            params=params,
        )
        res.raise_for_status

        return StandardResponse(**res.json())

    def post_request(
        self, endpoint, headers: Dict = {}, json: Dict = {}, params: Dict = {}
    ) -> StandardResponse:
        res = requests.post(
            url=f"{base_url}{endpoint}",
            headers=self.headers.update(headers),
            json=json,
            params=params,
        )
        res.raise_for_status
        return StandardResponse(**res.json())

    def get_document(self, document_id: str) -> Document:
        endpoint = f"/document/{document_id}"
        res = self.get_request(endpoint=endpoint)

        return Document(**res.data[0])

    def get_files_document(self, document_id: str) -> List[ParsedFile]:
        endpoint = f"/document/{document_id}/files"
        res = self.get_request(endpoint=endpoint)

        return [ParsedFile(**d) for d in res.data]
