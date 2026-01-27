#!/usr/bin/env python
"""Setup Databricks Vector Search endpoint and index.

Creates the necessary infrastructure for RAG:
1. Unity Catalog schema (if not exists)
2. Delta table for document chunks
3. Vector Search endpoint
4. Delta Sync index with managed embeddings

Usage:
    # Dry run - show what would be created
    uv run python scripts/setup_vector_search.py --dry-run

    # Create resources
    uv run python scripts/setup_vector_search.py

    # Custom endpoint name
    uv run python scripts/setup_vector_search.py --endpoint-name my-endpoint

    # Skip endpoint creation (use existing)
    uv run python scripts/setup_vector_search.py --skip-endpoint
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Config

# Default configuration (can be overridden by environment variables)
import os
DEFAULT_ENDPOINT_NAME = os.getenv("VECTOR_SEARCH_ENDPOINT", "rag-demo-endpoint")
DEFAULT_CATALOG = os.getenv("VS_CATALOG", "workspace")
DEFAULT_SCHEMA = os.getenv("VS_SCHEMA", "rag_demo")
DEFAULT_TABLE = os.getenv("VS_TABLE", "document_chunks")
DEFAULT_INDEX = os.getenv("VS_INDEX", "document_index")

# Delta table schema for document chunks
# Note: Change Data Feed is required for Delta Sync Vector Search indexes
TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS {catalog}.{schema}.{table} (
    id STRING NOT NULL COMMENT 'Unique chunk identifier (content hash)',
    content STRING NOT NULL COMMENT 'Document chunk text',
    source STRING NOT NULL COMMENT 'Source document filename',
    metadata STRING COMMENT 'JSON metadata (section, position, etc.)'
)
USING DELTA
TBLPROPERTIES (delta.enableChangeDataFeed = true)
COMMENT 'Document chunks for RAG Vector Search'
"""

# SQL to enable CDF on existing table
ENABLE_CDF_SQL = """
ALTER TABLE {catalog}.{schema}.{table}
SET TBLPROPERTIES (delta.enableChangeDataFeed = true)
"""


def create_schema(config: Config, catalog: str, schema: str, dry_run: bool = False) -> bool:
    """Create Unity Catalog schema if not exists.

    Args:
        config: Configuration instance
        catalog: Catalog name
        schema: Schema name to create
        dry_run: If True, only print what would be done

    Returns:
        True if successful or dry run
    """
    print(f"\n📁 Creating schema: {catalog}.{schema}")

    sql = f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}"

    if dry_run:
        print(f"   [DRY RUN] Would execute: {sql}")
        return True

    try:
        from databricks.sdk import WorkspaceClient

        client = WorkspaceClient(
            host=config.databricks_host,
            token=config.databricks_token,
        )

        # Execute SQL to create schema
        client.statement_execution.execute_statement(
            warehouse_id=config.warehouse_id,
            statement=sql,
            wait_timeout="30s",
        )
        print(f"   ✅ Schema {catalog}.{schema} ready")
        return True

    except Exception as e:
        print(f"   ❌ Failed to create schema: {e}")
        return False


def create_delta_table(
    config: Config,
    catalog: str,
    schema: str,
    table: str,
    dry_run: bool = False,
) -> bool:
    """Create Delta table for document chunks.

    Args:
        config: Configuration instance
        catalog: Catalog name
        schema: Schema name
        table: Table name
        dry_run: If True, only print what would be done

    Returns:
        True if successful or dry run
    """
    full_name = f"{catalog}.{schema}.{table}"
    print(f"\n📊 Creating Delta table: {full_name}")

    sql = TABLE_SCHEMA.format(catalog=catalog, schema=schema, table=table)
    cdf_sql = ENABLE_CDF_SQL.format(catalog=catalog, schema=schema, table=table)

    if dry_run:
        print(f"   [DRY RUN] Would execute:")
        for line in sql.strip().split("\n"):
            print(f"      {line}")
        return True

    try:
        from databricks.sdk import WorkspaceClient

        client = WorkspaceClient(
            host=config.databricks_host,
            token=config.databricks_token,
        )

        # Execute SQL to create table
        client.statement_execution.execute_statement(
            warehouse_id=config.warehouse_id,
            statement=sql,
            wait_timeout="30s",
        )
        print(f"   ✅ Table {full_name} created")

        # Ensure Change Data Feed is enabled (required for Delta Sync)
        print(f"   ⏳ Enabling Change Data Feed...")
        client.statement_execution.execute_statement(
            warehouse_id=config.warehouse_id,
            statement=cdf_sql,
            wait_timeout="30s",
        )
        print(f"   ✅ Change Data Feed enabled")
        return True

    except Exception as e:
        print(f"   ❌ Failed to create table: {e}")
        return False


