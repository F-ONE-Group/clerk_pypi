import os
import time
import backoff
from typing import Literal, List, Optional, Self, Union

from pydantic import BaseModel, Field, model_validator, field_validator
from .base import BaseAction, ActionTypes
from .support import maybe_engage_operator_ui_action
from ..action_model.model import (
    Coords,
    Screenshot,
)
from ..client_actor import perform_action
from ..action_model.utils import get_coordinates
from ..client_actor.model import (
    DeleteFilesExecutePayload,
    ExecutePayload,
    ApplicationExecutePayload,
    FileDetails,
    GetFileExecutePayload,
    SaveFilesExecutePayload,
    WindowExecutePayload,
)
from ..client_actor.exception import GetScreenError
from ..exceptions.modality.exc import ModalityNotKnownError

MAX_TIME = 5


class File(BaseModel):
    """A class representing a file with filename, mimetype, and content.

    Attributes:
        filename (str): filename of the file
        mimetype (Optional[str]): type of the file
        content (bytes): file content

    Methods:
        save(path: str): Saves the file content to the specified path after creating any necessary directories.
    """

    filename: str = Field(description="filename of the file")
    mimetype: Optional[str] = Field(description="type of the file")
    content: bytes = Field(description="file content")

    @field_validator("content", mode="before")
    @classmethod
    def convert_to_bytes(cls, v) -> bytes:
        if isinstance(v, str):
            from base64 import b64decode

            return b64decode(v)
        return v

    def save(self, path: str):
        if not os.path.exists(path):
            os.makedirs(path)

        with open(os.path.join(path, self.filename), "wb") as f:
            f.write(self.content)


class LeftClick(BaseAction):
    """
    Class representing a left click action.

    Attributes:
        action_type (Literal["left_click"]): The type of action, which is always "left_click".

    Methods:
        do(): Performs the left click action by preparing the payload, getting the widget coordinates, and executing the action.
        actionable_string(): Returns a string representation of the action that can be executed.

    Example Usage:
        LeftClick(target="Suche").above("Kalender").do()
    """

    action_type: Literal["left_click"] = "left_click"

    @backoff.on_exception(
        backoff.expo,
        (RuntimeError, GetScreenError),
        max_time=MAX_TIME,
        on_giveup=maybe_engage_operator_ui_action,
        raise_on_giveup=False,  # Exception might be raised in the giveup handler instead
    )
    def do(self):
        if not self.widget_bbox:
            payload: Screenshot
            payload = self._prepare_payload()

            widget_bbox: Coords = get_coordinates(payload)
            center_coords = self._get_center_coords(widget_bbox)
        else:
            center_coords = self._get_center_coords(self.widget_bbox)
        execute_payload = ExecutePayload(
            action_type=self.action_type, coordinates=center_coords
        )
        perform_action(execute_payload)

    @property
    def actionable_string(self):
        return f"LeftClick(action_type='{self.action_type}', target='{self.target}', anchor='{self.anchor}', relation='{self.relation}').do()"


class RightClick(BaseAction):
    """
    Class representing a right click action.

    Attributes:
        action_type (Literal["right_click"]): The type of action, which is always "right_click".

    Methods:
        do(): Performs the right click action by preparing the payload, getting the widget coordinates, and executing the action.
        actionable_string(): Returns a string representation of the action that can be executed.

    Example Usage:
        RightClick(target="Suche").above("Kalender").do()
    """

    action_type: Literal["right_click"] = "right_click"

    @backoff.on_exception(
        backoff.expo,
        (RuntimeError, GetScreenError),
        max_time=MAX_TIME,
        on_giveup=maybe_engage_operator_ui_action,
        raise_on_giveup=False,  # Exception might be raised in the giveup handler instead
    )
    def do(self):
        if not self.widget_bbox:
            payload: Screenshot
            payload = self._prepare_payload()

            widget_bbox: Coords = get_coordinates(payload)
            center_coords = self._get_center_coords(widget_bbox)
        else:
            center_coords = self._get_center_coords(self.widget_bbox)
        execute_payload = ExecutePayload(
            action_type=self.action_type, coordinates=center_coords
        )
        perform_action(execute_payload)

    @property
    def actionable_string(self):
        return f"RightClick(action_type='{self.action_type}', target='{self.target}', anchor='{self.anchor}', relation='{self.relation}').do()"


