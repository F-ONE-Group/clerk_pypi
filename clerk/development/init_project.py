"""Project initialization module for Clerk custom code projects."""
import sys
from pathlib import Path
from typing import Optional


def safe_print(message: str) -> None:
    """Print message with fallback for terminals that don't support Unicode."""
    try:
        print(message)
    except UnicodeEncodeError:
        # Fallback: remove emojis and special characters
        import re
        ascii_message = re.sub(r'[^\x00-\x7F]+', '', message)
        print(ascii_message)


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
        safe_print(f"⚠️  {main_path} already exists, skipping...")
        return
    
    template_name = "main_gui.py.template" if with_gui else "main_basic.py.template"
    content = read_template(template_name)
    
    with open(main_path, "w", encoding='utf-8') as f:
        f.write(content)
    
    safe_print(f"✅ Created {main_path}")


def create_gui_structure(target_dir: Path) -> None:
    """Create GUI automation folder structure with template files.
    
    Args:
        target_dir: Target directory where gui folder should be created
    """
    safe_print("\n🔧 Creating GUI automation structure...")
    
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
            safe_print(f"⚠️  {output_path} already exists, skipping...")
            continue
        
        content = read_template(template_name)
        
        with open(output_path, "w", encoding='utf-8') as f:
            f.write(content)
    
    safe_print(f"✅ Created GUI automation structure in {gui_path}")


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
    
    safe_print("=" * 60)
    safe_print("🚀 Initializing Clerk Custom Code Project")
    safe_print("=" * 60)
    if with_gui:
        safe_print("📱 GUI Automation: ENABLED")
    else:
        safe_print("📱 GUI Automation: DISABLED")
    safe_print("=" * 60)
    
    # Create main.py
    create_main_py(target_dir, with_gui=with_gui)
    
    # Create GUI structure if requested
    if with_gui:
        create_gui_structure(target_dir)
    
    safe_print("\n" + "=" * 60)
    safe_print("🎉 Project initialization completed!")
    safe_print("=" * 60)
    if with_gui:
        safe_print("✅ GUI automation structure created")
        safe_print("✅ main.py configured with ScreenPilot")
    else:
        safe_print("✅ Basic main.py created")
    safe_print("\n💡 Next steps:")
    safe_print("   1. Configure your .env file with CLERK_API_KEY and PROJECT_ID")
    safe_print("   2. Run 'clerk fetch-schema' to generate schema models")
    safe_print("   3. Start developing your custom code!")
    safe_print("=" * 60)


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
        safe_print(f"\n❌ Error during project initialization: {e}")
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
