from clerk.development.schema.fetch_schema import (
    generate_models_from_schema,
    VariableData,
    VariableTypes,
)


def test_generate_models_assigns_default_none_for_leaf_types():
    """Leaf types (str, float, bool, date, etc.) should be Optional with default=None."""
    variables = [
        VariableData(
            id="1",
            name="my_string",
            display_name="My String",
            is_array=False,
            type=VariableTypes.STRING,
            position_index=0,
        ),
        VariableData(
            id="2",
            name="my_number",
            display_name="My Number",
            is_array=False,
            type=VariableTypes.NUMBER,
            position_index=1,
        ),
    ]

    code = generate_models_from_schema(variables)

    assert "my_string: Optional[str]" in code
    assert "my_number: Optional[float]" in code
    assert "default=None" in code


def test_generate_models_assigns_default_factory_list_for_arrays():
    """List types should have default_factory=list."""
    variables = [
        VariableData(
            id="1",
            name="my_list",
            display_name="My List",
            is_array=True,
            type=VariableTypes.STRING,
            position_index=0,
        ),
    ]

    code = generate_models_from_schema(variables)

    assert "my_list: List[str]" in code
    assert "default_factory=list" in code


def test_generate_models_assigns_optional_none_for_nested_objects():
    """Nested object types should be Optional with default=None."""
    variables = [
        VariableData(
            id="parent_1",
            name="my_object",
            display_name="My Object",
            is_array=False,
            type=VariableTypes.OBJECT,
            position_index=0,
        ),
        VariableData(
            id="child_1",
            name="child_field",
            display_name="Child Field",
            is_array=False,
            type=VariableTypes.STRING,
            parent_id="parent_1",
            position_index=0,
        ),
    ]

    code = generate_models_from_schema(variables)

    # The nested model class should be generated
    assert "class MyObject(BaseModel):" in code
    # The root field should be Optional with None default
    assert "my_object: Optional[MyObject]" in code
    assert "default=None" in code


def test_generate_models_assigns_default_factory_list_for_object_arrays():
    """Arrays of objects should have default_factory=list."""
    variables = [
        VariableData(
            id="parent_1",
            name="my_objects",
            display_name="My Objects",
            is_array=True,
            type=VariableTypes.OBJECT,
            position_index=0,
        ),
        VariableData(
            id="child_1",
            name="item_field",
            display_name="Item Field",
            is_array=False,
            type=VariableTypes.STRING,
            parent_id="parent_1",
            position_index=0,
        ),
    ]

    code = generate_models_from_schema(variables)

    # The nested model class should be generated
    assert "class MyObjects(BaseModel):" in code
    # The root field should be List with default_factory
    assert "my_objects: List[MyObjects]" in code
    assert "default_factory=list" in code


def test_generate_models_preserves_explicit_defaults():
    """Explicit defaults from schema should be preserved."""
    variables = [
        VariableData(
            id="1",
            name="my_string",
            display_name="My String",
            is_array=False,
            type=VariableTypes.STRING,
            position_index=0,
            default="hello",
        ),
    ]

    code = generate_models_from_schema(variables)

    assert "default='hello'" in code


def test_generate_models_handles_enum_with_literal():
    """Enum types should generate Literal type hints."""
    variables = [
        VariableData(
            id="1",
            name="status",
            display_name="Status",
            is_array=False,
            type=VariableTypes.ENUM,
            position_index=0,
            enum_options=["active", "inactive"],
        ),
    ]

    code = generate_models_from_schema(variables)

    assert 'Literal["active", "inactive"]' in code
    assert "default=None" in code


def test_generate_models_handles_all_types_with_defaults():
    """Integration test: all field types should have sensible defaults."""
    variables = [
        VariableData(
            id="1",
            name="leaf_str",
            display_name="Leaf String",
            is_array=False,
            type=VariableTypes.STRING,
            position_index=0,
        ),
        VariableData(
            id="2",
            name="list_str",
            display_name="List of Strings",
            is_array=True,
            type=VariableTypes.STRING,
            position_index=1,
        ),
        VariableData(
            id="obj_1",
            name="nested_obj",
            display_name="Nested Object",
            is_array=False,
            type=VariableTypes.OBJECT,
            position_index=2,
        ),
        VariableData(
            id="child_1",
            name="nested_field",
            display_name="Nested Field",
            is_array=False,
            type=VariableTypes.NUMBER,
            parent_id="obj_1",
            position_index=0,
        ),
    ]

    code = generate_models_from_schema(variables)

    # Verify the generated code is syntactically valid
    compile(code, "<string>", "exec")

    # Leaf type has Optional and default=None
    assert "leaf_str: Optional[str]" in code

    # List has default_factory=list
    assert "list_str: List[str]" in code
    assert "default_factory=list" in code

    # Nested object has Optional and default=None
    assert "nested_obj: Optional[NestedObj]" in code