class MiddleClickAction(BaseAction):
    """
    Class representing a middle click action.

    Attributes:
        action_type (Literal["middle_click"]): The type of action, which is always "middle_click".

    Methods:
        do(): Performs the middle click action by preparing the payload, getting the widget coordinates, and executing the action.
        actionable_string(): Returns a string representation of the action that can be executed.

    Example Usage:
        MiddleClickAction(target="Suche").above("Kalender").do()
    """

    action_type: Literal["middle_click"] = "middle_click"

    @backoff.on_exception(
        backoff.expo,
        (RuntimeError, GetScreenError),
        max_time=MAX_TIME,
        on_giveup=maybe_engage_operator_ui_action,
        raise_on_giveup=False,  # Exception might be raised in the giveup handler instead
    )
    def do(self):
        if not self.widget_bbox:
            payload: Screenshot
            payload = self._prepare_payload()

            widget_bbox: Coords = get_coordinates(payload)
            center_coords = self._get_center_coords(widget_bbox)
        else:
            center_coords = self._get_center_coords(self.widget_bbox)
        execute_payload = ExecutePayload(
            action_type=self.action_type, coordinates=center_coords
        )
        perform_action(execute_payload)

    @property
    def actionable_string(self):
        return f"MiddleClickAction(action_type='{self.action_type}', target='{self.target}', anchor='{self.anchor}', relation='{self.relation}').do()"


class DoubleClick(BaseAction):
    """
    Class representing a double click action.

    Attributes:
        action_type (Literal["double_click"]): The type of action, which is always "double_click".

    Methods:
        do(): Performs the double click action by preparing the payload, getting the widget coordinates, and executing the action.
        actionable_string(): Returns a string representation of the action that can be executed.

    Example Usage:
        DoubleClick(target="Suche").above("Kalender").do()
    """

    action_type: Literal["double_click"] = "double_click"

    @backoff.on_exception(
        backoff.expo,
        (RuntimeError, GetScreenError),
        max_time=MAX_TIME,
        on_giveup=maybe_engage_operator_ui_action,
        raise_on_giveup=False,  # Exception might be raised in the giveup handler instead
    )
    def do(self):
        if not self.widget_bbox:
            payload: Screenshot
            payload = self._prepare_payload()

            widget_bbox: Coords = get_coordinates(payload)
            center_coords = self._get_center_coords(widget_bbox)
        else:
            center_coords = self._get_center_coords(self.widget_bbox)
        execute_payload = ExecutePayload(
            action_type=self.action_type, coordinates=center_coords
        )
        perform_action(execute_payload)

    @property
    def actionable_string(self):
        return f"DoubleClick(action_type='{self.action_type}', target='{self.target}', anchor='{self.anchor}', relation='{self.relation}').do()"


class Scroll(BaseAction):
    """
    Class representing a mouse scroll action.

    Attributes:
        action_type (Literal["scroll"]): The type of action, which is always "scroll".
        clicks (int): indicates the amount of clicks to scroll. A positive integer scrolls up, a negative down
        click_coords (Optional[List[int]]): Optional, if provided specifies coordinates of the click action which will be perfomed before scrolling.
        y (Optional[int]): the y coordinate to be clicked.
    Methods:
        do(): Performs the double click action by preparing the payload, getting the widget coordinates, and executing the action.
        actionable_string(): Returns a string representation of the action that can be executed.

    Example Usage:
        DoubleClick(target="Suche").above("Kalender").do()
    """

    action_type: Literal["scroll"] = "scroll"
    clicks: int
    click_coords: List[int] = Field(default=[])

    @backoff.on_exception(
        backoff.expo,
        (RuntimeError, GetScreenError),
        max_time=MAX_TIME,
        on_giveup=maybe_engage_operator_ui_action,
        raise_on_giveup=False,  # Exception might be raised in the giveup handler instead
    )
    def do(self):
        execute_payload = ExecutePayload(
            action_type=self.action_type,
            coordinates=self.click_coords,
            clicks=self.clicks,
        )
        perform_action(execute_payload)

    @property
    def actionable_string(self):
        return f"Scroll(action_type='{self.action_type}', clicks={self.clicks}, click_coords={self.click_coords}).do()"


