import pickle
from pathlib import Path

import pytest

from clerk.decorator.models import ClerkCodePayload, Document, File
from clerk.decorator.task_decorator import clerk_code
from clerk.exceptions.exceptions import ApplicationException


def make_payload() -> ClerkCodePayload:
    return ClerkCodePayload(
        document=Document(id="doc", files=[File(name="f", url="u")]),
        structured_data={"key": "value"},
        run_id="run-1",
    )


def test_clerk_code_returns_function_result(monkeypatch):
    payload = make_payload()

    @clerk_code()
    def handler(data: ClerkCodePayload) -> ClerkCodePayload:
        assert data == payload
        return data

    assert handler(payload) == payload


def test_clerk_code_reads_and_writes_pickles(tmp_path, monkeypatch):
    payload = make_payload()
    input_path = tmp_path / "input.pkl"
    output_path = tmp_path / "output.pkl"
    with input_path.open("wb") as fh:
        pickle.dump(payload.model_dump(mode="json"), fh)

    from clerk.decorator import task_decorator as module

    monkeypatch.setattr(module, "input_pkl", str(input_path))
    monkeypatch.setattr(module, "output_pkl", str(output_path))

    @module.clerk_code()
    def handler(data: ClerkCodePayload) -> ClerkCodePayload:
        return data

    result = handler()

    assert result == payload
    with output_path.open("rb") as fh:
        dumped = pickle.load(fh)
    assert dumped == payload.model_dump(mode="json")


def test_clerk_code_writes_exception_to_output(tmp_path, monkeypatch):
    payload = make_payload()
    input_path = tmp_path / "input.pkl"
    output_path = tmp_path / "output.pkl"
    with input_path.open("wb") as fh:
        pickle.dump(payload.model_dump(mode="json"), fh)

    from clerk.decorator import task_decorator as module

    monkeypatch.setattr(module, "input_pkl", str(input_path))
    monkeypatch.setattr(module, "output_pkl", str(output_path))

    @module.clerk_code()
    def handler(data: ClerkCodePayload) -> ClerkCodePayload:
        raise RuntimeError("boom")

    with pytest.raises(ApplicationException):
        handler()

    with output_path.open("rb") as fh:
        dumped = pickle.load(fh)
    assert isinstance(dumped, ApplicationException)
    assert "boom" in dumped.message
