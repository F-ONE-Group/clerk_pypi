# Clerk Python SDK

A production-ready Python client for the Clerk API. The SDK wraps Clerk's REST endpoints, rich document models, automation helpers, and structured task decorators so that your applications can create, update, and process Clerk documents with minimal boilerplate.

## Table of Contents
- [Overview](#overview)
- [Key Features](#key-features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Quick Start](#quick-start)
  - [Instantiate a Client](#instantiate-a-client)
  - [Fetch Documents](#fetch-documents)
  - [Upload a Document](#upload-a-document)
  - [Update Structured Data](#update-structured-data)
  - [Work with Files](#work-with-files)
- [Automation Utilities](#automation-utilities)
  - [Task Decorator](#task-decorator)
  - [GUI Automation Toolkit](#gui-automation-toolkit)
- [Error Handling](#error-handling)
- [Development Workflow](#development-workflow)
- [Contributing](#contributing)
- [License](#license)

## Overview
The Clerk SDK centers around the `Clerk` client (`clerk.client.Clerk`), which extends a resilient `BaseClerk` transport layer with automatic retries and typed responses. Models under `clerk.models` provide Pydantic-powered validation for documents, files, and API payloads, ensuring type safety across network boundaries. Additional modules cover automated task execution via the `clerk.decorator` package and UI workflows under `clerk.gui_automation`.

## Key Features
- **Document lifecycle management** – Create, fetch, list, and update Clerk documents with first-class models.
- **File handling** – Upload binary files or parsed base64 payloads and attach them to documents.
- **Robust networking** – Automatic retries for transient HTTP issues, configurable base URLs, and bearer authentication out of the box.
- **Structured task execution** – Decorators for running Clerk tasks locally or inside worker environments with consistent pickle-based I/O.
- **GUI automations** – Utilities for orchestrating low-level UI actions, state machines, and operator interactions when human-in-the-loop steps are required.

## Requirements
- Python 3.10+
- Dependencies listed in [`requirements.txt`](requirements.txt), including `pydantic` and `backoff`.

## Installation
Install the SDK from PyPI:

```bash
pip install clerk-sdk
```

For local development inside this repository, install the dependencies in editable mode:

```bash
pip install -e .[dev]
```

## Configuration
The client reads configuration from keyword arguments or environment variables.

| Setting | Environment Variable | Description |
| --- | --- | --- |
| API key | `CLERK_API_KEY` | Required secret used for bearer authentication. |
| Base URL | `CLERK_BASE_URL` | Optional override of the default API host (`https://api.clerk-app.com`). |

```bash
export CLERK_API_KEY="sk_live_123"
export CLERK_BASE_URL="https://staging.clerk-app.com"  # optional
```

You can also pass the API key directly when instantiating `Clerk`:

```python
from clerk import Clerk

client = Clerk(api_key="sk_live_123")
```

## Quick Start
The following snippets demonstrate the core document operations supported by the SDK.

### Instantiate a Client
```python
from clerk import Clerk

client = Clerk(api_key="sk_live_123")
```

### Fetch Documents
Retrieve a single document by its identifier or list documents with query filters.

```python
from clerk.models.document import GetDocumentsRequest

# Single document
invoice = client.get_document(document_id="doc_123")
print(invoice.title, invoice.status)

# Query multiple documents
request = GetDocumentsRequest(project_id="proj_456", limit=25)
documents = client.get_documents(request)
for doc in documents:
    print(doc.id, doc.status)
```

### Upload a Document
Use `UploadDocumentRequest` to send metadata and file attachments. Files can be supplied as paths or `ParsedFile` instances.

```python
from clerk.models.document import UploadDocumentRequest

upload_request = UploadDocumentRequest(
    workflow_id="proj_456",
    message_subject="Invoice 2024-01",
    files=["/path/to/invoice.pdf"],
    input_structured_data={"customer_id": "cust_789"},
)

created = client.upload_document(upload_request)
print(f"Created document: {created.id}")
```

### Update Structured Data
Patch a document's structured payload without re-uploading files.

```python
updated = client.update_document_structured_data(
    document_id="doc_123",
    updated_structured_data={"status": "processed", "processed_by": "automation"},
)
print(updated.structured_data)
```

### Work with Files
Retrieve parsed file metadata or attach additional files to existing documents.

```python
from clerk.models.file import UploadFile

# List associated files
files = client.get_files_document(document_id="doc_123")
for file in files:
    print(file.name, file.mimetype)

# Append output files
client.add_files_to_document(
    document_id="doc_123",
    type="output",
    files=[
        UploadFile(name="summary.txt", mimetype="text/plain", content=b"Processed")
    ],
)
```

## Custom Code Utilities
### Task Decorator
The `@clerk_code` decorator standardizes how Clerk tasks load inputs and persist outputs when executed by the Clerk workflow. It automatically reads a pickled `ClerkCodePayload` from `/app/data/input/input.pkl`, executes your function, and writes the result (or an `ApplicationException`) to `/app/data/output/output.pkl`.

```python
from clerk.decorator import clerk_code
from clerk.decorator.models import ClerkCodePayload, Document

@clerk_code()
def handle_document(payload: ClerkCodePayload) -> ClerkCodePayload:
    document: Document = payload.document
    payload.structured_data = payload.structured_data or {}
    payload.structured_data["status"] = f"Processed {document.id}"
    return payload

if __name__ == "__main__":
    handle_document()  # Auto-loads from pickle files when payload is omitted
```

For unit testing, you can bypass the pickle integration by passing an explicit payload instance:

```python
from datetime import datetime
from clerk.decorator.models import ClerkCodePayload, Document
from clerk.models.document_statuses import DocumentStatuses

sample_payload = ClerkCodePayload(
    document=Document(
        id="doc_123",
        project_id="proj_456",
        title="Sample",
        upload_date=datetime.utcnow(),
        status=DocumentStatuses.draft,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    ),
    structured_data={},
)
result = handle_document(sample_payload)
assert "Processed" in result.structured_data["status"]
```

> **Note:** Refer to `tests/test_task_decorator.py` for additional usage examples covering error propagation and pickle round-trips.

### GUI Automation Toolkit
The `clerk.gui_automation` package contains models, actions, and state machines for orchestrating UI interactions. Highlights include:

- `BaseAction` and concrete actions for cursor movement, clicks, and keyboard input.
- `ActionModel` builders that translate payloads into executable UI sequences.
- State machine primitives (`ui_state_machine`) to coordinate multi-step automations.
- Helpers for safely reading files, validating anchors, and converting payload flags.

These utilities are designed to be composed with your own automation runners or integrated into Clerk tasks. Review the tests in `tests/test_gui_automation.py` for patterns on stubbing operator clients and verifying payload transformations.

## Error Handling
All network helpers raise `requests` exceptions for HTTP errors. When using the task decorator, runtime failures are wrapped in `ApplicationException` objects that capture the exception type, message, and traceback for easier debugging. Deserialize the returned payload or inspect the pickle output to handle errors gracefully.

## Development Workflow
1. **Clone the repository** and install dependencies with `pip install -e .[dev]`.
2. **Run the test suite** using `pytest`. The CI workflow executes these tests before packaging releases.
3. **Add type-safe models** or extend the client in `clerk/client.py` and `clerk/models` as needed.
4. **Contribute automations** under `clerk/gui_automation` by following the established action/state machine patterns.
5. **Commit and open a pull request** once tests pass and documentation is updated.

## Contributing
Contributions are welcome! Please open an issue to discuss substantial changes, follow the existing code style (Pydantic models, typed functions, and pytest fixtures), and ensure the test suite passes before submitting a pull request.

## License
This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
