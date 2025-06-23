from typing import Literal, Self, Union, List, Optional
from pydantic import BaseModel, Field, model_validator
from ..client_actor import get_screen
from ..exceptions.modality.exc import TargetModalityError
from ..action_model.model import (
    ImageB64,
    Coords,
    Screenshot,
    Anchor,
)
import os

ModalityType = Union[Literal["icon"], Literal["text"]]
TARGET_IMAGES_PATH = os.path.join(os.getcwd(), "targets")


def to_full_img_path(img: Union[str, ImageB64]) -> str:
    """
    Add prefix if provided `img` is a string, otherwise return a default value which will later be evaluated
    `False` in `_is_path`
    """
    if isinstance(img, ImageB64):
        return ""
    return os.path.join(TARGET_IMAGES_PATH, img)


ActionTypes = Literal[
    "left_click",
    "right_click",
    "middle_click",
    "double_click",
    "send_keys",
    "press_keys",
    "wait_for",
    "open_app",
    "force_close_app",
    "maximize_window",
    "minimize_window",
    "close_window",
    "activate_window",
    "save_files",
    "delete_files",
    "get_file",
    "get_text",
    "paste_text",
    "scroll",
]


class BaseAction(BaseModel):
    """
    BaseAction class represents a base model for UI actions.

    Attributes:
        action_type (ActionTypes): Type of UI action to execute.
        target_name (Optional[str]): A readable representation of a target which is set automatically when validating the target and is used in the AM for logging.
        target (Optional[Union[str, ImageB64]]): Target of the UI action. It can be provided as a string, an instance of the ImageB64 class, or a path to an image.
        anchors (List[Anchor]): List of anchor points for the UI action.
        is_awaited (bool): A flag to signal whether the target should appear immediately or is awaited. Should be set to `True` in WaitFor
        widget_bbox: (Optional[Coords]): The bounding box coordinates of the widget. If set, the call to the action module will be bypassed.

    Methods:
        _get_center_coords(bbox: Coords) -> Union[List[int], List[float]]:
            Returns the center coordinates of a bounding box.

        check_target(cls, value):
            Validator function to check the target modality.

        _prepare_payload():
            Prepares the payload for the UI action.

        _prepare_payload_test(screen_id: str, bbox: CoordsType, is_last: bool = False):
            Prepares the payload for the detection test.

        test(screen_id: str, bbox: CoordsType, is_last: bool = False):
            Performs a detection test using the provided payload.

        left(anchor: Union[str, ImageB64]):
            Adds a left anchor point to the list of anchors.

        right(anchor: Union[str, ImageB64]):
            Adds a right anchor point to the list of anchors.

        above(anchor: Union[str, ImageB64]):
            Adds an above anchor point to the list of anchors.

        below(anchor: Union[str, ImageB64]):
            Adds a below anchor point to the list of anchors.

        _is_path(value: str) -> bool:
            Checks if a given value is a valid file path.

        do():
            Placeholder method for executing the UI action.
    """

    action_type: ActionTypes = Field(..., description="Type of ui action to execute")
    target_name: Optional[str] = Field(default=None)
    target: Optional[Union[str, ImageB64]] = Field(default=None)
    anchors: List[Anchor] = []
    click_offset: List[int] = [0, 0]
    is_awaited: bool = False
    widget_bbox: Optional[Coords] = None

    @model_validator(mode="after")
    def validate_target_and_set_name(self) -> Self:
        target = self.target
        if isinstance(target, str):  # either text target or img path
            full_image_path = to_full_img_path(target)
            if self._is_path(full_image_path):
                self.target = ImageB64.from_path(full_image_path)
                self.target_name = target  # Set target name as path for logging
            else:
                # Set target name as provided string for logging
                self.target_name = target
            return self
        elif isinstance(target, ImageB64):
            self.target_name = "provided as obj with value in b64"
            return self
        elif target is None:
            self.target_name = "not_provided"
            return self
        raise TargetModalityError()

    def _get_center_coords(self, bbox: Coords) -> Union[List[int], List[float]]:
        w: Union[int, float] = bbox.value[2] - bbox.value[0]
        h: Union[int, float] = bbox.value[3] - bbox.value[1]
        xcenter: Union[int, float] = bbox.value[0] + w // 2 + self.click_offset[0]
        ycenter: Union[int, float] = bbox.value[1] + h // 2 + self.click_offset[1]
        return [xcenter, ycenter]

    def _prepare_payload(self):
        payload: Screenshot = Screenshot(
            screen_b64=ImageB64(value=get_screen()),
            target=self.target,
            anchors=self.anchors,
            is_awaited=self.is_awaited,
            target_name=self.target_name,
        )
        return payload

    def left(self, anchor: Union[str, ImageB64]):
        value: Union[str, ImageB64] = (
            anchor
            if not self._is_path(to_full_img_path(anchor))
            else ImageB64.from_path(to_full_img_path(anchor))
        )
        self.anchors.append(Anchor(value=value, relation="left"))
        return self

    def right(self, anchor: Union[str, ImageB64]):
        value: Union[str, ImageB64] = (
            anchor
            if not self._is_path(to_full_img_path(anchor))
            else ImageB64.from_path(to_full_img_path(anchor))
        )
        self.anchors.append(Anchor(value=value, relation="right"))
        return self

    def above(self, anchor: Union[str, ImageB64]):
        value: Union[str, ImageB64] = (
            anchor
            if not self._is_path(to_full_img_path(anchor))
            else ImageB64.from_path(to_full_img_path(anchor))
        )
        self.anchors.append(Anchor(value=value, relation="above"))
        return self

    def below(self, anchor: Union[str, ImageB64]):
        value: Union[str, ImageB64] = (
            anchor
            if not self._is_path(to_full_img_path(anchor))
            else ImageB64.from_path(to_full_img_path(anchor))
        )
        self.anchors.append(Anchor(value=value, relation="below"))
        return self

    def offset(self, x: int = 0, y: int = 0):
        """
        Add a pixel offset to the click action (coordinates start at the top-left corner of the screen).
        Args:
            x (int): Horizontal offset (left to right).
            y (int): Vertical offset (top to bottom).
        Returns:
            BaseAction: BaseAction instance with the updated click offset.
        Usage:
            # click 10 pixels to the right and 20 pixels above the center of the target.
            LeftClick(target="target").offset(x=10, y=-20).do()
        """
        self.click_offset = [x, y]
        return self

    @staticmethod
    def _is_path(value: str) -> bool:
        if not os.path.isfile(value):
            return os.path.isfile(value)
        return True

    def do(self):
        pass
