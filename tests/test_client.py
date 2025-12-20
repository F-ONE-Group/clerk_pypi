from datetime import datetime
from typing import Any, Dict, List

import pytest

from clerk.client import Clerk
from clerk.models.document import (
    Document,
    DocumentStatuses,
    GetDocumentsRequest,
    UploadDocumentRequest,
)
from clerk.models.file import ParsedFile, UploadFile
from clerk.models.response_model import StandardResponse


def make_document_payload(**overrides: Any) -> Dict[str, Any]:
    base = dict(
        id="doc-1",
        project_id="proj-1",
        title="A document",
        upload_date=datetime.utcnow().isoformat(),
        requestor=None,
        message_subject=None,
        message_content=None,
        message_html=None,
        structured_data=None,
        status=DocumentStatuses.SUBMITTED.value,
        created_at=datetime.utcnow().isoformat(),
        updated_at=datetime.utcnow().isoformat(),
    )
    base.update(overrides)
    return base


def test_upload_document_calls_post(monkeypatch):
    clerk = Clerk(api_key="token")
    parsed_file = ParsedFile(
        name="file.txt",
        content="ZmFrZQ==",
        mimetype="text/plain",
    )
    request = UploadDocumentRequest(workflow_id="proj-1", files=[parsed_file])

    captured: Dict[str, Any] = {}

    def fake_post(self: Clerk, endpoint: str, data: Dict[str, Any], files: List[Any]):
        captured.update(endpoint=endpoint, data=data, files=files)
        return StandardResponse(data=[make_document_payload(id="doc-2")], success=True)

    monkeypatch.setattr(Clerk, "post_request", fake_post)

    document = clerk.upload_document(request)

    assert captured["endpoint"] == "/document"
    assert captured["files"][0][0] == "files"
    assert document.id == "doc-2"


def test_update_document_structured_data(monkeypatch):
    clerk = Clerk(api_key="token")
    captured: Dict[str, Any] = {}

    def fake_put(self: Clerk, endpoint: str, json: Dict[str, Any]):
        captured.update(endpoint=endpoint, json=json)
        return StandardResponse(
            data=[make_document_payload(id="doc-3", structured_data={"a": 1})]
        )

    monkeypatch.setattr(Clerk, "put_request", fake_put)

    document = clerk.update_document_structured_data("doc-3", {"a": 1})

    assert captured["endpoint"] == "/document/doc-3"
    assert captured["json"] == {"structured_data": {"a": 1}}
    assert document.structured_data == {"a": 1}


def test_get_document(monkeypatch):
    clerk = Clerk(api_key="token")

    def fake_get(self: Clerk, endpoint: str):
        return StandardResponse(data=[make_document_payload(id="doc-4")])

    monkeypatch.setattr(Clerk, "get_request", fake_get)

    document = clerk.get_document("doc-4")

    assert document.id == "doc-4"


def test_get_documents_requires_filters():
    clerk = Clerk(api_key="token")
    request = GetDocumentsRequest()

    with pytest.raises(ValueError):
        clerk.get_documents(request)


def test_get_documents_calls_get(monkeypatch):
    clerk = Clerk(api_key="token")
    request = GetDocumentsRequest(project_id="proj-1")
    captured: Dict[str, Any] = {}

    def fake_get(self: Clerk, endpoint: str, params: Dict[str, Any]):
        captured.update(endpoint=endpoint, params=params)
        return StandardResponse(
            data=[make_document_payload(id="doc-5"), make_document_payload(id="doc-6")]
        )

    monkeypatch.setattr(Clerk, "get_request", fake_get)

    documents = clerk.get_documents(request)

    assert captured["endpoint"] == "/documents"
    assert captured["params"]["project_id"] == "proj-1"
    assert [doc.id for doc in documents] == ["doc-5", "doc-6"]


def test_get_files_document(monkeypatch):
    clerk = Clerk(api_key="token")

    def fake_get(self: Clerk, endpoint: str):
        return StandardResponse(
            data=[
                {"name": "file.txt", "mimetype": "text/plain", "content": "ZmFrZQ=="},
            ]
        )

    monkeypatch.setattr(Clerk, "get_request", fake_get)

    files = clerk.get_files_document("doc-1")

    assert files[0].name == "file.txt"


def test_add_files_to_document(monkeypatch):
    clerk = Clerk(api_key="token")
    upload_files = [UploadFile(name="new.txt", mimetype="text/plain", content=b"abc")]
    captured: Dict[str, Any] = {}

    def fake_post(self: Clerk, endpoint: str, params: Dict[str, Any], files: List[Any]):
        captured.update(endpoint=endpoint, params=params, files=files)
        return StandardResponse(data=[make_document_payload()])

    monkeypatch.setattr(Clerk, "post_request", fake_post)

    clerk.add_files_to_document("doc-1", "input", upload_files)

    assert captured["endpoint"] == "/document/doc-1/files/upload"
    assert captured["params"] == {"type": "input"}
    assert captured["files"][0][0] == "files"


def test_cancel_document_run(monkeypatch):
    clerk = Clerk(api_key="token")
    captured: Dict[str, Any] = {}

    def fake_post(self: Clerk, endpoint: str):
        captured.update(endpoint=endpoint)
        return StandardResponse(data=[make_document_payload(id="doc-7")])

    monkeypatch.setattr(Clerk, "post_request", fake_post)

    document = clerk.cancel_document_run("doc-7")

    assert captured["endpoint"] == "/document/doc-7/cancel"
    assert document.id == "doc-7"