class SendKeys(BaseAction):
    """
    Class representing a send keys action. Use for typing  on the target machine.

    Attributes:
        action_type (Union[Literal["send_keys"], Literal["type"]]): The type of action, which can be "send_keys" or "type".
        keys  Union[str, List[str]]: The keys to be typed. If a list of strings is provided, it is mandatory to specify their key_separator (ie, tab, enter, etc..)
        key_separator Optional[str]: The key to be pressed in order to separate the list of strings provided.
        followed_by Optional[str]: The key that needs to be pressed after the keys are typed.
        interval (float): The interval between each key press. Default is 0.05 seconds.

    Methods:
        do(): Performs the send keys action by preparing the payload, getting the widget coordinates, and executing the action.
        actionable_string(): Returns a string representation of the action that can be executed.

    Example Usage:
        SendKeys(keys="Hello World").do()
    """

    action_type: ActionTypes = "send_keys"
    keys: Union[str, List[str]]
    key_separator: Optional[str] = Field(default=None)
    followed_by: Optional[str] = Field(default=None)
    interval: float = 0.05

    @model_validator(mode="after")
    def validate_keys(self) -> Self:
        if isinstance(self.keys, list) and not self.key_separator:
            raise ValueError(
                "The attribute 'key_seperator' must be provided if 'keys' is a list."
            )
        return self

    def do(self):
        payload: Screenshot
        try:
            if self.target:
                payload = self._prepare_payload()
                widget_bbox: Coords = get_coordinates(payload)
                center_coords = self._get_center_coords(widget_bbox)
            elif self.widget_bbox:
                center_coords = self._get_center_coords(self.widget_bbox)
            else:
                center_coords: List[int] = []

        except ModalityNotKnownError:
            center_coords: List[int] = []

        execute_payload = ExecutePayload(
            action_type="send_keys",
            coordinates=center_coords,
            keys=self.keys,
            interval=self.interval,
            key_separator=self.key_separator,
            followed_by=self.followed_by,
        )
        perform_action(execute_payload)

    @property
    def actionable_string(self):
        return f"SendKeys(action_type='{self.action_type}', target='{self.target}', anchor='{self.anchor}', relation='{self.relation}', keys='{self.keys}').do()"


class PressKeys(BaseAction):
    """
    Class representing a press keys action or keyboard shortcut action.

    Attributes:
        action_type (Union[Literal["press_keys"], Literal["keyboard_shortcut"]]): The type of action, which can be "press_keys" or "keyboard_shortcut".
        keys (str): The keys to be pressed or the keyboard shortcut to be executed.

    Methods:
        do(): Performs the press keys action or keyboard shortcut action by preparing the payload and executing the action.
        actionable_string(): Returns a string representation of the action that can be executed.

    Example Usage:
        PressKeys(keys='ctrl+c').do()
        PressKeys(keys='ctrl+shift+esc').do()
    """

    action_type: ActionTypes = "press_keys"
    keys: str

    def do(self):
        # provide widget + screen to the action model via http request
        execute_payload = ExecutePayload(
            action_type="hot_keys",
            keys=self.keys,
        )
        perform_action(execute_payload)

    @property
    def actionable_string(self):
        return f"PressKeys(action_type='{self.action_type}', target='{self.target}', anchor='{self.anchor}', relation='{self.relation}', keys='{self.keys}').do()"


