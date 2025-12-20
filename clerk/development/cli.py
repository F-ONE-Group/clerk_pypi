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

    # GUI graph check subcommand
    gui_graph_parser = gui_subparsers.add_parser(
        "graph", help="Graph analysis commands"
    )
    gui_graph_subparsers = gui_graph_parser.add_subparsers(
        dest="graph_command", help="Graph subcommands"
    )

    gui_graph_check_parser = gui_graph_subparsers.add_parser(
        "check", help="Check and visualize state machine graph structure"
    )
    gui_graph_check_parser.add_argument(
        "--module-path",
        type=str,
        required=False,
        default=None,
        help="Path to the Python file containing the state machine (defaults to src/main.py)",
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

    # Code command group
    code_parser = subparsers.add_parser(
        "code", help="Custom code development and testing commands"
    )
    code_subparsers = code_parser.add_subparsers(
        dest="code_command", help="Code subcommands"
    )

    # Code run subcommand
    code_run_parser = code_subparsers.add_parser(
        "run", help="Run custom code with test payloads"
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

        elif args.gui_command == "graph":
            if not hasattr(args, "graph_command") or not args.graph_command:
                print("Error: graph command requires a subcommand")
                print("Available subcommands: check")
                sys.exit(1)

            if args.graph_command == "check":
                from clerk.development.gui.graph_checker import check_graph

                check_graph(args.module_path)

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

    elif args.command == "code":
        if not hasattr(args, "code_command") or not args.code_command:
            code_parser.print_help()
            sys.exit(1)

        if args.code_command == "run":
            from clerk.development.code_runner import main_with_args

            main_with_args(project_root)


if __name__ == "__main__":
    main()
