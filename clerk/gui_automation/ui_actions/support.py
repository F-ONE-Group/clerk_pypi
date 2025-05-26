from distutils.util import strtobool
import os
import time
from backoff._typing import Details

from ..client_actor import get_screen
from ..ui_actions.base import BaseAction
from ..ui_state_inspector.models import (
    LoadingState,
    ExpectedState,
    States,
)

from typing import List, Union, Callable, Optional


def ensure_state_with_vision(
    states: Union[States, Callable[[], States]], timeout: int = 60
) -> bool:
    """
    Ensures that the GUI is in the desired state using the Vision class.

    Parameters:
    - states (Union[States, Callable]): The desired state(s) of the GUI. It can be either a States object or a callable that generates a States object.
    - timeout (int, optional): The maximum time (in seconds) to wait for the desired state. Defaults to 60 seconds.

    Returns:
    - bool: True if the GUI is in the desired state, False otherwise.

    Note:
    - If a callable is provided for the 'states' parameter, it will be called to generate the States object.
    - If the GUI is in the expected state, the function returns True.
    - If the GUI is in the loading state, the function waits for the specified timeout and then re-verifies the state. If the state is still loading, it returns False.
    - If the GUI is in any other state, the function returns False.
    """
    # call the state generator if one is provided
    if callable(states):
        states = states()
    state = Vision().verify_state(states)
    if isinstance(state, ExpectedState):
        return True
    elif isinstance(state, LoadingState):
        time.sleep(timeout)
        return Vision().verify_state(states) == ExpectedState
    return False


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
    # save the file into the process instance folder
    return save_file_into_instance_folder(screen_64, filename, sub_folder)


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
                    MODULE_NAME,
                    f"The action {action} was not performed successfully.\nDetails: {str(e)}",
                )
        # all the actions have failed. log an error and raise a runtime error
        logger.error(MODULE_NAME, "All actions have failed.")
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
    use_operator = bool(strtobool(os.getenv("USE_OPERATOR", default="False")))
    if not use_operator:
        logger.debug(MODULE_NAME, "The operator is not engaged")
        raise details["exception"]  # type: ignore

    # Extract the action object from the details dictionary
    action: BaseAction = details["args"][0]
    issue_description = _format_action_string(action)

    # Create an issue in the operator queue
    try:
        operator_result = operator.create_issue_and_wait(
            proc_inst_id=os.getenv("PROC_ID"),
            client_name=os.getenv("TARGET_CLIENT"),
            issue_title="RuntimeError in UI automation",
            issue_description=issue_description,
            timeout_mins=int(os.getenv("UI_OPERATOR_TIMEOUT_MINS", default=60)),
            attachments=None,  # Not implemented yet
        )
        if operator_result:
            # Suppress further raising of the exception
            logger.debug(MODULE_NAME, "The issue was resolved by the operator")
            return None
    except Exception as e:
        logger.error(MODULE_NAME, f"An error occurred while engaging the operator: {e}")

    # Raise the exception if the issue is not resolved within the allotted time
    raise details["exception"]  # type: ignore
