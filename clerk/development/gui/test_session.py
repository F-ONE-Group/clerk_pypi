import sys
from pathlib import Path
import time
from datetime import datetime
import traceback
import importlib
from typing import Any

from dotenv import load_dotenv

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


# ANSI color codes for terminal
class Colors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    GRAY = "\033[90m"


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
        reload_states()

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

        # Pass output_model=None to get tuple instead of BaseModel
        result: BaseState = VISION_CLIENT.classify_state(possible_states)  # type: ignore[arg-type]
        return True, result.id, result.description
    except Exception:
        return False, "", f"Classification failed: {traceback.format_exc()}"


def print_welcome():
    """Print welcome message"""
    print(
        f"\n{Colors.BOLD}{Colors.OKCYAN}╔══════════════════════════════════════════════════════════════════════════════╗"
    )
    print(
        f"║                   GUI Automation Interactive Test Session                    ║"
    )
    print(
        f"╚══════════════════════════════════════════════════════════════════════════════╝{Colors.ENDC}\n"
    )
    print(f"{Colors.OKBLUE}Commands:{Colors.ENDC}")
    print(
        f"  {Colors.GRAY}classify_state: Classify current GUI state (auto-reloads states)"
    )
    print(f"  exit: End session{Colors.ENDC}\n")
    print(f"{Colors.OKBLUE}Testing actions:{Colors.ENDC}")
    print(f"  {Colors.GRAY}Type an action and press Enter to execute{Colors.ENDC}\n")


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
            return (
                True,
                f"{Colors.OKGREEN}Current State:{Colors.ENDC} {Colors.BOLD}{state_id}{Colors.ENDC}\n  {Colors.GRAY}{description}{Colors.ENDC}",
            )
        else:
            return True, f"{Colors.FAIL}{description}{Colors.ENDC}"

    return False, ""


def format_result(result):
    """Format action result for display"""
    if result is None:
        return f"{Colors.GRAY}(no return value){Colors.ENDC}"
    elif isinstance(result, bool):
        return f"{Colors.OKGREEN if result else Colors.WARNING}{result}{Colors.ENDC}"
    elif isinstance(result, (str, int, float)):
        return f"{Colors.OKCYAN}{repr(result)}{Colors.ENDC}"
    else:
        return (
            f"{Colors.OKCYAN}{type(result).__name__}: {str(result)[:100]}{Colors.ENDC}"
        )


@gui_automation()
def start_interactive_session(payload: ClerkCodePayload):
    """Start an interactive test session with websocket connection"""
    session_start = datetime.now()
    action_count = 0

    print_welcome()
    print(f"{Colors.OKGREEN}✓{Colors.ENDC} WebSocket connection established\n")

    # Mark session as active
    SESSION_FILE.touch()

    try:
        while True:
            # Get input from user
            try:
                action_string = input(
                    f"{Colors.BOLD}{Colors.OKBLUE}command/action>{Colors.ENDC} "
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
                print(f"\n{message}\n")
                continue

            # Record action
            ACTION_HISTORY.append(
                {"timestamp": datetime.now(), "action": action_string, "success": None}
            )

            # Execute action
            start_time = time.time()
            print(f"\n{Colors.GRAY}▶ Executing...{Colors.ENDC}")

            success, result, error_msg = perform_single_action(action_string)
            execution_time = time.time() - start_time

            # Update history
            ACTION_HISTORY[-1]["success"] = success
            ACTION_HISTORY[-1]["execution_time"] = execution_time
            ACTION_HISTORY[-1]["result"] = result

            # Display result
            print(
                f"{Colors.GRAY}⏱ Execution time: {execution_time:.3f}s{Colors.ENDC}\n"
            )

            if success:
                action_count += 1
                print(f"{Colors.OKGREEN}✓ SUCCESS{Colors.ENDC}")
                if result is not None:
                    print(f"  Result: {format_result(result)}")
            else:
                print(f"{Colors.FAIL}✗ FAILED{Colors.ENDC}")
                print(f"{Colors.FAIL}{error_msg}{Colors.ENDC}")

            print()  # Extra newline for spacing

    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}Session interrupted by user{Colors.ENDC}")
    finally:
        if SESSION_FILE.exists():
            SESSION_FILE.unlink()

        # Print summary
        print(f"\n{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
        print(f"{Colors.BOLD}Session Summary{Colors.ENDC}")
        print(f"{Colors.BOLD}{'=' * 80}{Colors.ENDC}")
        print(f"  Total actions executed: {action_count}")
        print(f"  Session duration: {datetime.now() - session_start}")

        if ACTION_HISTORY:
            successful = sum(1 for a in ACTION_HISTORY if a.get("success"))
            failed = len(ACTION_HISTORY) - successful
            print(f"  Successful: {Colors.OKGREEN}{successful}{Colors.ENDC}")
            print(f"  Failed: {Colors.FAIL}{failed}{Colors.ENDC}")

        print(f"\n{Colors.OKBLUE}WebSocket connection closed{Colors.ENDC}\n")


def main():
    """Main entry point for the gui_test_session command"""
    # Start interactive session
    load_dotenv()
    payload = ClerkCodePayload(
        document=Document(id="test-session"),
        structured_data={},
        run_id="test-session-run",
    )
    start_interactive_session(payload)


if __name__ == "__main__":
    main()
