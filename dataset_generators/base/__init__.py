"""
Base classes and utilities for dataset generators.
"""

from .utils import set_random_seed, CleanlinessLevel, scale_count
from .generator import BaseDataGenerator, GeneratorConfig
from .anti_patterns import (
    AntiPattern,
    AntiPatternRegistry,
    get_registry,
    # Naming patterns
    CrypticCodesPattern,
    InconsistentCasePattern,
    AbbreviationsPattern,
    AmbiguousNamesPattern,
    # Redundancy patterns
    DuplicateColumnsPattern,
    DuplicateIdsPattern,
    CalculatedStoredPattern,
    # Type patterns
    MixedBooleansPattern,
    InconsistentDatesPattern,
    NullVariationsPattern,
    # Structural patterns
    DenormalizationPattern,
    ConflictingValuesPattern,
    OrphanKeysPattern,
    # Metadata patterns
    NoDescriptionsPattern,
    UndocumentedCodesPattern,
    HiddenLogicPattern,
)
from .traps import (
    TrapColumn,
    TrapRegistry,
    get_trap_registry,
    # Individual trap classes
    TrapRevenue,
    TrapTotal,
    TrapDate,
    TrapStatus,
    TrapMargin,
    TrapCustomerCount,
    TrapDiscount,
)
from .test_queries import (
    TestQuery,
    TestQueryGenerator,
    get_query_generator,
)

__all__ = [
    # Generator classes
    'BaseDataGenerator',
    'GeneratorConfig',
    # Utilities
    'CleanlinessLevel',
    'set_random_seed',
    'scale_count',
    # Anti-pattern system
    'AntiPattern',
    'AntiPatternRegistry',
    'get_registry',
    # Naming patterns
    'CrypticCodesPattern',
    'InconsistentCasePattern',
    'AbbreviationsPattern',
    'AmbiguousNamesPattern',
    # Redundancy patterns
    'DuplicateColumnsPattern',
    'DuplicateIdsPattern',
    'CalculatedStoredPattern',
    # Type patterns
    'MixedBooleansPattern',
    'InconsistentDatesPattern',
    'NullVariationsPattern',
    # Structural patterns
    'DenormalizationPattern',
    'ConflictingValuesPattern',
    'OrphanKeysPattern',
    # Metadata patterns
    'NoDescriptionsPattern',
    'UndocumentedCodesPattern',
    'HiddenLogicPattern',
    # Trap system
    'TrapColumn',
    'TrapRegistry',
    'get_trap_registry',
    # Individual trap classes
    'TrapRevenue',
    'TrapTotal',
    'TrapDate',
    'TrapStatus',
    'TrapMargin',
    'TrapCustomerCount',
    'TrapDiscount',
    # Test query system
    'TestQuery',
    'TestQueryGenerator',
    'get_query_generator',
]
