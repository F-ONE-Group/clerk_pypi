import base64
import os

os.environ.setdefault("CLERK_API_KEY", "test-key")

import pytest

from clerk.gui_automation.action_model.model import Coords, ImageB64, Screenshot
from clerk.gui_automation.client_actor.model import ExecutePayload
from clerk.gui_automation.ui_actions import actions
from clerk.gui_automation.ui_actions import base as base_actions
from clerk.gui_automation.ui_actions.support import (
    _format_action_string,
    maybe_engage_operator_ui_action,
    save_screenshot,
    strtobool,
    try_actions,
)
from clerk.gui_automation.ui_actions.actions import File, LeftClick
from clerk.gui_automation.exceptions.modality.exc import TargetModalityError


def test_to_full_img_path_with_image_b64(tmp_path, monkeypatch):
    monkeypatch.setattr(base_actions, "TARGET_IMAGES_PATH", str(tmp_path))
    image = ImageB64(value="encoded")

    assert base_actions.to_full_img_path(image) == ""


def test_to_full_img_path_with_string(tmp_path, monkeypatch):
    monkeypatch.setattr(base_actions, "TARGET_IMAGES_PATH", str(tmp_path))
    assert base_actions.to_full_img_path("icon.png") == os.path.join(
        str(tmp_path), "icon.png"
    )


def test_base_action_sets_target_name_for_text():
    action = base_actions.BaseAction(action_type="left_click", target="Submit")
    assert action.target_name == "Submit"
    assert action.target == "Submit"


def test_base_action_converts_path_target(monkeypatch, tmp_path):
    monkeypatch.setattr(base_actions, "TARGET_IMAGES_PATH", str(tmp_path))
    target_file = tmp_path / "button.png"
    target_file.write_bytes(b"png-bytes")

    action = base_actions.BaseAction(action_type="left_click", target="button.png")

    assert isinstance(action.target, ImageB64)
    assert action.target_name == "button.png"
    assert action.target.id == "button.png"


def test_base_action_handles_none_target():
    action = base_actions.BaseAction(action_type="left_click", target=None)
    assert action.target_name == "not_provided"


def test_base_action_invalid_target():
    action = base_actions.BaseAction.model_construct(
        action_type="left_click",
        target=object(),
    )

    with pytest.raises(TargetModalityError):
        action.validate_target_and_set_name()


def test_get_center_coords():
    action = base_actions.BaseAction(action_type="left_click", target=None)
    bbox = Coords(value=[0, 0, 10, 10])
    assert action._get_center_coords(bbox) == [5, 5]


def test_prepare_payload(monkeypatch):
    monkeypatch.setattr(base_actions, "get_screen", lambda: "c2NyZWVu")
    action = base_actions.BaseAction(action_type="left_click", target="Submit")

    payload = action._prepare_payload()

    assert isinstance(payload, Screenshot)
    assert payload.target == "Submit"
    assert payload.target_name == "Submit"
    assert payload.screen_b64.value == "c2NyZWVu"


def test_anchor_methods_add_expected_relations():
    action = base_actions.BaseAction(action_type="left_click", target="Submit")
    action.left("Username").right("Password").above("Top").below("Bottom")

    relations = [anchor.relation for anchor in action.anchors]
    assert relations == ["left", "right", "above", "below"]
    values = [anchor.value for anchor in action.anchors]
    assert values == ["Username", "Password", "Top", "Bottom"]


def test_anchor_methods_convert_paths_to_images(monkeypatch, tmp_path):
    monkeypatch.setattr(base_actions, "TARGET_IMAGES_PATH", str(tmp_path))
    for name in ("left.png", "right.png", "above.png", "below.png"):
        (tmp_path / name).write_bytes(b"img")

    action = base_actions.BaseAction(action_type="left_click", target="Submit")
    action.left("left.png").right("right.png").above("above.png").below("below.png")

    assert all(isinstance(anchor.value, ImageB64) for anchor in action.anchors)


def test_offset_updates_click_offset():
    action = base_actions.BaseAction(action_type="left_click", target="Submit")
    action.offset(x=10, y=-5)
    assert action.click_offset == [10, -5]


def test_is_path(tmp_path):
    file_path = tmp_path / "image.png"
    file_path.write_bytes(b"img")
    assert base_actions.BaseAction._is_path(str(file_path))
    assert not base_actions.BaseAction._is_path(str(file_path.with_suffix(".missing")))