def create_vector_search_endpoint(
    config: Config,
    endpoint_name: str,
    dry_run: bool = False,
) -> bool:
    """Create Vector Search endpoint if not exists.

    Note: Free tier allows only 1 endpoint with 1 unit.
    Endpoint creation takes 5-15 minutes.

    Args:
        config: Configuration instance
        endpoint_name: Name for the VS endpoint
        dry_run: If True, only print what would be done

    Returns:
        True if successful or dry run
    """
    print(f"\n🔍 Creating Vector Search endpoint: {endpoint_name}")

    if dry_run:
        print(f"   [DRY RUN] Would create endpoint '{endpoint_name}' (type: STANDARD)")
        return True

    try:
        from databricks.vector_search.client import VectorSearchClient

        vsc = VectorSearchClient(
            workspace_url=config.databricks_host,
            personal_access_token=config.databricks_token,
        )

        # Check if endpoint already exists
        try:
            endpoints = vsc.list_endpoints()
            existing = [e for e in endpoints.get("endpoints", []) if e.get("name") == endpoint_name]

            if existing:
                status = existing[0].get("endpoint_status", {}).get("state", "UNKNOWN")
                print(f"   ℹ️  Endpoint '{endpoint_name}' already exists (status: {status})")
                return True
        except Exception:
            pass  # Assume endpoint doesn't exist

        # Create new endpoint
        print(f"   ⏳ Creating endpoint (this takes 5-15 minutes)...")
        vsc.create_endpoint(
            name=endpoint_name,
            endpoint_type="STANDARD",  # Required for free tier
        )

        # Wait for endpoint to be ready
        print(f"   ⏳ Waiting for endpoint to be ONLINE...")
        max_wait = 900  # 15 minutes
        wait_interval = 30
        elapsed = 0

        while elapsed < max_wait:
            try:
                endpoint = vsc.get_endpoint(endpoint_name)
                status = endpoint.get("endpoint_status", {}).get("state", "UNKNOWN")

                if status == "ONLINE":
                    print(f"   ✅ Endpoint '{endpoint_name}' is ONLINE")
                    return True
                elif status in ("FAILED", "DELETED"):
                    print(f"   ❌ Endpoint creation failed: {status}")
                    return False

                print(f"   ... Status: {status} (waited {elapsed}s)")

            except Exception as e:
                print(f"   ... Checking status: {e}")

            time.sleep(wait_interval)
            elapsed += wait_interval

        print(f"   ⚠️  Endpoint creation timed out after {max_wait}s. Check Databricks UI.")
        return False

    except Exception as e:
        print(f"   ❌ Failed to create endpoint: {e}")
        return False


