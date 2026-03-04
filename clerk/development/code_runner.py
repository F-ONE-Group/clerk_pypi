"""Code runner module for testing custom code with payloads."""

import sys
from pathlib import Path
import importlib.util

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich import print as rprint

from clerk.client import Clerk
from clerk.decorator.models import ClerkCodePayload, Document, File
from clerk.development.schema import deserialize_clerk_data

console = Console()


def _generate_structured_data_code(structured_data_class) -> str:
    """Generate code for StructuredData initialization with all fields.

    Args:
        structured_data_class: The StructuredData class from schema

    Returns:
        String with indented field assignments
    """
    from typing import get_origin, get_args
    from pydantic import BaseModel

    lines = []

    # Get model fields
    if hasattr(structured_data_class, "model_fields"):
        fields = structured_data_class.model_fields

        for field_name, field_info in fields.items():
            annotation = field_info.annotation

            # Check if it's a List type
            origin = get_origin(annotation)
            if origin is list:
                lines.append(f"        {field_name}=[],")
            # Check if it's an Optional type
            elif origin is type(None) or (
                hasattr(annotation, "__origin__")
                and annotation.__origin__ is type(None)
            ):
                lines.append(f"        {field_name}=None,")
            # Check if the annotation is a BaseModel subclass
            else:
                # Try to check if it's a BaseModel (handle Optional types)
                actual_type = annotation
                if origin:
                    # For Optional[Type], get the actual type
                    args = get_args(annotation)
                    if args:
                        # Filter out NoneType
                        non_none_args = [arg for arg in args if arg is not type(None)]
                        if non_none_args:
                            actual_type = non_none_args[0]

                # Check if actual_type is a class and subclass of BaseModel
                try:
                    if isinstance(actual_type, type) and issubclass(
                        actual_type, BaseModel
                    ):
                        class_name = actual_type.__name__
                        lines.append(f"        {field_name}={class_name}(),")
                    else:
                        lines.append(f"        {field_name}=None,")
                except (TypeError, AttributeError):
                    lines.append(f"        {field_name}=None,")

    return "\n".join(lines)


def find_test_payloads(project_root: Path) -> list[Path]:
    """Find all test payload Python files in test/payloads directory.

    Args:
        project_root: Project root directory

    Returns:
        List of Path objects for payload files
    """
    payload_dir = project_root / "test" / "payloads"

    if not payload_dir.exists():
        return []

    # Find all .py files except __init__.py
    return [p for p in payload_dir.glob("*.py") if p.name != "__init__.py"]


