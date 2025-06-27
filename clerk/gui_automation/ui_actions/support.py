import os
import base64
from typing import Optional
from backoff._typing import Details

from clerk.utils.save_artifact import save_artifact
from ..client_actor import get_screen


_MAP = {
    "y": True,
    "yes": True,
    "t": True,
    "true": True,
    "on": True,
    "1": True,
    "n": False,
    "no": False,
    "f": False,
    "false": False,
    "off": False,
    "0": False,
}


def strtobool(value):
    try:
        return _MAP[str(value).lower()]
    except KeyError:
        raise ValueError('"{}" is not a valid bool value'.format(value))


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
    screen_b64: str = get_screen()
    return save_artifact(
        filename=filename,
        file_bytes=base64.b64decode(screen_b64),
        subfolder=sub_folder,
    )


def maybe_engage_operator_ui_action(details: Details) -> None:
    """
    Makes a call to the operator queue server to create an issue and waits for the allotted time for it to be resolved.
    :param details: A dictionary containing the details of the exception raised (https://pypi.org/project/backoff/)
    :returns: None
    :raises: The exception raised by the action if the issue is not resolved within the allotted time
    """
    # Determine if the operator should be engaged
    use_operator = strtobool(os.getenv("USE_OPERATOR", default="False"))
    if not use_operator:
        raise details["exception"]  # type: ignore

    raise NotImplementedError("Feature not yet implemented")
