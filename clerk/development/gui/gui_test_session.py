import sys
from pathlib import Path
import time
from datetime import datetime
import traceback
import importlib
from typing import Any

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from clerk.gui_automation.ui_actions.actions import (    
    File, 
    LeftClick,
    RightClick,
    DoubleClick,
    PressKeys,
    SendKeys,
    WaitFor,
    Scroll,
    OpenApplication,
    ForceCloseApplication,
    SaveFiles,
    DeleteFiles,
    GetFile,
    MaximizeWindow,
    MinimizeWindow,
    CloseWindow,
    ActivateWindow,
    GetText,
    PasteText,
    BaseAction
)
from clerk.gui_automation.decorators import gui_automation
from clerk.decorator.models import ClerkCodePayload, Document
from clerk.gui_automation.ui_state_machine.state_machine import ScreenPilot
from clerk.gui_automation.ui_state_inspector.gui_vision import Vision, BaseState


# Initialize rich console
console = Console()

# Store session state
SESSION_FILE = Path(".test_session_active")
ACTION_HISTORY = []
VISION_CLIENT = Vision()


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


def reload_states() -> int:
    """Reload states from conventional paths. Returns number of states loaded."""
    project_root = find_project_root()

    # Common module paths where states might be defined
    # These are module paths (dot-separated), not file paths
    state_module_paths = ["src.gui.states", "states"]

    loaded_count = 0

    # Add project root to sys.path if not already there
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # Try to import/reload each module path
    for module_path in state_module_paths:
        try:
            # Reload if already imported, otherwise import fresh
            if module_path in sys.modules:
                importlib.reload(sys.modules[module_path])
            else:
                importlib.import_module(module_path)
            loaded_count += 1
        except Exception:
            continue

    return loaded_count


def get_registered_states() -> dict:
    """Get all registered states from ScreenPilot"""
    states = {}
    for state_name, data in ScreenPilot._graph.nodes(data=True):
        state_cls = data.get("cls")
        if state_cls:
            states[state_name] = {
                "description": getattr(state_cls, "description", "No description"),
                "class": state_cls,
            }
    return states


def classify_current_state() -> tuple[bool, str, str]:
    """Classify the current GUI state using Vision. Reloads states first."""
    try:
        # Always reload states to pick up any changes
        with console.status("[dim]Reloading states...", spinner="dots") as status:
            reload_states()
            status.update("[green]+[/green] Reloaded states")
            time.sleep(0.3)  # Brief pause to show success

        states = get_registered_states()

        if not states:
            return (
                False,
                "",
                "No states found. Make sure state definitions exist in your project.",
            )

        # Convert to format expected by Vision.classify_state
        possible_states = [
            {"id": name, "description": data["description"]}
            for name, data in states.items()
        ]

        with console.status(
            "[dim]Classifying current state (waiting for AI)...", spinner="dots"
        ):
            # Pass output_model=None to get tuple instead of BaseModel
            result: BaseState = VISION_CLIENT.classify_state(possible_states)  # type: ignore[arg-type]

        console.print("[green]+[/green] Classification complete")
        return True, result.id, result.description
    except Exception:
        return False, "", f"Classification failed: {traceback.format_exc()}"


def print_welcome():
    """Print welcome message"""
    title = Text("GUI Automation Interactive Test Session", style="bold cyan")
    panel = Panel(title, border_style="cyan", padding=(1, 2))
    console.print()
    console.print(panel)
    console.print()
    console.print("[bold blue]Commands:[/bold blue]")
    console.print(
        "  [dim]classify_state: Classify current GUI state (auto-reloads states)[/dim]"
    )
    console.print("  [dim]exit: End session[/dim]")
    console.print()
    console.print("[bold blue]Testing actions:[/bold blue]")
    console.print("  [dim]Type an action and press Enter to execute[/dim]")
    console.print()


def perform_single_action(action_string: str) -> tuple[bool, Any, str]:
    """Execute a single action and return success status, result, and error message"""
    try:
        # Ensure action has .do() call
        if not "do(" in action_string:
            action_string = f"{action_string}.do()"

        # Execute and capture result
        result = eval(action_string)
        return True, result, ""
    except Exception as e:
        error_msg = traceback.format_exc()
        return False, None, error_msg


