from pathlib import Path
from typing import Any, List, Optional, Dict
from enum import Enum
from pydantic import BaseModel, Field

from clerk.client import Clerk


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
    """
    # TODO: Replace mock data with actual API call when endpoint is ready
    # client = Clerk()
    # endpoint = f"/project/{project_id}/schema"
    # res = client.get_request(endpoint=endpoint)
    # return [VariableData.model_validate(item) for item in res.data]
    
    # Mock data for development - real example from production
    mock_data = [
        {"name":"client","display_name":"Client","tags":[],"units":None,"description":None,"is_array":False,"parent_id":None,"type":"string","position_index":0,"additional_properties":None,"default":None,"enum_options":[]},
        {"name":"orders","display_name":"Orders","tags":[],"units":None,"description":None,"is_array":True,"parent_id":None,"type":"object","position_index":0,"additional_properties":None,"default":None,"enum_options":[]},
        {"name":"amount_translogica","display_name":"Amount translogica","tags":[],"units":"€","description":None,"is_array":False,"parent_id":"orders","type":"number","position_index":2,"additional_properties":None,"default":None,"enum_options":[]},
        {"name":"order_reference","display_name":"Order reference","tags":[],"units":None,"description":None,"is_array":False,"parent_id":"orders","type":"string","position_index":0,"additional_properties":None,"default":None,"enum_options":[]},
        {"name":"amount_difference","display_name":"Amount difference","tags":[],"units":"€","description":None,"is_array":False,"parent_id":"orders","type":"number","position_index":3,"additional_properties":None,"default":None,"enum_options":[]},
        {"name":"amount","display_name":"Amount","tags":[],"units":"€","description":None,"is_array":False,"parent_id":"orders","type":"number","position_index":1,"additional_properties":None,"default":None,"enum_options":[]},
        {"name":"review_result","display_name":"Review result","tags":[],"units":None,"description":None,"is_array":False,"parent_id":"orders","type":"string","position_index":4,"additional_properties":None,"default":None,"enum_options":[]},
        {"name":"document_total_net","display_name":"Document total net","tags":[],"units":"€","description":None,"is_array":False,"parent_id":None,"type":"number","position_index":0,"additional_properties":None,"default":None,"enum_options":[]},
        {"name":"approved_to_invoice","display_name":"Approved to invoice","tags":[],"units":None,"description":None,"is_array":False,"parent_id":None,"type":"boolean","position_index":0,"additional_properties":None,"default":False,"enum_options":[]},
        {"name":"credit_note_date","display_name":"Credit note date","tags":[],"units":None,"description":None,"is_array":False,"parent_id":None,"type":"string","position_index":0,"additional_properties":None,"default":None,"enum_options":[]},
        {"name":"document_total_gross","display_name":"Document total gross","tags":[],"units":None,"description":None,"is_array":False,"parent_id":None,"type":"number","position_index":0,"additional_properties":None,"default":None,"enum_options":[]},
        {"name":"credit_note_number","display_name":"Credit note number","tags":[],"units":None,"description":None,"is_array":False,"parent_id":None,"type":"string","position_index":0,"additional_properties":None,"default":None,"enum_options":[]},
        {"name":"ge_number","display_name":"GE number","tags":[],"units":None,"description":None,"is_array":False,"parent_id":None,"type":"string","position_index":0,"additional_properties":None,"default":None,"enum_options":[]}
    ]
    
    return [VariableData.model_validate(item) for item in mock_data]


def _python_type_from_variable(var: VariableData, nested_models: Dict[str, str]) -> str:
    """Convert VariableData type to Python type string"""
    type_map = {
        VariableTypes.STRING: "str",
        VariableTypes.NUMBER: "float",
        VariableTypes.DATE: "date",
        VariableTypes.DATETIME: "datetime",
        VariableTypes.TIME: "time",
        VariableTypes.BOOLEAN: "bool",
        VariableTypes.ENUM: "str",  # Will be refined with Literal if enum_options exist
    }
    
    if var.type == VariableTypes.OBJECT:
        # Use the nested model class name
        base_type = nested_models.get(var.name, "Dict[str, Any]")
    elif var.type == VariableTypes.ENUM and var.enum_options:
        # Create Literal type for enum
        options = ", ".join([f'"{opt}"' for opt in var.enum_options])
        base_type = f"Literal[{options}]"
    else:
        base_type = type_map.get(var.type, "Any")
    
    # Handle arrays
    if var.is_array:
        return f"List[{base_type}]"
    
    return base_type


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
    
    # Map variable names to their generated class names
    nested_models: Dict[str, str] = {}
    for var_name in nested_vars.keys():
        class_name = "".join(word.capitalize() for word in var_name.split("_"))
        nested_models[var_name] = class_name
    
    code_lines: List[str] = []
    
    # Autogenerated code comment
    code_lines.append("# Autogenerated by the fetch_schema tool - do not edit manually.\n")

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
    
    def generate_class(var_name: str, vars_list: List[VariableData], class_name: str):
        if class_name in generated_classes:
            return
        
        # First generate any nested children
        for var in vars_list:
            if var.type == VariableTypes.OBJECT and var.name in nested_vars:
                child_class_name = nested_models[var.name]
                generate_class(var.name, nested_vars[var.name], child_class_name)
        
        # Generate this class
        code_lines.append(f"class {class_name}(BaseModel):")
        
        if not vars_list:
            code_lines.append("    pass")
        else:
            for var in sorted(vars_list, key=lambda v: v.position_index):
                field_name = var.name
                python_type = _python_type_from_variable(var, nested_models)
                
                # Build field definition
                field_parts = []
                if var.description:
                    field_parts.append(f'description="{var.description}"')
                if var.default is not None:
                    field_parts.append(f"default={repr(var.default)}")
                
                if field_parts:
                    field_def = f"Field({', '.join(field_parts)})"
                    code_lines.append(f"    {field_name}: {python_type} = {field_def}")
                else:
                    code_lines.append(f"    {field_name}: {python_type}")
        
        code_lines.append("")
        generated_classes.add(class_name)
    
    # Generate all nested models
    for var_name, vars_list in nested_vars.items():
        class_name = nested_models[var_name]
        generate_class(var_name, vars_list, class_name)
    
    # Generate root model
    code_lines.append("class StructuredData(BaseModel):")
    if not root_vars:
        code_lines.append("    pass")
    else:
        for var in sorted(root_vars, key=lambda v: v.position_index):
            field_name = var.name
            python_type = _python_type_from_variable(var, nested_models)
            
            # Build field definition
            field_parts = []
            if var.description:
                field_parts.append(f'description="{var.description}"')
            if var.default is not None:
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


def find_project_root() -> Path:
    """Find the project root by looking for common markers"""
    cwd = Path.cwd()

    project_root_files = ["pyproject.toml"]

    # Check current directory and parents
    for path in [cwd] + list(cwd.parents):
        for marker in project_root_files:
            if (path / marker).exists():
                return path

    return cwd


def main():
    """CLI entry point for fetch_schema"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fetch and generate Pydantic models from Clerk project schema")
    parser.add_argument("--project_id", help="Project ID to fetch schema for")    
    
    args = parser.parse_args()
    
    print(f"Fetching schema for project: {args.project_id}")
    variables = fetch_schema(args.project_id)
    print(f"Found {len(variables)} variables")
    
    # Default to schema.py in project root
    project_root = find_project_root()
    output_file = project_root / "schema.py"
    
    code = generate_models_from_schema(variables, output_file)
    
    print(f"\nGenerated models written to: {output_file}")
    print("\nPreview:")
    print("=" * 80)
    print(code[:500] + "..." if len(code) > 500 else code)


if __name__ == "__main__":
    main()
    