class WaitFor(BaseAction):
    """
    Class representing a wait for action.

    Attributes:
        action_type (Literal["wait_for"]): The type of action, which is always "wait_for".
        retry_timeout (float): The time interval between each retry in seconds. Default is 0.5 seconds.
        is_awaited (bool): A flag to signal whether the target should appear immediately or is awaited.

    Methods:
        do(timeout: int = 30) -> bool: Waits for a UI target for a specified timeout and returns True if found, False otherwise.

    Example Usage:
        WaitFor("element").do(timeout=60)
    """

    action_type: Literal["wait_for"] = "wait_for"
    retry_timeout: float = 0.5
    is_awaited: bool = True

    def do(self, timeout: int = 30) -> Union[bool, Coords]:
        """
        Attempts to find a UI target within a specified timeout, optimizing wait times between retries.

        This method introduces an adaptive wait strategy based on the duration of previous attempts,
        aiming to maximize the number of retries within the given timeout period. Unlike `slow_do`,
        which statically waits for a fixed interval, `do` dynamically adjusts wait times to improve
        the chances of finding the target within the timeout.

        Parameters:
        - timeout (int): The maximum time to wait in seconds. Default is 30.

        Returns:
        - bool: True if the UI target is found before the timeout, False otherwise.
        """
        time_spent: float = 0.0
        n_requests: int = 0

        while True:
            # Start tracking time
            start = time.perf_counter()

            # Given that after a screenshot is taken, an end-to-end request to the AM might take some meaningful time,
            # additional sleeping time was removed
            # We assume that the screen will have enough time to update,
            # while the previous screen travels through the AM services

            # take new screenshot
            try:
                return get_coordinates(self._prepare_payload())
            except RuntimeError:
                n_requests += 1
                time_spent += round((time.perf_counter() - start), 2)  # e.g. 2.45 s
                average_request_time: float = round((time_spent / n_requests), 2)

                # do we have time for one more request?
                # if not, let's not wait for another retry and quit immediately
                if time_spent > timeout - average_request_time:
                    return False

                ## check if this is the last call, notify the action model that the target is not awaited anymore
                if time_spent > timeout - 2 * average_request_time:
                    self.is_awaited = False


class OpenApplication(BaseAction):
    """
    Class representing an open application action.

    Attributes:
        action_type (Literal["open_app"]): The type of action, which is always "open_app".
        app_path (str): The absolute path of the application.
        app_window_name (str): The name of the application window once open. Wildcard logic enabled.

    Methods:
        do(timeout: int = 60): Opens the application by preparing the payload and executing the action.

    Example Usage:
        OpenApplication(app_path="/path/to/application.exe", app_window_name="Application Window").do()
    """

    action_type: Literal["open_app"] = "open_app"
    app_path: str = Field(description="Absolute path of the application")
    app_window_name: str = Field(
        description="Name of the application window once open. Wildcard logic enabled."
    )

    def do(self, timeout: int = 60):
        payload = ApplicationExecutePayload(
            action_type=self.action_type,
            app_path=self.app_path,
            app_window_name=self.app_window_name,
            timeout=timeout,
        )
        perform_action(payload)


class ForceCloseApplication(BaseAction):
    """
    ForceCloseApplication class represents an action to force close an application.

    Attributes:
        action_type (Literal["force_close_app"]): Type of the action, set to "force_close_app".
        process_name (str): Process name from the task manager that identifies the application to be force closed.

    Methods:
        do():
            Executes the action to force close the application by creating and performing an ApplicationExecutePayload with the specified process name.
    """

    action_type: Literal["force_close_app"] = "force_close_app"
    process_name: str = Field(
        description="Process name from task manager. Example: process.exe"
    )

    def do(self):
        payload = ApplicationExecutePayload(
            action_type=self.action_type,
            process_name=self.process_name,
        )
        perform_action(payload)


