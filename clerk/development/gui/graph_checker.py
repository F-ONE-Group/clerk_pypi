"""Graph checker utility for ScreenPilot state machines"""
import sys
import importlib.util
import logging
from pathlib import Path
from typing import Set, List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


class ErrorCapturingHandler(logging.Handler):
    """Custom logging handler to capture error messages during module load"""
    
    def __init__(self):
        super().__init__()
        self.errors: List[str] = []
        self.setLevel(logging.ERROR)
    
    def emit(self, record):
        if "involves undefined state" in record.getMessage():
            self.errors.append(record.getMessage())


def load_module_from_path(module_path: str) -> ErrorCapturingHandler:
    """
    Load a Python module from a file path.
    
    Args:
        module_path: Path to the Python file containing the state machine
        
    Returns:
        ErrorCapturingHandler with any errors captured during load
    """
    path = Path(module_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Module not found: {module_path}")
    
    # Set up error capturing handler
    error_handler = ErrorCapturingHandler()
    logger = logging.getLogger("state_machine.py")
    logger.addHandler(error_handler)
    
    try:
        # Add the parent directory to sys.path for relative imports
        parent_dir = str(path.parent)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        
        # Load the module
        spec = importlib.util.spec_from_file_location(path.stem, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load module from {module_path}")
        
        module = importlib.util.module_from_spec(spec)
        sys.modules[path.stem] = module
        
        # Capture ValueError exceptions during module execution
        try:
            spec.loader.exec_module(module)
        except ValueError as e:
            error_msg = str(e)
            if "already registered" in error_msg or "provide a condition function" in error_msg:
                # This is a fatal error - the transition can't be registered
                # Re-raise it so we can show it properly
                raise ValueError(f"Duplicate transition error: {error_msg}") from e
            else:
                raise
    finally:
        # Clean up handler
        logger.removeHandler(error_handler)
    
    return error_handler


def check_graph(module_path: Optional[str] = None):
    """
    Main function to check a ScreenPilot state machine graph.
    
    Args:
        module_path: Path to the Python file containing the state machine.
                    If None, defaults to src/main.py in current directory.
    """
    try:
        # Clear any existing graph state from ScreenPilot before loading
        from clerk.gui_automation.ui_state_machine import ScreenPilot
        import networkx as nx
        ScreenPilot._graph = nx.MultiDiGraph()
        
        # Default to src/main.py if no path provided
        if module_path is None:
            default_path = Path.cwd() / "src" / "main.py"
            if not default_path.exists():
                console.print(f"\n[red]Error: Default file not found: {default_path}[/red]")
                console.print("[dim]Specify --module-path to check a different file[/dim]")
                sys.exit(1)
            module_path = str(default_path)
            console.print(f"[dim]Using default: {module_path}[/dim]")
        
        # Load the module (this will trigger state/transition registrations)
        console.print(f"\n[dim]Loading module: {module_path}[/dim]")
        error_handler = load_module_from_path(module_path)
        
        graph = ScreenPilot._graph
        
        if len(graph.nodes()) == 0:
            console.print("\n[yellow]⚠️  Warning: No states found in the graph.[/yellow]")
            console.print("[dim]Make sure your module imports and registers states using decorators[/dim]")
            return
        
        # Count states and transitions
        state_count = len(graph.nodes())
        transition_count = len(graph.edges())
        
        # Show statistics
        console.print()
        stats_table = Table(show_header=False, box=None, padding=(0, 2))
        stats_table.add_column(style="cyan bold")
        stats_table.add_column(style="white")
        stats_table.add_row("States:", str(state_count))
        stats_table.add_row("Transitions:", str(transition_count))
        
        console.print(Panel(
            stats_table,
            title="[bold]Graph Statistics[/bold]",
            style="cyan"
        ))
        
        # Collect all valid state names
        valid_states: Set[str] = set(graph.nodes())
        
        # Collect all state names referenced in transitions
        referenced_states: Set[str] = set()
        for u, v in graph.edges():
            referenced_states.add(u)
            referenced_states.add(v)
        
        console.print()
        console.print(Panel("[bold]Graph Checks[/bold]", style="cyan"))
        console.print()
        
        has_warnings = False
        has_info = False
        
        # Check for invalid state names in transitions (from captured errors)
        if error_handler.errors:
            has_warnings = True
            console.print(f"[yellow]⚠️  WARNING: Found {len(error_handler.errors)} transition(s) with invalid state names:[/yellow]")
            for error in error_handler.errors:
                # Extract the relevant info from the error message
                console.print(f"   [yellow]• {error.replace('Error: ', '')}[/yellow]")
            console.print()
        
        # Check for orphaned states (no incoming AND no outgoing transitions)
        orphaned = [
            node for node in graph.nodes() 
            if graph.in_degree(node) == 0 and graph.out_degree(node) == 0
        ]
        if orphaned:
            has_warnings = True
            console.print(f"[yellow]⚠️  WARNING: Found {len(orphaned)} orphaned state(s) (no incoming or outgoing transitions):[/yellow]")
            for state in sorted(orphaned):
                console.print(f"   [yellow]• {state}[/yellow]")
            console.print()
        
        # Info: States with no incoming transitions
        no_incoming = [node for node in graph.nodes() if graph.in_degree(node) == 0 and graph.out_degree(node) > 0]
        if no_incoming:
            has_info = True
            console.print(f"[blue]ℹ️  INFO: Found {len(no_incoming)} state(s) with no incoming transitions (entry points):[/blue]")
            for state in sorted(no_incoming):
                console.print(f"   [blue]• {state}[/blue]")
            console.print()
        
        # Info: States with no outgoing transitions
        no_outgoing = [node for node in graph.nodes() if graph.out_degree(node) == 0 and graph.in_degree(node) > 0]
        if no_outgoing:
            has_info = True
            console.print(f"[blue]ℹ️  INFO: Found {len(no_outgoing)} state(s) with no outgoing transitions (terminal states):[/blue]")
            for state in sorted(no_outgoing):
                console.print(f"   [blue]• {state}[/blue]")
            console.print()
        
        # All good message
        if not has_warnings:
            console.print("[green]✅ No issues detected.[/green]")
            console.print()
        
    except Exception as e:
        console.print(f"\n[red]Error checking graph: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


def main():
    """Entry point for standalone script execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Check ScreenPilot state machine graph")
    parser.add_argument(
        "--module-path",
        required=False,
        default=None,
        help="Path to the Python file containing the state machine (defaults to src/main.py)"
    )
    
    args = parser.parse_args()
    check_graph(args.module_path)


if __name__ == "__main__":
    main()
