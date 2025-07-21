from datetime import timedelta, datetime
import os
import base64
import time
from typing import List, Optional
from backoff._typing import Details

from clerk.models.ui_operator import TaskStatuses, UiOperatorTask
from clerk.utils.save_artifact import save_artifact
from clerk.utils import logger
from ..client_actor import get_screen
from ..ui_actions.base import BaseAction
from ..decorators.gui_automation import clerk_client


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


def try_actions(actions: List[BaseAction]):
    """
    Executes a list of UI actions and handles any errors that occur.

    This function takes a list of UI actions as input and executes them one by one.
    If an action fails with a RuntimeError, it logs a warning message and moves on to the next action.
    If all actions fail, it logs an error message and raises a RuntimeError.

    Args:
        actions (List[BaseAction]): A list of UI actions to be executed.

    Raises:
        TypeError: If any of the actions in the list is not an instance of BaseAction.
        RuntimeError: If all actions fail.

    Returns:
        None

    Example Usage:
        actions = [action1, action2, action3]
        try_actions(actions)
    """
    try:
        assert all(isinstance(action, BaseAction) for action in actions)
        for action in actions:
            try:
                action.do()
                return
            except RuntimeError as e:
                logger.warning(
                    f"The action {action} was not performed successfully.\nDetails: {str(e)}",
                )
        # all the actions have failed. log an error and raise a runtime error
        logger.error("All actions have failed.")
        raise RuntimeError("All actions have failed")
    except AssertionError as e:
        raise TypeError(
            f"All actions must be valid. Encountered invalid action: {str(e)}"
        )


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
    ui_operator_enabled = strtobool(os.getenv("_ui_operator_enabled", default="False"))

    if not ui_operator_enabled:
        raise details["exception"]  # type: ignore

    ui_operator_pooling_interval = int(os.getenv("_ui_operator_pooling_interval", "1"))
    ui_operator_timeout = int(os.getenv("_ui_operator_timeout", "3600"))
    resolution_deadline = datetime.now() + timedelta(seconds=ui_operator_timeout)

    # Extract the action object from the details dictionary
    action: BaseAction = details["args"][0]
    issue_description = _format_action_string(action)

    # create ui operator task
    payload = {
        "document_id": os.getenv("_document_id"),
        "remote_device_id": os.getenv("REMOTE_DEVICE_ID"),
        "issue_description": issue_description,
    }
    task: UiOperatorTask = clerk_client.create_ui_operator_task(payload)
    while datetime.now() < resolution_deadline:
        task: UiOperatorTask = clerk_client.get_ui_operator_task(task.id)
        if task.status == TaskStatuses.COMPLETED:
            logger.debug(
                f"The ui operator task {task.id} has been resolved by {task.assignee_name}"
            )
            return
        elif task.status == TaskStatuses.CANCELLED:
            logger.warning(f"The ui operator task {task.id} has been cancelled")
            raise details["exception"]

        time.sleep(ui_operator_pooling_interval)

    logger.warning(
        f"The ui operator task {task.id} was not resolved after {ui_operator_timeout} seconds"
    )
    raise details["exception"]
