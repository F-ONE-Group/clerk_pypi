# ScreenPilot 

ScreenPilot is a state machine meant for operating UIs.
- Accepts a state evaluation function and a goal function
- Runs in a loop ("run" method) until the goal function returns True
- Handles logging, error handling and attempts recovery on errors
- The states and transitions are added to a directional multi-graph
- "run" method performs anti-patter detection (repeated transitions, unplanned transitions) and exits on encountering them
- Known states and transitions are provided with the respective decorators


## Instructions

- Use 'BusinessException' class to raise business exceptions
- Evaluate the exit_reason returned by the run method to execution outcomes
- Provide custom instructions to AI recovery to handle the UI's quirks

## Usage example

```python
from f_one_core_utilities.ui_actions import Vision, ScreenPilot, state, transition, rollback, BusinessException, complete_ui_automation
from f_one_core_utilities.ui_actions import LeftClick, SendKeys, PressKeys
from f_one_core_utilities.camunda import raise_error, return_and_wait, raise_incident

# Import states, transitions and rollbacks for them to be registered
from .states import *
from .transitions import *
from .rollbacks import *

# Configure states and transitions

@state(end_allowed=False)
class WindowOpen:
    description = "Window is open"

@state(start_allowed=False)
class WindowClosed:
    description = "Window is closed"

@transition(from_state="WindowOpen", to_state="WindowClosed", condition=lambda payload: payload.message == "Closed")
def close_window(payload):
    # 'payload' is the order object passed to the run method
    SendKeys(keys=f"{payload.message}").do()
    LeftClick(target="Close").do()

# Define rollbacks which will be triggered in case of runtime errors
@rollback("WindowClosed", "WindowOpen")
def teardown_app():
    PressKeys(keys="Alt+F4").do()

# Provide a goal function

def goal_function(current_state: str, **kwargs) -> None:
    """
    Goal function for the state machine.
    Args:
        current_state (str): The current state of the state machine
        **kwargs: (you can provide additional arguments as needed, e.g. order: dict)
    Returns:
        None
    """
    if current_state == "WindowClosed":
        complete_ui_automation("Window closed")
    else:
        raise BusinessException("Window not closed")

ScreenPilot.configure(
   ai_recovery_instructions = "If the popup appears, click OK and interrupt the process",
)

# payload is a kwarg that will be propagated to all transitions and the goal function
exit_reason = ScreenPilot.run(goal_function, payload=process_variables)

# Exit status and messages can be used for graceful error handling
if isinstance(exit_reason, BusinessException):
    raise_error(message="Window still open", bpmn_error="WindowOpen")
elif isinstance(exit_reason, SuccessfulCompletion):
    process_variables.billable = True
```
