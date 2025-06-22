from pydantic import BaseModel, field_validator, model_validator
from typing import List, Dict, Optional


class BaseState(BaseModel):
    """
    BaseState class represents a base state for an application.

    Attributes:
        id (str): The ID of the state.
        description (str): The description of the state.
        screenshots (List): A list of dictionaries representing the screenshots associated with the state.

    Methods:
        add_screenshot(bucket_name: str, file_name: str) -> None:
            Adds a screenshot to the state.

        get_screenshots_urls() -> List[str]:
            Returns a list of presigned URLs for the screenshots associated with the state.
    """

    id: str
    description: str
    screenshots: List = []

    def add_screenshot(self, bucket_name: str, file_name: str):
        self.screenshots.append({"bucket_name": bucket_name, "file_name": file_name})


class LoadingState(BaseState):
    """
    LoadingState class represents a loading state for an application.

    Attributes:
        id (str): The ID of the loading state.
        description (str): The description of the loading state.

    """

    id: str = "loading"
    description: str = (
        "the application is loading. Typically indicated by a spinner or progress bar, greyed out UI"
    )


class ErrorState(BaseState):
    """
    ErrorState class represents an error state for an application.

    Attributes:
        id (str): The ID of the error state.
        description (str): The description of the error state.

    """

    id: str = "error"
    description: str = (
        "the application is in an error state. Typically indicated by an error message, or a red banner"
    )


class ExpectedState(BaseState):
    """
    ExpectedState class represents an expected state for an application.

    Attributes:
        id (str): The ID of the state.
        description (str): The description of the state.

    """

    id: str = "expected"
    description: str = (
        "the application is in an expected state, as in the provided screenshot"
    )


class States(BaseModel):
    """
    States class represents a collection of states for an application.

    Attributes:
        possible_states (Dict[type, BaseState]): A dictionary mapping state types to their corresponding instances.
        bucket_name (str): The name of the bucket where screenshots are stored.
        process_name (str): The name of the process associated with the states.

    Methods:
        add_screenshot(state: type[BaseState], file_name: str) -> None:
            Adds a screenshot to the specified state.

        add_description(state: type[BaseState], description: str) -> None:
            Updates the description of the specified state.
    """

    possible_states: Dict[type, BaseState] = {
        LoadingState: LoadingState(),
        ErrorState: ErrorState(),
        ExpectedState: ExpectedState(),
    }
    bucket_name: str
    process_name: str

    def add_screenshot(self, state_type: type[BaseState], file_name: str):
        state = self.possible_states.get(state_type)
        if state is None:
            raise ValueError("state is not found in possible states")
        state.add_screenshot(
            bucket_name=f"{self.bucket_name}",
            file_name=f"{self.process_name}/{file_name}",
        )

    def add_description(self, state_type: type[BaseState], description: str):
        state = self.possible_states.get(state_type)
        if state is None:
            raise ValueError("state is not found in possible states")
        state.description = description


class TargetWithAnchor(BaseModel):
    """
    TargetWithAnchor class represents a target with an anchor for an application.

    Attributes:
        target (str): The target element or object.
        anchor (str): The anchor element or object that the target is related to. Default is an empty string.
        relation (str): The relation between the target and the anchor. Default is an empty string.

    Methods:
        retain_one_word(v: str) -> str:
            Validator function that retains only the last word of the target string.

    """

    target: str
    anchor: str = ""
    relation: str = ""

    @field_validator("target", mode="before")
    @classmethod
    def retain_one_word(cls, v):
        return v.split(" ")[-1]


class Answer(BaseModel):
    """
    Answer class represents the result of an operation or a response to a question.

    Attributes:
        answer (str): The answer or response.
        success (bool): Indicates whether the operation was successful or not.

    """

    answer: str
    success: bool


class ActionString(BaseModel):
    """
    ActionString class represents a string that represents an action in an application.

    Attributes:
        action_string (str): The string representation of the action.
        comment (str, optional): An optional comment or description for the action.

    Methods:
        ensure_format(v: str) -> str:
            Validator function that ensures the action string has the correct format.

    """

    action_string: str
    comment: Optional[str] = None

    @field_validator("action_string", mode="before")
    @classmethod
    def ensure_format(cls, v):
        if not isinstance(v, str):
            raise ValueError("Action string must be a string")
        if not v.startswith("LeftClick") and not v.startswith("NoAction"):
            raise ValueError("Action string must start with 'LeftClick' or 'NoAction'")
        if not v.endswith(".do()") and not v.startswith("NoAction"):
            raise ValueError("Action string must end with '.do()'")
        return v
