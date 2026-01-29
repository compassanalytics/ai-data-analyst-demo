"""
Unified Dataset Generator with Cleanliness Slider.

This module provides a unified interface for generating datasets with varying
degrees of data quality, controlled by a "cleanliness slider" (0-100).

Architecture: Generate Clean -> Flatten -> Apply Anti-Patterns
- cleanliness=100: Pristine star schema, no issues
- cleanliness=50-99: Star schema with light naming/metadata patterns
- cleanliness=1-49: Super table with progressive anti-patterns and traps
- cleanliness=0: Nightmare super table with all anti-patterns and traps

Usage:
    from dataset_generators.unified_generator import generate_dataset, CleanlinessLevel

    # Generate dataset at specific cleanliness
    result, queries = generate_dataset(cleanliness=50, seed=42)

    # Generate at preset level
    result, queries = generate_at_level(CleanlinessLevel.MESSY)

    # Convenience functions
    tables = generate_star_schema_clean()  # cleanliness=100
    super_table = generate_super_table_dirty()  # cleanliness=0
"""

from __future__ import annotations

import json
import os
from typing import Any, Literal

import pandas as pd
from typing_extensions import TypedDict

from .base import (
    BaseDataGenerator,
    CleanlinessLevel,
    GeneratorConfig,
    TestQuery,
    get_query_generator,
    get_registry,
    get_trap_registry,
    set_random_seed,
)


class GeneratedDataset(TypedDict):
    """Output contract for the unified generator."""

    tables: dict[str, pd.DataFrame]
    """Dictionary mapping table names to DataFrames."""

    format: Literal["star", "super", "hybrid"]
    """Output format: star schema, super table, or hybrid."""

    cleanliness: int
    """Cleanliness level (0-100) used to generate this dataset."""

    active_patterns: list[str]
    """List of anti-pattern IDs that were applied."""

    active_traps: list[str]
    """List of trap column IDs that were applied."""

    metadata: dict[str, Any]
    """Additional metadata about the generation."""


class StarSchemaGenerator(BaseDataGenerator):
    """
    Generator for clean star schema datasets.

    Uses the base class dimension generation methods to produce a consistent
    star schema with properly modeled fact and dimension tables.
    """

    def __init__(self, config: GeneratorConfig) -> None:
        """
        Initialize the star schema generator.

        Args:
            config: Generator configuration settings
        """
        super().__init__(config)

    def generate(self) -> dict[str, pd.DataFrame]:
        """
        Generate complete star schema dataset.

        Returns:
            Dictionary mapping table names to DataFrames:
            - dim_date: Date dimension with fiscal calendar
            - dim_product: Product dimension with category hierarchy
            - dim_customer: Customer dimension with segments
            - dim_store: Store/distribution center dimension
            - dim_promotion: Promotion dimension
            - fact_sales: Sales fact table
        """
        # Generate dimensions
        dim_date = self._generate_dim_date()
        dim_product = self._generate_dim_product()
        dim_customer = self._generate_dim_customer()
        dim_store = self._generate_dim_store()
        dim_promotion = self._generate_dim_promotion()

        # Generate fact table
        fact_sales = self._generate_fact_sales(
            dim_date=dim_date,
            dim_product=dim_product,
            dim_customer=dim_customer,
            dim_store=dim_store,
            dim_promotion=dim_promotion,
        )

        return {
            "dim_date": dim_date,
            "dim_product": dim_product,
            "dim_customer": dim_customer,
            "dim_store": dim_store,
            "dim_promotion": dim_promotion,
            "fact_sales": fact_sales,
        }