def create_test_payload_template(project_root: Path) -> Path:
    """Create a template test payload Python file.

    Args:
        project_root: Project root directory

    Returns:
        Path to the created template file
    """
    payload_dir = project_root / "test" / "payloads"
    payload_dir.mkdir(parents=True, exist_ok=True)

    # Check if schema exists
    schema_path = project_root / "src" / "schema.py"
    if not schema_path.exists():
        console.print("[red]x[/red] No schema found. Run 'clerk schema fetch' first.")
        console.print("[dim]Cannot generate test payload without schema.[/dim]")
        sys.exit(1)

    console.print("[green]✓[/green] Found schema at src/schema.py")

    # Load schema to generate structured data template
    structured_data_code = None
    try:
        # Add src to path
        src_path = str(project_root / "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

        spec = importlib.util.spec_from_file_location("schema", schema_path)
        if spec and spec.loader:
            schema_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(schema_module)

            if hasattr(schema_module, "StructuredData"):
                structured_data_class = getattr(schema_module, "StructuredData")
                # Generate code with all fields
                structured_data_code = _generate_structured_data_code(
                    structured_data_class
                )
    except Exception as e:
        console.print(f"[red]x[/red] Could not load schema: {str(e)}")
        sys.exit(1)

    if not structured_data_code:
        console.print(
            "[red]x[/red] Could not generate structured data code from schema."
        )
        sys.exit(1)

    # Get name from user
    name = Prompt.ask("Enter a name for this test payload", default="test_payload_1")

    # Ensure .py extension
    if not name.endswith(".py"):
        name = f"{name}.py"

    payload_path = payload_dir / name

    # Load and populate template
    template_dir = Path(__file__).parent / "templates"
    template_path = template_dir / "test_payload.py.template"
    template_code = template_path.read_text(encoding="utf-8")
    # Replace placeholder with actual fields
    template_code = template_code.replace(
        "{structured_data_fields}", structured_data_code
    )

    # Write the template
    with open(payload_path, "w", encoding="utf-8") as f:
        f.write(template_code)

    console.print(f"\n[green]✓[/green] Created template payload: {payload_path}")
    console.print(
        "\n[yellow]Please edit this file to customize your test data before continuing.[/yellow]"
    )

    return payload_path


def select_payload(payloads: list[Path]) -> Path:
    """Let user select a payload by number.

    Args:
        payloads: List of payload file paths

    Returns:
        Selected payload path
    """
    console.print("\n[bold]Available test payloads:[/bold]")
    for i, payload in enumerate(payloads, 1):
        console.print(f"  [cyan]{i}[/cyan]. {payload.stem}")

    while True:
        try:
            choice = Prompt.ask("\nSelect a payload", default="1")
            idx = int(choice) - 1
            if 0 <= idx < len(payloads):
                return payloads[idx]
            else:
                console.print(
                    f"[red]Please enter a number between 1 and {len(payloads)}[/red]"
                )
        except ValueError:
            console.print("[red]Please enter a valid number[/red]")


def load_payload(payload_path: Path, project_root: Path):
    """Load payload from Python module.

    Args:
        payload_path: Path to payload Python file
        project_root: Project root directory

    Returns:
        ClerkCodePayload object
    """
    # Add project root and src to path so imports work
    project_root_str = str(project_root)
    src_path = str(project_root / "src")

    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    # Load the payload module
    spec = importlib.util.spec_from_file_location(
        f"test_payload_{payload_path.stem}", payload_path
    )
    if not spec or not spec.loader:
        raise ImportError(f"Could not load payload module from {payload_path}")

    payload_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(payload_module)

    # Get the payload object
    if not hasattr(payload_module, "payload"):
        raise AttributeError(f"Payload module must define a 'payload' variable")

    return payload_module.payload


def _load_structured_data_class(project_root: Path):
    """Load StructuredData model from src/schema.py."""
    schema_path = project_root / "src" / "schema.py"
    if not schema_path.exists():
        raise FileNotFoundError("No schema found. Run 'clerk schema fetch' first.")

    src_path = str(project_root / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    spec = importlib.util.spec_from_file_location("schema", schema_path)
    if not spec or not spec.loader:
        raise ImportError(f"Could not load schema module from {schema_path}")

    schema_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(schema_module)

    if not hasattr(schema_module, "StructuredData"):
        raise AttributeError("src/schema.py must define a StructuredData model")

    return getattr(schema_module, "StructuredData")


def _normalize_input_structured_data(input_structured_data: Any) -> Dict[str, Any]:
    """Normalize input structured data to a dictionary."""
    if input_structured_data is None:
        return {}

    if isinstance(input_structured_data, dict):
        return input_structured_data

    if isinstance(input_structured_data, str):
        try:
            parsed = json.loads(input_structured_data)
        except json.JSONDecodeError as e:
            raise ValueError(f"input_structured_data is not valid JSON: {e}") from e
        if isinstance(parsed, dict):
            return parsed
        raise ValueError("input_structured_data JSON must decode to an object")

    raise TypeError("input_structured_data must be a dict, JSON string, or None")


def build_payload_from_clerk_data(
    project_root: Path, document_id: str, processor_run_id: str
) -> ClerkCodePayload:
    """Build ClerkCodePayload from Clerk document and processor run input data."""
    client = Clerk()
    raw_document = client._get_document_internal(document_id)

    processor_runs = raw_document.get("processor_run_instances", [])
    selected_run = next(
        (
            run
            for run in processor_runs
            if isinstance(run, dict) and str(run.get("id", "")) == processor_run_id
        ),
        None,
    )
    if selected_run is None:
        available_run_ids = (
            ", ".join(
                str(run.get("id"))
                for run in processor_runs
                if isinstance(run, dict) and run.get("id") is not None
            )
            or "none"
        )
        raise ValueError(
            f"Processor run '{processor_run_id}' not found on document '{document_id}'. "
            f"Available run IDs: {available_run_ids}"
        )

    structured_data_class = _load_structured_data_class(project_root)
    raw_input_structured_data = _normalize_input_structured_data(
        selected_run.get(
            "inputStructuredData", selected_run.get("input_structured_data")
        )
    )
    structured_data_model = deserialize_clerk_data(
        raw_input_structured_data, structured_data_class
    )

    raw_document_id = raw_document.get("id")
    if not raw_document_id:
        raise ValueError("Document payload is missing required 'id'")

    raw_files = raw_document.get("files") or []
    payload_files = [
        File(name=str(file.get("name")), url=str(file.get("url")))
        for file in raw_files
        if isinstance(file, dict) and file.get("name") and file.get("url")
    ]
    payload_document = Document(
        id=str(raw_document_id),
        message_subject=raw_document.get("message_subject")
        or raw_document.get("messageSubject"),
        message_content=raw_document.get("message_content")
        or raw_document.get("messageContent"),
        files=payload_files,
        upload_date=raw_document.get("upload_date") or raw_document.get("uploadDate"),
    )

    return ClerkCodePayload(
        document=payload_document,
        structured_data=structured_data_model.model_dump(),
        run_id=str(selected_run.get("id")),
    )


def select_payload_source() -> str:
    """Select payload source: local payload file or Clerk run data."""
    console.print("\n[bold]Payload sources:[/bold]")
    console.print("  [cyan]1[/cyan]. Local test payload")
    console.print("  [cyan]2[/cyan]. Clerk data (document + processor run)")

    while True:
        choice = Prompt.ask("\nSelect payload source", default="1")
        normalized = choice.strip().lower()
        if normalized in {"1", "local", "payload", "test"}:
            return "local"
        if normalized in {"2", "clerk", "clerk data"}:
            return "clerk"
        console.print("[red]Please choose 1 (local) or 2 (Clerk data).[/red]")


def prompt_clerk_identifiers() -> tuple[str, str]:
    """Prompt user for Clerk document and processor run IDs."""
    while True:
        document_id = Prompt.ask("Enter Clerk document ID").strip()
        if document_id:
            break
        console.print("[red]Document ID is required.[/red]")

    while True:
        processor_run_id = Prompt.ask("Enter Clerk processor run ID").strip()
        if processor_run_id:
            break
        console.print("[red]Processor run ID is required.[/red]")

    return document_id, processor_run_id


def run_main_with_payload(project_root: Path, payload_path: Path):
    """Run main() from src/main.py with payload loaded from local file.

    Args:
        project_root: Project root directory
        payload_path: Path to the payload Python file
    """
    try:
        payload_obj = load_payload(payload_path, project_root)
        console.print("[green]✓[/green] Loaded payload")
    except Exception as e:
        console.print(f"[red]x[/red] Failed to load payload: {str(e)}")
        import traceback

        console.print("[dim]" + traceback.format_exc() + "[/dim]")
        sys.exit(1)

    run_main_with_payload_object(project_root, payload_obj, payload_path.name)


def run_main_with_payload_object(
    project_root: Path, payload_obj: ClerkCodePayload, payload_label: str
):
    """Run main() from src/main.py with a prepared payload object.

    Args:
        project_root: Project root directory
        payload_obj: Prepared ClerkCodePayload object
        payload_label: Label shown in CLI output
    """
    console.print()
    console.print(
        Panel(
            f"[bold]Running main() with payload: {payload_label}[/bold]", style="cyan"
        )
    )

    # Find main.py
    main_path = project_root / "src" / "main.py"
    if not main_path.exists():
        console.print(f"[red]x[/red] main.py not found at {main_path}")
        sys.exit(1)

    # Add src to path
    src_path = str(project_root / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    # Start debugpy server and wait for VS Code to attach
    import debugpy

    debug_port = 5678

    # Check if already running under debugger
    if not debugpy.is_client_connected():
        console.print(f"\n[cyan]Starting debug server on port {debug_port}...[/cyan]")
        debugpy.listen(("localhost", debug_port))

        console.print()
        console.print("[bold yellow]⚡ Ready for debugging![/bold yellow]")
        console.print()
        console.print("[bold]To start debugging:[/bold]")
        console.print("  [cyan]→ Press F5 in VS Code[/cyan]")
        console.print(
            "  [dim]or select 'Clerk: Debug Code Run' from the debug panel[/dim]"
        )
        console.print()
        console.print(
            "[dim]Press Ctrl+C to skip debugging and run without debugger[/dim]\n"
        )

        try:
            debugpy.wait_for_client()
            console.print("[green]✓[/green] Debugger attached!\n")
        except KeyboardInterrupt:
            console.print(
                "\n[yellow]Skipping debugger, running without debug...[/yellow]\n"
            )
    else:
        console.print("\n[green]✓[/green] Already running under debugger\n")

    # Import and run
    try:
        console.print()
        console.print(
            "[bold cyan]═══════════════════════════════════════════════════════[/bold cyan]"
        )
        console.print(
            "[bold cyan]                    Starting Execution                    [/bold cyan]"
        )
        console.print(
            "[bold cyan]═══════════════════════════════════════════════════════[/bold cyan]"
        )
        console.print()

        # Import main module
        spec = importlib.util.spec_from_file_location("main", main_path)
        if spec and spec.loader:
            main_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(main_module)

            # Call main
            if hasattr(main_module, "main"):
                # Run main with the loaded payload
                result = main_module.main(payload_obj)

                console.print()
                console.print(
                    "[bold cyan]═══════════════════════════════════════════════════════[/bold cyan]"
                )
                console.print(
                    "[bold cyan]                   Execution Complete                    [/bold cyan]"
                )
                console.print(
                    "[bold cyan]═══════════════════════════════════════════════════════[/bold cyan]"
                )
                console.print()

                # Show result
                if result:
                    console.print("[bold]Result:[/bold]")
                    console.print(
                        Panel(
                            f"Document ID: {result.document.id}\n"
                            f"Run ID: {result.run_id}",
                            title="Execution Result",
                            style="green",
                        )
                    )

                    # Show updated structured_data
                    if result.structured_data:
                        console.print("\n[bold]Updated Structured Data:[/bold]")
                        rprint(result.structured_data)
                else:
                    console.print("[yellow]![/yellow] No result returned")
            else:
                console.print(f"[red]x[/red] No main() function found in {main_path}")
                sys.exit(1)
        else:
            console.print(f"[red]x[/red] Could not load {main_path}")
            sys.exit(1)

    except Exception as e:
        console.print()
        console.print(f"[red]x Error during execution:[/red] {str(e)}")
        import traceback

        console.print("[dim]" + traceback.format_exc() + "[/dim]")
        sys.exit(1)


def main_with_args(project_root: Path):
    """Main entry point for code runner.

    Args:
        project_root: Project root directory
    """
    console.print()
    console.print(
        Panel(
            "[bold]Clerk Code Runner[/bold]\n"
            "Run your custom code with local payloads or Clerk data",
            style="cyan",
        )
    )

    payload_source = select_payload_source()

    if payload_source == "clerk":
        document_id, processor_run_id = prompt_clerk_identifiers()
        try:
            payload_obj = build_payload_from_clerk_data(
                project_root=project_root,
                document_id=document_id,
                processor_run_id=processor_run_id,
            )
            console.print("[green]✓[/green] Loaded payload from Clerk data")
        except Exception as e:
            console.print(
                f"[red]x[/red] Failed to build payload from Clerk data: {str(e)}"
            )
            import traceback

            console.print("[dim]" + traceback.format_exc() + "[/dim]")
            sys.exit(1)

        run_main_with_payload_object(
            project_root,
            payload_obj,
            f"Clerk run {processor_run_id} (document {document_id})",
        )
        return

    # Find payloads
    payloads = find_test_payloads(project_root)

    if not payloads:
        console.print("\n[yellow]No test payloads found in test/payloads/[/yellow]")

        if Confirm.ask("Would you like to generate a template payload?", default=True):
            payload_path = create_test_payload_template(project_root)

            console.print("\n[bold]Next steps:[/bold]")
            console.print(f"1. Edit {payload_path} with your test data")
            console.print("2. Run [cyan]clerk code run[/cyan] again to execute")
            return
        else:
            console.print(
                "\n[dim]Create a Python file in test/payloads/ and run again.[/dim]"
            )
            return

    # Show available payloads
    console.print(f"\n[green]✓[/green] Found {len(payloads)} test payload(s)")

    # Let user select
    selected_payload = select_payload(payloads)
    console.print(f"\n[green]→[/green] Selected: {selected_payload.name}")

    # Run with selected payload
    run_main_with_payload(project_root, selected_payload)
