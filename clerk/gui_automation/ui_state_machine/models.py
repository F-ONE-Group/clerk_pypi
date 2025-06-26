from typing import Optional
from pydantic import BaseModel, field_validator, model_validator


class ActionString(BaseModel):
    """
    ActionString class represents a string that represents an action in an application.

    Attributes:
        action_string (str): The string representation of the action.
        comment (str, optional): An optional comment or description for the action.
        interrupt_process (bool, optional): A flag indicating whether the action should interrupt the process.

    Methods:
        ensure_format(v: str) -> str:
            Validator function that ensures the action string has the correct format.

    """

    action_string: str
    action_comment: Optional[str] = None
    observation: Optional[str] = None
    interrupt_process: Optional[bool] = False

    @field_validator("action_string", mode="before")
    @classmethod
    def ensure_format(cls, v):
        if not isinstance(v, str):
            raise ValueError("Action string must be a string")
        if not v.endswith(".do()") and not v.startswith("NoAction"):
            raise ValueError("Action string must end with '.do()'")
        return v

    @field_validator("interrupt_process", mode="before")
    def convert_to_bool(cls, v):
        if v is None:
            return False
        elif isinstance(v, str):
            return v.lower() in ["true", "1", "yes"]
        return v
