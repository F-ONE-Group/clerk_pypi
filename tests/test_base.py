import os
from typing import Any, Dict

import pytest
import requests

from clerk.base import BaseClerk, giveup_handler
from clerk.models.response_model import StandardResponse


class DummyResponse:
    def __init__(self, payload: Dict[str, Any], status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def json(self) -> Dict[str, Any]:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)  # type: ignore[arg-type]


def test_giveup_handler_returns_true_for_client_error():
    response = DummyResponse({}, status_code=400)
    error = requests.HTTPError(response=response)
    assert giveup_handler(error) is True


def test_giveup_handler_returns_false_for_server_error():
    response = DummyResponse({}, status_code=503)
    error = requests.HTTPError(response=response)
    assert giveup_handler(error) is False


def test_giveup_handler_returns_false_for_non_http_error():
    assert giveup_handler(ValueError("boom")) is False


def test_base_clerk_loads_api_key_from_environment(monkeypatch):
    monkeypatch.delenv("CLERK_API_KEY", raising=False)
    monkeypatch.setenv("CLERK_API_KEY", "secret-key")

    clerk = BaseClerk()

    assert clerk.api_key == "secret-key"
    assert clerk.headers == {"Authorization": "Bearer secret-key"}


def test_base_clerk_raises_when_no_api_key(monkeypatch):
    monkeypatch.delenv("CLERK_API_KEY", raising=False)

    with pytest.raises(ValueError):
        BaseClerk()


def test_get_request_merges_headers_and_builds_url(monkeypatch):
    monkeypatch.setenv("CLERK_API_KEY", "key")
    called: Dict[str, Any] = {}

    def fake_get(url: str, headers: Dict[str, str], json: Dict[str, Any], params: Dict[str, Any]):
        called.update(url=url, headers=headers, json=json, params=params)
        return DummyResponse({"success": True, "data": [{"value": 1}]})

    monkeypatch.setattr("clerk.base.requests.get", fake_get)

    clerk = BaseClerk(root_endpoint="/v1")
    response = clerk.get_request("/test", headers={"X": "1"}, params={"foo": "bar"})

    assert called["url"] == f"{clerk.base_url}{clerk.root_endpoint}/test"
    assert called["headers"]["Authorization"] == "Bearer key"
    assert called["headers"]["X"] == "1"
    assert isinstance(response, StandardResponse)
    assert response.data == [{"value": 1}]


def test_post_request_sends_payload(monkeypatch, tmp_path):
    monkeypatch.setenv("CLERK_API_KEY", "key")
    called: Dict[str, Any] = {}
    file_path = tmp_path / "sample.bin"
    file_path.write_bytes(b"data")
    files_payload = [("files", ("sample.bin", b"data", "application/octet-stream"))]

    def fake_post(
        url: str,
        headers: Dict[str, str],
        json: Dict[str, Any],
        params: Dict[str, Any],
        data: Dict[str, Any] | None,
        files: Any,
    ):
        called.update(
            url=url,
            headers=headers,
            json=json,
            params=params,
            data=data,
            files=files,
        )
        return DummyResponse({"success": True, "data": [{"value": 2}]})

    monkeypatch.setattr("clerk.base.requests.post", fake_post)

    clerk = BaseClerk()
    response = clerk.post_request(
        "/upload",
        json={"hello": "world"},
        params={"page": 1},
        data={"form": "value"},
        files=files_payload,
    )

    assert called["url"] == f"{clerk.base_url}/upload"
    assert called["json"] == {"hello": "world"}
    assert called["params"] == {"page": 1}
    assert called["data"] == {"form": "value"}
    assert called["files"] == files_payload
    assert response.data == [{"value": 2}]


def test_put_request_sends_payload(monkeypatch):
    monkeypatch.setenv("CLERK_API_KEY", "key")
    called: Dict[str, Any] = {}

    def fake_put(
        url: str,
        headers: Dict[str, str],
        json: Dict[str, Any],
        params: Dict[str, Any],
        data: Dict[str, Any] | None,
        files: Any,
    ):
        called.update(
            url=url,
            headers=headers,
            json=json,
            params=params,
            data=data,
            files=files,
        )
        return DummyResponse({"success": True, "data": [{"value": 3}]})

    monkeypatch.setattr("clerk.base.requests.put", fake_put)

    clerk = BaseClerk(root_endpoint="/api")
    response = clerk.put_request(
        "/update",
        json={"hello": "world"},
        params={"page": 1},
        data={"form": "value"},
    )

    assert called["url"] == f"{clerk.base_url}{clerk.root_endpoint}/update"
    assert response.data == [{"value": 3}]
