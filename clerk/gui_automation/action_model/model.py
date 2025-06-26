import base64
import os
from typing import List, Literal, Optional, Union
from pydantic import BaseModel, Field, validator

CoordsType = Union[List[float], List[int]]

PredictionsFormat = Union[
    Literal["xyxy"], Literal["xyxyn"], Literal["xywh"], Literal["xywhn"]
]

RelationsType = Union[
    Literal["above"], Literal["below"], Literal["left"], Literal["right"], Literal[""]
]


class ImageB64(BaseModel):
    """
    A class representing an image encoded in base64 format.

    Attributes:
        id (Optional[str]): The ID of the image. Defaults to None.
        value (str): The base64 encoded value of the image.

    Methods:
        from_path(value: Union[str, "ImageB64"]) -> "ImageB64":
            Creates an ImageB64 instance from a file path or an existing ImageB64 instance.

            Args:
                value (Union[str, "ImageB64"]): The file path or an existing ImageB64 instance.

            Returns:
                ImageB64: The created ImageB64 instance.

        _to_b64(path: str) -> str:
            Encodes the image file at the given path to base64 format.

            Args:
                path (str): The path to the image file.

            Returns:
                str: The base64 encoded image.
    """

    id: Optional[str] = None
    value: str = ""

    @classmethod
    def from_path(cls, value: Union[str, "ImageB64"]) -> "ImageB64":
        if isinstance(value, ImageB64):
            return value
        return ImageB64(
            id=os.path.basename(value),
            value=to_b64(value),
        )


def to_b64(path: str) -> str:
    with open(path, "rb") as f:
        img_b64: str = base64.b64encode(f.read()).decode("utf-8")
    return img_b64


class Anchor(BaseModel):
    """
    A class representing an anchor for a screenshot.

    Attributes:
        value (Union[str, ImageB64]): The value of the anchor, which can be a string or an ImageB64 instance.
        relation (RelationsType): The relation of the anchor to the target, which can be one of the following: "above", "below", "left", "right", or an empty string.

    """

    value: Union[str, ImageB64] = ""
    relation: RelationsType = ""


class Screenshot(BaseModel):
    """
    A class representing a screenshot.

    Attributes:
        screen_b64 (ImageB64): The base64 encoded value of the screenshot.
        target (Union[str, ImageB64]): The target of the screenshot, which can be a string or an ImageB64 instance.
        anchors (List[Anchor]): The list of anchors for the screenshot.
        is_awaited (bool): A flag to signal whether the target should appear immediately or is awaited.
        target_name (Optional[str]): A readable representation of a target which is set automatically when validating the target and is used in the AM for logging.


    """

    screen_b64: ImageB64
    target: Union[str, ImageB64]
    anchors: List[Anchor] = []
    is_awaited: bool = False
    target_name: Optional[str] = None


class Coords(BaseModel):
    """
    A class representing coordinates.

    Attributes:
        value (CoordsType): The value of the coordinates, which can be a list of floats or a list of integers.
        score (int): The score associated with the coordinates, defaults to 0.

    """

    value: CoordsType
    score: int = 0


class RouterOutput(BaseModel):
    """
    A class representing the output of a router.

    Attributes:
        Resources (List[Coords]): A list of coordinates representing the resources.
        StatusMessage (Union[Literal["Success"], Literal["Failure"], None]): The status message of the router output.
        ErrorMessage (str): The error message associated with the router output.

    """

    Resources: List[Coords] = []
    StatusMessage: Union[Literal["Success"], Literal["Failure"], None] = None
    ErrorMessage: str = ""
