#!/usr/bin/env python3
"""Upload dataset parquet files to Azure Blob Storage.

This script is for maintainers to upload generated datasets to Azure Blob Storage,
making them available for workshop participants to download.

Usage:
    # Upload velocity_motors dataset
    uv run python scripts/upload_to_azure.py --dataset velocity_motors

    # Upload all datasets
    uv run python scripts/upload_to_azure.py --dataset all

    # Dry run (preview what would be uploaded)
    uv run python scripts/upload_to_azure.py --dataset velocity_motors --dry-run

    # Specify custom container
    uv run python scripts/upload_to_azure.py --dataset star_schema --container my-container

Environment Variables:
    AZURE_STORAGE_CONNECTION_STRING - Full connection string (preferred)

    OR

    AZURE_STORAGE_ACCOUNT - Storage account name
    AZURE_STORAGE_KEY - Storage account key

Requirements:
    pip install azure-storage-blob
    # or: uv add azure-storage-blob
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "dataset_generators" / "data"

# Dataset configurations
DATASETS = {
    "velocity_motors": {
        "path": DATA_DIR / "velocity_motors",
        "files": [
            "salespersons.parquet",
            "vehicles.parquet",
            "orders.parquet",
            "order_items.parquet",
            "customer_segments.parquet",
            "customers.parquet",
            "interactions.parquet",
            "leads.parquet",
            "warehouse_locations.parquet",
            "suppliers.parquet",
            "parts_inventory.parquet",
            "service_orders.parquet",
        ],
    },
    "star_schema": {
        "path": DATA_DIR / "star_schema",
        "files": [
            "dim_date.parquet",
            "dim_product.parquet",
            "dim_customer.parquet",
            "dim_store.parquet",
            "dim_promotion.parquet",
            "fact_sales.parquet",
        ],
    },
    "super_table": {
        "path": DATA_DIR / "super_table",
        "files": [
            "super_table.parquet",
        ],
    },
}

DEFAULT_CONTAINER = "datasets"


def get_blob_service_client():
    """Get Azure Blob Service Client from environment variables.

    Looks for either:
    - AZURE_STORAGE_CONNECTION_STRING (full connection string)
    - AZURE_STORAGE_ACCOUNT + AZURE_STORAGE_KEY (account credentials)

    Returns:
        BlobServiceClient instance

    Raises:
        SystemExit: If credentials are not configured
    """
    try:
        from azure.storage.blob import BlobServiceClient  # pyright: ignore[reportMissingImports]
    except ImportError:
        print("ERROR: azure-storage-blob package not installed.")
        print("Install with: uv add azure-storage-blob")
        print("         or: pip install azure-storage-blob")
        sys.exit(1)

    # Try connection string first
    conn_str = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    if conn_str:
        print("Using AZURE_STORAGE_CONNECTION_STRING for authentication")
        return BlobServiceClient.from_connection_string(conn_str)

    # Try account + key
    account = os.environ.get("AZURE_STORAGE_ACCOUNT")
    key = os.environ.get("AZURE_STORAGE_KEY")
    if account and key:
        print(f"Using account '{account}' with AZURE_STORAGE_KEY for authentication")
        account_url = f"https://{account}.blob.core.windows.net"
        return BlobServiceClient(account_url, credential=key)

    # No credentials found
    print("ERROR: Azure Storage credentials not configured.")
    print()
    print("Set one of the following:")
    print("  Option 1: AZURE_STORAGE_CONNECTION_STRING")
    print("            export AZURE_STORAGE_CONNECTION_STRING='DefaultEndpointsProtocol=https;...'")
    print()
    print("  Option 2: AZURE_STORAGE_ACCOUNT + AZURE_STORAGE_KEY")
    print("            export AZURE_STORAGE_ACCOUNT='mystorageaccount'")
    print("            export AZURE_STORAGE_KEY='your-access-key'")
    sys.exit(1)


def upload_file(
    blob_service_client,
    container_name: str,
    local_path: Path,
    blob_name: str,
    dry_run: bool = False,
) -> bool:
    """Upload a single file to Azure Blob Storage.

    Args:
        blob_service_client: Azure BlobServiceClient instance
        container_name: Target container name
        local_path: Local file path
        blob_name: Destination blob name (path within container)
        dry_run: If True, only print what would be done

    Returns:
        True if successful (or dry run), False on error
    """
    if not local_path.exists():
        print(f"    WARNING: File not found: {local_path}")
        return False

    file_size = local_path.stat().st_size
    size_mb = file_size / (1024 * 1024)

    if dry_run:
        print(f"    [DRY RUN] Would upload: {local_path.name} ({size_mb:.2f} MB)")
        print(f"              Destination: {container_name}/{blob_name}")
        return True

    print(f"    Uploading: {local_path.name} ({size_mb:.2f} MB)")

    try:
        blob_client = blob_service_client.get_blob_client(
            container=container_name,
            blob=blob_name,
        )

        with open(local_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)

        print(f"    Uploaded to: {container_name}/{blob_name}")
        return True

    except Exception as e:
        print(f"    ERROR: {e}")
        return False


def upload_dataset(
    dataset: str,
    container_name: str,
    dry_run: bool = False,
) -> dict[str, bool]:
    """Upload all files for a dataset to Azure Blob Storage.

    Args:
        dataset: Dataset name (velocity_motors, star_schema, super_table)
        container_name: Azure container name
        dry_run: If True, only print what would be done

    Returns:
        Dict mapping filenames to success status
    """
    config = DATASETS.get(dataset)
    if not config:
        print(f"ERROR: Unknown dataset: {dataset}")
        print(f"Available datasets: {', '.join(DATASETS.keys())}")
        return {}

    data_path = config["path"]
    files = config["files"]

    print(f"\n{'=' * 60}")
    print(f"Uploading dataset: {dataset}")
    print(f"Source: {data_path}")
    print(f"Container: {container_name}")
    print(f"Files: {len(files)}")
    print(f"{'=' * 60}")

    if not data_path.exists():
        print(f"\nERROR: Data directory not found: {data_path}")
        print("Generate the dataset first:")
        print(f"  uv run python dataset_generators/generate_{dataset}.py")
        return {}

    # Get blob service client
    if not dry_run:
        blob_service_client = get_blob_service_client()

        # Ensure container exists
        try:
            container_client = blob_service_client.get_container_client(container_name)
            if not container_client.exists():
                print(f"\nCreating container: {container_name}")
                container_client.create_container(public_access="blob")
        except Exception as e:
            print(f"\nWARNING: Could not verify/create container: {e}")
    else:
        blob_service_client = None

    # Upload each file
    results = {}
    for filename in files:
        local_path = data_path / filename
        blob_name = f"{dataset}/{filename}"

        success = upload_file(
            blob_service_client,
            container_name,
            local_path,
            blob_name,
            dry_run,
        )
        results[filename] = success

    return results


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Upload dataset parquet files to Azure Blob Storage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Upload velocity_motors dataset
    uv run python scripts/upload_to_azure.py --dataset velocity_motors

    # Upload all datasets
    uv run python scripts/upload_to_azure.py --dataset all

    # Preview without uploading
    uv run python scripts/upload_to_azure.py --dataset all --dry-run

Environment:
    AZURE_STORAGE_CONNECTION_STRING - Full connection string
    AZURE_STORAGE_ACCOUNT          - Storage account name (with KEY)
    AZURE_STORAGE_KEY              - Storage account key (with ACCOUNT)
        """,
    )

    parser.add_argument(
        "--dataset",
        choices=list(DATASETS.keys()) + ["all"],
        required=True,
        help="Dataset to upload (or 'all' for all datasets)",
    )
    parser.add_argument(
        "--container",
        default=DEFAULT_CONTAINER,
        help=f"Azure Blob container name (default: {DEFAULT_CONTAINER})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be uploaded without actually uploading",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Azure Blob Storage Uploader")
    print("=" * 60)
    print(f"Container: {args.container}")
    if args.dry_run:
        print("Mode: DRY RUN (no actual uploads)")
    print()

    # Determine which datasets to upload
    if args.dataset == "all":
        datasets_to_upload = list(DATASETS.keys())
    else:
        datasets_to_upload = [args.dataset]

    # Upload each dataset
    all_results = {}
    for ds in datasets_to_upload:
        results = upload_dataset(ds, args.container, args.dry_run)
        all_results[ds] = results

    # Summary
    print("\n" + "=" * 60)
    print("UPLOAD SUMMARY")
    print("=" * 60)

    total_success = 0
    total_failed = 0

    for ds, results in all_results.items():
        if not results:
            print(f"\n{ds}: SKIPPED (no files processed)")
            continue

        success = sum(1 for v in results.values() if v)
        failed = sum(1 for v in results.values() if not v)
        total_success += success
        total_failed += failed

        print(f"\n{ds}: {success} succeeded, {failed} failed")
        for filename, ok in results.items():
            status = "OK" if ok else "FAILED"
            print(f"  [{status}] {filename}")

    print(f"\nTotal: {total_success} files uploaded, {total_failed} failed")

    if not args.dry_run and total_success > 0:
        print("\n" + "-" * 60)
        print("FILES ARE NOW AVAILABLE AT:")
        print("-" * 60)
        # Note: The actual URL depends on the storage account
        print("Configure your storage account URL in config/dataset_schemas.py")
        print("Example: https://<account>.blob.core.windows.net/datasets/<dataset>/<file>.parquet")

    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
