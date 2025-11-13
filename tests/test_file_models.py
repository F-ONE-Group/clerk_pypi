import base64

import pytest

from clerk.models.file import ParsedFile, UploadFile


def test_parsed_file_decoded_content():
    content = base64.b64encode(b"content").decode()
    parsed = ParsedFile(name="file.txt", content=content)
    assert parsed.decoded_content == b"content"


def test_parsed_file_invalid_base64():
    parsed = ParsedFile(name="file.txt", content="!notbase64!")
    with pytest.raises(ValueError):
        _ = parsed.decoded_content


def test_upload_file_to_multipart_format():
    upload = UploadFile(name="file.txt", mimetype="text/plain", content=b"abc")
    key, (name, content, mimetype) = upload.to_multipart_format()
    assert key == "files"
    assert name == "file.txt"
    assert content == b"abc"
    assert mimetype == "text/plain"
