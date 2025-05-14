import datetime
from typing import Dict, Optional
from pydantic import BaseModel

from clerk.models.document_statuses import DocumentStatuses


class Document(BaseModel):
    id: str
    project_id: str
    title: str
    upload_date: datetime
    requestor: Optional[str] = None
    message_subject: Optional[str] = None
    message_content: Optional[str] = None
    message_html: Optional[str] = None
    structured_data: Optional[Dict] = None
    status: DocumentStatuses
    created_at: datetime
    updated_at: datetime
