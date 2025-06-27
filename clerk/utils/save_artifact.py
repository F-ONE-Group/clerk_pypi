import os
from typing import Optional
from clerk.utils import logger


def save_artifact(
    filename: str, file_bytes: bytes, subfolder: Optional[str] = None
) -> str:
    """
    Save an artifact to a specified path.

    Args:
        artifact: The artifact to save.
        filename (str): The name of the file to save.
        file_bytes (bytes): The bytes of the file to save.
        subfolder (str): The subfolder where the artifact will be saved. Defaults to "artifacts".
    Returns:
        str: The path to the saved artifact.
    """

    # get the run ID from environment variable or default to "unknown"
    run_id = os.getenv("_RUN_ID", "unknown")

    # create the base path for artifacts
    base_path = os.path.join(os.getcwd(), "data", "artifacts", run_id)
    if subfolder:
        base_path = os.path.join(base_path, subfolder)

    os.makedirs(base_path, exist_ok=True)

    # save the file
    file_path = os.path.join(base_path, filename)
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    logger.debug(f"Artifact successfully saved at: {file_path}")
    return file_path
