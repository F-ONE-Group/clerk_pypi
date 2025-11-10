import os

import pytest

from clerk.utils import logger
from clerk.utils.save_artifact import save_artifact


def test_logger_writes_log_file(monkeypatch, tmp_path):
    monkeypatch.setenv("_artifacts_folder", "session")
    monkeypatch.setattr(logger, "base_path", str(tmp_path))

    logger.debug("hello world")

    log_file = tmp_path / "session" / "logs.txt"
    assert log_file.exists()
    contents = log_file.read_text()
    assert "hello world" in contents


def test_save_artifact_persists_file(monkeypatch, tmp_path):
    monkeypatch.setenv("_artifacts_folder", "session")
    monkeypatch.setattr(os, "getcwd", lambda: str(tmp_path))

    path = save_artifact("file.txt", b"payload", subfolder="logs")

    assert path.endswith(os.path.join("data", "artifacts", "session", "logs", "file.txt"))
    with open(path, "rb") as fh:
        assert fh.read() == b"payload"
