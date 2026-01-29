"""
Base classes and utilities for dataset generators.
"""

from .anti_patterns import (
    AbbreviationsPattern,
    AmbiguousNamesPattern,
    AntiPattern,
    AntiPatternRegistry,
    CalculatedStoredPattern,
    ConflictingValuesPattern,
    # Naming patterns
    CrypticCodesPattern,
    # Structural patterns
    DenormalizationPattern,
    # Redundancy patterns
    DuplicateColumnsPattern,
    DuplicateIdsPattern,
    HiddenLogicPattern,
    InconsistentCasePattern,
    InconsistentDatesPattern,
    # Type patterns
    MixedBooleansPattern,
    # Metadata patterns
    NoDescriptionsPattern,
    NullVariationsPattern,
    OrphanKeysPattern,
    UndocumentedCodesPattern,
    get_registry,
)
from .generator import BaseDataGenerator, GeneratorConfig
from .test_queries import (
    TestQuery,
    TestQueryGenerator,
    get_query_generator,
)
from .traps import (
    TrapColumn,
    TrapCustomerCount,
    TrapDate,
    TrapDiscount,
    TrapMargin,
    TrapRegistry,
    # Individual trap classes
    TrapRevenue,
    TrapStatus,
    TrapTotal,
    get_trap_registry,
)
from .utils import CleanlinessLevel, scale_count, set_random_seed

__all__ = [
    # Generator classes
    "BaseDataGenerator",
    "GeneratorConfig",
    # Utilities
    "CleanlinessLevel",
    "set_random_seed",
    "scale_count",
    # Anti-pattern system
    "AntiPattern",
    "AntiPatternRegistry",
    "get_registry",
    # Naming patterns
    "CrypticCodesPattern",
    "InconsistentCasePattern",
    "AbbreviationsPattern",
    "AmbiguousNamesPattern",
    # Redundancy patterns
    "DuplicateColumnsPattern",
    "DuplicateIdsPattern",
    "CalculatedStoredPattern",
    # Type patterns
    "MixedBooleansPattern",
    "InconsistentDatesPattern",
    "NullVariationsPattern",
    # Structural patterns
    "DenormalizationPattern",
    "ConflictingValuesPattern",
    "OrphanKeysPattern",
    # Metadata patterns
    "NoDescriptionsPattern",
    "UndocumentedCodesPattern",
    "HiddenLogicPattern",
    # Trap system
    "TrapColumn",
    "TrapRegistry",
    "get_trap_registry",
    # Individual trap classes
    "TrapRevenue",
    "TrapTotal",
    "TrapDate",
    "TrapStatus",
    "TrapMargin",
    "TrapCustomerCount",
    "TrapDiscount",
    # Test query system
    "TestQuery",
    "TestQueryGenerator",
    "get_query_generator",
]
