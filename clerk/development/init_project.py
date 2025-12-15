"""Project initialization module for Clerk custom code projects."""
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console()


def read_template(template_name: str) -> str:
    """Read a template file from the templates directory."""
    template_dir = Path(__file__).parent / "templates"
    template_path = template_dir / template_name
    
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_name}")
    
    with open(template_path, 'r', encoding='utf-8') as f:
        return f.read()


def create_main_py(target_dir: Path, with_gui: bool = False) -> None:
    """Create main.py with or without GUI automation setup.
    
    Args:
        target_dir: Target directory where main.py should be created
        with_gui: Whether to include GUI automation functionality
    """
    main_path = target_dir / "main.py"

    if main_path.exists():
        console.print(f"[yellow]⚠[/yellow]  {main_path} already exists, skipping...")
        return

    template_name = "main_gui.py.template" if with_gui else "main_basic.py.template"
    content = read_template(template_name)

    with open(main_path, "w", encoding='utf-8') as f:
        f.write(content)

    console.print(f"[green]✓[/green] Created {main_path}")


def create_gui_structure(target_dir: Path) -> None:
    """Create GUI automation folder structure with template files.
    
    Args:
        target_dir: Target directory where gui folder should be created
    """
    console.print("\n[dim]Creating GUI automation structure...[/dim]")

    gui_path = target_dir / "gui"
    gui_path.mkdir(parents=True, exist_ok=True)

    # Create targets subfolder
    targets_path = gui_path / "targets"
    targets_path.mkdir(exist_ok=True)

    # Template files to create
    template_files = [
        "states.py.template",
        "transitions.py.template",
        "rollbacks.py.template",
        "exceptions.py.template",
    ]

    for template_name in template_files:
        output_name = template_name.replace(".template", "")
        output_path = gui_path / output_name

        if output_path.exists():
            console.print(
                f"[yellow]⚠[/yellow]  {output_path} already exists, skipping..."
            )
            continue

        content = read_template(template_name)

        with open(output_path, "w", encoding='utf-8') as f:
            f.write(content)

    console.print(f"[green]✓[/green] Created GUI automation structure in {gui_path}")


def init_project(
    target_dir: Optional[Path] = None,
    with_gui: bool = False
) -> None:
    """Initialize a new Clerk custom code project.
    
    Args:
        target_dir: Target directory for the project (defaults to ./src)
        with_gui: Whether to include GUI automation functionality
    """
    if target_dir is None:
        target_dir = Path.cwd() / "src"

    # Ensure target directory exists
    target_dir.mkdir(parents=True, exist_ok=True)

    console.print("[bold]" + "=" * 60 + "[/bold]")
    console.print("[bold cyan]Initializing Clerk Custom Code Project[/bold cyan]")
    console.print("[bold]" + "=" * 60 + "[/bold]")
    if with_gui:
        console.print("[cyan]GUI Automation: ENABLED[/cyan]")
    else:
        console.print("[cyan]GUI Automation: DISABLED[/cyan]")
    console.print("[bold]" + "=" * 60 + "[/bold]")

    # Create main.py
    create_main_py(target_dir, with_gui=with_gui)

    # Create GUI structure if requested
    if with_gui:
        create_gui_structure(target_dir)

    console.print("\n[bold]" + "=" * 60 + "[/bold]")
    console.print("[bold green]Project initialization completed![/bold green]")
    console.print("[bold]" + "=" * 60 + "[/bold]")
    if with_gui:
        console.print("[green]✓[/green] GUI automation structure created")
        console.print("[green]✓[/green] main.py configured with ScreenPilot")
    else:
        console.print("[green]✓[/green] Basic main.py created")
    console.print("\n[cyan]Next steps:[/cyan]")
    console.print("   1. Configure your .env file with CLERK_API_KEY and PROJECT_ID")
    console.print("   2. Run 'clerk fetch-schema' to generate schema models")
    console.print("   3. Start developing your custom code!")
    console.print("[bold]" + "=" * 60 + "[/bold]")


def main_with_args(gui_automation: bool = False, target_dir: Optional[str] = None):
    """Main entry point for CLI usage.
    
    Args:
        gui_automation: Whether to include GUI automation functionality
        target_dir: Target directory for the project
    """
    try:
        target_path = Path(target_dir) if target_dir else None
        init_project(target_dir=target_path, with_gui=gui_automation)
    except Exception as e:
        console.print(f"\n[red]✗ Error during project initialization: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    # For standalone testing
    import argparse
    
    parser = argparse.ArgumentParser(description="Initialize Clerk custom code project")
    parser.add_argument(
        "--gui-automation",
        action="store_true",
        help="Include GUI automation functionality"
    )
    parser.add_argument(
        "--target-dir",
        type=str,
        default=None,
        help="Target directory for the project (default: ./src)"
    )
    
    args = parser.parse_args()
    main_with_args(gui_automation=args.gui_automation, target_dir=args.target_dir)
