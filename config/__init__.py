"""Configuration module for dataset schemas and settings."""

from config.dataset_schemas import (
    DATASET_CONFIGS,
    STAR_SCHEMA_DESCRIPTIONS,
    SUPER_TABLE_DESCRIPTIONS,
    VELOCITY_MOTORS_SCHEMAS,
    get_base_url,
    get_column_descriptions,
    get_table_list,
    list_datasets,
)

__all__ = [
    "DATASET_CONFIGS",
    "VELOCITY_MOTORS_SCHEMAS",
    "STAR_SCHEMA_DESCRIPTIONS",
    "SUPER_TABLE_DESCRIPTIONS",
    "get_column_descriptions",
    "get_table_list",
    "get_base_url",
    "list_datasets",
]