def _flatten_to_super_table(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Flatten star schema tables into a single denormalized table.

    Performs left joins from fact_sales to all dimension tables,
    preserving all fact rows while denormalizing dimension attributes.

    Args:
        tables: Dictionary of star schema tables (must include fact_sales
               and dimension tables)

    Returns:
        Single denormalized DataFrame with all attributes flattened
    """
    # Start with the fact table
    if "fact_sales" not in tables:
        raise ValueError("tables must include 'fact_sales'")

    result = tables["fact_sales"].copy()

    # Join dimension tables - use left joins to preserve all fact rows
    join_specs = [
        ("dim_date", "date_key"),
        ("dim_product", "product_key"),
        ("dim_customer", "customer_key"),
        ("dim_store", "store_key"),
        ("dim_promotion", "promotion_key"),
    ]

    for dim_name, key_col in join_specs:
        if dim_name in tables and key_col in result.columns:
            dim_df = tables[dim_name]

            # Avoid column name collisions by using suffixes
            result = result.merge(
                dim_df,
                on=key_col,
                how="left",
                suffixes=("", f"_{dim_name}"),
            )

    return result


def _apply_light_patterns(
    tables: dict[str, pd.DataFrame],
    cleanliness: int,
) -> dict[str, pd.DataFrame]:
    """
    Apply light anti-patterns (naming, metadata) to star schema tables.

    Only applies patterns that don't require structural changes:
    - Cryptic codes
    - Inconsistent case
    - Abbreviations
    - Ambiguous names
    - Hidden logic

    Does NOT apply:
    - Denormalization (already separate tables)
    - Duplicate columns
    - Conflicting values

    Args:
        tables: Dictionary of star schema tables
        cleanliness: Cleanliness level (50-99)

    Returns:
        Modified dictionary of star schema tables with light patterns applied
    """
    registry = get_registry()
    result = {}

    # Light patterns that can apply to star schema without breaking structure
    light_pattern_ids = [
        "naming_cryptic_codes",
        "naming_inconsistent_case",
        "naming_abbreviations",
        "naming_ambiguous",
        "metadata_undocumented_codes",
        "metadata_hidden_logic",
    ]

    # Calculate intensity based on cleanliness
    # At 99, intensity is very low; at 50, intensity is moderate
    base_intensity = (100 - cleanliness) / 50  # 0.02 at 99, 1.0 at 50

    for table_name, df in tables.items():
        modified_df = df.copy()

        # Apply applicable light patterns
        active_patterns = registry.get_active_patterns(cleanliness)
        for pattern_id in active_patterns:
            if pattern_id not in light_pattern_ids:
                continue

            pattern = registry.get(pattern_id)
            intensity = registry.calculate_intensity(cleanliness, pattern.severity)

            # Scale intensity down for hybrid mode
            intensity = min(intensity, base_intensity)

            try:
                modified_df = pattern.apply(modified_df, intensity)
            except Exception as e:
                print(f"Warning: Pattern '{pattern_id}' failed on {table_name}: {e}")

        result[table_name] = modified_df

    return result


def generate_dataset(
    cleanliness: int = 100,
    seed: int = 42,
    output_dir: str | None = None,
    include_test_queries: bool = False,
    config: GeneratorConfig | None = None,
) -> tuple[GeneratedDataset, list[TestQuery] | None]:
    """
    Generate dataset with specified cleanliness level (0-100).

    Architecture: Generate Clean -> Flatten -> Apply Anti-Patterns

    1. Always starts by generating a clean star schema
    2. Based on cleanliness level:
       - 100: Return pristine star schema
       - 50-99: Apply light patterns to star schema (hybrid)
       - 1-49: Flatten to super table, apply progressive anti-patterns
       - 0: Full nightmare mode with all anti-patterns and traps

    Args:
        cleanliness: Cleanliness level (0=nightmare, 100=pristine star schema)
        seed: Random seed for reproducibility
        output_dir: Optional directory to save parquet files
        include_test_queries: Whether to generate matching test queries
        config: Optional generator configuration (overrides seed if provided)

    Returns:
        Tuple of:
        - GeneratedDataset TypedDict with tables, format, cleanliness,
          active_patterns, active_traps, and metadata
        - Optional list of TestQuery instances (if include_test_queries=True)

    Raises:
        ValueError: If cleanliness is not in range 0-100

    Example:
        >>> result, queries = generate_dataset(cleanliness=50, seed=42)
        >>> print(result['format'])  # 'super'
        >>> print(len(result['active_patterns']))  # patterns active at 50%
    """
    # Validate cleanliness
    if not 0 <= cleanliness <= 100:
        raise ValueError(f"cleanliness must be 0-100, got {cleanliness}")

    # Create or use provided config
    if config is None:
        config = GeneratorConfig(seed=seed)
    else:
        # Update seed if using provided config
        config.seed = seed

    # Type narrowing assertion for Pyright
    assert config is not None

    # Set random seed for reproducibility
    set_random_seed(seed)

    # Get registries
    registry = get_registry()
    trap_registry = get_trap_registry()

    # Step 1: Always generate clean star schema first
    star_generator = StarSchemaGenerator(config)
    clean_tables = star_generator.generate()

    # Step 2: Determine output based on cleanliness
    if cleanliness >= 100:
        # Pure star schema - return as-is
        output_format: Literal["star", "super", "hybrid"] = "star"
        tables = clean_tables
        active_patterns: list[str] = []
        active_traps: list[str] = []

    elif cleanliness <= 0:
        # Full super table - delegate to existing super_table_generator for schema parity
        output_format = "super"

        # Import existing generator to maintain schema compatibility
        from .super_table_generator import generate_super_table

        super_table = generate_super_table(n_rows=config.n_transactions)
        tables = {"super_table": super_table}

        # All patterns and traps are active at cleanliness=0
        active_patterns = registry.get_active_patterns(0)
        active_traps = [t.id for t in trap_registry.get_active_traps(0)]

    elif cleanliness <= 50:
        # Flatten to super table structure, then apply patterns and traps
        # MESSY (50) and below get full super table treatment
        output_format = "super"

        # Flatten star schema to single table
        flattened = _flatten_to_super_table(clean_tables)

        # Apply anti-patterns based on cleanliness
        result_df = registry.apply_by_cleanliness(flattened, cleanliness)

        # Apply trap columns based on cleanliness
        result_df = trap_registry.apply_traps(result_df, cleanliness)

        tables = {"super_table": result_df}
        active_patterns = registry.get_active_patterns(cleanliness)
        active_traps = [t.id for t in trap_registry.get_active_traps(cleanliness)]

    else:
        # Hybrid mode: Keep star schema structure, apply light patterns only
        output_format = "hybrid"

        # Apply only naming and metadata patterns
        tables = _apply_light_patterns(clean_tables, cleanliness)

        active_patterns = [
            p for p in registry.get_active_patterns(cleanliness) if registry.get(p).category in ["naming", "metadata"]
        ]
        active_traps = []  # No traps in hybrid mode

    # Build result
    result: GeneratedDataset = {
        "tables": tables,
        "format": output_format,
        "cleanliness": cleanliness,
        "active_patterns": active_patterns,
        "active_traps": active_traps,
        "metadata": {
            "seed": seed,
            "n_products": config.n_products,
            "n_customers": config.n_customers,
            "n_stores": config.n_stores,
            "n_promotions": config.n_promotions,
            "n_transactions": config.n_transactions,
            "start_date": config.start_date,
            "end_date": config.end_date,
            "table_counts": {name: len(df) for name, df in tables.items()},
            "column_counts": {name: len(df.columns) for name, df in tables.items()},
        },
    }

    # Save to parquet if output_dir provided
    if output_dir:
        _save_datasets(result, output_dir)

    # Generate test queries if requested
    test_queries: list[TestQuery] | None = None
    if include_test_queries:
        query_generator = get_query_generator()
        test_queries = query_generator.get_for_cleanliness(cleanliness, active_patterns)

    return result, test_queries


def generate_at_level(
    level: CleanlinessLevel,
    seed: int = 42,
    **kwargs: Any,
) -> tuple[GeneratedDataset, list[TestQuery] | None]:
    """
    Generate dataset at a preset cleanliness level.

    Convenience wrapper around generate_dataset that accepts CleanlinessLevel enum.

    Args:
        level: Preset cleanliness level (PRISTINE, MOSTLY_CLEAN, MODERATE,
               MESSY, CHAOTIC, or NIGHTMARE)
        seed: Random seed for reproducibility
        **kwargs: Additional arguments passed to generate_dataset

    Returns:
        Tuple of (GeneratedDataset dict, optional test queries list)

    Example:
        >>> result, queries = generate_at_level(CleanlinessLevel.MESSY)
        >>> print(result['cleanliness'])  # 50
        >>> print(result['format'])  # 'super'
    """
    return generate_dataset(cleanliness=level.value, seed=seed, **kwargs)


def generate_star_schema_clean(
    seed: int = 42,
    **kwargs: Any,
) -> dict[str, pd.DataFrame]:
    """
    Convenience: Generate pristine star schema.

    Shorthand for generate_dataset(cleanliness=100)[0]['tables'].

    Args:
        seed: Random seed for reproducibility
        **kwargs: Additional arguments passed to generate_dataset

    Returns:
        Dictionary mapping table names to DataFrames:
        - dim_date, dim_product, dim_customer, dim_store, dim_promotion
        - fact_sales

    Example:
        >>> tables = generate_star_schema_clean()
        >>> print(tables.keys())
        dict_keys(['dim_date', 'dim_product', 'dim_customer', 'dim_store',
                   'dim_promotion', 'fact_sales'])
    """
    result, _ = generate_dataset(cleanliness=100, seed=seed, **kwargs)
    return result["tables"]


def generate_super_table_dirty(
    seed: int = 42,
    **kwargs: Any,
) -> pd.DataFrame:
    """
    Convenience: Generate nightmare super table.

    Shorthand for generate_dataset(cleanliness=0)[0]['tables']['super_table'].
    Uses the original super_table_generator for schema compatibility.

    Args:
        seed: Random seed for reproducibility
        **kwargs: Additional arguments passed to generate_dataset

    Returns:
        Single DataFrame with all anti-patterns and traps applied

    Example:
        >>> df = generate_super_table_dirty()
        >>> print(f"{len(df.columns)} columns of chaos")
    """
    result, _ = generate_dataset(cleanliness=0, seed=seed, **kwargs)
    return result["tables"]["super_table"]


def _save_datasets(result: GeneratedDataset, output_dir: str) -> None:
    """
    Save generated datasets to parquet files.

    Creates the output directory if it doesn't exist, saves each table
    as a parquet file, and writes a metadata.json with generation info.

    Args:
        result: GeneratedDataset dict from generate_dataset
        output_dir: Directory to save files to
    """
    os.makedirs(output_dir, exist_ok=True)

    # Save each table as parquet
    for name, df in result["tables"].items():
        path = os.path.join(output_dir, f"{name}.parquet")
        df.to_parquet(path, index=False)
        print(f"  Saved {path} ({len(df):,} rows, {len(df.columns)} columns)")

    # Save metadata
    metadata_path = os.path.join(output_dir, "metadata.json")
    metadata = {
        "cleanliness": result["cleanliness"],
        "format": result["format"],
        "active_patterns": result["active_patterns"],
        "active_traps": result["active_traps"],
        "generation_metadata": result["metadata"],
    }

    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2, default=str)

    print(f"  Saved {metadata_path}")


def describe_cleanliness_level(cleanliness: int) -> str:
    """
    Describe what happens at a given cleanliness level.

    Args:
        cleanliness: Cleanliness level (0-100)

    Returns:
        Human-readable description of the cleanliness level
    """
    registry = get_registry()
    trap_registry = get_trap_registry()

    if cleanliness >= 100:
        return (
            "PRISTINE (100): Perfect star schema with no anti-patterns.\n"
            "- Separate fact and dimension tables\n"
            "- Clear, consistent naming\n"
            "- Proper data types\n"
            "- Well-documented columns\n"
            "- Ideal for AI/BI tools like Genie"
        )

    active_patterns = registry.get_active_patterns(cleanliness)
    active_traps = trap_registry.get_active_traps(cleanliness)

    if cleanliness <= 0:
        return (
            "NIGHTMARE (0): Everything wrong, maximum confusion.\n"
            "- Single super table with 100+ columns\n"
            f"- {len(active_patterns)} anti-patterns active\n"
            f"- {len(active_traps)} trap columns added\n"
            "- Cryptic codes, duplicate columns, mixed types\n"
            "- Guaranteed to confuse AI/BI tools"
        )

    if cleanliness < 50:
        return (
            f"CHAOTIC/MESSY ({cleanliness}): Heavy anti-patterns.\n"
            "- Flattened to super table\n"
            f"- {len(active_patterns)} anti-patterns active\n"
            f"- {len(active_traps)} trap columns added\n"
            "- Significant issues, likely to cause AI failures"
        )

    return (
        f"HYBRID ({cleanliness}): Light patterns on star schema.\n"
        "- Star schema structure preserved\n"
        f"- {len(active_patterns)} light patterns active (naming/metadata only)\n"
        "- No trap columns\n"
        "- May cause some AI confusion but mostly functional"
    )
