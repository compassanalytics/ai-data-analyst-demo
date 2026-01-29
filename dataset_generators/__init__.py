"""
Dataset generators package for AI Data Analyst Workshop.
Provides clean (star schema) and dirty (super table) data generators
with configurable cleanliness levels.
"""

from .base import CleanlinessLevel
from .star_schema_generator import StarSchemaGenerator, generate_star_schema
from .super_table_generator import SuperTableGenerator, generate_super_table, save_super_table
from .unified_generator import (
    GeneratedDataset,
    generate_at_level,
    generate_dataset,
    generate_star_schema_clean,
    generate_super_table_dirty,
)

__all__ = [
    # Original generators
    "generate_star_schema",
    "StarSchemaGenerator",
    "generate_super_table",
    "save_super_table",
    "SuperTableGenerator",
    # Unified generator
    "generate_dataset",
    "generate_at_level",
    "generate_star_schema_clean",
    "generate_super_table_dirty",
    "GeneratedDataset",
    "CleanlinessLevel",
]
