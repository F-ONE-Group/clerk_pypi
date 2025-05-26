class ModalityNotKnownError(Exception):
    """
    This exception is raised when the modality of a target is not known or not supported.

    Attributes:
        message (str): The error message explaining the allowed modalities.

    Example:
        raise ModalityNotKnownError("The modality must be either 'text' or 'icon'")
    """

    def __init__(self, message: str = "allowed modalities are: `text` | `icon`"):
        super().__init__(message)


class AnchorTypeError(Exception):
    """
    This exception is raised when the anchor type is not valid or not supported.

    Attributes:
        message (str): The error message explaining the allowed anchor types.

    Example:
        raise AnchorTypeError("The anchor type must be either 'text' or 'image'")
    """

    def __init__(self, message: str):
        super().__init__(message)


class TargetModalityError(Exception):
    """
    This exception is raised when the modality of a target is not valid or not supported.

    Attributes:
        message (str): The error message explaining the allowed target modalities.

    Example:
        raise TargetModalityError("target must be provided as either text (str) | image (ImageB64) | image path (str) or skipped")
    """

    def __init__(
        self,
        message: str = "target must be provided as either text (str) | image (ImageB64) | image path (str) or skipped",
    ):
        super().__init__(message)