def test_file_converts_base64_content():
    encoded = base64.b64encode(b"payload").decode()
    file_model = File(filename="a.bin", mimetype="application/octet-stream", content=encoded)
    assert file_model.content == b"payload"


def test_file_save_writes_bytes(tmp_path):
    file_model = File(filename="artifact.bin", mimetype=None, content=b"data")
    target_dir = tmp_path / "artifacts"
    file_model.save(str(target_dir))

    saved_path = target_dir / "artifact.bin"
    assert saved_path.read_bytes() == b"data"


def test_left_click_do_with_widget_bbox(monkeypatch):
    captured = {}

    def fake_perform_action(payload: ExecutePayload):
        captured["payload"] = payload

    monkeypatch.setattr(actions, "perform_action", fake_perform_action)
    action = LeftClick(target="Submit", widget_bbox=Coords(value=[0, 0, 20, 20]))

    action.do()

    payload = captured["payload"]
    assert payload.action_type == "left_click"
    assert payload.coordinates == [10, 10]


def test_left_click_do_prepares_payload(monkeypatch):
    monkeypatch.setattr(base_actions, "get_screen", lambda: "c2NyZWVu")
    expected_bbox = Coords(value=[0, 0, 10, 10])

    def fake_get_coordinates(payload):
        assert isinstance(payload, Screenshot)
        return expected_bbox

    captured = {}

    def fake_perform_action(payload: ExecutePayload):
        captured["payload"] = payload

    monkeypatch.setattr(actions, "get_coordinates", fake_get_coordinates)
    monkeypatch.setattr(actions, "perform_action", fake_perform_action)

    action = LeftClick(target="Submit")
    action.do()

    payload = captured["payload"]
    assert payload.coordinates == [5, 5]


def test_actionable_string_representation():
    action = LeftClick(target="Submit").offset(x=3, y=-2)
    object.__setattr__(action, "anchor", "Username")
    object.__setattr__(action, "relation", "left")

    representation = action.actionable_string
    assert "LeftClick" in representation
    assert "Username" in representation


def test_strtobool_valid_values():
    assert strtobool("yes")
    assert not strtobool("No")


def test_strtobool_invalid_value():
    with pytest.raises(ValueError):
        strtobool("maybe")


def test_save_screenshot(monkeypatch, tmp_path):
    image_bytes = b"img-data"
    encoded = base64.b64encode(image_bytes).decode()

    monkeypatch.setattr(
        "clerk.gui_automation.ui_actions.support.get_screen", lambda: encoded
    )

    saved_path = tmp_path / "saved"

    def fake_save_artifact(filename, file_bytes, subfolder):
        path = saved_path / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(file_bytes)
        return str(path)

    monkeypatch.setattr(
        "clerk.gui_automation.ui_actions.support.save_artifact", fake_save_artifact
    )

    output = save_screenshot("screen.png", sub_folder="runs")
    assert os.path.exists(output)
    assert (saved_path / "screen.png").read_bytes() == image_bytes


def test_try_actions_runs_first_success(monkeypatch):
    executed = []

    class DummyAction(base_actions.BaseAction):
        action_type: str = "left_click"

        def do(self):  # type: ignore[override]
            executed.append("run")

    action = DummyAction(target="Submit")
    try_actions([action])
    assert executed == ["run"]


def test_try_actions_raises_after_failures(monkeypatch):
    class FailingAction(base_actions.BaseAction):
        action_type: str = "left_click"

        def do(self):  # type: ignore[override]
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        try_actions([FailingAction(target="Submit"), FailingAction(target="Submit")])


def test_try_actions_type_validation():
    with pytest.raises(TypeError):
        try_actions(["not-an-action"])  # type: ignore[list-item]


def test_format_action_string_includes_details():
    action = base_actions.BaseAction(action_type="left_click", target="Submit")
    action.left("Username").offset(x=1, y=2)
    formatted = _format_action_string(action)
    assert formatted.startswith("BaseAction")
    assert "offset(x=1, y=2)" in formatted


def test_maybe_engage_operator_raises_when_disabled():
    error = RuntimeError("failure")
    details = {"exception": error, "args": [LeftClick(target="Submit")]}

    with pytest.raises(RuntimeError) as exc:
        maybe_engage_operator_ui_action(details)

    assert exc.value is error
