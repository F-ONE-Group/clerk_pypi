"""Context Agent - Fetch and save project schema with document structured data"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console

from clerk.client import Clerk
from clerk.development.schema.fetch_schema import (
    fetch_schema,
    generate_models_from_schema,
    VariableData,
)
from clerk.exceptions.exceptions import ApplicationException

console = Console()


def fetch_context(
    project_id: str, document_id: str
) -> tuple[List[VariableData], Dict[str, Any]]:
    """
    Fetch schema and document structured data for a given project and document.

    Args:
        project_id: The project ID to fetch schema for
        document_id: The document ID to fetch structured data for

    Returns:
        Tuple of (schema_data, structured_data)

    Raises:
        ApplicationException: If API calls fail
    """
    # Fetch schema
    console.print(f"[cyan]Fetching schema for project: {project_id}[/cyan]")
    schema_data = fetch_schema(project_id)

    # Fetch document
    console.print(f"[cyan]Fetching document: {document_id}[/cyan]")
    try:
        client = Clerk()
        document = client.get_document(document_id)
    except Exception as e:
        raise ApplicationException(message=f"Failed to fetch document: {str(e)}")

    structured_data = document.structured_data or {}

    return schema_data, structured_data


def save_schema_file(schema_data: List[VariableData], target_dir: Path) -> Path:
    """
    Save schema as a Python file with Pydantic models.

    Args:
        schema_data: List of VariableData objects
        target_dir: Directory to save the file

    Returns:
        Path to the saved file
    """
    output_path = target_dir / "schema.py"
    generate_models_from_schema(schema_data, output_path)
    return output_path


def save_data_file(structured_data: Dict[str, Any], target_dir: Path) -> Path:
    """
    Save structured data as a JSON file.

    Args:
        structured_data: The structured data dictionary
        target_dir: Directory to save the file

    Returns:
        Path to the saved file
    """
    output_path = target_dir / "data.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(structured_data, f, indent=2, ensure_ascii=False, default=str)
    return output_path


def main_with_args(
    project_id: str, document_id: str, target_dir: Optional[str] = None
) -> None:
    """
    Main entry point for context-agent command.

    Args:
        project_id: The project ID
        document_id: The document ID
        target_dir: Optional target directory (default: current working directory)
    """
    try:
        schema_data, structured_data = fetch_context(project_id, document_id)

        output_dir = Path(target_dir) if target_dir else Path.cwd()
        output_dir.mkdir(parents=True, exist_ok=True)

        schema_path = save_schema_file(schema_data, output_dir)
        data_path = save_data_file(structured_data, output_dir)

        console.print(f"[green]✓ Schema saved to: {schema_path}[/green]")
        console.print(f"[green]✓ Data saved to: {data_path}[/green]")
        console.print(f"  Schema variables: {len(schema_data)}")

    except ApplicationException as e:
        console.print(f"[red]Error: {e.message}[/red]")
        raise SystemExit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {str(e)}[/red]")
        raise SystemExit(1)