def create_delta_sync_index(
    config: Config,
    endpoint_name: str,
    catalog: str,
    schema: str,
    table: str,
    index_name: str,
    embedding_endpoint: str,
    dry_run: bool = False,
) -> bool:
    """Create Delta Sync index with managed embeddings.

    The index will automatically generate embeddings from the 'content' column
    using the specified embedding model endpoint.

    Args:
        config: Configuration instance
        endpoint_name: VS endpoint name
        catalog: Catalog name
        schema: Schema name
        table: Source table name
        index_name: Index name to create
        embedding_endpoint: Embedding model endpoint name
        dry_run: If True, only print what would be done

    Returns:
        True if successful or dry run
    """
    source_table = f"{catalog}.{schema}.{table}"
    full_index_name = f"{catalog}.{schema}.{index_name}"

    print(f"\n📇 Creating Delta Sync index: {full_index_name}")
    print(f"   Source table: {source_table}")
    print(f"   Embedding model: {embedding_endpoint}")

    if dry_run:
        print(f"   [DRY RUN] Would create index with:")
        print(f"      - endpoint_name: {endpoint_name}")
        print(f"      - source_table: {source_table}")
        print(f"      - index_name: {full_index_name}")
        print(f"      - primary_key: id")
        print(f"      - embedding_source_column: content")
        print(f"      - embedding_model_endpoint_name: {embedding_endpoint}")
        print(f"      - pipeline_type: TRIGGERED")
        return True

    try:
        from databricks.vector_search.client import VectorSearchClient

        vsc = VectorSearchClient(
            workspace_url=config.databricks_host,
            personal_access_token=config.databricks_token,
        )

        # Check if index already exists
        try:
            index = vsc.get_index(
                endpoint_name=endpoint_name,
                index_name=full_index_name,
            )
            status = index.get("status", {}).get("ready", False)
            print(f"   ℹ️  Index '{full_index_name}' already exists (ready: {status})")
            return True
        except Exception:
            pass  # Index doesn't exist, create it

        # Create Delta Sync index with managed embeddings
        print(f"   ⏳ Creating index...")
        vsc.create_delta_sync_index(
            endpoint_name=endpoint_name,
            source_table_name=source_table,
            index_name=full_index_name,
            pipeline_type="TRIGGERED",  # Manual sync
            primary_key="id",
            embedding_source_column="content",
            embedding_model_endpoint_name=embedding_endpoint,
        )

        print(f"   ✅ Index '{full_index_name}' created")
        print(f"   ℹ️  Note: Index needs to be synced after loading documents")
        return True

    except Exception as e:
        print(f"   ❌ Failed to create index: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Setup Databricks Vector Search for RAG",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--endpoint-name",
        default=DEFAULT_ENDPOINT_NAME,
        help=f"Vector Search endpoint name (default: {DEFAULT_ENDPOINT_NAME})",
    )
    parser.add_argument(
        "--catalog",
        default=DEFAULT_CATALOG,
        help=f"Unity Catalog name (default: {DEFAULT_CATALOG})",
    )
    parser.add_argument(
        "--schema",
        default=DEFAULT_SCHEMA,
        help=f"Schema name (default: {DEFAULT_SCHEMA})",
    )
    parser.add_argument(
        "--table",
        default=DEFAULT_TABLE,
        help=f"Table name (default: {DEFAULT_TABLE})",
    )
    parser.add_argument(
        "--index",
        default=DEFAULT_INDEX,
        help=f"Index name (default: {DEFAULT_INDEX})",
    )
    parser.add_argument(
        "--skip-endpoint",
        action="store_true",
        help="Skip endpoint creation (use existing endpoint)",
    )
    parser.add_argument(
        "--skip-table",
        action="store_true",
        help="Skip table creation (use existing table)",
    )

    args = parser.parse_args()

    # Load configuration
    print("🔧 Loading configuration...")
    config = Config.from_env()

    # Validate configuration
    if not config.mock_mode:
        if not config.databricks_host:
            print("❌ DATABRICKS_HOST is required")
            sys.exit(1)
        if not config.warehouse_id:
            print("❌ WAREHOUSE_ID is required for SQL operations")
            sys.exit(1)

    embedding_endpoint = config.embedding_endpoint

    print(f"\n📋 Configuration:")
    print(f"   Databricks Host: {config.databricks_host}")
    print(f"   Warehouse ID: {config.warehouse_id}")
    print(f"   Embedding Model: {embedding_endpoint}")
    print(f"   Catalog: {args.catalog}")
    print(f"   Schema: {args.schema}")
    print(f"   Table: {args.table}")
    print(f"   Index: {args.index}")
    print(f"   Endpoint: {args.endpoint_name}")

    if args.dry_run:
        print(f"\n🔍 DRY RUN MODE - No changes will be made\n")

    # Step 1: Create schema
    if not create_schema(config, args.catalog, args.schema, args.dry_run):
        print("\n❌ Failed to create schema. Aborting.")
        sys.exit(1)

    # Step 2: Create Delta table
    if not args.skip_table:
        if not create_delta_table(config, args.catalog, args.schema, args.table, args.dry_run):
            print("\n❌ Failed to create table. Aborting.")
            sys.exit(1)
    else:
        print(f"\n⏭️  Skipping table creation (--skip-table)")

    # Step 3: Create Vector Search endpoint
    if not args.skip_endpoint:
        if not create_vector_search_endpoint(config, args.endpoint_name, args.dry_run):
            print("\n❌ Failed to create endpoint. Aborting.")
            sys.exit(1)
    else:
        print(f"\n⏭️  Skipping endpoint creation (--skip-endpoint)")

    # Step 4: Create Delta Sync index
    if not create_delta_sync_index(
        config,
        args.endpoint_name,
        args.catalog,
        args.schema,
        args.table,
        args.index,
        embedding_endpoint,
        args.dry_run,
    ):
        print("\n❌ Failed to create index. Aborting.")
        sys.exit(1)

    # Summary
    print("\n" + "=" * 60)
    if args.dry_run:
        print("✅ DRY RUN COMPLETE - No changes were made")
    else:
        print("✅ SETUP COMPLETE")
        print(f"\nAdd to your .env file:")
        print(f"   VECTOR_SEARCH_ENDPOINT={args.endpoint_name}")
        print(f"   VECTOR_SEARCH_INDEX={args.catalog}.{args.schema}.{args.index}")
        print(f"\nNext steps:")
        print(f"   1. Load documents: uv run python scripts/load_documents.py")
        print(f"   2. Sync index: The sync happens automatically after loading")


if __name__ == "__main__":
    main()