def handle_special_command(command: str) -> tuple[bool, str]:
    """Handle special commands like classify. Returns (is_special, message)"""
    command = command.strip()

    # Classify command
    if command == "classify_state":
        success, state_id, description = classify_current_state()
        if success:
            # Return empty string since console.print handles it
            console.print()
            console.print(f"[green]Current State:[/green] [bold]{state_id}[/bold]")
            console.print(f"  [dim]{description}[/dim]")
            console.print()
            return True, ""
        else:
            console.print(f"[red]{description}[/red]")
            return True, ""

    return False, ""


def format_result(result):
    """Format action result for rich display"""
    if result is None:
        return "[dim](no return value)[/dim]"
    elif isinstance(result, bool):
        color = "green" if result else "yellow"
        return f"[{color}]{result}[/{color}]"
    elif isinstance(result, (str, int, float)):
        return f"[cyan]{repr(result)}[/cyan]"
    else:
        return f"[cyan]{type(result).__name__}: {str(result)[:100]}[/cyan]"


@gui_automation()
def start_interactive_session(payload: ClerkCodePayload):
    """Start an interactive test session with websocket connection"""
    session_start = datetime.now()
    action_count = 0

    print_welcome()

    # The gui_automation decorator establishes the connection before this function runs
    # By the time we get here, connection is already established
    console.print("[green]+[/green] WebSocket connection established")
    console.print()

    # Mark session as active
    SESSION_FILE.touch()

    try:
        while True:
            # Get input from user
            try:
                action_string = console.input(
                    "[bold blue]command/action>[/bold blue] "
                ).strip()
            except EOFError:
                break

            # Check for exit command
            if action_string.lower() in ["exit", "quit", "q"]:
                break

            # Skip empty input
            if not action_string:
                continue

            # Check if it's a special command
            is_special, message = handle_special_command(action_string)
            if is_special:
                if message:  # Only print if there's a message
                    console.print(message)
                continue

            # Record action
            ACTION_HISTORY.append(
                {"timestamp": datetime.now(), "action": action_string, "success": None}
            )

            # Execute action with status
            start_time = time.time()

            with console.status(
                "[dim]Executing action (waiting for tool)...", spinner="dots"
            ):
                success, result, error_msg = perform_single_action(action_string)
                execution_time = time.time() - start_time

            # Show completion message
            if success:
                console.print(
                    f"[green]+[/green] Action completed ({execution_time:.3f}s)"
                )
            else:
                console.print(f"[red]x[/red] Action failed ({execution_time:.3f}s)")

            # Update history
            ACTION_HISTORY[-1]["success"] = success
            ACTION_HISTORY[-1]["execution_time"] = execution_time
            ACTION_HISTORY[-1]["result"] = result

            # Display result
            if success:
                action_count += 1
                if result is not None:
                    console.print(f"  Result: {format_result(result)}")
            else:
                console.print(f"[red]{error_msg}[/red]")

            console.print()  # Extra newline for spacing

    except KeyboardInterrupt:
        console.print("\n\n[yellow]Session interrupted by user[/yellow]")
    finally:
        if SESSION_FILE.exists():
            SESSION_FILE.unlink()

        # Print summary
        console.print("\n[bold]" + "=" * 80 + "[/bold]")
        console.print("[bold]Session Summary[/bold]")
        console.print("[bold]" + "=" * 80 + "[/bold]")
        console.print(f"  Total actions executed: {action_count}")
        console.print(f"  Session duration: {datetime.now() - session_start}")

        if ACTION_HISTORY:
            successful = sum(1 for a in ACTION_HISTORY if a.get("success"))
            failed = len(ACTION_HISTORY) - successful
            console.print(f"  Successful: [green]{successful}[/green]")
            console.print(f"  Failed: [red]{failed}[/red]")

        console.print("\n[blue]WebSocket connection closed[/blue]\n")


def main():
    """Main entry point for the gui_test_session command"""
    # Start interactive session
    load_dotenv()
    payload = ClerkCodePayload(
        document=Document(id="test-session"),
        structured_data={},
        run_id="test-session-run",
    )

    # The @gui_automation decorator will establish the connection
    # and the function itself will print the connection status
    start_interactive_session(payload)


if __name__ == "__main__":
    main()
