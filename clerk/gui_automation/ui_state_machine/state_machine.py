import os
import networkx as nx  # type: ignore
import functools
import inspect
from collections import deque
from pydantic import BaseModel, ValidationError
from typing import List, Tuple, Callable, Optional, Deque, Literal, Union
import traceback
from datetime import datetime

from ..ui_actions.actions import ForceCloseApplication
from ..ui_actions.support import save_screenshot
from .exceptions import (
    BusinessException,
    ScreenPilotException,
    UnplannedTransitionsError,
    RepeatTransitions,
    RollbackCompleted,
    RepeatStatesError,
    ScreenPilotOutcome,
    CourseCorrectionImpossible,
    SuccessfulCompletion,
)
from ..ui_state_machine.models import ActionString
from .ai_recovery import CourseCorrector, course_corrector_v1
from ..client_actor.exception import PerformActionException
from ..ui_state_inspector.gui_vision import Vision
from ...client import Clerk
from ...utils import logger


class ScreenPilot:
    """
    A class representing a screen pilot state machine.

    Attributes:
        ai_recovery (bool): Whether to use AI recovery on errors. Default True.
        ai_recovery_attempts (int): The number of AI recovery attempts. Default 5.
        ai_recovery_agent_factory (Optional[Callable]): Factory for AI recovery agents. Default course_corrector_v1.
        ai_recovery_instructions (Optional[str]): Custom instructions for the AI recovery agent. Default None.
        state_eval_function (Callable): Function to evaluate the current state of the state machine. Default Vision().classify_state.
        state_eval_output_model (BaseModel): Optional custom output model of the state evaluation function. Default None.
        tolerate_unplanned_transitions (int): Number of unplanned transitions to tolerate before breaking the execution. Default 5.
        tolerate_repeat_transitions (int): Number of repeated transitions to tolerate before breaking the execution. Default 5.
        tolerate_repeat_states (int): Number of repeated states to tolerate before breaking the execution. Default 5.
        enable_force_close_app_process (bool): If true, terminates the application process via `taskkill` command. Default False.
        ui_operator_enabled (bool): if true, enables the creation of ui operator task which needs to be resolved in Clerk.
        ui_operator_pooling_interval (int): in seconds, defines the time pooling interval for ui operator task. Default 1.
        ui_operator_timeout (int): in seconds, defines the max waiting time for the ui operator task to be resolved before raising and exception.
        process_name (Optional[str]): Name of the process that needs to be closed (ie. process.exe). Required attribute if `enable_force_close_app_process` is True

    Methods:
        register_state(cls, state_cls): Register a state class in the state machine graph.
        register_transition(cls, from_state, to_state): Register a transition function in the state machine graph.
        configure(cls, **kwargs): Provide class parameters to configure the state machine.
        run(cls, goal_function, **kwargs): Main loop of the state machine.
    """

    ai_recovery: bool = True
    ai_recovery_attempts: int = 5
    ai_recovery_agent_factory: Optional[Callable] = course_corrector_v1
    ai_recovery_instructions: Optional[str] = None
    state_eval_function: Optional[Callable] = Vision().classify_state
    state_eval_output_model: Optional[BaseModel] = None
    tolerate_unplanned_transitions: int = 5
    tolerate_repeat_transitions: int = 5
    tolerate_repeat_states: int = 5
    enable_force_close_app_process: bool = False
    process_name: Optional[str] = None
    _acted_since_state_eval: bool = False
    _ai_recovery_agent: Optional[CourseCorrector] = None
    _current_state: Optional[str] = None
    _exit_reason: Optional[Union[ScreenPilotOutcome, ScreenPilotException]] = None
    _final_state: Optional[str] = None
    _graph = nx.MultiDiGraph()
    _mode: Literal["planned", "rollback"] = "planned"
    _next_target_state: Optional[str] = None
    _runtime_error_details: Optional[Tuple[str, str, str]] = None
    _state_history: Deque[str] = deque(maxlen=25)
    _transition_history: Deque[Callable] = deque(maxlen=25)
    _clerk_client: Clerk = Clerk(
        base_url=os.getenv("CLERK_BASE_URL", "https://api.clerk-app.com")
    )

    @classmethod
    def register_state(
        cls, state_cls, start_allowed: bool = True, end_allowed: bool = True
    ):
        """
        Register a state class in the state machine graph.

        Parameters:
            state_cls (class): The state class to be registered.

        Returns:
            class: The registered state class.

        """
        cls._graph.add_node(
            state_cls.__name__,
            cls=state_cls,
            description=state_cls.description,
            start_allowed=start_allowed,
            end_allowed=end_allowed,
        )
        return state_cls

    @classmethod
    def register_transition(
        cls,
        from_state: str,
        to_state: str,
        mode: Literal["planned", "rollback"] = "planned",
        condition: Optional[Callable] = None,
    ):
        """
        Register a transition function in the state machine graph.

        Provides a decorator with logging and error handling.

        Parameters:
            from_state (str): The state from which the transition occurs.
            to_state (str): The state to which the transition leads.
            mode (Literal["planned", "rollback"]): The mode of the transition. Default "planned".
            condition (Optional[Callable]): A condition function for the transition. Should return boolean. Default None.

        Returns:
            function: The decorated transition function.

        Raises:
            ValueError: If either the from_state or to_state is not a defined state in the state machine graph.

        Example:
            @register_transition("StateA", "StateB", mode="planned", condition=None)
            def transition_func():
                # Transition logic here
                pass
        """

        def decorator(transition_func):
            @functools.wraps(transition_func)
            def wrapper(*args, **kwargs):
                # Argument filtering
                sig = inspect.signature(transition_func)
                supported_params = sig.parameters
                filtered_kwargs = {
                    k: v for k, v in kwargs.items() if k in supported_params
                }

                try:
                    logger.debug(
                        f"Starting {transition_func.__name__}",
                    )
                    # Apply filtered_kwargs instead of kwargs
                    result = transition_func(*args, **filtered_kwargs)
                    logger.debug(
                        f"Finished {transition_func.__name__}",
                    )

                    return result
                except BusinessException as e:
                    logger.info(f"Business exception: {e}\nExiting ScreenPilot.")
                    raise e
                except RuntimeError as e:
                    cls._runtime_error_details = _action_line_from_exc()
                    logger.error(
                        f"Runtime error in {transition_func.__name__} at action {cls._runtime_error_details[1]}",
                    )
                    logger.debug(
                        f"Runtime error traceback: {cls._runtime_error_details[0]}",
                    )
                    screenshot_and_log("Runtime error")
                    logger.info(
                        "Proceeding to course correction, activating rollback mode.",
                    )
                    cls._attempt_ai_recovery(
                        scenario="runtime_error",
                        error_details=cls._runtime_error_details[1],
                    )
                    cls._mode = "rollback"
                except RollbackCompleted as e:
                    logger.info("Rollback completed.")
                    raise type(e)(cls._runtime_error_details[0])

            # Ensure that any duplicate transitions have a condition function
            possible_transitions = cls._graph.out_edges(
                from_state, keys=True, data=True
            )
            for start_state, end_state, key, data in possible_transitions:
                if data.get("mode") == mode and (
                    not data.get("condition") or not condition
                ):
                    existing_transition_name = data.get("func").__name__
                    transition_type = "rollback" if mode == "rollback" else "transition"
                    raise ValueError(
                        f"Error while registering {wrapper.__name__}: {existing_transition_name} is already registered as {transition_type} from {start_state} to {end_state}. To add multiple transitions between the same states, provide a condition function for each of them."
                    )

            # Register the wrapped function as a transition in the graph
            if from_state in cls._graph.nodes and to_state in cls._graph.nodes:
                key = f"{wrapper.__name__}_from_{from_state}_to_{to_state}_{mode}"
                cls._graph.add_edge(
                    from_state,
                    to_state,
                    key=key,
                    func=wrapper,
                    condition=condition,
                    mode=mode,
                )
            else:
                logger.error(
                    f"Error: Transition from {from_state} to {to_state} involves undefined state.",
                )
            return wrapper

        return decorator

    @classmethod
    def _log_transition(cls, transition_func: Callable):
        """
        Log a transition from one state to another.

        Parameters:
            from_state (str): The state from which the transition occurs.
            to_state (str): The state to which the transition leads.

        Returns:
            None

        """
        cls._transition_history.append(transition_func)

    @classmethod
    def _log_state(cls, state):
        """
        Log a state in the state machine history.

        Parameters:
            state (str): The state to be logged.

        Returns:
            None

        """
        cls._state_history.append(state)

    @classmethod
    def _evaluate_state(cls) -> None:
        """
        Evaluate the current state of the state machine.

        This method evaluates the current state of the state machine by calling the state evaluation function
        provided during configuration. It retrieves the possible states from the state machine graph and passes
        them along with the state evaluation output model to the state evaluation function. The current state and
        its description are then updated based on the evaluation result. The current state is logged in the state
        history.

        If there is a previous state in the state history, an actual transition is added to the state machine graph,
        connecting the previous state to the current state.

        Raises:
            ValueError: If the state evaluation function is not set or not callable.
        """
        if not callable(cls.state_eval_function):
            raise ValueError("State evaluation function is not set or not callable.")

        possible_states = [
            {state: cls._graph.nodes[state]["cls"].description}
            for state in cls._graph.nodes
        ]
        cls._current_state, cur_state_description = cls.state_eval_function(
            possible_states, cls.state_eval_output_model
        )
        logger.debug(
            f"Current state: {cls._current_state}\nDescription: {cur_state_description}",
        )
        cls._log_state(cls._current_state)
        cls._acted_since_state_eval = False
        try:
            screenshot_and_log(f"State_{cls._current_state}")
        except Exception as e:
            logger.warning("Error occurred while taking and saving screenshot")
            logger.warning(f"Details: {str(e)}")

        if len(cls._state_history) > 1 and len(cls._transition_history) > 0:
            key = f"{cls._transition_history[-1].__name__}_from_{cls._state_history[-2]}_to_{cls._current_state}_actual"
            cls._graph.add_edge(
                cls._state_history[-2], cls._current_state, key=key, mode="actual"
            )

    @staticmethod
    def _find_unplanned_transitions(graph: nx.MultiDiGraph) -> List[Tuple[str, str]]:
        """
        Identify transitions in the graph which were not originally planned.

        Parameters:
            graph (nx.MultiDiGraph): The graph representing the state machine.

        Returns:
            List[Tuple[str, str]]: A list of tuples representing the unplanned transitions. Each tuple contains the source state and the destination state of the transition.

        """
        actual_edges = [
            (u, v)
            for u, v, k, data in graph.edges(keys=True, data=True)
            if data.get("mode") == "actual"
        ]
        planned_edges = set(
            [
                (u, v)
                for u, v, k, data in graph.edges(keys=True, data=True)
                if data.get("mode") == "planned"
            ]
        )

        # Filter out actual edges that have a corresponding planned edge
        unplanned_transitions = [
            edge for edge in actual_edges if edge not in planned_edges
        ]

        if unplanned_transitions:
            logger.info(f"Found unplanned transitions: {unplanned_transitions}")

        return unplanned_transitions

    @staticmethod
    def _find_repeated_transitions(transition_history: deque) -> List[str]:
        """
        Identify repeated transitions in the transition history.

        This method takes in a deque object representing the transition history and identifies any repeated transitions. It iterates over each item in the transition history and checks if the count of that item is greater than 1. If a repeated transition is found, it is added to the list of repeated transitions.

        Parameters:
            transition_history (deque): A deque object representing the transition history.

        Returns:
            List[str]: A list of strings representing the repeated transitions.

        """
        repeated_transitions = [
            item.__name__
            for item in transition_history
            if transition_history.count(item) > 1
        ]
        if repeated_transitions:
            logger.info(f"Found repeated transitions: {repeated_transitions}")
        return repeated_transitions

    @staticmethod
    def _find_repeated_states(state_history) -> List[str]:
        """
        This method identifies repeated states in the state history.
        Parameters:
            state_history (deque): A deque object representing the state history.
        Returns:
            List[str]: A list of strings representing the repeated states.
        """
        repeated_states = [
            item for item in state_history if state_history.count(item) > 1
        ]
        if repeated_states:
            logger.info(f"Found repeated states: {repeated_states}")
        return repeated_states

    @classmethod
    def _find_anti_patterns(cls) -> bool:
        """
        Detect abnormal patterns in the state machine execution and take appropriate action.

        Returns:
            bool: Whether an anti-pattern was detected.
        """
        # Detect deviation from planned transitions
        unplanned_transitions: List = cls._find_unplanned_transitions(cls._graph)
        if len(unplanned_transitions) > cls.tolerate_unplanned_transitions:
            cls._exit_reason = UnplannedTransitionsError(
                f"{len(unplanned_transitions)} unplanned transitions detected: {unplanned_transitions}."
            )
            raise cls._exit_reason

        repeated_transitions: List = cls._find_repeated_transitions(
            cls._transition_history
        )
        if (
            len(repeated_transitions) > cls.tolerate_repeat_transitions + 1
        ):  # +1 to account for the first transition
            cls._exit_reason = RepeatTransitions(
                f"{len(repeated_transitions)} repeated transitions detected: {repeated_transitions}."
            )
            raise cls._exit_reason

        repeated_states: List = cls._find_repeated_states(cls._state_history)
        if len(repeated_states) > cls.tolerate_repeat_states:
            cls._exit_reason = RepeatStatesError(
                f"{len(repeated_states)} repeated states detected: {repeated_states}."
            )
            if cls.enable_force_close_app_process and cls.process_name:
                logger.info(
                    f"RepeatStatesError detected. Killing application with process name: {cls.process_name}",
                )
                try:
                    ForceCloseApplication(process_name=cls.process_name).do()
                except Exception as e:
                    logger.warning("Killing application failed. Details")
                    logger.warning(f"{str(e)}")
            elif cls.enable_force_close_app_process and not cls.process_name:
                logger.warning(
                    "RepeatStatesError detected. Application cannot be killed as process_name was not provided.",
                )
            raise cls._exit_reason

        # No anti-patterns detected
        return False

    @classmethod
    def configure(
        cls,
        **kwargs,
    ) -> None:
        """
        Configure the state machine.

        Parameters:
            **kwargs: Additional keyword arguments for the configuration.

        Returns:
            None
        """
        for k, v in kwargs.items():
            if hasattr(cls, k) and not k.startswith("_"):
                setattr(cls, k, v)
            else:
                logger.error(f"Public attribute {k} not found in ScreenPilot.")
        return None

    @classmethod
    def _evaluate_goal_function(cls, goal_function: Callable, **kwargs) -> None:
        """
        Evaluate the success of the current state machine execution.

        Args:
            goal_function: A function that evaluates the completion and success of the current state machine execution.
                Args: current_state (class), **kwargs.
                Returns: Tuple[bool, bool].
            **kwargs: Additional arguments for the goal function.

        Returns:
            None
        """
        # Filter out unsupported kwargs
        sig = inspect.signature(goal_function)
        supported_params = sig.parameters
        filtered_kwargs = {k: v for k, v in kwargs.items() if k in supported_params}
        goal_function(cls._current_state, **filtered_kwargs)
        return None

    @classmethod
    def _act_on_start(cls) -> None:
        """
        Actions to be taken when the state machine execution is started.

        Returns:
            None
        """
        cls._exit_reason = None
        cls._current_state = None
        cls._final_state = None
        logger.info("State machine execution started.")

    @classmethod
    def _act_on_completed(cls) -> None:
        """
        Actions to be taken when the state machine execution is completed.

        This method performs the following actions:
        - Sets the final state of the state machine to the current state.
        - Clears the transition history and state history.
        - Removes the actual transitions from the state machine graph.
        - Resets the remaining AI recovery attempts to the initial value.
        - Logs a message indicating that the state machine execution is completed and cleanup has been performed.

        Returns:
            None
        """
        try:
            cls._ensure_allowed_end_state()
        except Exception as e:
            logger.error(f"Error during end state check: {e}")
            raise e
        finally:
            cls._final_state = cls._current_state
            cls._transition_history.clear()
            cls._state_history.clear()
            # remove actual transitions from the graph
            cls._graph.remove_edges_from(
                [
                    (u, v, k)
                    for u, v, k, data in cls._graph.edges(keys=True, data=True)
                    if data.get("mode") == "actual"
                ]
            )
            cls._mode = "planned"
            cls._runtime_error_details = None
            cls._ai_recovery_agent = None
            cls._next_target_state = None

            logger.info("State machine execution completed, cleanup performed.")
        return None

    @classmethod
    def _write_ai_recovery_prompt(
        cls,
        scenario: Literal["exit", "runtime_error", "unexpected_state"],
        error_details: Optional[str] = None,
    ) -> str:
        # If no transition history is available, we are dealing with an error from the previous instance
        if scenario == "unexpected_state" and not cls._transition_history:
            start_nodes = ", ".join(
                [
                    f"{node} ({data.get('description')})"
                    for node, data in cls._graph.nodes(data=True)
                    if data.get("start_allowed") == True
                ]
            )
            action_prompt = f"The process just started but the system is in an unexpected state. We need to return to one of the known states: {start_nodes}."
        # If the ScreenPilot is exiting, we just need to clean up the system for the next instance
        elif scenario == "exit":
            end_nodes = ", ".join(
                [
                    f"{node} ({data.get('description')})"
                    for node, data in cls._graph.nodes(data=True)
                    if data.get("end_allowed") == True
                ]
            )
            action_prompt = f"The process has completed and we need to bring the system back to a state where we can exit safely: {end_nodes}."
        # If we have error details, we assume an error during a transition
        elif scenario == "runtime_error":
            attempted_transition = cls._transition_history[-1]
            attempted_transition_description = attempted_transition.__doc__
            previous_state = cls._state_history[-1]
            previous_state_description = next(
                (
                    data.get("description")
                    for node, data in cls._graph.nodes(data=True)
                    if node == previous_state
                ),
                "",  # Default value if no description is found
            )
            action_prompt = f"We tried performing '{attempted_transition.__name__}' ({attempted_transition_description}) but ran into an error: {error_details}. Could you try and remove possible causes of the error? It could be e.g. a popup, or window focus. We want to return to the previous state, {previous_state} ({previous_state_description})."
        # Otherewise we assume  atransition has completed but the resulting screen is not as expected
        else:
            attempted_transition = cls._transition_history[-1]
            attempted_transition_description = attempted_transition.__doc__
            target_state = cls._next_target_state
            target_state_description = next(
                (
                    data.get("description")
                    for node, data in cls._graph.nodes(data=True)
                    if node == target_state
                ),
                "",  # Default value if no description is found
            )
            action_prompt = f"We tried performing '{attempted_transition.__name__}' ({attempted_transition_description}) and expected to see state '{target_state}' ({target_state_description}) but the screen does not match the expected state."
        return action_prompt

    @classmethod
    def _attempt_ai_recovery(
        cls,
        scenario: Literal["exit", "runtime_error", "unexpected_state"],
        attempts: int = 5,
        error_details: Optional[str] = None,
    ) -> None:
        """
        Attempt AI recovery in case of an error state.
        Args:
            attempts (int, optional): The number of attempts to recover using AI.
            error_details (str, optional): Details of the error that occurred.
        Returns:
            None
        """
        # import actions used in AI recovery
        from ..ui_actions import (
            LeftClick,
            DoubleClick,
            SendKeys,
            PressKeys,
            ActivateWindow,
            CloseWindow,
        )

        # Initialize CourseCorrector, if not already initialized
        if not cls._ai_recovery_agent and cls.ai_recovery_agent_factory is not None:
            action_prompt = cls._write_ai_recovery_prompt(scenario, error_details)
            cls._ai_recovery_agent = cls.ai_recovery_agent_factory(
                goal=action_prompt, custom_instructions=cls.ai_recovery_instructions
            )
            if cls._ai_recovery_agent is not None:
                logger.debug(
                    f"AI recovery agent {cls._ai_recovery_agent.name} initialized with prompt: '{action_prompt}'",
                )
        if cls._ai_recovery_agent is not None:
            attempts_made = 0

            while attempts_made < attempts:
                attempts_made += 1
                logger.info(
                    f"AI recovery attempt {attempts_made} / {attempts}",
                )
                action: Optional[ActionString] = None
                try:
                    # Get corrective actions from the course corrector and execute the first one
                    action = cls._ai_recovery_agent.get_corrective_actions()[0]
                    logger.info(f"Corrective action: {action}")

                    # If no action is suggested, break the loop and return None
                    if action.action_string.startswith("NoAction"):
                        return None

                    try:
                        eval(action.action_string)
                        cls._acted_since_state_eval = True
                        break
                    except (
                        AttributeError,
                        SyntaxError,
                        ValidationError,
                        NameError,
                    ) as e:
                        cls._ai_recovery_agent.add_feedback(str(e))
                        logger.error(f"Error during AI recovery: {e}")
                        logger.info(
                            f"Retrying with feedback to course corrector: {cls._ai_recovery_agent.get_latest_feedback()}",
                        )
                        continue
                    except RuntimeError:
                        cls._ai_recovery_agent.add_feedback(
                            "The target could not be uniquely identified. Try using different anchors or target."
                        )
                        logger.error("Runtime error during AI recovery.")
                        logger.info(
                            f"Retrying with feedback to course corrector: {cls._ai_recovery_agent.get_latest_feedback()}",
                        )
                        continue
                    except PerformActionException:
                        cls._ai_recovery_agent.add_feedback(
                            "The action could not be performed."
                        )
                        logger.error("PerformActionException during AI recovery.")
                        logger.info(
                            f"Retrying with feedback to course corrector: {cls._ai_recovery_agent.get_latest_feedback()}",
                        )
                        continue

                except Exception as e:
                    logger.error(f"Unexpected error during AI recovery: {e}")
                    logger.info("Interrupting AI recovery.")
                    break
                finally:
                    # Interrupt the process if the action is impossible to process
                    if not action:
                        raise CourseCorrectionImpossible(
                            "No course correction action could be generated, see logs for details."
                        )
                    elif action.interrupt_process:
                        raise CourseCorrectionImpossible(action.observation)
                    screenshot_and_log("Completed AI recovery")
            cls._ai_recovery_agent.reset_feedback()

    @classmethod
    def _get_next_transition(cls, **kwargs) -> Tuple[Callable, str]:
        """
        Get the next transition function based on the current state.
        Args:
            **kwargs: Additional arguments for the condition functions.

        Returns:
            Callable: The next transition function.
            str: The next state.
        """
        possible_transitions = cls._graph.out_edges(
            cls._current_state, keys=True, data=True
        )
        if not possible_transitions:
            logger.error(
                f"No available {cls._mode} transitions from {cls._current_state}.",
            )
        for _, to_state, key, data in possible_transitions:
            if data.get("mode") == cls._mode:
                # Execute the first transition which has no condition or has a condition that evaluates to True
                condition: Optional[Callable] = data.get("condition", None)
                if not condition:
                    return data.get("func"), to_state
                else:
                    # Argument filtering
                    sig = inspect.signature(condition)
                    supported_params = sig.parameters
                    filtered_kwargs = {
                        k: v for k, v in kwargs.items() if k in supported_params
                    }
                    if condition(**filtered_kwargs):
                        return data.get("func"), to_state

        # raise an error to prevent failing in run()
        err_msg = f"Cannot get a valid transition from {cls._current_state} in {cls._mode} mode. {len(possible_transitions)} transitions available, but none of them match the mode and conditions."
        logger.error(err_msg)
        raise ValueError(err_msg)

    @staticmethod
    def _default_goal_function(current_state: str) -> None:
        """
        Default goal function for the state machine.

        Args:
            current_state (str): The current state of the state machine.
            **kwargs: Additional arguments for the goal function.

        Returns:
            None
        """
        return None

    @classmethod
    def run(
        cls, goal_function: Optional[Callable] = None, **kwargs
    ) -> Union[ScreenPilotOutcome, ScreenPilotException]:
        """
        Main loop of the state machine.

        Args:
            goal_function (Optional[Callable]): Function to evaluate the success of the current state machine execution. If no goal function is provided, the complete_ui_automation() method must be called from a transition.
                Args: current_state (str), **kwargs.
                Returns: bool.
            **kwargs: Additional arguments for the goal function and the transition functions (will be dynamically filtered as needed).

        Returns:
                - Exit reason (ScreenPilotOutcome): Exception class that interrupted the state machine execution.
        """
        if not goal_function:
            goal_function = cls._default_goal_function
        cls._act_on_start()
        try:
            while not cls._exit_reason:
                # Detect anti-patterns (raises exceptions if detected)
                cls._find_anti_patterns()

                # Evaluate the current state and check for completion
                cls._evaluate_state()
                cls._evaluate_goal_function(goal_function, **kwargs)

                # Attempt AI recovery if required
                if cls._current_state == "Error" and cls.ai_recovery:
                    cls._attempt_ai_recovery(
                        scenario="unexpected_state", attempts=cls.ai_recovery_attempts
                    )
                    continue
                # Reset course corrector if the state is not Error
                else:
                    cls._ai_recovery_agent = None

                # Find possible transitions from the current state
                if cls._current_state not in cls._graph:
                    err_msg: str = (
                        f"Current state {cls._current_state} is not recognized."
                    )
                    logger.error(err_msg)
                    raise ValueError(err_msg)
                next_transition, cls._next_target_state = cls._get_next_transition(
                    **kwargs
                )

                # Execute the transition function
                cls._log_transition(next_transition)
                cls._acted_since_state_eval = True
                next_transition(**kwargs)  # Execute the transition function

        except (BusinessException, SuccessfulCompletion) as e:
            cls._exit_reason = e
        except Exception as e:
            logger.error(traceback.format_exc())
            raise e
        finally:
            cls._act_on_completed()
        return cls._exit_reason

    @classmethod
    def _ensure_allowed_end_state(cls):
        # If actions have been performed since the last state evaluation, evaluate the state again
        if cls._acted_since_state_eval:
            cls._evaluate_state()
        end_states = [
            state
            for state, data in cls._graph.nodes(data=True)
            if data.get("end_allowed") == True
        ]
        if cls._current_state not in end_states and cls.ai_recovery:
            cls._attempt_ai_recovery(scenario="exit", attempts=cls.ai_recovery_attempts)


