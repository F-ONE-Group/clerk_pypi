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
        "--gui-automation",
        action="store_true",
        help="Include GUI automation functionality",
    )
    init_parser.add_argument(
        "--target-dir",
        type=str,
        default=None,
        help="Target directory for the project (default: ./src)",
    )

    # GUI test session subcommand
    gui_parser = subparsers.add_parser(
        "gui-test",
        help="Start interactive GUI automation test session"
    )

    # Fetch schema subcommand
    schema_parser = subparsers.add_parser(
        "fetch-schema",
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

        main_with_args(gui_automation=args.gui_automation, target_dir=args.target_dir)

    elif args.command == "gui-test":
        from clerk.development.gui.test_session import main as gui_main
        gui_main()

    elif args.command == "fetch-schema":
        from clerk.development.schema.fetch_schema import main_with_args
        project_id = os.getenv("PROJECT_ID")
        if not project_id:
            print("Error: PROJECT_ID environment variable not set.")
            sys.exit(1)
        main_with_args(project_id, project_root)


if __name__ == "__main__":
    main()
