"""Clerk CLI - Unified command-line interface for Clerk development tools"""
import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv


def find_project_root() -> Path:
    """Find the project root by looking for common markers"""
    cwd = Path.cwd()

    project_root_files = ["pyproject.toml", ".env"]

    # Check current directory and parents
    for path in [cwd] + list(cwd.parents):
        for marker in project_root_files:
            if (path / marker).exists():
                return path

    return cwd


def main():
    """Main CLI entry point with subcommands"""
    # Find project root and load environment variables from there
    project_root = find_project_root()
    dotenv_path = project_root / ".env"
    load_dotenv(dotenv_path)

    parser = argparse.ArgumentParser(
        prog="clerk",
        description="Clerk development tools",
        epilog="Run 'clerk <command> --help' for more information on a command."
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Init project subcommand
    init_parser = subparsers.add_parser(
        "init", help="Initialize a new Clerk custom code project"
    )
    init_parser.add_argument(
        "--target-dir",
        type=str,
        default=None,
        help="Target directory for the project (default: ./src)",
    )

    # GUI command group
    gui_parser = subparsers.add_parser(
        "gui",
        help="GUI automation commands"
    )
    gui_subparsers = gui_parser.add_subparsers(dest="gui_command", help="GUI subcommands")
    
    # GUI connect subcommand
    gui_connect_parser = gui_subparsers.add_parser(
        "connect",
        help="Start interactive GUI automation test session"
    )

    # Schema command group
    schema_parser = subparsers.add_parser(
        "schema",
        help="Schema management commands"
    )
    schema_subparsers = schema_parser.add_subparsers(dest="schema_command", help="Schema subcommands")
    
    # Schema fetch subcommand
    schema_fetch_parser = schema_subparsers.add_parser(
        "fetch",
        help="Fetch and generate Pydantic models from project schema"
    )

    args = parser.parse_args()

    # Show help if no command specified
    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Route to appropriate handler
    if args.command == "init":
        from clerk.development.init_project import main_with_args

        main_with_args(gui_automation=None, target_dir=args.target_dir)

    elif args.command == "gui":
        if not hasattr(args, 'gui_command') or not args.gui_command:
            gui_parser.print_help()
            sys.exit(1)
        
        if args.gui_command == "connect":
            from clerk.development.gui.test_session import main as gui_main
            gui_main()

    elif args.command == "schema":
        if not hasattr(args, 'schema_command') or not args.schema_command:
            schema_parser.print_help()
            sys.exit(1)
        
        if args.schema_command == "fetch":
            from clerk.development.schema.fetch_schema import main_with_args
            project_id = os.getenv("PROJECT_ID")
            if not project_id:
                print("Error: PROJECT_ID environment variable not set.")
                sys.exit(1)
            main_with_args(project_id, project_root)


if __name__ == "__main__":
    main()
