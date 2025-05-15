import os

# import logging
import requests
import backoff
from typing import Dict, List, Optional, Self
from xml.dom.minidom import Document


from pydantic import BaseModel, model_validator, Field

from .models.file import ParsedFile
from .models.response_model import StandardResponse


# logger = logging.getLogger(__name__)
# logger.setLevel(logging.INFO)

# if not logger.handlers:
#     handler = logging.StreamHandler()
#     formatter = logging.Formatter("[%(levelname)s] %(asctime)s - %(message)s")
#     handler.setFormatter(formatter)
#     logger.addHandler(handler)


# def backoff_handler(details):
#     logger.warning(
#         f"Retrying {details['target'].__name__} after {details['tries']} tries..."
#     )


def giveup_handler(e):
    return (
        isinstance(e, requests.exceptions.HTTPError)
        and e.response is not None
        and e.response.status_code < 500
    )


class Clerk(BaseModel):
    api_key: Optional[str] = Field(default=None, min_length=1)
    headers: Dict[str, str] = Field(default_factory=dict)
    base_url: str = Field(
        default_factory=lambda: os.getenv("CLERK_BASE_URL", "https://api.clerk-app.com")
    )

    @model_validator(mode="after")
    def validate_api_key(self) -> Self:
        if not self.api_key:
            self.api_key = os.getenv("CLERK_API_KEY")

        if not self.api_key:
            raise ValueError("API key has not been provided.")

        self.headers = {"Authorization": f"Bearer {self.api_key}"}
        return self

    @backoff.on_exception(
        backoff.expo,
        (requests.exceptions.RequestException,),
        max_tries=3,
        jitter=None,
        # on_backoff=backoff_handler,
        giveup=giveup_handler,
    )
    def get_request(
        self,
        endpoint: str,
        headers: Dict[str, str] = {},
        json: Dict = {},
        params: Dict = {},
    ) -> StandardResponse:

        merged_headers = {**self.headers, **headers}
        url = f"{self.base_url}{endpoint}"

        # logger.info(f"GET {url} | params={params}")

        response = requests.get(url, headers=merged_headers, json=json, params=params)
        response.raise_for_status()

        return StandardResponse(**response.json())

    @backoff.on_exception(
        backoff.expo,
        (requests.exceptions.RequestException,),
        max_tries=3,
        jitter=None,
        # on_backoff=backoff_handler,
        giveup=giveup_handler,
    )
    def post_request(
        self,
        endpoint: str,
        headers: Dict[str, str] = {},
        json: Dict = {},
        params: Dict = {},
    ) -> StandardResponse:

        merged_headers = {**self.headers, **headers}
        url = f"{self.base_url}{endpoint}"

        # logger.info(f"POST {url} | body={json} | params={params}")

        response = requests.post(url, headers=merged_headers, json=json, params=params)
        response.raise_for_status()

        return StandardResponse(**response.json())

    def get_document(self, document_id: str) -> Document:
        endpoint = f"/document/{document_id}"
        res = self.get_request(endpoint=endpoint)
        return Document(**res.data[0])

    def get_files_document(self, document_id: str) -> List[ParsedFile]:
        endpoint = f"/document/{document_id}/files"
        res = self.get_request(endpoint=endpoint)
        return [ParsedFile(**d) for d in res.data]