class SaveFiles(BaseAction):
    """
    SaveFiles class represents an action for saving files.

    Attributes:
        action_type (Literal["save_files"]): The type of action, indicating that it is for saving files.
        save_location (str): The location where the files will be saved on client machine.
        files (List[str]): A list of absolute paths of the files to be saved.

    Methods:
        do():
            Executes the save files action by creating a payload and performing the action using the perform_action function.

    Example Usage:
        SaveFiles(save_location="/path/to/", files=["/path/to/file_1", "/path/to/file_2"]).do()
    """

    action_type: ActionTypes = "save_files"
    save_location: str
    files: Union[List[str], List[FileDetails]]

    def get_files_details(self) -> List[FileDetails]:
        import os
        import base64

        files_details: List[FileDetails] = []
        for file in self.files:
            if isinstance(file, str):
                if not os.path.exists(file):
                    raise FileExistsError(file)
                file_details: FileDetails = FileDetails(
                    filename=os.path.basename(file),
                    value=base64.standard_b64encode(open(file, "rb").read()).decode(),
                )
                files_details.append(file_details)
            else:
                files_details.append(file)
        return files_details

    def do(self):
        payload = SaveFilesExecutePayload(
            action_type=self.action_type,
            save_location=self.save_location,
            files=self.get_files_details(),
        )
        perform_action(payload)


class DeleteFiles(BaseAction):
    """
    DeleteFiles class represents an action for deleting files.

    Attributes:
        action_type (Literal["delete_files"]): The type of action, indicating that it is for deleting files.
        files_location (List[str]): A list of file locations representing the files to be deleted.

    Methods:
        do():
            Executes the delete files action by creating a payload and performing the action using the 'perform_action' function.
    Example Usage:
        DeleteFiles(files_location=["/path/to/file_1", "/path/to/file_2"]).do()
    """

    action_type: ActionTypes = "delete_files"
    files_location: List[str]

    def do(self):
        payload = DeleteFilesExecutePayload(
            action_type=self.action_type, files_location=self.files_location
        )
        perform_action(payload)


class GetFile(BaseAction):
    """
    GetFile class represents an action for getting file from target machine.

    Attributes:
        action_type (Literal["get_file"]): The type of action, indicating that it is for getting a file
        files_location (str): file location of the target file.

    Methods:
        do():
            Executes the delete files action by creating a payload and performing the action using the 'perform_action' function.
    Example Usage:
        GetFile(file_location="/path/to/file_1").do()
    """

    action_type: Literal["get_file"] = "get_file"
    file_location: str

    def do(self) -> File:
        payload = GetFileExecutePayload(
            action_type=self.action_type, file_location=self.file_location
        )
        return File(**perform_action(payload))


class MaximizeWindow(BaseAction):
    """
    Class representing a maximize window action.

    Attributes:
        action_type (Literal["maximize_window"]): The type of action, which is always "maximize_window".
        window_name (str): The name of the window to be maximized.

    Methods:
        do(timeout: int = 10): Maximizes the specified window by preparing the payload and executing the action.

    Example Usage:
        MaximizeWindow(window_name="MyWindow").do()
    """

    action_type: Literal["maximize_window"] = "maximize_window"
    window_name: str

    def do(self, timeout: int = 10):
        payload = WindowExecutePayload(
            action_type=self.action_type, window_name=self.window_name, timeout=timeout
        )
        perform_action(payload)


class MinimizeWindow(BaseAction):
    """
    Class representing a minimize window action.

    Attributes:
        action_type (Literal["minimize_window"]): The type of action, which is always "minimize_window".
        window_name (str): The name of the window to be minimized.

    Methods:
        do(timeout: int = 10): Minimizes the specified window by preparing the payload and executing the action.

    Example Usage:
        MinimizeWindow(window_name="MyWindow").do()
    """

    action_type: Literal["minimize_window"] = "minimize_window"
    window_name: str

    def do(self, timeout: int = 10):
        payload = WindowExecutePayload(
            action_type=self.action_type, window_name=self.window_name, timeout=timeout
        )
        perform_action(payload)


