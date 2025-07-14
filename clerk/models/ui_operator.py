from enum import Enum
from typing import Optional
from pydantic import BaseModel


class TaskStatuses(str, Enum):
    OPEN = "open"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class UiOperatorTask(BaseModel):
    id: str
    status: TaskStatuses
    assignee_name: Optional[str]
