import base64
import json
from datetime import datetime
from typing import Dict

import pytest

from clerk.models.document import Document, GetDocumentsRequest, UploadDocumentRequest
from clerk.models.document_statuses import DocumentStatuses
from clerk.models.file import ParsedFile


def make_document(**overrides: Dict[str, object]) -> Document:
    base = dict(
        id="doc-1",
        project_id="proj-1",
        title="Title",
        upload_date=datetime.utcnow(),
        status=DocumentStatuses.SUBMITTED,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    base.update(overrides)
    return Document(**base)


def test_upload_document_request_files_handles_paths(tmp_path):
    file_path = tmp_path / "doc.txt"
    file_path.write_text("hello")
    request = UploadDocumentRequest(workflow_id="proj-1", files=[str(file_path)])

    files = request.files_

    assert files[0][0] == "files"
    assert files[0][1][0] == "doc.txt"
    assert files[0][1][2] == "text/plain"


def test_upload_document_request_files_handles_parsed_file():
    content = base64.b64encode(b"hello").decode()
    parsed = ParsedFile(name="doc.txt", content=content, mimetype="text/plain")
    request = UploadDocumentRequest(workflow_id="proj-1", files=[parsed])

    files = request.files_

    assert files[0][1][0] == "doc.txt"
    assert files[0][1][1] == b"hello"


def test_upload_document_request_invalid_path_raises(tmp_path):
    request = UploadDocumentRequest(
        workflow_id="proj-1", files=[str(tmp_path / "missing.txt")]
    )

    with pytest.raises(FileExistsError):
        _ = request.files_


def test_upload_document_request_data_serializes_structured_data():
    request = UploadDocumentRequest(
        workflow_id="proj-1", input_structured_data={"a": 1}
    )
    payload = request.data

    assert json.loads(payload["input_structured_data"]) == {"a": 1}


def test_upload_document_request_invalid_structured_data():
    request = UploadDocumentRequest(
        workflow_id="proj-1", input_structured_data={"bad": {1, 2, 3}}
    )

    with pytest.raises(ValueError):
        _ = request.data


def test_document_model_parses_payload():
    doc = make_document(structured_data={"key": "value"})
    assert doc.structured_data == {"key": "value"}


def test_get_documents_request_defaults():
    request = GetDocumentsRequest()
    assert request.limit == 50
    assert request.project_id is None
