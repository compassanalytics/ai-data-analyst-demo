"""
Dataset generators package for AI Data Analyst Workshop.
Provides clean (star schema) and dirty (super table) data generators
with configurable cleanliness levels.
"""

from .star_schema_generator import generate_star_schema, StarSchemaGenerator
from .super_table_generator import generate_super_table, save_super_table, SuperTableGenerator
from .unified_generator import (
    generate_dataset,
    generate_at_level,
    generate_star_schema_clean,
    generate_super_table_dirty,
    GeneratedDataset,
)
from .base import CleanlinessLevel

__all__ = [
    # Original generators
    'generate_star_schema',
    'StarSchemaGenerator',
    'generate_super_table',
    'save_super_table',
    'SuperTableGenerator',
    # Unified generator
    'generate_dataset',
    'generate_at_level',
    'generate_star_schema_clean',
    'generate_super_table_dirty',
    'GeneratedDataset',
    'CleanlinessLevel',
]
