from datetime import datetime
import json
import mimetypes
import os
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from clerk.models.document_statuses import DocumentStatuses
from clerk.models.file import ParsedFile


class Document(BaseModel):
    id: str
    project_id: str
    title: str
    upload_date: datetime
    requestor: Optional[str] = None
    message_subject: Optional[str] = None
    message_content: Optional[str] = None
    message_html: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None
    status: DocumentStatuses
    created_at: datetime
    updated_at: datetime


class UploadDocumentRequest(BaseModel):
    workflow_id: str
    message_subject: Optional[str] = None
    message_content: Optional[str] = None
    files: List[str | ParsedFile] = []
    input_structured_data: Dict[str, Any] | None = None

    def _define_files(self):
        formatted_files: List[
            tuple[
                str,
                tuple[
                    str,
                    bytes,
                    str | None,
                ],
            ]
        ] = []

        for file in self.files:
            if isinstance(file, str):
                if os.path.exists(file):
                    tmp = (
                        "files",
                        (
                            os.path.basename(file).replace(" ", "_"),
                            open(file, "rb").read(),
                            mimetypes.guess_type(file)[0],
                        ),
                    )

                else:
                    raise FileExistsError(file)
            else:
                tmp = (
                    "files",
                    (
                        file.name,
                        file.decoded_content,
                        file.mimetype,
                    ),
                )
            formatted_files.append(tmp)

        return formatted_files

    @property
    def data(self) -> Dict[str, Any]:

        serialized_input_structured_data: str | None = None
        if self.input_structured_data:
            try:
                serialized_input_structured_data = json.dumps(
                    self.input_structured_data
                )
            except Exception as e:
                raise ValueError(
                    f"`input_structured_data` is not JSON serializable: {e}"
                )

        return dict(
            workflow_id=self.workflow_id,
            message_subject=self.message_subject,
            mesasge_content=self.message_content,
            input_structured_data=serialized_input_structured_data,
        )

    @property
    def files_(self):
        return self._define_files()


class GetDocumentsRequest(BaseModel):
    organization_id: str | None = None
    project_id: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    query: str | None = None
    include_statuses: List[DocumentStatuses] | None = None
    limit: int = 50
