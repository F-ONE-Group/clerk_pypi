from typing import Optional


class ScreenPilotOutcome(Exception):
    """Base class for all exceptions and conditions raised by the ScreenPilot state machine."""


class ScreenPilotException(Exception):
    """Base class for all exceptions raised by the ScreenPilot state machine."""


class BusinessException(ScreenPilotOutcome):
    """Raised from inside transitions to indicate a business process condition."""


class UnplannedTransitionsError(ScreenPilotException):
    """Raised when a transition occurs that is not planned in the state machine."""


class RepeatStatesError(ScreenPilotException):
    """Raised when an attempt is made to re-enter a state that should not be repeated."""


class RepeatTransitions(ScreenPilotException):
    """Raised when the same transition is attempted to be repeated in an invalid context."""


class CourseCorrectionImpossible(ScreenPilotException):
    """Raised when the state machine cannot determine a course correction."""


class SuccessfulCompletion(ScreenPilotOutcome):
    """Raised when the state machine has completed successfully."""


class RollbackCompleted(ScreenPilotOutcome):
    """Raised when the state machine has completed a rollback successfully."""


def complete_ui_automation(message: Optional[str] = None):
    """Raise an exception to interrupt ScreenPilot and indicate that the UI automation has completed successfully."""
    raise SuccessfulCompletion(message)