class CloseWindow(BaseAction):
    """
    Class representing a close window action.

    Attributes:
        action_type (Literal["close_window"]): The type of action, which is always "close_window".
        window_name (str): The name of the window to be closed.

    Methods:
        do(timeout: int = 10): Closes the specified window by preparing the payload and executing the action.

    Example Usage:
        CloseWindow(window_name="MyWindow").do()
    """

    action_type: Literal["close_window"] = "close_window"
    window_name: str

    def do(self, timeout: int = 10):
        payload = WindowExecutePayload(
            action_type=self.action_type, window_name=self.window_name, timeout=timeout
        )
        perform_action(payload)


class ActivateWindow(BaseAction):
    """
    Class representing an activate window action.

    Attributes:
        action_type (Literal["activate_window"]): The type of action, which is always "activate_window".
        window_name (str): The name of the window to be activated.

    Methods:
        do(timeout: int = 10): Activates the specified window by preparing the payload and executing the action.

    Example Usage:
        ActivateWindow(window_name="MyWindow").do()
    """

    action_type: Literal["activate_window"] = "activate_window"
    window_name: str

    def do(self, timeout: int = 10):
        payload = WindowExecutePayload(
            action_type=self.action_type, window_name=self.window_name, timeout=timeout
        )
        perform_action(payload)


class GetText(BaseAction):
    """
    GetText class represents a UI action for retrieving text from a target/preselected textbox or input field.

    Attributes:
        action_type (Literal["get_text"]): Type of UI action to execute.

    Methods:
        do(): Executes the UI action and returns the retrieved text.

    Example:
        # retrieve text from a target input field
        text = GetText(target="Suche").above("Kalender").do()

        # retrieve text from a pre-selected
        text = GetText().do()

    """

    action_type: Literal["get_text"] = "get_text"

    @backoff.on_exception(
        backoff.expo,
        (RuntimeError, GetScreenError),
        max_time=MAX_TIME,
        on_giveup=maybe_engage_operator_ui_action,
        raise_on_giveup=False,  # Exception might be raised in the giveup handler instead
    )
    def do(self) -> str:
        if self.target:
            payload: Screenshot
            payload = self._prepare_payload()

            widget_bbox: Coords = get_coordinates(payload)
            center_coords = self._get_center_coords(widget_bbox)
        else:
            center_coords = []
        execute_payload = ExecutePayload(
            action_type=self.action_type, coordinates=center_coords
        )
        return perform_action(execute_payload)


class PasteText(BaseAction):
    """
    PasteText class represents a UI action for paste text from a using ctrl+a,ctrl+v combination.

    Attributes:
        action_type (Literal["paste_text"]): Type of UI action to execute.

    Methods:
        do(): Executes the UI action and returns the retrieved text.

    Example:
        # paste text into a target input field
        text = PasteText(target="Suche", keys="text to paste").above("Kalender").do()

        # paste text into a pre-selected field
        text = PasteText(keys="text to paste").do()

    """

    action_type: Literal["paste_text"] = "paste_text"
    keys: Union[str, List[str]]
    followed_by: Optional[str] = Field(default=None)

    @backoff.on_exception(
        backoff.expo,
        (RuntimeError, GetScreenError),
        max_time=MAX_TIME,
        on_giveup=maybe_engage_operator_ui_action,
        raise_on_giveup=False,  # Exception might be raised in the giveup handler instead
    )
    def do(self) -> str:
        if self.target:
            payload: Screenshot
            payload = self._prepare_payload()

            widget_bbox: Coords = get_coordinates(payload)
            center_coords = self._get_center_coords(widget_bbox)
        else:
            center_coords = []
        execute_payload = ExecutePayload(
            action_type=self.action_type,
            coordinates=center_coords,
            followed_by=self.followed_by,
            keys=self.keys,
        )
        return perform_action(execute_payload)
