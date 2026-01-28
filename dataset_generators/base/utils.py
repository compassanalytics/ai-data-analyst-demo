"""
Shared utilities for dataset generators.
"""

from __future__ import annotations

import random
from enum import IntEnum

import numpy as np


def set_random_seed(seed: int) -> None:
    """
    Set random seed for reproducibility across all random number generators.

    Args:
        seed: Integer seed value
    """
    random.seed(seed)
    np.random.seed(seed)


class CleanlinessLevel(IntEnum):
    """
    Cleanliness level for generated datasets.

    Higher values indicate cleaner data with fewer issues.
    Lower values introduce more anti-patterns, inconsistencies, and traps.
    """
    PRISTINE = 100      # Perfect star schema, no issues
    MOSTLY_CLEAN = 85   # Minor naming inconsistencies
    MODERATE = 70       # Some denormalization, mixed naming
    MESSY = 50          # Significant issues, partial denormalization
    CHAOTIC = 25        # Heavy anti-patterns, trap columns
    NIGHTMARE = 0       # Everything wrong, maximum confusion


def scale_count(base: int, scale: float) -> int:
    """
    Apply scale factor to a base count, ensuring minimum of 1.

    Args:
        base: Base count
        scale: Scale factor (e.g., 0.1 for 10%)

    Returns:
        Scaled count, minimum 1
    """
    return max(1, int(base * scale))
