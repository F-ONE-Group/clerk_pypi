from typing import Any, List, Literal, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum


ActionTypes = Literal[
    "left_click",
    "right_click",
    "middle_click",
    "double_click",
    "send_keys",
    "press_keys",
    "hot_keys",
    "paste_text",
    "get_text",
    "scroll",
]


class ActionStates(Enum):
    """
    Enumeration class representing the possible states of an action.

    Attributes:
        completed (str): Represents a completed action state.
        failed (str): Represents a failed action state.
    """

    completed = "COMPLETED"
    failed = "FAILED"


class ExecutePayload(BaseModel):
    """
    A class representing the payload for executing various actions.

    Attributes:
        action_type (Literal[str]): The type of action to be performed. It can be one of the following:
            - "left_click": Perform a left click action.
            - "right_click": Perform a right click action.
            - "middle_click": Perform a middle click action.
            - "double_click": Perform a double click action.
            - "send_keys": Send a sequence of keys.
            - "press_keys": Press and hold a sequence of keys.
            - "hot_keys": Perform a combination of hot keys.
        coordinates (List[int]): The coordinates of the action. Default is an empty list.
        keys (Optional[str]): The keys to be sent or pressed. Default is None.
        interval (float): The interval between each action. Default is 0.05 seconds.
    """

    action_type: ActionTypes
    coordinates: Union[List[int], List[float]] = Field(default=[])
    keys: Optional[Union[str, List[str]]] = Field(default=None)
    key_separator: Optional[str] = Field(default=None)
    followed_by: Optional[str] = Field(default=None)
    interval: float = Field(default=0.05)
    clicks: Optional[int] = None


class WindowExecutePayload(BaseModel):
    """
    A class representing the payload for executing window-related actions.

    Attributes:
        action_type (Literal[str]): The type of window action to be performed. It can be one of the following:
            - "maximize_window": Maximize the window.
            - "minimize_window": Minimize the window.
            - "close_window": Close the window.
            - "activate_window": Activate the window.
        window_name (str): The name of the window on which the action should be performed.
        timeout (int): The timeout value in seconds for the action to complete. Default is 10 seconds.
    """

    action_type: Literal[
        "maximize_window",
        "minimize_window",
        "close_window",
        "activate_window",
    ]
    window_name: str
    timeout: int = Field(default=10)


class ApplicationExecutePayload(BaseModel):
    """
    A class representing the payload for executing an application-related action.

    Attributes:
        action_type (Literal[str]): The type of application action to be performed. It can only be "open_app".
        app_path (str): The absolute path of the application to be opened.
        app_window_name (str): The name of the application window once it is open. Wildcard logic is enabled.
        timeout (int): The timeout value in seconds for the action to complete. Default is 60 seconds.
        process_name (str): Process name from task manager. Example: process.exe
    """

    action_type: Literal["open_app", "force_close_app"]
    app_path: str = Field(description="Absolute path of the application", default="")
    app_window_name: str = Field(
        description="Name of the application window once open. Wildcard logic enabled.",
        default="",
    )
    timeout: int = Field(default=60)
    process_name: str = Field(
        description="Process name from task manager. Example: process.exe", default=""
    )


class FileDetails(BaseModel):
    """
    A class representing the details of a file.

    Attributes:
        filename (str): The filename of the file.
        value (str): The base64 string representation of the binary file.
    """

    filename: str = Field(description="Filename of the file")
    value: str = Field(description="Base64 string representation of the binary file")


class SaveFilesExecutePayload(BaseModel):
    """
    A class representing the payload for saving files.

    Attributes:
        action_type (Literal["save_files"]): The action type indicating the payload is for saving files.
        save_location (str): The location where the files will be saved.
        files (List[FileDetails]): A list of FileDetails objects representing the files to be saved.
    """

    action_type: Literal["save_files"]
    save_location: str
    files: List[FileDetails]


class DeleteFilesExecutePayload(BaseModel):
    """
    A class representing the payload for deleting files.

    Attributes:
        action_type (Literal["delete_files"]): The action type indicating the payload is for deleting files.
        files_location (List[str]): A list of file locations representing the files to be deleted.
    """

    action_type: Literal["delete_files"]
    files_location: List[str]


class GetFileExecutePayload(BaseModel):
    """
    A class representing the payload for executing a 'get_file' action.

    Attributes:
        action_type: Literal["get_file"] - Specifies the action type as 'get_file'.
        file_location: str - The location of the file to retrieve.
    """

    action_type: Literal["get_file"]
    file_location: str


class GetScreenResponse(BaseModel):
    """
    A class representing the response for getting a screen.

    Attributes:
        screen_b64 (str): The base64 encoded string representing the screen image.
    """

    screen_b64: str


class PerformActionResponse(BaseModel):
    """
    A class representing the response of performing an action.

    Attributes:
        id (str): The ID of the action.
        state (ActionStates): The state of the action.
        message (Optional[str]): An optional message associated with the action.
        return_value (Optional[Any]): A value that the action could return.
    """

    id: Optional[str] = None
    state: ActionStates
    message: Optional[str] = None
    return_value: Optional[Any] = None
    screen_b64: Optional[str] = None


class AllocateTargetResponse(BaseModel):
    client: str
