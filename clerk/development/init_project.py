"""Project initialization module for Clerk custom code projects."""
import os
import sys
from pathlib import Path
from typing import Optional, Dict

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

console = Console()


def prompt_for_env_var(var_name: str, description: str, required: bool = True, default: str = "") -> str:
    """Prompt user for an environment variable value."""
    prompt_text = f"{var_name}"
    if description:
        prompt_text = f"{description} ({var_name})"
    
    while True:
        value = Prompt.ask(prompt_text, default=default if default else None)
        if value or not required:
            return value if value else ""
        console.print(f"[yellow]{var_name} is required. Please provide a value.[/yellow]")


def create_env_file(gui_automation: bool = False) -> Dict[str, str]:
    """Interactively create .env file with user secrets.
    
    Args:
        gui_automation: Whether GUI automation is enabled (adds REMOTE_DEVICE_NAME)
        
    Returns:
        Dictionary of environment variable key-value pairs
    """
    console.print()
    console.print(Panel(
        "[bold]Environment Configuration[/bold]\n"
        "Please provide the following configuration values.", 
        style="cyan"
    ))
    
    env_vars = {
        "CLERK_API_KEY": ("Clerk API Key", True, ""),
        "PROJECT_ID": ("Project ID", True, ""),
    }
    
    # Add REMOTE_DEVICE_NAME if GUI automation is enabled
    if gui_automation:
        env_vars["REMOTE_DEVICE_NAME"] = ("Remote Device Name (for GUI automation)", True, "")
    
    env_content = []
    env_values = {}
    env_path = Path(".env")
    
    # Check if .env already exists
    if env_path.exists():
        if not Confirm.ask("\n[yellow].env file already exists. Overwrite?[/yellow]", default=False):
            console.print("[dim]Using existing .env file[/dim]")
            return load_env_file()
    
    for var_name, (description, required, default) in env_vars.items():
        value = prompt_for_env_var(var_name, description, required, default)
        if value:
            env_content.append(f"{var_name}={value}")
            env_values[var_name] = value
    
    # Write .env file
    with open(env_path, 'w') as f:
        f.write('\n'.join(env_content) + '\n')
    
    console.print(f"\n[green]✓[/green] Created .env file with {len(env_content)} variables")
    return env_values


def load_env_file() -> Dict[str, str]:
    """Load environment variables from .env file.
    
    Returns:
        Dictionary of environment variable key-value pairs
    """
    env_values = {}
    env_path = Path(".env")

    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_values[key.strip()] = value.strip()

    return env_values


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
        console.print(f"[yellow]![/yellow]  {main_path} already exists, skipping...")
        return

    template_name = "main_gui.py.template" if with_gui else "main_basic.py.template"
    content = read_template(template_name)

    with open(main_path, "w", encoding='utf-8') as f:
        f.write(content)

    console.print(f"[green]+[/green] Created {main_path}")


def create_init_py(target_dir: Path) -> None:
    """Create __init__.py in the target directory if it doesn't exist.

    Args:
        target_dir: Target directory where __init__.py should be created
    """
    init_path = target_dir / "__init__.py"

    if init_path.exists():
        console.print(f"[yellow]![/yellow]  {init_path} already exists, skipping...")
        return

    with open(init_path, "w", encoding="utf-8") as f:
        f.write("# Init file for the package\n")

    console.print(f"[green]+[/green] Created {init_path}")


def create_vscode_launch_config() -> None:
    """Create .vscode/launch.json for debugging."""
    vscode_dir = Path(".vscode")
    vscode_dir.mkdir(exist_ok=True)
    
    launch_path = vscode_dir / "launch.json"
    
    if launch_path.exists():
        console.print(f"[yellow]![/yellow]  {launch_path} already exists, skipping...")
        return
    
    content = read_template("launch.json.template")
    
    with open(launch_path, "w", encoding='utf-8') as f:
        f.write(content)
    
    console.print(f"[green]+[/green] Created {launch_path}")


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
                f"[yellow]![/yellow]  {output_path} already exists, skipping..."
            )
            continue

        content = read_template(template_name)

        with open(output_path, "w", encoding='utf-8') as f:
            f.write(content)

    console.print(f"[green]+[/green] Created GUI automation structure in {gui_path}")


