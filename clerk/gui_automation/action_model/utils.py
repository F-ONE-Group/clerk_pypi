from .model import Coords, Screenshot
from ..decorators.gui_automation import clerk_client


def get_coordinates(payload: Screenshot) -> Coords:
    """
    Get coordinates from the action model API endpoint.

    The method requires the following environmental variables to work:
        - AM_URL: action model URL

    Parameters:
        payload (Screenshot): The payload containing the necessary data for the request.

    Returns:
        Coords: The coordinates obtained from the API response.

    Raises:
        RuntimeError: If the API response status code is not 200.

    Example:
        payload = Screenshot(screen_b64="base64_encoded_image", target="target_image")
        coordinates = get_coordinates(payload)
    """

    return clerk_client.get_coordinates(payload.model_dump())
