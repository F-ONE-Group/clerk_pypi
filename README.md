# CLERK

`clerk-sdk` is a Python library designed to simplify interactions with the Clerk API. It provides a robust and user-friendly interface for managing documents, handling API requests, and integrating structured data models into your workflows. `clerk-sdk` is ideal for developers looking to streamline their integration with Clerk.

## Features

- **Document Management**: Retrieve and manage documents and their associated files.
- **API Request Handling**: Simplified GET and POST requests with automatic retries and error handling.
- **Data Models**: Predefined Pydantic models for structured data validation and serialization.
- **Task Flow Integration**: Decorator for creating and managing task flows.
- **Extensibility**: Easily extend and customize the library to fit your specific use case.

## Installation

Install the library using pip:

```bash
pip install clerk-sdk
```

## Usage

### Initialize the Client

```python
from clerk import Clerk

clerk_client = Clerk(api_key="your_api_key")
```

### Retrieve a Document

```python
document = clerk_client.get_document(document_id="12345")
print(document.title)
```

### Retrieve Files Associated with a Document

```python
files = clerk_client.get_files_document(document_id="12345")
for file in files:
    print(file.name)
```

### Use the Task Decorator

#### PROD

```python
from clerk.decorator import clerk_code
from clerk.decorator.models import ClerkCodePayload

@clerk_code()
def main(payload: ClerkCodePayload) -> ClerkCodePayload:
    payload.structured_data["status"] = "ok"
    return payload

main()
```

#### TEST

```python
from clerk.decorator.models import ClerkCodePayload, Document

def test_main():
    test_payload = ClerkCodePayload(
        document=Document(id="doc-123", message_subject="Hello"),
        structured_data={}
    )

    result = main(test_payload)  # ✅ Just pass it!
    assert result.structured_data["status"] == "ok"
```


## Requirements

- Python 3.10+
- Dependencies listed in `requirements.txt`:
  - `pydantic>2.0.0`
  - `backoff>2.0.0`

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please submit a pull request or open an issue to discuss your ideas.