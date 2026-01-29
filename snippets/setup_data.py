"""Workshop Data Setup - Condensed Script

Copy-paste friendly script to load workshop datasets into Unity Catalog.
Requires Databricks with Unity Catalog enabled (not Community Edition).
"""

import io
import os

import requests

# === CONFIGURATION ===
DATASET = "velocity_motors"  # Options: "velocity_motors", "star_schema", "super_table", "all"
CATALOG = "workshop"

DATASET_CONFIGS = {
    "velocity_motors": {
        "base_url": "https://compassagentemofiles.blob.core.windows.net/datasets/velocity_motors",
        "schemas": {
            "sales": [
                "territories",
                "salespersons",
                "vehicles",
                "features",
                "vehicle_features",
                "price_history",
                "orders",
                "order_items",
            ],
            "crm": ["customer_segments", "customers", "interactions", "leads"],
            "operations": ["warehouse_locations", "suppliers", "parts_inventory", "service_orders"],
        },
    },
    "star_schema": {
        "base_url": "https://compassagentemofiles.blob.core.windows.net/datasets/star_schema",
        "schemas": {
            "analytics": ["dim_date", "dim_product", "dim_customer", "dim_store", "dim_promotion", "fact_sales"],
        },
    },
    "super_table": {
        "base_url": "https://compassagentemofiles.blob.core.windows.net/datasets/super_table",
        "schemas": {"demo": ["super_table"]},
    },
}

# === FUNCTIONS ===

IN_DATABRICKS = "DATABRICKS_RUNTIME_VERSION" in os.environ


def download_file(url: str, volume_path: str) -> bool:
    """Download file from URL to Unity Catalog Volume using SDK Files API."""
    try:
        print(f"    Downloading {url.split('/')[-1]}...")
        response = requests.get(url, timeout=120)
        response.raise_for_status()

        if IN_DATABRICKS:
            from databricks.sdk import WorkspaceClient

            WorkspaceClient().files.upload(volume_path, io.BytesIO(response.content), overwrite=True)
            print(f"    Uploaded to {volume_path}")
        else:
            import tempfile

            local_path = os.path.join(tempfile.gettempdir(), os.path.basename(volume_path))
            with open(local_path, "wb") as f:
                f.write(response.content)
            print(f"    Saved to {local_path}")
        return True
    except Exception as e:
        print(f"    ERROR: {e}")
        return False


def add_column_comments(catalog: str, schema: str, table: str, descriptions: dict[str, str]) -> None:
    """Add column comments to a table for Genie AI context."""
    for column, description in descriptions.items():
        try:
            spark.sql(
                f"ALTER TABLE {catalog}.{schema}.{table} ALTER COLUMN `{column}` COMMENT '{description.replace(chr(39), chr(39) * 2)}'"
            )  # noqa: F821
        except Exception:
            pass


def setup_dataset(dataset_name: str, catalog: str) -> dict[str, bool]:
    """Set up a complete dataset in Unity Catalog."""
    config = DATASET_CONFIGS.get(dataset_name)
    if not config:
        print(f"ERROR: Unknown dataset: {dataset_name}")
        return {}

    results = {}
    print(f"\n{'=' * 60}\nSetting up: {dataset_name} -> {catalog}\n{'=' * 60}")

    # Try to load column descriptions
    try:
        from config.dataset_schemas import get_column_descriptions

        has_descriptions = True
    except ImportError:
        has_descriptions = False

    for schema_name, tables in config["schemas"].items():
        print(f"\nSchema: {catalog}.{schema_name}")
        try:
            spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema_name}")  # noqa: F821
        except Exception as e:
            print(f"  ERROR creating schema: {e}")
            continue

        for table in tables:
            print(f"  Table: {table}")
            try:
                file_url = f"{config['base_url']}/{table}.parquet"
                volume_path = f"/Volumes/{catalog}/staging/uploads/{dataset_name}_{table}.parquet"
                full_table = f"{catalog}.{schema_name}.{table}"

                if not download_file(file_url, volume_path):
                    results[table] = False
                    continue

                spark.sql(f"DROP TABLE IF EXISTS {full_table}")  # noqa: F821
                spark.sql(
                    f"CREATE TABLE {full_table} AS SELECT * FROM read_files('{volume_path}', format => 'parquet')"
                )  # noqa: F821

                if has_descriptions:
                    try:
                        ds_schema = "default" if dataset_name in ["star_schema", "super_table"] else schema_name
                        descriptions = get_column_descriptions(dataset_name, ds_schema, table)
                        add_column_comments(catalog, schema_name, table, descriptions)
                    except Exception:
                        pass

                results[table] = True
                print(f"    Created: {full_table}")
            except Exception as e:
                print(f"    ERROR: {e}")
                results[table] = False

    return results


# === EXECUTE ===
if __name__ == "__main__":
    print(f"Config: dataset={DATASET}, catalog={CATALOG}")

    if not IN_DATABRICKS:
        print("\nNOTICE: Not in Databricks. This script requires Unity Catalog.")
    else:
        # Create catalog and staging volume
        print("\nBootstrap: Creating catalog and staging volume...")
        try:
            spark.sql(f"CREATE CATALOG IF NOT EXISTS {CATALOG}")  # noqa: F821
            spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.staging")  # noqa: F821
            spark.sql(f"CREATE VOLUME IF NOT EXISTS {CATALOG}.staging.uploads")  # noqa: F821
            print(f"  Catalog '{CATALOG}' and staging volume ready")
        except Exception as e:
            print(f"  Bootstrap error: {e}")

        # Load datasets
        datasets = list(DATASET_CONFIGS.keys()) if DATASET == "all" else [DATASET]
        all_results = {ds: setup_dataset(ds, CATALOG) for ds in datasets}

        # Summary
        print(f"\n{'=' * 60}\nSUMMARY\n{'=' * 60}")
        total_ok, total_fail = 0, 0
        for ds, results in all_results.items():
            ok = sum(results.values())
            fail = len(results) - ok
            total_ok += ok
            total_fail += fail
            print(f"{ds}: {ok} OK, {fail} failed")

        print(f"\nTotal: {total_ok} tables loaded, {total_fail} failed")

        # Verify row counts
        print(f"\n{'=' * 60}\nVERIFICATION\n{'=' * 60}")
        for ds in datasets:
            for schema_name, tables in DATASET_CONFIGS[ds]["schemas"].items():
                for table in tables:
                    try:
                        count = spark.sql(f"SELECT COUNT(*) FROM {CATALOG}.{schema_name}.{table}").collect()[0][0]  # noqa: F821
                        print(f"  {schema_name}.{table}: {count:,} rows")
                    except Exception as e:
                        print(f"  {schema_name}.{table}: ERROR - {e}")