def _action_line_from_exc() -> Tuple[str, str, str]:
    """
    Format the current exception to extract the action line and action string.
    Returns:
        Tuple[str, str, str]: Tuple with the full traceback, line with action, and action string.
    """
    import sys

    (
        exc_type,
        exc_value,
        exc_traceback,
    ) = sys.exc_info()  # Capture the current exception info
    tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    output = (
        "\n".join(tb_lines),
        "",
        "",
    )  # Tuple: (full traceback, line with action, action)
    for line in tb_lines:
        if ".do(" in line:
            import re

            # Match anything after an action type and before do()
            match = re.search(
                r"(LeftClick|PressKeys|SendKeys|DoubleClick|WaitFor|RightClick|OpenApplication|MaximizeWindow|CloseWindow|ActivateWindow|SaveFiles|DeleteFiles|\(.*?\)\.do\((.*)\))",
                line,
            )
            if match:
                output = (output[0], line, match.group(0))
                break
    return output


def screenshot_and_log(message: str, screenshot_folder: str = "screenshots") -> None:
    logger.info(message)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    screenshot_name = f"{message.replace(' ', '_')}.png"
    save_screenshot(f"{timestamp}_{screenshot_name}", screenshot_folder)
    logger.info(
        f"Saved screenshot {timestamp}_{screenshot_name} in {screenshot_folder}."
    )
    return None
