from typing import Any, Dict, Optional

from pydantic import BaseModel
from pydantic.fields import FieldInfo

def _get_var_id(field_info: FieldInfo) -> Optional[str]:
    """Extract the clerk_var_id from a field's json_schema_extra."""
    extra = field_info.json_schema_extra
    if isinstance(extra, dict):
        var_id = extra.get("clerk_var_id")
        if isinstance(var_id, str):
            return var_id
    return None


def _build_id_to_field_map(model: type[BaseModel]) -> Dict[str, str]:
    """Build a mapping from clerk_var_id to field name for a model."""
    return {
        var_id: field_name
        for field_name, field_info in model.model_fields.items()
        if (var_id := _get_var_id(field_info)) is not None
    }


def _get_list_item_type(field_info: FieldInfo, field_name: str, model: type[BaseModel]) -> Optional[type[BaseModel]]:
    """Get the item type for a List field if it's a BaseModel subclass."""
    import typing
    annotation = model.model_fields[field_name].annotation
    origin = typing.get_origin(annotation)
    if origin is list:
        args = typing.get_args(annotation)
        if args and isinstance(args[0], type) and issubclass(args[0], BaseModel):
            return args[0]
    return None


def deserialize_clerk_data(data: Dict[str, Any], model: type[BaseModel]) -> BaseModel:
    """
    Deserialize a Clerk ID-keyed dict into a Pydantic model.
    
    The input dict has variable IDs as keys, and leaf values are 
    {"id": "<unique_id>", "value": <actual_value>} dicts.
    
    Args:
        data: The ID-keyed dict from Clerk
        model: The Pydantic model class with ClerkVariable fields
        
    Returns:
        An instance of the model populated with deserialized values
    """
    id_to_field = _build_id_to_field_map(model)
    result: Dict[str, Any] = {}
    
    for var_id, value in data.items():
        field_name = id_to_field.get(var_id)
        if field_name is None:
            continue  # Unknown variable ID, skip
        
        field_info = model.model_fields[field_name]
        
        if isinstance(value, list):
            # Handle list of nested objects
            item_type = _get_list_item_type(field_info, field_name, model)
            if item_type is not None:
                result[field_name] = [
                    deserialize_clerk_data(item, item_type) for item in value
                ]
            else:
                # List of primitives - extract values
                result[field_name] = [
                    v.get("value") if isinstance(v, dict) and "value" in v else v
                    for v in value
                ]
        elif isinstance(value, dict) and "id" in value and "value" in value:
            # Leaf value with id/value structure
            result[field_name] = value["value"]
        elif isinstance(value, dict):
            # Nested object without id/value structure - try to find nested model
            # This handles cases where a field is a nested BaseModel
            annotation = field_info.annotation
            if isinstance(annotation, type) and issubclass(annotation, BaseModel):
                result[field_name] = deserialize_clerk_data(value, annotation)
            else:
                result[field_name] = value
        else:
            result[field_name] = value
    
    return model(**result)