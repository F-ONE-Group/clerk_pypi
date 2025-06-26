class PerformActionException(Exception):
    """
    A custom exception class for handling errors related to performing actions.
    """

    pass


class GetScreenError(Exception):
    """
    A custom exception class for handling errors related to getting the screen.
    """

    pass


class WebSocketConnectionFailed(Exception):
    """
    Connection to websocket was not successful
    """

    pass
