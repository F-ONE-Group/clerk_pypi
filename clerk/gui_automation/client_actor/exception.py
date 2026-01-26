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


class AckTimeoutError(Exception):
    """
    Timeout waiting for ACK message from WebSocket.
    """

    pass


class ActionTimeoutError(Exception):
    """
    Timeout waiting for action response from WebSocket.
    """

    pass
