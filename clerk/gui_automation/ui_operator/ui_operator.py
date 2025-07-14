from datetime import datetime, timedelta, timezone
import os
import time
from typing import Dict, Final, List, Literal, Optional

import backoff
import requests

from clerk.utils import logger

# Local constants
_RESOLUTION_OPTIONS = Literal["performed", "raise", "timeout"]
_NAME: Final[str] = "OPERATOR TASK QUEUE"


def _get_operator_queue_url() -> str:
    return os.getenv("OPERATOR_QUEUE_URL", default="http://monitoring.f-one.group:1488")


def _get_operator_queue_api_token() -> Optional[str]:
    return os.getenv("OPERATOR_QUEUE_API_TOKEN")


def _handle_response(response: requests.Response) -> Optional[Dict]:
    """
    Handles the HTTP response.
    :param response: The HTTP response to handle.
    :returns: The response JSON if the request was successful, None otherwise.
    :raises: HTTPError if the request was not successful.
    """
    try:
        response.raise_for_status()

        # Handle the case twhen code is 200 but success is False
        if not response.json().get("success"):
            logger.error(
                _NAME,
                f"Error from the operator queue: {response.json().get('message', 'Unknown error')}",
            )
            return None

        # Return the resources if the request was successful
        return response.json().get("resources")[
            0
        ]  # Parsing the standard backend response

    # Return None for any non-200 HTTP status code
    except requests.HTTPError as e:
        logger.error(f"HTTPError: {e}")
        return None


@backoff.on_exception(backoff.expo, requests.HTTPError, max_tries=3)
def _create_issue(
    proc_inst_id: Optional[str],
    title: str,
    description: str,
    resolution_deadline: str,
    client_name: Optional[str] = None,
    attachments: Optional[List[str]] = None,
) -> Optional[Dict]:
    """
    Calls the operator queue server to create an operator issue.
    :returns: IssueStatus dictionary or None
    """
    payload = {
        "proc_inst_id": proc_inst_id,
        "client_name": client_name,
        "title": title,
        "description": description,
        "resolution_deadline": resolution_deadline,
        "attachments": attachments,
    }
    headers = {"Authorization": f"Bearer {_get_operator_queue_api_token()}"}
    response = requests.post(
        f"{_get_operator_queue_url()}/issue", json=payload, headers=headers
    )
    return _handle_response(response)


@backoff.on_exception(backoff.expo, requests.HTTPError, max_tries=3)
def _get_issue_status(issue_id: str) -> Optional[Dict]:
    """
    Calls the operator queue server to get the status of an operator issue.
    :returns: IssueStatus dictionary or None
    """
    headers = {"Authorization": f"Bearer {_get_operator_queue_api_token()}"}
    response = requests.get(
        f"{_get_operator_queue_url()}/issue/{issue_id}", headers=headers
    )
    return _handle_response(response)


@backoff.on_exception(backoff.expo, requests.HTTPError, max_tries=3)
def _resolve_issue(issue_id: str, resolution: _RESOLUTION_OPTIONS) -> Optional[Dict]:
    """
    Calls the operator queue server to resolve an operator issue.
    :returns: IssueStatus dictionary or None
    """
    payload = {"resolution": resolution, "resolved_by": __name__}
    headers = {"Authorization": f"Bearer {_get_operator_queue_api_token()}"}
    response = requests.put(
        f"{_get_operator_queue_url()}/issue/{issue_id}/resolve",
        json=payload,
        headers=headers,
    )
    return _handle_response(response)


def create_issue_and_wait(
    issue_title: str = "",
    issue_description: str = "",
    timeout_mins: int = 60,
    client_name: Optional[str] = None,
    run_id: Optional[str] = None,
    attachments: Optional[List[str]] = None,
) -> bool:
    """
    Makes a call to the operator queue server to create an issue and waits for the allotted time for it to be resolved.
    :param issue_title: The title of the issue
    :param issue_description: The description of the issue
    :returns: True if the issue is resolved, False otherwise
    """
    wait_time_start = datetime.now(tz=timezone.utc)
    resolution_deadline = wait_time_start + timedelta(minutes=timeout_mins)

    # Create an issue in the operator queue
    issue: Optional[Dict] = _create_issue(
        proc_inst_id=run_id,
        client_name=client_name,
        title=issue_title,
        description=issue_description,
        resolution_deadline=resolution_deadline.isoformat(),
        attachments=attachments,
    )
    if issue:
        logger.info(f"Operator issue {issue['id']} has been created.")
        logger.info(f"Awaiting resolution for {timeout_mins} minutes.")
    else:
        logger.error("The operator issue could not be created.")
        return False

    # Wait for the issue to be resolved
    while datetime.now(tz=timezone.utc) < resolution_deadline:
        issue_status = _get_issue_status(issue["id"])
        if issue_status:
            resolution: _RESOLUTION_OPTIONS = issue_status["resolution"]
            if resolution == "performed":
                # The issue has been resolved
                logger.info(
                    f"Operator issue {issue['id']} has been resolved as 'performed'.",
                )
                return True
            elif resolution == "raise":
                logger.info(
                    f"Operator issue {issue['id']} has been resolved as 'raise'."
                )
                # The issue has been escalated
                break
        time.sleep(1)

    # Resolve the issue as a timeout if it is not resolved within the allotted time
    logger.info(f"Operator issue {issue['id']} has timed out.")
    _resolve_issue(issue["id"], "timeout")

    return False
