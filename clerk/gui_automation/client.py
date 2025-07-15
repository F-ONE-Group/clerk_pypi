from typing import Dict, List, Optional

from pydantic import BaseModel
from clerk.base import BaseClerk
from clerk.gui_automation.action_model.model import Coords
from clerk.gui_automation.exceptions.agent_manager import NoClientsAvailable
from clerk.gui_automation.ui_state_inspector.models import (
    ActionString,
    BaseState,
    States,
    TargetWithAnchor,
)
from clerk.models.remote_device import RemoteDevice
from clerk.models.ui_operator import UiOperatorTask


class RPAClerk(BaseClerk):

    root_endpoint: str = "/gui_automation"

    def allocate_remote_device(self, group_name: str, run_id: str):
        endpoint = "/remote_device/allocate"
        res = self.post_request(
            endpoint=endpoint, json={"group_name": group_name, "run_id": run_id}
        )

        if res.data[0] is None:
            raise NoClientsAvailable()

        return RemoteDevice(**res.data[0])

    def deallocate_remote_device(
        self,
        remote_device: RemoteDevice,
        run_id: str,
    ):
        endpoint = "/remote_device/deallocate"
        self.post_request(
            endpoint=endpoint,
            json={"id": remote_device.id, "name": remote_device.name, "run_id": run_id},
        )

    def get_coordinates(self, payload: Dict) -> Coords:
        endpoint = "/action_model/get_coordinates"
        res = self.post_request(endpoint=endpoint, json=payload)
        if res.data[0] is None:
            raise RuntimeError("No coordinates found in the response.")
        return Coords(**res.data[0])

    def create_ui_operator_task(self, payload: Dict) -> UiOperatorTask:
        endpoint = "/ui_operator"
        res = self.post_request(endpoint=endpoint, json=payload)
        return UiOperatorTask(**res.data[0])

    def get_ui_operator_task(self, id: str) -> UiOperatorTask:
        endpoint = "/ui_operator"
        res = self.get_request(endpoint=endpoint, params={"task_id": id})
        return UiOperatorTask(**res.data[0])


class GUIVisionClerk(BaseClerk):
    root_endpoint: str = "/gui_automation/vision"

    def find_target(self, screen_b64: str, use_ocr: bool, target_prompt: str):
        endpoint = "/find_target"
        res = self.post_request(
            endpoint=endpoint,
            json={
                "screen_b64": screen_b64,
                "use_ocr": use_ocr,
                "target_prompt": target_prompt,
            },
        )
        return TargetWithAnchor(**res.data[0])

    def verify_state(
        self, screen_b64: str, use_ocr: bool, possible_states: States
    ) -> BaseState:
        endpoint = "/verify_state"
        res = self.post_request(
            endpoint=endpoint,
            json={
                "screen_b64": screen_b64,
                "use_ocr": use_ocr,
                "possible_states": possible_states,
            },
        )

        return BaseState(**res.data[0])

    def answer(
        self, screen_b64: str, use_ocr: bool, question: str, output_model: BaseModel
    ) -> Dict:
        endpoint = "/answer"
        res = self.post_request(
            endpoint=endpoint,
            json={
                "screen_b64": screen_b64,
                "use_ocr": use_ocr,
                "question": question,
                "output_model": output_model.model_json_schema(),
            },
        )

        return output_model(**res.data[0])

    def classify_state(
        self, screen_b64: str, use_ocr: bool, possible_states: List[Dict[str, str]]
    ) -> BaseState:
        endpoint = "/classify_state"
        res = self.post_request(
            endpoint=endpoint,
            json={
                "screen_b64": screen_b64,
                "use_ocr": use_ocr,
                "possible_states": possible_states,
            },
        )

        return BaseState(**res.data[0])

    def write_action_string(
        self, screen_b64: str, use_ocr: bool, action_prompt: str
    ) -> ActionString:
        endpoint = "/write_action-string"
        res = self.post_request(
            endpoint=endpoint,
            json={
                "screen_b64": screen_b64,
                "use_ocr": use_ocr,
                "action_prompt": action_prompt,
            },
        )

        return ActionString(**res.data[0])


class CourseCorrectorClerk(BaseClerk):
    root_endpoint: str = "/gui_automation/course_corrector"

    def get_corrective_actions(
        self,
        screen_b64: str,
        use_ocr: str,
        goal: str,
        custom_instructions: Optional[str] = None,
    ) -> ActionString:
        endpoint = "/get_corrective_actions"
        res = self.post_request(
            endpoint=endpoint,
            json={
                "screen_b64": screen_b64,
                "use_ocr": use_ocr,
                "goal": goal,
                "custom_instructions": custom_instructions,
            },
        )

        return ActionString(**res.data[0])
