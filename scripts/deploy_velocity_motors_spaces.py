#!/usr/bin/env python3
"""Deploy Velocity Motors Genie Spaces to Databricks.

This script deploys Genie Spaces for the Velocity Motors demo dataset:
- Sales Analytics: Vehicle sales, orders, and salesperson performance
- Customer Intelligence: Customer segments, interactions, and lead pipeline
- Operations & Inventory: Parts inventory, suppliers, and service operations
- Unified Analytics: Cross-domain analytics combining all 16 tables

Usage:
    # Dry run (preview what would be created)
    uv run python scripts/deploy_velocity_motors_spaces.py --dry-run

    # Deploy all spaces with a specific profile
    uv run python scripts/deploy_velocity_motors_spaces.py --profile demo-free

    # Deploy specific domain only
    uv run python scripts/deploy_velocity_motors_spaces.py --profile demo-free --domain sales

    # Update existing spaces (uses registry)
    uv run python scripts/deploy_velocity_motors_spaces.py --profile demo-free --update

    # Force recreate (delete and recreate)
    uv run python scripts/deploy_velocity_motors_spaces.py --profile demo-free --force-recreate

Environment Variables:
    WAREHOUSE_ID: Required SQL Warehouse ID (except for --dry-run)
    PARENT_PATH: Required workspace path for Genie Spaces (e.g., /Workspace/Users/you@email.com/genie-spaces)

Options:
    --profile: Databricks CLI profile for authentication (recommended)

Output Files:
    config/velocity_motors_spaces.yaml: Registry of deployed space IDs
    config/velocity_motors_manual_setup.md: Manual setup guide for UI configuration
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from infra.genie_space_manager import GenieSpaceConfig, GenieSpaceManager

# Space configurations
SPACES = {
    "sales": {
        "config_file": "infra/configs/velocity_motors/sales_analytics.yaml",
        "name": "Sales Analytics",
        "domain": "sales",
    },
    "crm": {
        "config_file": "infra/configs/velocity_motors/customer_intelligence.yaml",
        "name": "Customer Intelligence",
        "domain": "crm",
    },
    "operations": {
        "config_file": "infra/configs/velocity_motors/operations_inventory.yaml",
        "name": "Operations & Inventory",
        "domain": "operations",
    },
    "unified": {
        "config_file": "infra/configs/velocity_motors/unified_analytics.yaml",
        "name": "Unified Analytics",
        "domain": "unified",
    },
}

REGISTRY_FILE = PROJECT_ROOT / "config" / "velocity_motors_spaces.yaml"
MANUAL_SETUP_FILE = PROJECT_ROOT / "config" / "velocity_motors_manual_setup.md"


def load_registry() -> dict[str, Any]:
    """Load the space registry from file.

    Returns:
        Dictionary mapping domain names to space IDs and metadata.
    """
    if REGISTRY_FILE.exists():
        with open(REGISTRY_FILE) as f:
            return yaml.safe_load(f) or {}
    return {}


def save_registry(registry: dict[str, Any]) -> None:
    """Save the space registry to file.

    Args:
        registry: Dictionary mapping domain names to space IDs and metadata.
    """
    REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(REGISTRY_FILE, "w") as f:
        yaml.dump(registry, f, default_flow_style=False, sort_keys=False)
    print(f"Registry saved to: {REGISTRY_FILE}")


def generate_manual_setup_guide() -> None:
    """Generate a manual setup guide with instructions, joins, and example SQLs.

    Extracts the documentation-only fields from each YAML config and formats
    them for easy copy-paste into the Databricks Genie UI.
    """
    lines = [
        "# Velocity Motors Genie Spaces - Manual Setup Guide",
        "",
        "This guide contains instructions, join specifications, and example SQL queries",
        "that need to be manually configured in the Databricks Genie UI after space creation.",
        "",
        "> **Note**: The Genie API currently does not support setting these fields programmatically.",
        "> Copy-paste these into the Genie Space settings in the Databricks UI.",
        "",
        "---",
        "",
    ]

    for _, space_info in SPACES.items():
        config_path = PROJECT_ROOT / space_info["config_file"]
        if not config_path.exists():
            continue

        with open(config_path) as f:
            config_data = yaml.safe_load(f)

        lines.append(f"## {space_info['name']}")
        lines.append("")
        lines.append(f"**Config file**: `{space_info['config_file']}`")
        lines.append("")

        # Instructions
        if config_data.get("instructions"):
            lines.append("### Instructions")
            lines.append("")
            lines.append("```")
            lines.append(config_data["instructions"].strip())
            lines.append("```")
            lines.append("")

        # Join Specs
        if config_data.get("join_specs"):
            lines.append("### Join Specifications")
            lines.append("")
            lines.append("| Left Table | Right Table | Join Keys |")
            lines.append("|------------|-------------|-----------|")
            for join in config_data["join_specs"]:
                keys = ", ".join(join["join_keys"])
                lines.append(f"| `{join['left_table']}` | `{join['right_table']}` | `{keys}` |")
            lines.append("")

        # Example SQLs
        if config_data.get("example_sqls"):
            lines.append("### Example SQL Queries")
            lines.append("")
            for i, example in enumerate(config_data["example_sqls"], 1):
                lines.append(f"**{i}. {example['question']}**")
                lines.append("")
                lines.append("```sql")
                lines.append(example["sql"].strip())
                lines.append("```")
                lines.append("")

        lines.append("---")
        lines.append("")

    # Write the guide
    MANUAL_SETUP_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MANUAL_SETUP_FILE, "w") as f:
        f.write("\n".join(lines))
    print(f"Manual setup guide saved to: {MANUAL_SETUP_FILE}")


def deploy_space(
    manager: GenieSpaceManager,
    domain: str,
    space_info: dict[str, str],
    registry: dict[str, Any],
    dry_run: bool = False,
    update: bool = False,
    force_recreate: bool = False,
) -> tuple[str | None, bool]:
    """Deploy a single Genie Space.

    Args:
        manager: GenieSpaceManager instance.
        domain: Domain name (sales, crm, operations).
        space_info: Space configuration info.
        registry: Current registry of deployed spaces.
        dry_run: If True, only preview what would be done.
        update: If True, update existing space from registry.
        force_recreate: If True, delete and recreate existing space.

    Returns:
        Tuple of (space_id, success). space_id is None if failed.
    """
    config_path = PROJECT_ROOT / space_info["config_file"]
    print(f"\n{'=' * 60}")
    print(f"Deploying: {space_info['name']}")
    print(f"Config: {config_path}")
    print(f"{'=' * 60}")

    if not config_path.exists():
        print(f"ERROR: Config file not found: {config_path}")
        return None, False

    try:
        # Load config (will substitute env vars)
        config = GenieSpaceConfig.from_yaml(config_path, substitute_env=not dry_run)

        existing_space_id = registry.get(domain, {}).get("space_id")

        if force_recreate and existing_space_id and not dry_run:
            print(f"Force recreating - deleting existing space: {existing_space_id}")
            try:
                manager.delete_space(existing_space_id)
                print(f"Deleted space: {existing_space_id}")
            except Exception as e:
                print(f"Warning: Could not delete space (may already be deleted): {e}")
            existing_space_id = None

        if update and existing_space_id:
            # Update existing space
            print(f"Updating existing space: {existing_space_id}")
            try:
                manager.update_space(existing_space_id, config, dry_run=dry_run)
                if not dry_run:
                    print(f"Successfully updated space: {existing_space_id}")
                return existing_space_id, True
            except Exception as e:
                error_str = str(e)
                if "404" in error_str or "NOT_FOUND" in error_str:
                    print("Space not found (404). Registry may be stale.")
                    print("Attempting to create new space instead...")
                    # Fall through to create
                    existing_space_id = None
                else:
                    raise

        # Create new space
        if not existing_space_id:
            space_id = manager.create_space(config, dry_run=dry_run)
            if not dry_run:
                print(f"Successfully created space: {space_id}")
            return space_id, True

        # No action needed
        print(f"Space already exists: {existing_space_id}")
        print("Use --update to update or --force-recreate to recreate")
        return existing_space_id, True

    except ValueError as e:
        if "Environment variable" in str(e):
            print(f"ERROR: {e}")
            print("Set WAREHOUSE_ID environment variable or use --dry-run")
            return None, False
        raise
    except Exception as e:
        print(f"ERROR deploying {space_info['name']}: {e}")
        return None, False


def main():
    parser = argparse.ArgumentParser(
        description="Deploy Velocity Motors Genie Spaces to Databricks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be created without making changes",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Update existing spaces from registry",
    )
    parser.add_argument(
        "--force-recreate",
        action="store_true",
        help="Delete and recreate existing spaces",
    )
    parser.add_argument(
        "--domain",
        choices=["sales", "crm", "operations", "unified"],
        help="Deploy only a specific domain",
    )
    parser.add_argument(
        "--profile",
        help="Databricks CLI profile to use for authentication",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Velocity Motors Genie Spaces Deployment")
    print("=" * 60)
    if args.profile:
        print(f"Using profile: {args.profile}")

    # Validate environment
    if not args.dry_run:
        warehouse_id = os.environ.get("WAREHOUSE_ID")
        parent_path = os.environ.get("PARENT_PATH")

        missing = []
        if not warehouse_id:
            missing.append("WAREHOUSE_ID")
        if not parent_path:
            missing.append("PARENT_PATH")

        if missing:
            print(f"\nERROR: Missing required environment variables: {', '.join(missing)}")
            print("\nSet them with:")
            print("  export WAREHOUSE_ID=your_warehouse_id")
            print("  export PARENT_PATH=/Workspace/Users/you@email.com/genie-spaces")
            print("\nOr use --dry-run to preview without deploying")
            sys.exit(1)

        print(f"Using warehouse: {warehouse_id}")
        print(f"Using parent path: {parent_path}")
    else:
        print("DRY RUN MODE - No changes will be made")

    # Load registry
    registry = load_registry()
    if registry:
        print(f"\nLoaded registry with {len(registry)} existing space(s)")
        for domain, info in registry.items():
            print(f"  - {domain}: {info.get('space_id', 'unknown')}")

    # Determine which spaces to deploy
    if args.domain:
        spaces_to_deploy = {args.domain: SPACES[args.domain]}
    else:
        spaces_to_deploy = SPACES

    # Initialize manager
    manager = GenieSpaceManager(profile=args.profile)

    # Deploy spaces
    results = {}
    for domain, space_info in spaces_to_deploy.items():
        space_id, success = deploy_space(
            manager=manager,
            domain=domain,
            space_info=space_info,
            registry=registry,
            dry_run=args.dry_run,
            update=args.update,
            force_recreate=args.force_recreate,
        )
        results[domain] = {"space_id": space_id, "success": success}

        # Update registry if successful
        if success and space_id and not args.dry_run:
            registry[domain] = {
                "space_id": space_id,
                "name": space_info["name"],
                "config_file": space_info["config_file"],
            }

    # Save registry if not dry run
    if not args.dry_run and any(r["success"] for r in results.values()):
        save_registry(registry)

    # Generate manual setup guide
    generate_manual_setup_guide()

    # Summary
    print("\n" + "=" * 60)
    print("DEPLOYMENT SUMMARY")
    print("=" * 60)

    successes = [d for d, r in results.items() if r["success"]]
    failures = [d for d, r in results.items() if not r["success"]]

    if successes:
        print(f"\nSuccessfully deployed ({len(successes)}):")
        for domain in successes:
            space_id = results[domain]["space_id"]
            if args.dry_run:
                print(f"  - {SPACES[domain]['name']}: [DRY RUN]")
            else:
                print(f"  - {SPACES[domain]['name']}: {space_id}")

    if failures:
        print(f"\nFailed ({len(failures)}):")
        for domain in failures:
            print(f"  - {SPACES[domain]['name']}")

    print("\n" + "-" * 60)
    print("NEXT STEPS")
    print("-" * 60)
    print("1. Open each Genie Space in Databricks UI")
    print(f"2. Review the manual setup guide: {MANUAL_SETUP_FILE}")
    print("3. Configure the following in the UI (not supported by API):")
    print("   - Instructions (business context for the AI)")
    print("   - Join specifications (how tables relate)")
    print("   - Example SQL queries (for AI learning)")
    print("4. Test sample questions to verify configuration")

    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
