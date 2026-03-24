from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import StrEnum

from pydantic import BaseModel, Field


class VariableTypes(StrEnum):
    STRING = "string"
    NUMBER = "number"
    DATE = "date"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    TIME = "time"
    OBJECT = "object"
    ENUM = "enum"


class DatasetTypes(StrEnum):
    CODE_LIST = "code_list"
    STANDARD = "standard"


class DatasetMetadata(BaseModel):
    id: str
    domain_id: Optional[str] = None
    organization_id: Optional[str] = None
    project_id: Optional[str] = None
    type: DatasetTypes
    display_name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    row_count: int = 0


class DatasetColumn(BaseModel):
    id: str
    dataset_id: str
    name: str
    display_name: str
    data_type: VariableTypes
    position_index: int = 0
    is_required: bool = False
    is_unique: bool = False
    created_at: datetime
    updated_at: datetime


class DatasetRow(BaseModel):
    id: str
    dataset_id: str
    position_index: int
    created_at: datetime
    updated_at: datetime
    values: Dict[str, Any] = Field(default_factory=lambda: {})


class DatasetDownload(BaseModel):
    metadata: DatasetMetadata
    columns: List[DatasetColumn] = Field(default_factory=lambda: [])
    rows: List[DatasetRow] = Field(default_factory=lambda: [])
