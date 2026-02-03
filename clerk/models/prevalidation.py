from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class LabelWithDescriptions(BaseModel):
    label: str = Field(..., description="The label/category name")
    description: Optional[str] = Field(
        None, description="Optional description of the label/category"
    )
    attributes: Optional[List[str]] = Field(
        None, description="Optional attributes for the label/category"
    )
    start_page: Optional[int] = Field(
        None, description="Start page for classification (0-based, inclusive)"
    )
    end_page: Optional[int] = Field(
        None, description="End page for classification (0-based, exclusive)"
    )


class FileClassificationResponse(BaseModel):
    valid: bool = Field(False, description="Whether the file classification is valid")
    filename: str = Field(..., description="The name of the file that was classified")
    classification: Optional[str] = Field(
        None, description="The selected classification category"
    )
    reason: Optional[str] = Field(
        None,
        description="The reasoning behind the classification. To be filled if no classification is made.",
    )
    possible_categories: Optional[Dict[str, LabelWithDescriptions]] = Field(
        None, description="Possible categories for classification"
    )
