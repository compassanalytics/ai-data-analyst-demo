#!/usr/bin/env python
"""CLI for Databricks Genie Space Infrastructure-as-Code management.

This CLI provides commands to deploy, list, get, delete, and export Genie Spaces
using YAML configuration files.

Usage:
    # Deploy a new space
    uv run python infra/cli.py deploy infra/configs/sample_genie_space.yaml

    # Update an existing space
    uv run python infra/cli.py deploy infra/configs/sample_genie_space.yaml --update SPACE_ID

    # Preview changes without applying (dry run)
    uv run python infra/cli.py deploy infra/configs/sample_genie_space.yaml --dry-run

    # List all spaces
    uv run python infra/cli.py list

    # Get space details
    uv run python infra/cli.py get SPACE_ID

    # Export space to YAML
    uv run python infra/cli.py export SPACE_ID --output my_space.yaml

    # Delete a space
    uv run python infra/cli.py delete SPACE_ID
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def get_manager():
    """Get a GenieSpaceManager instance."""
    from infra.genie_space_manager import GenieSpaceManager

    return GenieSpaceManager()


def cmd_deploy(args: argparse.Namespace) -> int:
    """Deploy a Genie Space from configuration.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Configuration file not found: {config_path}", file=sys.stderr)
        return 1

    try:
        manager = get_manager()
        space_id = manager.deploy_from_config(
            config_path=config_path,
            space_id=args.update,
            dry_run=args.dry_run,
        )

        if not args.dry_run:
            action = "Updated" if args.update else "Created"
            print(f"\n{action} Genie Space successfully!")
            print(f"  Space ID: {space_id}")

            # Print the workspace URL hint
            print(f"\nTo view the space, navigate to:")
            print(f"  SQL > Genie Spaces > (find by title)")

        return 0

    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error deploying space: {e}", file=sys.stderr)
        return 1


def cmd_list(args: argparse.Namespace) -> int:
    """List all Genie Spaces.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        manager = get_manager()
        spaces = manager.list_spaces()

        if not spaces:
            print("No Genie Spaces found.")
            return 0

        if args.json:
            print(json.dumps(spaces, indent=2))
        else:
            print(f"Found {len(spaces)} Genie Space(s):\n")
            print(f"{'Space ID':<40} {'Title':<40} {'Status':<15}")
            print("-" * 95)
            for space in spaces:
                space_id = space.get("space_id", "N/A")
                title = space.get("title", "N/A")[:38]
                status = space.get("status", "N/A")
                print(f"{space_id:<40} {title:<40} {status:<15}")

        return 0

    except Exception as e:
        print(f"Error listing spaces: {e}", file=sys.stderr)
        return 1


def cmd_get(args: argparse.Namespace) -> int:
    """Get details of a Genie Space.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        manager = get_manager()
        space = manager.get_space(args.space_id)

        if args.json:
            print(json.dumps(space, indent=2))
        else:
            print(f"Genie Space Details")
            print("=" * 60)
            print(f"Space ID:    {space.get('space_id', 'N/A')}")
            print(f"Title:       {space.get('title', 'N/A')}")
            print(f"Description: {space.get('description', 'N/A')}")
            print(f"Status:      {space.get('status', 'N/A')}")
            print(f"Warehouse:   {space.get('warehouse_id', 'N/A')}")
            print(f"Parent Path: {space.get('parent_path', 'N/A')}")
            print(f"Created By:  {space.get('created_by', 'N/A')}")
            print(f"Created At:  {space.get('created_at', 'N/A')}")
            print(f"Updated At:  {space.get('updated_at', 'N/A')}")

            # Parse and display serialized_space info
            serialized = space.get("serialized_space")
            if serialized:
                try:
                    data = json.loads(serialized)

                    # Tables
                    tables = data.get("data_sources", {}).get("tables", [])
                    if tables:
                        print(f"\nTables ({len(tables)}):")
                        for t in tables:
                            print(f"  - {t.get('identifier', 'N/A')}")

                    # Sample questions
                    questions = data.get("config", {}).get("sample_questions", [])
                    if questions:
                        print(f"\nSample Questions ({len(questions)}):")
                        for q in questions[:5]:  # Show first 5
                            question_text = q.get("question", [""])[0][:60]
                            print(f"  - {question_text}")
                        if len(questions) > 5:
                            print(f"  ... and {len(questions) - 5} more")

                except json.JSONDecodeError:
                    pass

        return 0

    except Exception as e:
        print(f"Error getting space: {e}", file=sys.stderr)
        return 1


