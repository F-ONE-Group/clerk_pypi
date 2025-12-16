from pathlib import Path
from typing import Any, List, Optional, Dict, Tuple
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field
import requests

from rich.console import Console

from clerk.client import Clerk
from clerk.exceptions.exceptions import ApplicationException

console = Console()


class VariableTypes(str, Enum):
    STRING = "string"
    NUMBER = "number"
    DATE = "date"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    TIME = "time"
    OBJECT = "object"
    ENUM = "enum"


class VariableData(BaseModel):
    id: str
    name: str
    display_name: str
    tags: List[str] = []
    units: Optional[str] = None
    description: Optional[str] = None
    is_array: bool
    parent_id: Optional[str] = None
    type: VariableTypes
    position_index: int
    additional_properties: Optional[bool] = None
    default: Any | None = None
    enum_options: List[str] = Field(default_factory=list)


def fetch_schema(project_id: str) -> List[VariableData]:
    """
    Fetch schema from Clerk backend for a given project.

    Args:
        project_id: The project ID to fetch schema for

    Returns:
        List of VariableData objects

    Raises:
        ApplicationException: If the API key is invalid (401)
        ApplicationException: If the project_id is invalid or not found (404)
        ApplicationException: If there's another API error
    """
    try:
        client = Clerk()
    except ValueError as e:
        raise ApplicationException(
            message=f"Invalid or missing API key. Please set CLERK_API_KEY environment variable or provide it explicitly. Error: {str(e)}"
        )

    endpoint = "/schema"
    params = {"project_id": project_id}

    try:
        res = client.get_request(endpoint=endpoint, params=params)
        return [VariableData.model_validate(item) for item in res.data]
    except requests.exceptions.HTTPError as e:
        if e.response is not None:
            status_code = e.response.status_code
            if status_code == 401:
                raise ApplicationException(
                    message="Invalid API key. Please check your CLERK_API_KEY."
                )
            elif status_code == 404:
                raise ApplicationException(
                    message=f"Project not found. The project_id '{project_id}' does not exist or you don't have access to it."
                )
            elif status_code == 403:
                raise ApplicationException(
                    message=f"Access forbidden. You don't have permission to access project '{project_id}'."
                )
            else:
                raise ApplicationException(
                    message=f"API error (HTTP {status_code}): {e.response.text}"
                )
        else:
            raise ApplicationException(message=f"HTTP error occurred: {str(e)}")
    except requests.exceptions.RequestException as e:
        raise ApplicationException(
            message=f"Network error while fetching schema: {str(e)}"
        )


def _python_type_from_variable(
    var: VariableData, nested_models: Dict[str, str]
) -> Tuple[str, bool]:
    """Convert VariableData type to Python type string

    Returns:
        tuple of (type_string, is_leaf_value)
        is_leaf_value is True for primitive types, False for lists and BaseModels
    """
    type_map = {
        VariableTypes.STRING: "str",
        VariableTypes.NUMBER: "float",
        VariableTypes.DATE: "date",
        VariableTypes.DATETIME: "datetime",
        VariableTypes.TIME: "time",
        VariableTypes.BOOLEAN: "bool",
        VariableTypes.ENUM: "str",  # Will be refined with Literal if enum_options exist
    }

    is_leaf = True  # Assume leaf unless it's a list or object

    if var.type == VariableTypes.OBJECT:
        # Use the nested model class name
        base_type = nested_models.get(var.id, "Dict[str, Any]")
        is_leaf = False  # Objects are not leaf values
    elif var.type == VariableTypes.ENUM and var.enum_options:
        # Create Literal type for enum
        options = ", ".join([f'"{opt}"' for opt in var.enum_options])
        base_type = f"Literal[{options}]"
    else:
        base_type = type_map.get(var.type, "Any")

    # Handle arrays
    if var.is_array:
        is_leaf = False  # Lists are not leaf values
        return f"List[{base_type}]", is_leaf

    return base_type, is_leaf