def init_project(
    target_dir: Optional[Path] = None,
    with_gui: Optional[bool] = None
) -> None:
    """Initialize a new Clerk custom code project.
    
    Args:
        target_dir: Target directory for the project (defaults to ./src)
        with_gui: Whether to include GUI automation functionality (prompts if None)
    """
    if target_dir is None:
        target_dir = Path.cwd() / "src"

    # Ensure target directory exists
    target_dir.mkdir(parents=True, exist_ok=True)

    # Welcome message
    console.print(Panel(
        "[bold cyan]Clerk Custom Code Setup[/bold cyan]\n\n"
        "This will set up your Clerk custom code project.",
        style="blue"
    ))

    # Prompt for GUI automation if not specified
    if with_gui is None:
        console.print()
        with_gui = Confirm.ask(
            "[cyan]Enable GUI automation functionality?[/cyan]",
            default=False
        )

    gui_status = "ENABLED" if with_gui else "DISABLED"
    console.print(f"\n[dim]GUI Automation: {gui_status}[/dim]")

    # Create .env file and get environment variables
    env_vars = create_env_file(gui_automation=with_gui)

    if not env_vars:
        console.print("\n[red]✗ Failed to configure environment[/red]")
        sys.exit(1)

    # Update os.environ with the new values for fetch_schema to use
    for key, value in env_vars.items():
        os.environ[key] = value

    console.print("\n[bold]" + "=" * 60 + "[/bold]")
    console.print("[bold cyan]Creating Project Structure[/bold cyan]")
    console.print("[bold]" + "=" * 60 + "[/bold]")

    # Create main.py
    create_main_py(target_dir, with_gui=with_gui)

    # Create __init__.py
    create_init_py(target_dir)

    # Create VS Code launch configuration
    create_vscode_launch_config()

    # Create GUI automation structure if requested
    if with_gui:
        create_gui_structure(target_dir)

    console.print("\n[bold]" + "=" * 60 + "[/bold]")
    console.print("[bold cyan]Fetching Schema from Clerk[/bold cyan]")
    console.print("[bold]" + "=" * 60 + "[/bold]")

    # Fetch schema automatically
    try:
        from clerk.development.schema.fetch_schema import main_with_args as fetch_schema_main
        project_id = env_vars.get("PROJECT_ID")
        if project_id:
            fetch_schema_main(project_id, Path.cwd())
        else:
            console.print("[yellow]⚠[/yellow]  PROJECT_ID not found, skipping schema fetch")
    except Exception as e:
        console.print(f"[yellow]⚠[/yellow]  Schema fetch failed: {e}")
        console.print("[dim]You can run 'clerk fetch-schema' later to fetch the schema[/dim]")

    # Final success message
    console.print("\n[bold]" + "=" * 60 + "[/bold]")
    console.print("[bold green]Setup Completed Successfully![/bold green]")
    console.print("[bold]" + "=" * 60 + "[/bold]")

    success_items = [
        "Environment configured (.env created)",
        "Schema fetched from Clerk",
    ]

    if with_gui:
        success_items.insert(0, "GUI automation structure created")
        success_items.insert(1, "main.py configured with ScreenPilot")
    else:
        success_items.insert(0, "Basic main.py created")

    for item in success_items:
        console.print(f"[green]✓[/green] {item}")

    console.print("\n[cyan]Next steps:[/cyan]")
    console.print("   1. Start developing your custom code in src/main.py")
    console.print("   2. When ready, check README.md for deployment guidance.")
    console.print("[bold]" + "=" * 60 + "[/bold]")


def main_with_args(gui_automation: Optional[bool] = None, target_dir: Optional[str] = None):
    """Main entry point for CLI usage.
    
    Args:
        gui_automation: Whether to include GUI automation functionality (prompts if None)
        target_dir: Target directory for the project
    """
    try:
        target_path = Path(target_dir) if target_dir else None
        init_project(target_dir=target_path, with_gui=gui_automation)
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Setup cancelled by user[/yellow]")
        sys.exit(1)
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