def cmd_export(args: argparse.Namespace) -> int:
    """Export a Genie Space to YAML.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        manager = get_manager()
        output_path = args.output or f"genie_space_{args.space_id}.yaml"
        manager.export_space(args.space_id, output_path)
        return 0

    except Exception as e:
        print(f"Error exporting space: {e}", file=sys.stderr)
        return 1


def cmd_delete(args: argparse.Namespace) -> int:
    """Delete (trash) a Genie Space.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        # Confirm deletion unless --force is specified
        if not args.force:
            print(f"Are you sure you want to delete Genie Space '{args.space_id}'?")
            print("This action moves the space to trash.")
            response = input("Type 'yes' to confirm: ")
            if response.lower() != "yes":
                print("Deletion cancelled.")
                return 0

        manager = get_manager()
        manager.delete_space(args.space_id, dry_run=args.dry_run)

        if not args.dry_run:
            print(f"Genie Space '{args.space_id}' has been moved to trash.")

        return 0

    except Exception as e:
        print(f"Error deleting space: {e}", file=sys.stderr)
        return 1


def main() -> int:
    """Main entry point for the CLI.

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    parser = argparse.ArgumentParser(
        description="Genie Space Infrastructure-as-Code CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Deploy a new space:
    uv run python infra/cli.py deploy infra/configs/sample_genie_space.yaml

  Update an existing space:
    uv run python infra/cli.py deploy infra/configs/sample_genie_space.yaml --update abc123

  Preview changes (dry run):
    uv run python infra/cli.py deploy infra/configs/sample_genie_space.yaml --dry-run

  List all spaces:
    uv run python infra/cli.py list

  Export a space to YAML:
    uv run python infra/cli.py export abc123 --output my_space.yaml
""",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # deploy command
    deploy_parser = subparsers.add_parser(
        "deploy", help="Deploy a Genie Space from a YAML configuration file"
    )
    deploy_parser.add_argument(
        "config", help="Path to the YAML configuration file"
    )
    deploy_parser.add_argument(
        "--update",
        metavar="SPACE_ID",
        help="Space ID to update instead of creating a new space",
    )
    deploy_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be created/updated without making changes",
    )
    deploy_parser.set_defaults(func=cmd_deploy)

    # list command
    list_parser = subparsers.add_parser("list", help="List all Genie Spaces")
    list_parser.add_argument(
        "--json", action="store_true", help="Output as JSON"
    )
    list_parser.set_defaults(func=cmd_list)

    # get command
    get_parser = subparsers.add_parser("get", help="Get Genie Space details")
    get_parser.add_argument("space_id", help="Space ID to retrieve")
    get_parser.add_argument(
        "--json", action="store_true", help="Output as JSON"
    )
    get_parser.set_defaults(func=cmd_get)

    # export command
    export_parser = subparsers.add_parser(
        "export", help="Export a Genie Space configuration to YAML"
    )
    export_parser.add_argument("space_id", help="Space ID to export")
    export_parser.add_argument(
        "--output", "-o", help="Output file path (default: genie_space_<id>.yaml)"
    )
    export_parser.set_defaults(func=cmd_export)

    # delete command
    delete_parser = subparsers.add_parser(
        "delete", help="Delete (trash) a Genie Space"
    )
    delete_parser.add_argument("space_id", help="Space ID to delete")
    delete_parser.add_argument(
        "--force", "-f", action="store_true", help="Skip confirmation prompt"
    )
    delete_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be deleted without making changes",
    )
    delete_parser.set_defaults(func=cmd_delete)

    # Parse arguments
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