def generate_models_from_schema(
    variables: List[VariableData], output_file: Optional[Path] = None
) -> str:
    """
    Generate Pydantic BaseModel classes from schema variables.
    
    Args:
        variables: List of VariableData objects
        output_file: Optional path to write the generated code
        
    Returns:
        Generated Python code as string
    """
    # Group variables by parent_id
    root_vars: List[VariableData] = []
    nested_vars: Dict[str, List[VariableData]] = {}

    for var in sorted(variables, key=lambda v: v.position_index):
        if var.parent_id is None:
            root_vars.append(var)
        else:
            if var.parent_id not in nested_vars:
                nested_vars[var.parent_id] = []
            nested_vars[var.parent_id].append(var)

    # Map variable IDs to their generated class names using name field
    nested_models: Dict[str, str] = {}
    var_id_to_data: Dict[str, VariableData] = {var.id: var for var in variables}

    for parent_id in nested_vars.keys():
        parent_var = var_id_to_data.get(parent_id)
        if parent_var and parent_var.name:
            # Use name field and convert snake_case to PascalCase
            class_name = "".join(
                word.capitalize() for word in parent_var.name.split("_")
            )
        else:
            # Fallback to parent_id
            class_name = "".join(word.capitalize() for word in parent_id.split("_"))
        nested_models[parent_id] = class_name

    code_lines: List[str] = []

    # Autogenerated code comment with sync timestamp
    sync_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    code_lines.append(
        f"# Autogenerated by the fetch_schema tool - do not edit manually."
    )
    code_lines.append(f"# Last fetched: {sync_timestamp}\n")

    # Generate imports
    imports = [
        "from typing import Any, List, Optional, Dict",
        "from datetime import date, datetime, time",
        "from pydantic import BaseModel, Field",
    ]

    # Check if we need Literal
    has_enums = any(var.type == VariableTypes.ENUM and var.enum_options for var in variables)
    if has_enums:
        imports[0] = "from typing import Any, List, Optional, Dict, Literal"

    code_lines.extend(imports)
    code_lines.append("")

    # Generate nested models first (bottom-up)
    generated_classes = set()

    def generate_class(var_id: str, vars_list: List[VariableData], class_name: str):
        if class_name in generated_classes:
            return

        # First generate any nested children
        for var in vars_list:
            if var.type == VariableTypes.OBJECT and var.id in nested_vars:
                child_class_name = nested_models[var.id]
                generate_class(var.id, nested_vars[var.id], child_class_name)

        # Generate this class
        code_lines.append(f"class {class_name}(BaseModel):")

        if not vars_list:
            code_lines.append("    pass")
        else:
            for var in sorted(vars_list, key=lambda v: v.position_index):
                field_name = var.name
                python_type, is_leaf = _python_type_from_variable(var, nested_models)

                # Make leaf values Optional and default to None
                if is_leaf:
                    python_type = f"Optional[{python_type}]"

                # Build field definition
                field_parts = []
                if var.description:
                    # Escape double quotes and newlines in description
                    escaped_desc = (
                        var.description.replace('"', '\\"')
                        .replace("\n", "\\n")
                        .replace("\r", "")
                    )
                    field_parts.append(f'description="{escaped_desc}"')

                # Set default to None for leaf values, or use existing default
                if is_leaf:
                    if var.default is not None:
                        field_parts.append(f"default={repr(var.default)}")
                    else:
                        field_parts.append("default=None")
                elif var.default is not None:
                    field_parts.append(f"default={repr(var.default)}")

                if field_parts:
                    field_def = f"Field({', '.join(field_parts)})"
                    code_lines.append(f"    {field_name}: {python_type} = {field_def}")
                else:
                    code_lines.append(f"    {field_name}: {python_type}")

        code_lines.append("")
        generated_classes.add(class_name)

    # Generate all nested models
    for var_id, vars_list in nested_vars.items():
        class_name = nested_models[var_id]
        generate_class(var_id, vars_list, class_name)

    # Generate root model
    code_lines.append("class StructuredData(BaseModel):")
    if not root_vars:
        code_lines.append("    pass")
    else:
        for var in sorted(root_vars, key=lambda v: v.position_index):
            field_name = var.name
            python_type, is_leaf = _python_type_from_variable(var, nested_models)

            # Make leaf values Optional and default to None
            if is_leaf:
                python_type = f"Optional[{python_type}]"

            # Build field definition
            field_parts = []
            if var.description:
                # Escape double quotes and newlines in description
                escaped_desc = (
                    var.description.replace('"', '\\"')
                    .replace("\n", "\\n")
                    .replace("\r", "")
                )
                field_parts.append(f'description="{escaped_desc}"')

            # Set default to None for leaf values, or use existing default
            if is_leaf:
                if var.default is not None:
                    field_parts.append(f"default={repr(var.default)}")
                else:
                    field_parts.append("default=None")
            elif var.default is not None:
                field_parts.append(f"default={repr(var.default)}")

            if field_parts:
                field_def = f"Field({', '.join(field_parts)})"
                code_lines.append(f"    {field_name}: {python_type} = {field_def}")
            else:
                code_lines.append(f"    {field_name}: {python_type}")

    generated_code = "\n".join(code_lines)

    # Write to file if specified
    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(generated_code)

    return generated_code


def main_with_args(project_id: str, project_root: Path | None = None):
    """Main logic that can be called from CLI or programmatically"""
    try:
        with console.status(
            f"[dim]Fetching schema for project: {project_id}...", spinner="dots"
        ):
            variables = fetch_schema(project_id)

        console.print(f"[green]+[/green] Found {len(variables)} variables")

        # Always save to schema.py in project root
        if project_root is None:
            project_root = Path.cwd()
        output_file = project_root / "src" / "schema.py"

        with console.status("[dim]Generating Pydantic models...", spinner="dots"):
            generate_models_from_schema(variables, output_file)

        console.print(
            f"[green]+[/green] Schema generated and written to: {output_file}"
        )
    except ApplicationException as e:
        console.print(f"[red]x Error: {e.message}[/red]")
        raise
    except Exception as e:
        console.print(f"[red]x Unexpected error: {str(e)}[/red]")
        raise
