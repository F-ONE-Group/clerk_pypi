import os

import requests
import backoff
from typing import Any, Dict, List, Optional, Self, Tuple


from pydantic import BaseModel, model_validator, Field

from .models.response_model import StandardResponse


def giveup_handler(e: Any):
    return (
        isinstance(e, requests.exceptions.HTTPError)
        and e.response is not None
        and e.response.status_code < 500
    )


class BaseClerk(BaseModel):
    api_key: Optional[str] = Field(default=None, min_length=1)
    headers: Dict[str, str] = Field(default_factory=dict)
    base_url: str = Field(
        default_factory=lambda: os.getenv("CLERK_BASE_URL", "https://api.clerk-app.com")
    )
    root_endpoint: Optional[str] = None

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
        giveup=giveup_handler,
    )
    def get_request(
        self,
        endpoint: str,
        headers: Dict[str, str] = {},
        json: Dict[str, Any] = {},
        params: Dict[str, Any] = {},
    ) -> StandardResponse[Any]:

        merged_headers = {**self.headers, **headers}
        url = f"{self.base_url}{endpoint}"
        if self.root_endpoint:
            url = f"{self.base_url}{self.root_endpoint}{endpoint}"

        # logger.info(f"GET {url} | params={params}")

        response = requests.get(url, headers=merged_headers, json=json, params=params)
        response.raise_for_status()

        return StandardResponse(**response.json())

    @backoff.on_exception(
        backoff.expo,
        Exception,
        max_tries=3,
        jitter=None,
        giveup=giveup_handler,
    )
    def post_request(
        self,
        endpoint: str,
        headers: Dict[str, str] = {},
        json: Dict[str, Any] = {},
        params: Dict[str, Any] = {},
        data: Dict[str, Any] | None = None,
        files: List[Tuple[str, Tuple[str, bytes, str | None]]] | None = None,
    ) -> StandardResponse[Dict[str, Any]]:

        merged_headers = {**self.headers, **headers}
        url = f"{self.base_url}{endpoint}"
        if self.root_endpoint:
            url = f"{self.base_url}{self.root_endpoint}{endpoint}"

        # logger.info(f"POST {url} | body={json} | params={params}")

        response = requests.post(
            url,
            headers=merged_headers,
            json=json,
            params=params,
            data=data,
            files=files,  # type: ignore
        )
        response.raise_for_status()

        return StandardResponse(**response.json())

    @backoff.on_exception(
        backoff.expo,
        (requests.exceptions.RequestException,),
        max_tries=3,
        jitter=None,
        giveup=giveup_handler,
    )
    def put_request(
        self,
        endpoint: str,
        headers: Dict[str, str] = {},
        json: Dict[str, Any] = {},
        params: Dict[str, Any] = {},
        data: Dict[str, Any] | None = None,
        files: List[Tuple[str, Tuple[str, bytes, str | None]]] | None = None,
    ) -> StandardResponse[Dict[str, Any]]:

        merged_headers = {**self.headers, **headers}
        url = f"{self.base_url}{endpoint}"
        if self.root_endpoint:
            url = f"{self.base_url}{self.root_endpoint}{endpoint}"

        # logger.info(f"POST {url} | body={json} | params={params}")

        response = requests.put(
            url,
            headers=merged_headers,
            json=json,
            params=params,
            data=data,
            files=files,  # type: ignore
        )
        response.raise_for_status()

        return StandardResponse(**response.json())
