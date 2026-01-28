"""
AI Trap Column System for Dataset Generators.

This module provides intentionally misleading columns designed to cause
AI/BI tools like Databricks Genie to give confident but WRONG answers.
These are educational tools to demonstrate the importance of data quality
and proper documentation.

Trap columns are different from anti-patterns:
- Anti-patterns make data hard to interpret (confusion)
- Trap columns are actively misleading (wrong answers)

Each trap is documented with:
- What it appears to be
- What it actually contains
- Why it causes AI to fail
- How to correctly interpret it

Trap columns use the 'trap_' prefix to avoid collisions with existing columns.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


@dataclass
class TrapColumn(ABC):
    """
    Base class for AI trap columns.

    Each trap column represents a misleading column that will cause
    AI/BI tools to give confident but incorrect answers.
    """

    id: str
    column_name: str
    apparent_meaning: str
    actual_content: str
    why_fails: str
    correct_interpretation: str
    apply_at_cleanliness: int  # Only apply below this cleanliness level

    @abstractmethod
    def generate(self, df: pd.DataFrame) -> pd.Series:
        """
        Generate the trap column data from source DataFrame.

        Args:
            df: Source DataFrame containing columns to derive trap from

        Returns:
            pd.Series containing the trap column data

        Raises:
            NotImplementedError: Subclasses must implement this method
        """
        raise NotImplementedError

    def can_apply(self, df: pd.DataFrame) -> bool:
        """
        Check if this trap can be applied to the given DataFrame.

        Override in subclasses if specific columns are required.

        Args:
            df: DataFrame to check

        Returns:
            True if trap can be applied, False otherwise
        """
        return True


# =============================================================================
# TRAP 1: REVENUE TRAP
# =============================================================================


@dataclass
class TrapRevenue(TrapColumn):
    """
    Trap column that looks like revenue but contains quantity.

    AI will SUM this as dollars, getting totals like '$45,000' when
    the actual revenue is '$2.3M'.
    """

    id: str = "trap_revenue"
    column_name: str = "trap_revenue"
    apparent_meaning: str = "Total revenue amount in dollars"
    actual_content: str = "Quantity sold (integer units)"
    why_fails: str = (
        "AI will SUM this as dollars, getting totals like '$45,000' when it should "
        "be '$2.3M'. The column name 'revenue' strongly implies a dollar amount, "
        "but it actually contains unit quantities. This causes order-of-magnitude errors."
    )
    correct_interpretation: str = (
        "This column contains the number of units sold, not revenue. "
        "To calculate actual revenue, multiply quantity by unit price."
    )
    apply_at_cleanliness: int = 50

    # Source columns to look for (in priority order)
    source_columns: List[str] = field(default_factory=lambda: [
        'quantity_sold', 'qty', 'quantity', 'QTY_SOLD', 'units_sold', 'unit_sold'
    ])

    def can_apply(self, df: pd.DataFrame) -> bool:
        """Check if any source quantity column exists."""
        return any(col in df.columns for col in self.source_columns)

    def generate(self, df: pd.DataFrame) -> pd.Series:
        """Copy quantity column as 'revenue'."""
        for col in self.source_columns:
            if col in df.columns:
                return df[col].copy()

        # Fallback: generate random quantities
        return pd.Series(
            np.random.randint(1, 50, size=len(df)),
            index=df.index,
            name=self.column_name
        )


# =============================================================================
# TRAP 2: TOTAL TRAP
# =============================================================================


@dataclass
class TrapTotal(TrapColumn):
    """
    Trap column that looks like order total but is missing tax/fees.

    AI reports totals that are systematically 15-20% lower than actual.
    """

    id: str = "trap_total"
    column_name: str = "trap_total"
    apparent_meaning: str = "Order total amount"
    actual_content: str = "Partial sum - only includes base price, excludes tax and fees"
    why_fails: str = (
        "AI reports totals that are systematically 15-20% lower than actual. "
        "When asked 'what is our total revenue?', the AI will sum this column "
        "and report a number that looks reasonable but is consistently underestimated. "
        "Users may not notice the discrepancy until comparing to finance reports."
    )
    correct_interpretation: str = (
        "This column is the pre-tax, pre-fee amount. To get the true total, "
        "you need to add tax (typically 8-10%) and any applicable fees. "
        "Use the actual gross_amount or net_amount columns instead."
    )
    apply_at_cleanliness: int = 40

    # Source columns to look for (in priority order)
    source_columns: List[str] = field(default_factory=lambda: [
        'gross_amount', 'gross_amt', 'gross_sales', 'GROSS', 'gross_revenue'
    ])
    multiplier: float = 0.85  # Simulates missing 15% tax/fees

    def can_apply(self, df: pd.DataFrame) -> bool:
        """Check if any source amount column exists."""
        return any(col in df.columns for col in self.source_columns)

    def generate(self, df: pd.DataFrame) -> pd.Series:
        """Generate partial total (missing tax/fees)."""
        for col in self.source_columns:
            if col in df.columns:
                return (df[col] * self.multiplier).round(2)

        # Fallback: if we have quantity and price, calculate
        qty_cols = ['quantity_sold', 'qty', 'quantity']
        price_cols = ['unit_price', 'px', 'price']

        for qty_col in qty_cols:
            for price_col in price_cols:
                if qty_col in df.columns and price_col in df.columns:
                    gross = df[qty_col] * df[price_col]
                    return (gross * self.multiplier).round(2)

        # Last resort fallback
        return pd.Series(
            np.random.uniform(10, 500, size=len(df)).round(2),
            index=df.index,
            name=self.column_name
        )


# =============================================================================
# TRAP 3: DATE TRAP
# =============================================================================


@dataclass
class TrapDate(TrapColumn):
    """
    Trap column that looks like a date but is Unix epoch milliseconds.

    AI interprets large integers as numbers, not dates. A date like
    Jan 1, 2024 becomes 1704067200000.
    """

    id: str = "trap_date"
    column_name: str = "trap_date"
    apparent_meaning: str = "Transaction date"
    actual_content: str = "Unix epoch milliseconds stored as integer"
    why_fails: str = (
        "AI interprets 1704067200000 as a large number, not Jan 1, 2024. "
        "When asked 'show me sales from January', the AI tries to filter "
        "on a numeric column with no understanding that it represents dates. "
        "Queries like 'last month' or 'Q4 2024' become impossible."
    )
    correct_interpretation: str = (
        "This column contains Unix epoch milliseconds (ms since 1970-01-01). "
        "To convert: divide by 1000 to get seconds, then convert to datetime. "
        "Example: 1704067200000 / 1000 = 1704067200 = 2024-01-01 00:00:00 UTC."
    )
    apply_at_cleanliness: int = 30

    # Source columns to look for (in priority order)
    source_columns: List[str] = field(default_factory=lambda: [
        'full_date', 'date_key', 'sale_date', 'order_date', 'trans_dt',
        'SaleDate', 'order_date_iso'
    ])

    def can_apply(self, df: pd.DataFrame) -> bool:
        """Check if any source date column exists."""
        return any(col in df.columns for col in self.source_columns)

    def generate(self, df: pd.DataFrame) -> pd.Series:
        """Convert date to Unix epoch milliseconds."""
        for col in self.source_columns:
            if col in df.columns:
                try:
                    # Try to convert to datetime first
                    dates = pd.to_datetime(df[col], errors='coerce')
                    # Convert to Unix epoch milliseconds
                    epoch_ms = (dates.astype('int64') // 10**6).astype('int64')
                    return epoch_ms
                except (ValueError, TypeError):
                    continue

        # Fallback: generate random dates as epoch ms
        # Random dates in 2023-2024 range
        start_epoch = int(pd.Timestamp('2023-01-01').timestamp() * 1000)
        end_epoch = int(pd.Timestamp('2024-12-31').timestamp() * 1000)
        return pd.Series(
            np.random.randint(start_epoch, end_epoch, size=len(df)),
            index=df.index,
            name=self.column_name
        )


# =============================================================================
# TRAP 4: STATUS TRAP
# =============================================================================


@dataclass
class TrapStatus(TrapColumn):
    """
    Trap column with inverted status logic.

    AI filters for status=1 to get active records but gets inactive ones instead.
    """

    id: str = "trap_status"
    column_name: str = "trap_status"
    apparent_meaning: str = "Active status flag (1=active, 0=inactive)"
    actual_content: str = "Inverted logic: 1=INACTIVE, 0=ACTIVE"
    why_fails: str = (
        "AI filters for status=1 to get active records but gets inactive ones. "
        "The universally expected convention is 1=active/true, 0=inactive/false. "
        "By inverting this, every query about 'active customers' or 'current products' "
        "returns exactly the wrong set of records."
    )
    correct_interpretation: str = (
        "In this column, the logic is inverted: 0 means ACTIVE, 1 means INACTIVE. "
        "To filter for active records, use WHERE trap_status = 0. "
        "This is the opposite of standard boolean conventions."
    )
    apply_at_cleanliness: int = 40

    # Source columns to look for (in priority order)
    source_columns: List[str] = field(default_factory=lambda: [
        'is_active', 'active', 'is_current', 'status'
    ])

    def can_apply(self, df: pd.DataFrame) -> bool:
        """Check if any source boolean/status column exists."""
        return any(col in df.columns for col in self.source_columns)

    def generate(self, df: pd.DataFrame) -> pd.Series:
        """Invert boolean status values."""
        for col in self.source_columns:
            if col in df.columns:
                # Try to convert to boolean and invert
                try:
                    # Handle various boolean representations
                    bool_map = {
                        True: 0, False: 1,
                        1: 0, 0: 1,
                        '1': 0, '0': 1,
                        'Y': 0, 'N': 1,
                        'Yes': 0, 'No': 1,
                        'True': 0, 'False': 1,
                        'true': 0, 'false': 1,
                        'ACTIVE': 0, 'INACTIVE': 1,
                        'Active': 0, 'Inactive': 1,
                        'A': 0, 'I': 1,
                    }
                    return df[col].map(lambda x: bool_map.get(x, 1 if x else 0))
                except (ValueError, TypeError):
                    continue

        # Fallback: random inverted status
        return pd.Series(
            np.random.choice([0, 1], size=len(df), p=[0.8, 0.2]),  # 80% "active" (value=0)
            index=df.index,
            name=self.column_name
        )


# =============================================================================
# TRAP 5: MARGIN TRAP
# =============================================================================


@dataclass
class TrapMargin(TrapColumn):
    """
    Trap column that shows markup instead of margin.

    25% markup != 25% margin. AI reports inflated margins.
    """

    id: str = "trap_margin"
    column_name: str = "trap_margin"
    apparent_meaning: str = "Profit margin percentage"
    actual_content: str = "Markup percentage (different formula: profit/cost vs profit/revenue)"
    why_fails: str = (
        "25% markup does not equal 25% margin. Markup = profit/cost, while "
        "margin = profit/revenue. A 25% markup gives ~20% margin. AI reports "
        "inflated margins (e.g., 'our average margin is 35%') when actual "
        "margins are lower (~26%). This can mislead pricing decisions."
    )
    correct_interpretation: str = (
        "This column contains MARKUP percentage, not margin percentage. "
        "Markup = (price - cost) / cost * 100. "
        "Margin = (price - cost) / price * 100. "
        "To convert: margin = markup / (1 + markup/100) * 100."
    )
    apply_at_cleanliness: int = 45

    def can_apply(self, df: pd.DataFrame) -> bool:
        """Check if we have the columns needed to calculate markup."""
        # Need either net_amount + cost_amount or price + cost
        has_amounts = (
            ('net_amount' in df.columns or 'net_amt' in df.columns) and
            ('cost_amount' in df.columns or 'cost_amt' in df.columns)
        )
        has_prices = (
            ('unit_price' in df.columns or 'px' in df.columns) and
            ('unit_cost' in df.columns)
        )
        return has_amounts or has_prices

    def generate(self, df: pd.DataFrame) -> pd.Series:
        """Calculate markup percentage (not margin)."""
        # Try to find net and cost amounts
        net_col = None
        cost_col = None

        for col in ['net_amount', 'net_amt', 'NET', 'net_sales']:
            if col in df.columns:
                net_col = col
                break

        for col in ['cost_amount', 'cost_amt', 'COGS', 'total_cost']:
            if col in df.columns:
                cost_col = col
                break

        if net_col and cost_col:
            # Calculate markup: profit / cost * 100
            profit = df[net_col] - df[cost_col]
            # Avoid division by zero
            cost_safe = df[cost_col].replace(0, np.nan)
            markup = (profit / cost_safe * 100).round(2)
            return markup.fillna(0)

        # Fallback: use unit prices if available
        price_col = 'unit_price' if 'unit_price' in df.columns else ('px' if 'px' in df.columns else None)
        ucost_col = 'unit_cost' if 'unit_cost' in df.columns else None

        if price_col and ucost_col:
            profit = df[price_col] - df[ucost_col]
            cost_safe = df[ucost_col].replace(0, np.nan)
            markup = (profit / cost_safe * 100).round(2)
            return markup.fillna(0)

        # Last resort fallback: random markup values
        return pd.Series(
            np.random.uniform(15, 45, size=len(df)).round(2),
            index=df.index,
            name=self.column_name
        )


# =============================================================================
# TRAP 6: CUSTOMER COUNT TRAP
# =============================================================================


@dataclass
class TrapCustomerCount(TrapColumn):
    """
    Trap column that looks like customer count but is transaction count.

    AI reports '50,000 customers' when there are only 500 unique customers
    with 100 orders each.
    """

    id: str = "trap_customer_count"
    column_name: str = "trap_customer_count"
    apparent_meaning: str = "Number of unique customers"
    actual_content: str = "Number of orders (transactions)"
    why_fails: str = (
        "AI reports '50,000 customers' when there are only 500 unique customers "
        "with 100 orders each. The column name suggests unique customer counts, "
        "but it's actually a transaction counter. This leads to massive "
        "overestimation of customer base and flawed market sizing."
    )
    correct_interpretation: str = (
        "This column is a row counter (transaction ID), not customer count. "
        "To get unique customers, use COUNT(DISTINCT customer_key). "
        "Never SUM or COUNT this column directly for customer metrics."
    )
    apply_at_cleanliness: int = 50

    # Source columns to look for (in priority order) - primary keys / counters
    source_columns: List[str] = field(default_factory=lambda: [
        'sale_key', 'txn_id', 'transaction_id', 'sale_id'
    ])

    def can_apply(self, df: pd.DataFrame) -> bool:
        """Check if any source key/ID column exists."""
        return any(col in df.columns for col in self.source_columns) or len(df) > 0

    def generate(self, df: pd.DataFrame) -> pd.Series:
        """Generate transaction counter as 'customer count'."""
        for col in self.source_columns:
            if col in df.columns:
                return df[col].copy()

        # Fallback: generate sequential counter
        return pd.Series(
            range(1, len(df) + 1),
            index=df.index,
            name=self.column_name
        )


# =============================================================================
# TRAP 7: DISCOUNT TRAP
# =============================================================================


@dataclass
class TrapDiscount(TrapColumn):
    """
    Trap column that looks like discount percentage but is dollar amount.

    AI reports 'average 15% discount' when it's actually $15 average discount.
    """

    id: str = "trap_discount"
    column_name: str = "trap_discount"
    apparent_meaning: str = "Discount percentage applied"
    actual_content: str = "Discount amount in dollars (not percentage)"
    why_fails: str = (
        "AI reports 'average 15% discount' when it's actually $15 average discount. "
        "For a $100 order with $15 discount, the AI thinks it's a 15% discount "
        "when it could be anything (e.g., $15 off a $500 order = 3%). "
        "This causes incorrect discount analysis and promotional ROI calculations."
    )
    correct_interpretation: str = (
        "This column contains the discount AMOUNT in dollars, not a percentage. "
        "To calculate discount percentage: (discount_amount / gross_amount) * 100. "
        "Never report this value directly as a percentage."
    )
    apply_at_cleanliness: int = 45

    # Source columns to look for (in priority order)
    source_columns: List[str] = field(default_factory=lambda: [
        'discount_amount', 'disc_amt', 'DISC_$', 'disc_$'
    ])

    def can_apply(self, df: pd.DataFrame) -> bool:
        """Check if any source discount amount column exists."""
        return any(col in df.columns for col in self.source_columns)

    def generate(self, df: pd.DataFrame) -> pd.Series:
        """Copy discount dollar amount as 'discount' (misleading as percentage)."""
        for col in self.source_columns:
            if col in df.columns:
                return df[col].copy()

        # Fallback: generate random discount amounts
        return pd.Series(
            np.random.choice([0, 0, 0, 5, 10, 15, 20, 25], size=len(df)).astype(float),
            index=df.index,
            name=self.column_name
        )


# =============================================================================
# TRAP REGISTRY
# =============================================================================


class TrapRegistry:
    """
    Registry of all available AI trap columns.

    Provides methods to retrieve traps by ID, filter by cleanliness level,
    and apply traps to DataFrames.
    """

    def __init__(self) -> None:
        """Initialize the registry with all built-in traps."""
        self._traps: Dict[str, TrapColumn] = {}
        self._register_all_traps()

    def _register_all_traps(self) -> None:
        """Register all built-in trap columns."""
        traps = [
            TrapRevenue(),
            TrapTotal(),
            TrapDate(),
            TrapStatus(),
            TrapMargin(),
            TrapCustomerCount(),
            TrapDiscount(),
        ]

        for trap in traps:
            self._traps[trap.id] = trap

    def register(self, trap: TrapColumn) -> None:
        """
        Register a custom trap column.

        Args:
            trap: TrapColumn instance to register
        """
        self._traps[trap.id] = trap

    def get(self, trap_id: str) -> TrapColumn:
        """
        Get trap by ID.

        Args:
            trap_id: Unique trap identifier

        Returns:
            TrapColumn instance

        Raises:
            KeyError: If trap ID not found
        """
        if trap_id not in self._traps:
            raise KeyError(
                f"Trap '{trap_id}' not found. Available: {list(self._traps.keys())}"
            )
        return self._traps[trap_id]

    def get_all(self) -> List[TrapColumn]:
        """
        Get all registered traps.

        Returns:
            List of all TrapColumn instances
        """
        return list(self._traps.values())

    def get_active_traps(self, cleanliness: int) -> List[TrapColumn]:
        """
        Get traps that should be active at given cleanliness level.

        Traps are applied when cleanliness is below their apply_at_cleanliness
        threshold. Lower cleanliness = more traps active.

        Args:
            cleanliness: Cleanliness level (0-100)

        Returns:
            List of TrapColumn instances that should be active
        """
        return [
            trap for trap in self._traps.values()
            if cleanliness < trap.apply_at_cleanliness
        ]

    def apply_traps(
        self,
        df: pd.DataFrame,
        cleanliness: int,
        include_traps: Optional[List[str]] = None,
        exclude_traps: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Add trap columns to DataFrame based on cleanliness level.

        Args:
            df: Input DataFrame
            cleanliness: Cleanliness level (0-100). Lower = more traps applied.
            include_traps: Optional list of trap IDs to include (overrides cleanliness-based selection)
            exclude_traps: Optional list of trap IDs to exclude

        Returns:
            DataFrame with trap columns added
        """
        df = df.copy()
        exclude_traps = exclude_traps or []

        # Determine which traps to apply
        if include_traps is not None:
            # Explicit list provided - use those
            traps_to_apply = [
                self._traps[trap_id] for trap_id in include_traps
                if trap_id in self._traps and trap_id not in exclude_traps
            ]
        else:
            # Use cleanliness-based selection
            traps_to_apply = [
                trap for trap in self.get_active_traps(cleanliness)
                if trap.id not in exclude_traps
            ]

        # Apply each trap
        for trap in traps_to_apply:
            if not trap.can_apply(df):
                continue

            try:
                trap_data = trap.generate(df)
                df[trap.column_name] = trap_data
            except Exception as e:
                # Log but don't fail - traps should be resilient
                print(f"Warning: Trap '{trap.id}' failed to apply: {e}")

        return df

    def describe_traps(self, include_inactive: bool = False, cleanliness: int = 100) -> str:
        """
        Generate documentation of all traps for workshop reference.

        Args:
            include_inactive: If True, show all traps regardless of cleanliness
            cleanliness: Cleanliness level to determine which traps are "active"

        Returns:
            Formatted string describing all traps
        """
        lines = [
            "=" * 80,
            "AI TRAP COLUMNS - EDUCATIONAL REFERENCE",
            "=" * 80,
            "",
            "These columns are intentionally misleading to demonstrate how AI/BI tools",
            "can give confident but WRONG answers when data quality is poor.",
            "",
            "IMPORTANT: In production, these traps would represent real data quality",
            "issues that exist in enterprise data warehouses.",
            "",
            "-" * 80,
        ]

        traps = self.get_all() if include_inactive else self.get_active_traps(cleanliness)

        for trap in traps:
            lines.extend([
                "",
                f"TRAP: {trap.column_name.upper()}",
                f"ID: {trap.id}",
                f"Activates below cleanliness: {trap.apply_at_cleanliness}",
                "",
                f"  What it APPEARS to be:",
                f"    {trap.apparent_meaning}",
                "",
                f"  What it ACTUALLY contains:",
                f"    {trap.actual_content}",
                "",
                f"  Why AI fails:",
                f"    {trap.why_fails}",
                "",
                f"  Correct interpretation:",
                f"    {trap.correct_interpretation}",
                "",
                "-" * 80,
            ])

        lines.extend([
            "",
            "SUMMARY TABLE",
            "-" * 80,
            f"{'Trap Column':<25} {'Appears As':<30} {'Actually Is':<25}",
            "-" * 80,
        ])

        for trap in self.get_all():
            appears = trap.apparent_meaning[:28] + ".." if len(trap.apparent_meaning) > 30 else trap.apparent_meaning
            actual = trap.actual_content[:23] + ".." if len(trap.actual_content) > 25 else trap.actual_content
            lines.append(f"{trap.column_name:<25} {appears:<30} {actual:<25}")

        lines.extend([
            "-" * 80,
            "",
            "HOW TO USE THIS IN THE WORKSHOP:",
            "1. Generate data at cleanliness=30 to include most traps",
            "2. Ask Genie questions that will hit these traps",
            "3. Compare Genie's answers to actual correct values",
            "4. Discuss how proper data modeling prevents these issues",
        ])

        return "\n".join(lines)

    def get_trap_questions(self) -> Dict[str, Dict[str, str]]:
        """
        Get sample questions that will trigger each trap.

        Returns:
            Dictionary mapping trap IDs to question/expected_wrong_answer/correct_answer
        """
        return {
            "trap_revenue": {
                "question": "What was our total revenue last quarter?",
                "wrong_answer": "AI reports '$45,000' (sum of quantities)",
                "correct_answer": "Actual revenue is '$2.3M' (sum of net_amount)",
            },
            "trap_total": {
                "question": "What is the total order value for 2024?",
                "wrong_answer": "AI reports '$850,000' (pre-tax amount)",
                "correct_answer": "Actual total is '$1M' (including tax/fees)",
            },
            "trap_date": {
                "question": "Show me sales from January 2024",
                "wrong_answer": "AI returns empty results or errors on numeric filter",
                "correct_answer": "Need to convert epoch ms to dates first",
            },
            "trap_status": {
                "question": "How many active customers do we have?",
                "wrong_answer": "AI filters status=1 and gets inactive customers",
                "correct_answer": "Active customers have status=0 (inverted logic)",
            },
            "trap_margin": {
                "question": "What is our average profit margin?",
                "wrong_answer": "AI reports '35% margin' (actually markup)",
                "correct_answer": "True margin is ~26% (profit/revenue, not profit/cost)",
            },
            "trap_customer_count": {
                "question": "How many customers did we serve last year?",
                "wrong_answer": "AI reports '50,000 customers' (transaction count)",
                "correct_answer": "Actual unique customers: 500",
            },
            "trap_discount": {
                "question": "What is our average discount percentage?",
                "wrong_answer": "AI reports '15%' (actually $15 amount)",
                "correct_answer": "Average discount is ~5% of order value",
            },
        }


# =============================================================================
# MODULE-LEVEL SINGLETON
# =============================================================================


_registry: Optional[TrapRegistry] = None


def get_trap_registry() -> TrapRegistry:
    """
    Get singleton trap registry.

    Returns:
        TrapRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = TrapRegistry()
    return _registry
