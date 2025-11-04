from datetime import datetime
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
    project_id: str
    message_subject: Optional[str] = None
    message_content: Optional[str] = None
    files: List[str | ParsedFile] = []

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
        return dict(
            project_id=self.project_id,
            message_subject=self.message_subject,
            mesasge_content=self.message_content,
        )

    @property
    def files_(self):
        return self._define_files()
