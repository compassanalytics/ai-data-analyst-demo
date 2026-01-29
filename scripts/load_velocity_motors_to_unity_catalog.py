#!/usr/bin/env python3
"""Load Velocity Motors datasets to Databricks Unity Catalog.

This script:
1. Uploads local Parquet files to Databricks Volumes
2. Creates the velocity_motors catalog and domain schemas
3. Creates tables from the uploaded Parquet files

Usage:
    # Dry run (preview what would be created)
    uv run python scripts/load_velocity_motors_to_unity_catalog.py --dry-run --profile demo-free

    # Full load
    uv run python scripts/load_velocity_motors_to_unity_catalog.py --profile demo-free

    # Load specific domain only
    uv run python scripts/load_velocity_motors_to_unity_catalog.py --profile demo-free --domain sales

Requirements:
    - Databricks CLI profile configured
    - CREATE CATALOG permission (or catalog already exists)
    - Access to a SQL warehouse
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Data directory
DATA_DIR = PROJECT_ROOT / "dataset_generators" / "data" / "velocity_motors"

# Catalog and schema configuration
CATALOG = "velocity_motors"

# Domain to schema mapping with their tables
DOMAINS = {
    "sales": {
        "schema": "sales",
        "tables": ["salespersons", "vehicles", "orders", "order_items"],
    },
    "crm": {
        "schema": "crm",
        "tables": ["customer_segments", "customers", "interactions", "leads"],
    },
    "operations": {
        "schema": "operations",
        "tables": ["warehouse_locations", "suppliers", "parts_inventory", "service_orders"],
    },
}


def get_workspace_client(profile: str | None = None):
    """Get Databricks WorkspaceClient."""
    from databricks.sdk import WorkspaceClient

    if profile:
        return WorkspaceClient(profile=profile)
    return WorkspaceClient()


def execute_sql(client, warehouse_id: str, sql: str, dry_run: bool = False) -> list | None:
    """Execute SQL statement using the SQL Statement API.

    Args:
        client: WorkspaceClient instance
        warehouse_id: SQL warehouse ID
        sql: SQL statement to execute
        dry_run: If True, only print the SQL

    Returns:
        List of result rows or None
    """
    if dry_run:
        print(f"    [DRY RUN] Would execute: {sql[:100]}...")
        return None

    response = client.statement_execution.execute_statement(
        warehouse_id=warehouse_id,
        statement=sql,
        wait_timeout="50s",
    )

    # Wait for completion
    while response.status.state.value in ("PENDING", "RUNNING"):
        time.sleep(1)
        response = client.statement_execution.get_statement(response.statement_id)

    if response.status.state.value == "FAILED":
        error_msg = response.status.error.message if response.status.error else "Unknown error"
        raise RuntimeError(f"SQL execution failed: {error_msg}")

    if response.result and response.result.data_array:
        return response.result.data_array
    return None


def upload_file_to_volume(
    client,
    local_path: Path,
    volume_path: str,
    dry_run: bool = False,
) -> str:
    """Upload a file to a Unity Catalog Volume.

    Args:
        client: WorkspaceClient instance
        local_path: Local file path
        volume_path: Full volume path (e.g., /Volumes/catalog/schema/volume/file.parquet)
        dry_run: If True, only print what would happen

    Returns:
        The volume path where file was uploaded
    """
    if dry_run:
        print(f"    [DRY RUN] Would upload {local_path.name} to {volume_path}")
        return volume_path

    print(f"    Uploading {local_path.name}...")

    with open(local_path, "rb") as f:
        client.files.upload(volume_path, f, overwrite=True)

    return volume_path


def create_catalog_and_schemas(
    client,
    warehouse_id: str,
    domains: list[str],
    dry_run: bool = False,
):
    """Create the catalog and domain schemas.

    Args:
        client: WorkspaceClient instance
        warehouse_id: SQL warehouse ID
        domains: List of domain names to create schemas for
        dry_run: If True, only print what would happen
    """
    print("\n" + "=" * 60)
    print("Creating Catalog and Schemas")
    print("=" * 60)

    # Create catalog
    print(f"\nCreating catalog: {CATALOG}")
    try:
        execute_sql(client, warehouse_id, f"CREATE CATALOG IF NOT EXISTS {CATALOG}", dry_run)
        print(f"  ✓ Catalog {CATALOG} ready")
    except Exception as e:
        print(f"  ⚠ Could not create catalog (may already exist or need permissions): {e}")

    # Create staging volume schema and volume for uploads
    print("\nCreating staging schema and volume...")
    try:
        execute_sql(client, warehouse_id, f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.staging", dry_run)
        execute_sql(client, warehouse_id, f"CREATE VOLUME IF NOT EXISTS {CATALOG}.staging.uploads", dry_run)
        print(f"  ✓ Staging volume {CATALOG}.staging.uploads ready")
    except Exception as e:
        print(f"  ⚠ Could not create staging volume: {e}")

    # Create domain schemas
    for domain in domains:
        schema = DOMAINS[domain]["schema"]
        print(f"\nCreating schema: {CATALOG}.{schema}")
        try:
            execute_sql(client, warehouse_id, f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{schema}", dry_run)
            print(f"  ✓ Schema {CATALOG}.{schema} ready")
        except Exception as e:
            print(f"  ✗ Failed to create schema: {e}")


def load_domain_tables(
    client,
    warehouse_id: str,
    domain: str,
    dry_run: bool = False,
) -> dict[str, bool]:
    """Load all tables for a domain.

    Args:
        client: WorkspaceClient instance
        warehouse_id: SQL warehouse ID
        domain: Domain name (sales, crm, operations)
        dry_run: If True, only print what would happen

    Returns:
        Dict mapping table names to success status
    """
    schema = DOMAINS[domain]["schema"]
    tables = DOMAINS[domain]["tables"]
    results = {}

    print("\n" + "=" * 60)
    print(f"Loading {domain.upper()} Domain Tables")
    print(f"Schema: {CATALOG}.{schema}")
    print("=" * 60)

    for table in tables:
        parquet_path = DATA_DIR / f"{table}.parquet"

        if not parquet_path.exists():
            print(f"\n  ⚠ Skipping {table}: {parquet_path} not found")
            results[table] = False
            continue

        print(f"\n  Loading: {table}")

        try:
            # Upload to volume
            volume_path = f"/Volumes/{CATALOG}/staging/uploads/{table}.parquet"
            upload_file_to_volume(client, parquet_path, volume_path, dry_run)

            # Create table from parquet
            full_table = f"{CATALOG}.{schema}.{table}"

            # Drop existing table first (for idempotency)
            drop_sql = f"DROP TABLE IF EXISTS {full_table}"
            execute_sql(client, warehouse_id, drop_sql, dry_run)

            # Create table from parquet file using read_files()
            create_sql = f"""
                CREATE OR REPLACE TABLE {full_table}
                AS SELECT * FROM read_files('{volume_path}', format => 'parquet')
            """
            execute_sql(client, warehouse_id, create_sql, dry_run)

            print(f"    ✓ Created {full_table}")
            results[table] = True

        except Exception as e:
            print(f"    ✗ Failed: {e}")
            results[table] = False

    return results


def verify_tables(
    client,
    warehouse_id: str,
    domains: list[str],
    dry_run: bool = False,
):
    """Verify all tables were created successfully.

    Args:
        client: WorkspaceClient instance
        warehouse_id: SQL warehouse ID
        domains: List of domains to verify
        dry_run: If True, skip verification
    """
    if dry_run:
        print("\n[DRY RUN] Skipping verification")
        return

    print("\n" + "=" * 60)
    print("Verifying Tables")
    print("=" * 60)

    for domain in domains:
        schema = DOMAINS[domain]["schema"]
        tables = DOMAINS[domain]["tables"]

        print(f"\n{domain.upper()} ({CATALOG}.{schema}):")

        for table in tables:
            full_table = f"{CATALOG}.{schema}.{table}"
            try:
                result = execute_sql(
                    client,
                    warehouse_id,
                    f"SELECT COUNT(*) FROM {full_table}",
                    dry_run,
                )
                if result:
                    count = int(result[0][0])
                    print(f"  ✓ {table}: {count:,} rows")
            except Exception as e:
                print(f"  ✗ {table}: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Load Velocity Motors data to Unity Catalog",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be created without making changes",
    )
    parser.add_argument(
        "--profile",
        help="Databricks CLI profile for authentication",
    )
    parser.add_argument(
        "--domain",
        choices=["sales", "crm", "operations"],
        help="Load only a specific domain",
    )
    parser.add_argument(
        "--skip-upload",
        action="store_true",
        help="Skip file upload (use if files already in volume)",
    )
    args = parser.parse_args()

    # Get warehouse ID from environment
    warehouse_id = os.environ.get("WAREHOUSE_ID")
    if not warehouse_id and not args.dry_run:
        print("ERROR: WAREHOUSE_ID environment variable required")
        print("Set with: export WAREHOUSE_ID=your_warehouse_id")
        sys.exit(1)

    print("=" * 60)
    print("Velocity Motors Data Loader")
    print("=" * 60)
    print(f"Data directory: {DATA_DIR}")
    print(f"Target catalog: {CATALOG}")
    if args.profile:
        print(f"Profile: {args.profile}")
    if args.dry_run:
        print("Mode: DRY RUN")
    print()

    # Check data directory exists
    if not DATA_DIR.exists():
        print(f"ERROR: Data directory not found: {DATA_DIR}")
        print("Run the data generator first:")
        print("  uv run python dataset_generators/generate_velocity_motors.py")
        sys.exit(1)

    # Determine domains to load
    if args.domain:
        domains = [args.domain]
    else:
        domains = list(DOMAINS.keys())

    print(f"Domains to load: {', '.join(domains)}")

    # Initialize client
    try:
        client = get_workspace_client(args.profile)
    except Exception as e:
        print(f"ERROR: Failed to initialize Databricks client: {e}")
        sys.exit(1)

    # Create catalog and schemas
    create_catalog_and_schemas(client, warehouse_id, domains, args.dry_run)

    # Load tables for each domain
    all_results = {}
    for domain in domains:
        results = load_domain_tables(client, warehouse_id, domain, args.dry_run)
        all_results[domain] = results

    # Verify tables
    verify_tables(client, warehouse_id, domains, args.dry_run)

    # Summary
    print("\n" + "=" * 60)
    print("LOAD SUMMARY")
    print("=" * 60)

    total_success = 0
    total_failed = 0

    for domain, results in all_results.items():
        success = sum(1 for v in results.values() if v)
        failed = sum(1 for v in results.values() if not v)
        total_success += success
        total_failed += failed
        print(f"\n{domain}: {success} succeeded, {failed} failed")
        for table, ok in results.items():
            status = "✓" if ok else "✗"
            print(f"  {status} {table}")

    print(f"\nTotal: {total_success} tables loaded, {total_failed} failed")

    if not args.dry_run and total_success > 0:
        print("\n" + "-" * 60)
        print("NEXT STEPS")
        print("-" * 60)
        print("1. Deploy Genie Spaces:")
        print(f"   uv run python scripts/deploy_velocity_motors_spaces.py --profile {args.profile or 'YOUR_PROFILE'}")
        print("\n2. Configure spaces in Databricks UI (instructions, joins, example SQLs)")

    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
