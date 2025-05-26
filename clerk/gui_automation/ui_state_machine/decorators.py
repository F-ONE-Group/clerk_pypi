from typing import Callable, Optional
from .state_machine import ScreenPilot


def state(*args, start_allowed=True, end_allowed=True):
    """
    Register a state class with the ScreenPilot state machine.

    Parameters:
    - start_allowed (bool): Whether the process may start from this state.
    - end_allowed (bool): Whether the process may end in this state.

    Returns:
    - None

    Example:
    @state(start_allowed=True, end_allowed=False)
    """
    if args and callable(args[0]):
        # It's used as @state without arguments, args[0] is the class
        cls = args[0]
        return state()(cls)  # Apply default arguments
    else:

        def class_decorator(cls):
            ScreenPilot.register_state(
                cls, start_allowed=start_allowed, end_allowed=end_allowed
            )
            return cls

        return class_decorator


def transition(from_state: str, to_state: str, condition: Optional[Callable] = None):
    """
    Register a transition between two states with the ScreenPilot state machine.

    Parameters:
    - from_state (str): The name of the state to transition from.
    - to_state (str): The name of the state to transition to.
    - condition (Callable): Condition to disambiguate between multiple transitions. Must return a boolean.

    Returns:
    - None

    Example:
    @transition('StateA', 'StateB')
    """
    return ScreenPilot.register_transition(
        from_state, to_state, mode="planned", condition=condition
    )


def rollback(from_state: str, to_state: str, condition: Optional[Callable] = None):
    """
    Register a rollback transition between two states with the ScreenPilot state machine.

    Parameters:
    - from_state (str): The name of the state to transition from.
    - to_state (str): The name of the state to transition to.
    - condition (Callable): Condition to disambiguate between multiple rollbacks. Must return a boolean.

    Returns:
    - None

    Example:
    @rollback('StateA', 'StateB')
    """
    return ScreenPilot.register_transition(
        from_state, to_state, mode="rollback", condition=condition
    )
