import pickle

from clerk.exceptions.exceptions import ApplicationException


def test_application_exception_pickling_roundtrip():
    exc = ApplicationException(type_="Custom", message="failure", traceback="trace")
    data = pickle.dumps(exc)
    loaded = pickle.loads(data)

    assert isinstance(loaded, ApplicationException)
    assert loaded.type == "Custom"
    assert loaded.message == "failure"
    assert loaded.traceback == "trace"
