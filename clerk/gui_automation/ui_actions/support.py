from distutils.util import strtobool
import os
from typing import Optional
from backoff._typing import Details

from ..client_actor import get_screen
from ..ui_actions.base import BaseAction


def save_screenshot(filename: str, sub_folder: Optional[str] = None) -> str:
    """
    Save a screenshot into the process instance folder.

    This function retrieves the base64 representation of the screen from the target environment using the 'get_screen' function.
    Then, it saves the screenshot into the process instance folder using the 'save_file_into_instance_folder' function.

    Args:
        filename (str): The name of the file to save the screenshot as.
        sub_folder (str, optional): The name of the subfolder within the instance folder where the screenshot will be saved. Defaults to None.

    Returns:
        str: The file path of the saved screenshot.

    """
    # get the base64 screen from target environment
    screen_64 = get_screen()
    # TODO: implement new system for save and provided metadata at processor run instance level


def _format_action_string(action: BaseAction) -> str:
    """
    Formats action in the same format as the one used in task modules.
    """
    action_string = (
        f"{action.__class__.__name__}(target='{action.target_name or action.target}')"
    )
    for anchor in action.anchors:
        action_string += f".{anchor.relation}('{anchor.value}')"
    if action.click_offset != [0, 0]:
        action_string += (
            f".offset(x={action.click_offset[0]}, y={action.click_offset[1]})"
        )
    action_string += ".do()"
    return action_string


def maybe_engage_operator_ui_action(details: Details) -> None:
    """
    Makes a call to the operator queue server to create an issue and waits for the allotted time for it to be resolved.
    :param details: A dictionary containing the details of the exception raised (https://pypi.org/project/backoff/)
    :returns: None
    :raises: The exception raised by the action if the issue is not resolved within the allotted time
    """
    # Determine if the operator should be engaged
    use_operator = bool(strtobool(os.getenv("USE_OPERATOR", default="False")))
    if not use_operator:
        raise details["exception"]  # type: ignore

    raise NotImplementedError("Feature not yet implemented")
