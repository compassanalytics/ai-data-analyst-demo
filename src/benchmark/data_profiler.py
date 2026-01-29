"""Data profiler for parquet tables to extract characteristics for benchmark generation.

This module provides tools to profile parquet files and extract data characteristics
that can be used to generate more accurate and relevant benchmark questions.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


# Threshold for considering a column as high-cardinality ID-like
HIGH_CARDINALITY_THRESHOLD = 1000
# Number of top values to keep for categorical columns
TOP_K_VALUES = 10


@dataclass
class ColumnProfile:
    """Profile of a single column in a table.

    Contains statistics and metadata about the column including null rates,
    unique counts, and type-specific statistics (numeric, categorical, date).

    Attributes:
        name: Column name
        dtype: Data type as string
        null_count: Number of null/missing values
        null_rate: Percentage of null values (0.0 to 1.0)
        unique_count: Number of unique values
        is_id_like: Whether column appears to be an ID column (high cardinality, no repeats)
        top_values: For categorical columns, top K (value, count) pairs
        min_value: For numeric columns, minimum value
        max_value: For numeric columns, maximum value
        mean_value: For numeric columns, mean value
        median_value: For numeric columns, median value
        std_value: For numeric columns, standard deviation
        min_date: For date columns, earliest date as ISO string
        max_date: For date columns, latest date as ISO string
    """

    name: str
    dtype: str
    null_count: int = 0
    null_rate: float = 0.0
    unique_count: int = 0
    is_id_like: bool = False

    # Categorical column stats
    top_values: list[tuple[str, int]] = field(default_factory=list)

    # Numeric column stats
    min_value: float | None = None
    max_value: float | None = None
    mean_value: float | None = None
    median_value: float | None = None
    std_value: float | None = None

    # Date column stats
    min_date: str | None = None
    max_date: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation of the column profile
        """
        result = {
            "name": self.name,
            "dtype": self.dtype,
            "null_count": self.null_count,
            "null_rate": self.null_rate,
            "unique_count": self.unique_count,
            "is_id_like": self.is_id_like,
        }

        # Only include non-empty/non-None values
        if self.top_values:
            result["top_values"] = self.top_values
        if self.min_value is not None:
            result["min_value"] = self.min_value
        if self.max_value is not None:
            result["max_value"] = self.max_value
        if self.mean_value is not None:
            result["mean_value"] = self.mean_value
        if self.median_value is not None:
            result["median_value"] = self.median_value
        if self.std_value is not None:
            result["std_value"] = self.std_value
        if self.min_date is not None:
            result["min_date"] = self.min_date
        if self.max_date is not None:
            result["max_date"] = self.max_date

        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ColumnProfile:
        """Create from dictionary.

        Args:
            data: Dictionary containing column profile data

        Returns:
            ColumnProfile instance
        """
        return cls(
            name=data["name"],
            dtype=data["dtype"],
            null_count=data.get("null_count", 0),
            null_rate=data.get("null_rate", 0.0),
            unique_count=data.get("unique_count", 0),
            is_id_like=data.get("is_id_like", False),
            top_values=data.get("top_values", []),
            min_value=data.get("min_value"),
            max_value=data.get("max_value"),
            mean_value=data.get("mean_value"),
            median_value=data.get("median_value"),
            std_value=data.get("std_value"),
            min_date=data.get("min_date"),
            max_date=data.get("max_date"),
        )

    def is_numeric(self) -> bool:
        """Check if this column has numeric statistics."""
        return self.min_value is not None

    def is_date(self) -> bool:
        """Check if this column has date statistics."""
        return self.min_date is not None

    def is_categorical(self) -> bool:
        """Check if this column has categorical statistics."""
        return len(self.top_values) > 0


@dataclass
class DataProfile:
    """Profile of a single table/parquet file.

    Contains metadata about the table and profiles of all columns.

    Attributes:
        table_name: Name of the table (derived from filename)
        row_count: Total number of rows in the table
        columns: List of column profiles
        data_signature: MD5 hash of file modification times for cache validation
        profiled_at: ISO timestamp of when the profile was generated
    """

    table_name: str
    row_count: int
    columns: list[ColumnProfile] = field(default_factory=list)
    data_signature: str = ""
    profiled_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation of the data profile
        """
        return {
            "table_name": self.table_name,
            "row_count": self.row_count,
            "columns": [col.to_dict() for col in self.columns],
            "data_signature": self.data_signature,
            "profiled_at": self.profiled_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DataProfile:
        """Create from dictionary.

        Args:
            data: Dictionary containing data profile data

        Returns:
            DataProfile instance
        """
        return cls(
            table_name=data["table_name"],
            row_count=data["row_count"],
            columns=[ColumnProfile.from_dict(col) for col in data.get("columns", [])],
            data_signature=data.get("data_signature", ""),
            profiled_at=data.get("profiled_at", ""),
        )

    def get_column(self, name: str) -> ColumnProfile | None:
        """Get a column profile by name.

        Args:
            name: Column name to find

        Returns:
            ColumnProfile if found, None otherwise
        """
        for col in self.columns:
            if col.name == name:
                return col
        return None

    def get_numeric_columns(self) -> list[ColumnProfile]:
        """Get all numeric columns."""
        return [col for col in self.columns if col.is_numeric()]

    def get_categorical_columns(self) -> list[ColumnProfile]:
        """Get all categorical columns (non-ID-like)."""
        return [col for col in self.columns if col.is_categorical() and not col.is_id_like]

    def get_date_columns(self) -> list[ColumnProfile]:
        """Get all date columns."""
        return [col for col in self.columns if col.is_date()]


class DataProfiler:
    """Profiler for parquet tables to extract data characteristics.

    Analyzes parquet files to generate profiles that describe column statistics,
    value distributions, and data characteristics useful for benchmark generation.

    Attributes:
        data_dir: Directory containing parquet files
    """

    def __init__(self, data_dir: str | Path) -> None:
        """Initialize the data profiler.

        Args:
            data_dir: Path to directory containing parquet files
        """
        self.data_dir = Path(data_dir)
        if not self.data_dir.exists():
            raise ValueError(f"Data directory does not exist: {self.data_dir}")
        if not self.data_dir.is_dir():
            raise ValueError(f"Path is not a directory: {self.data_dir}")

    def _compute_data_signature(self, table_paths: list[Path]) -> str:
        """Compute MD5 hash of file modification times for caching.

        Args:
            table_paths: List of parquet file paths

        Returns:
            MD5 hash string of modification times
        """
        hasher = hashlib.md5()
        for path in sorted(table_paths):
            mtime = path.stat().st_mtime
            hasher.update(f"{path.name}:{mtime}".encode())
        return hasher.hexdigest()

    def _is_numeric_dtype(self, dtype: str) -> bool:
        """Check if dtype string indicates a numeric type."""
        numeric_patterns = ["int", "float", "double", "decimal", "numeric"]
        dtype_lower = dtype.lower()
        return any(pattern in dtype_lower for pattern in numeric_patterns)

    def _is_datetime_dtype(self, dtype: str) -> bool:
        """Check if dtype string indicates a datetime type."""
        datetime_patterns = ["datetime", "timestamp", "date"]
        dtype_lower = dtype.lower()
        return any(pattern in dtype_lower for pattern in datetime_patterns)

    def _is_id_like_column(self, col: pd.Series, unique_count: int, row_count: int) -> bool:
        """Determine if a column appears to be an ID column.

        A column is considered ID-like if:
        - It has high cardinality (> threshold unique values)
        - Nearly all values are unique (uniqueness ratio > 0.95)
        - Column name suggests it's an ID

        Args:
            col: Pandas Series for the column
            unique_count: Number of unique values
            row_count: Total number of rows

        Returns:
            True if column appears to be ID-like
        """
        # Check name patterns
        name_lower = col.name.lower()
        id_patterns = ["_id", "id_", "_uuid", "uuid_", "_key", "key_"]
        name_is_id_like = any(pattern in name_lower for pattern in id_patterns) or name_lower.endswith("id")

        # Check cardinality
        if row_count == 0:
            return False

        uniqueness_ratio = unique_count / row_count
        is_high_cardinality = unique_count > HIGH_CARDINALITY_THRESHOLD
        is_mostly_unique = uniqueness_ratio > 0.95

        # Consider ID-like if name suggests it OR if it has high cardinality with unique values
        return name_is_id_like or (is_high_cardinality and is_mostly_unique)

    def _profile_numeric_column(self, col: pd.Series) -> dict[str, float | None]:
        """Extract numeric statistics from a column.

        Args:
            col: Pandas Series containing numeric data

        Returns:
            Dictionary with min, max, mean, median, std values
        """
        stats: dict[str, float | None] = {
            "min_value": None,
            "max_value": None,
            "mean_value": None,
            "median_value": None,
            "std_value": None,
        }

        try:
            non_null = col.dropna()
            if len(non_null) > 0:
                stats["min_value"] = float(non_null.min())
                stats["max_value"] = float(non_null.max())
                stats["mean_value"] = float(non_null.mean())
                stats["median_value"] = float(non_null.median())
                stats["std_value"] = float(non_null.std()) if len(non_null) > 1 else 0.0
        except (TypeError, ValueError) as e:
            logger.warning(f"Could not compute numeric stats for column {col.name}: {e}")

        return stats

    def _profile_datetime_column(self, col: pd.Series) -> dict[str, str | None]:
        """Extract date statistics from a column.

        Args:
            col: Pandas Series containing datetime data

        Returns:
            Dictionary with min_date and max_date as ISO strings
        """
        stats: dict[str, str | None] = {
            "min_date": None,
            "max_date": None,
        }

        try:
            non_null = col.dropna()
            if len(non_null) > 0:
                # Try to convert to datetime if not already
                if not pd.api.types.is_datetime64_any_dtype(non_null):
                    non_null = pd.to_datetime(non_null, errors="coerce").dropna()

                if len(non_null) > 0:
                    min_dt = non_null.min()
                    max_dt = non_null.max()
                    # Convert to ISO format string
                    stats["min_date"] = pd.Timestamp(min_dt).isoformat()
                    stats["max_date"] = pd.Timestamp(max_dt).isoformat()
        except (TypeError, ValueError) as e:
            logger.warning(f"Could not compute date stats for column {col.name}: {e}")

        return stats

    def _profile_categorical_column(self, col: pd.Series, top_k: int = TOP_K_VALUES) -> list[tuple[str, int]]:
        """Extract top K value counts from a categorical column.

        Args:
            col: Pandas Series containing categorical data
            top_k: Number of top values to return

        Returns:
            List of (value, count) tuples sorted by count descending
        """
        try:
            value_counts = col.value_counts(dropna=True).head(top_k)
            return [(str(val), int(count)) for val, count in value_counts.items()]
        except (TypeError, ValueError) as e:
            logger.warning(f"Could not compute value counts for column {col.name}: {e}")
            return []

    def _profile_column(self, col: pd.Series, row_count: int) -> ColumnProfile:
        """Profile a single column.

        Args:
            col: Pandas Series for the column
            row_count: Total number of rows in the table

        Returns:
            ColumnProfile with all relevant statistics
        """
        dtype_str = str(col.dtype)
        null_count = int(col.isna().sum())
        null_rate = null_count / row_count if row_count > 0 else 0.0
        unique_count = int(col.nunique(dropna=True))

        is_id_like = self._is_id_like_column(col, unique_count, row_count)

        profile = ColumnProfile(
            name=str(col.name),
            dtype=dtype_str,
            null_count=null_count,
            null_rate=round(null_rate, 4),
            unique_count=unique_count,
            is_id_like=is_id_like,
        )

        # Add type-specific statistics
        if self._is_numeric_dtype(dtype_str):
            numeric_stats = self._profile_numeric_column(col)
            profile.min_value = numeric_stats["min_value"]
            profile.max_value = numeric_stats["max_value"]
            profile.mean_value = numeric_stats["mean_value"]
            profile.median_value = numeric_stats["median_value"]
            profile.std_value = numeric_stats["std_value"]

        elif self._is_datetime_dtype(dtype_str):
            date_stats = self._profile_datetime_column(col)
            profile.min_date = date_stats["min_date"]
            profile.max_date = date_stats["max_date"]

        # Add categorical stats for non-ID columns with low-to-medium cardinality
        # We also add top values for ID-like columns if they have reasonable cardinality
        # to help understand the data patterns
        if not is_id_like and not self._is_numeric_dtype(dtype_str):
            profile.top_values = self._profile_categorical_column(col)

        return profile

    def profile_table(self, table_path: Path) -> DataProfile:
        """Profile a single parquet table.

        Args:
            table_path: Path to the parquet file

        Returns:
            DataProfile with table metadata and column profiles

        Raises:
            FileNotFoundError: If the table file does not exist
            ValueError: If the file is not a valid parquet file
        """
        if not table_path.exists():
            raise FileNotFoundError(f"Table file not found: {table_path}")

        table_name = table_path.stem  # filename without extension

        logger.info(f"Profiling table: {table_name}")

        try:
            df = pd.read_parquet(table_path)
        except Exception as e:
            raise ValueError(f"Failed to read parquet file {table_path}: {e}") from e

        row_count = len(df)
        columns = [self._profile_column(df[col], row_count) for col in df.columns]

        # Compute signature for just this file
        data_signature = self._compute_data_signature([table_path])

        return DataProfile(
            table_name=table_name,
            row_count=row_count,
            columns=columns,
            data_signature=data_signature,
            profiled_at=datetime.now().isoformat(),
        )

    def profile_all_tables(self) -> dict[str, DataProfile]:
        """Profile all parquet tables in the data directory.

        Returns:
            Dictionary mapping table names to their DataProfile instances
        """
        parquet_files = list(self.data_dir.glob("*.parquet"))

        if not parquet_files:
            logger.warning(f"No parquet files found in {self.data_dir}")
            return {}

        logger.info(f"Found {len(parquet_files)} parquet files to profile")

        profiles: dict[str, DataProfile] = {}
        for table_path in sorted(parquet_files):
            try:
                profile = self.profile_table(table_path)
                profiles[profile.table_name] = profile
            except Exception as e:
                logger.error(f"Failed to profile {table_path}: {e}")
                continue

        logger.info(f"Successfully profiled {len(profiles)} tables")
        return profiles

    def to_prompt_context(self, profiles: dict[str, DataProfile]) -> str:
        """Format profiles as context for LLM prompts.

        Generates a human-readable summary of the data profiles that can be
        included in prompts to help LLMs generate relevant benchmark questions.

        Args:
            profiles: Dictionary of table name to DataProfile

        Returns:
            Formatted string suitable for inclusion in LLM prompts
        """
        lines = ["## Data Profile Summary", ""]

        for table_name in sorted(profiles.keys()):
            profile = profiles[table_name]
            lines.append(f"### Table: {table_name}")
            lines.append(f"- Row count: {profile.row_count:,}")
            lines.append(f"- Columns: {len(profile.columns)}")
            lines.append("")

            # Group columns by type for cleaner output
            numeric_cols = profile.get_numeric_columns()
            date_cols = profile.get_date_columns()
            categorical_cols = profile.get_categorical_columns()

            if numeric_cols:
                lines.append("**Numeric Columns:**")
                for col in numeric_cols:
                    range_str = f"[{col.min_value:,.2f} - {col.max_value:,.2f}]" if col.min_value is not None else "N/A"
                    lines.append(
                        f"- `{col.name}` ({col.dtype}): range {range_str}, mean={col.mean_value:,.2f}"
                        if col.mean_value
                        else f"- `{col.name}` ({col.dtype})"
                    )
                lines.append("")

            if date_cols:
                lines.append("**Date Columns:**")
                for col in date_cols:
                    if col.min_date and col.max_date:
                        date_range = f"[{col.min_date[:10]} to {col.max_date[:10]}]"
                    else:
                        date_range = "N/A"
                    lines.append(f"- `{col.name}`: range {date_range}")
                lines.append("")

            if categorical_cols:
                lines.append("**Categorical Columns (with top values):**")
                for col in categorical_cols:
                    if col.top_values:
                        top_str = ", ".join(
                            f"'{val}' ({count}, {count / profile.row_count * 100:.1f}%)"
                            for val, count in col.top_values[:5]
                        )
                        lines.append(f"- `{col.name}` ({col.unique_count} unique): {top_str}")
                    else:
                        lines.append(f"- `{col.name}` ({col.unique_count} unique)")
                lines.append("")

            # List ID-like columns separately
            id_cols = [col for col in profile.columns if col.is_id_like]
            if id_cols:
                lines.append("**ID/Key Columns:**")
                for col in id_cols:
                    lines.append(f"- `{col.name}` ({col.unique_count:,} unique values)")
                lines.append("")

            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def save_profiles(self, profiles: dict[str, DataProfile], output_path: Path) -> None:
        """Save profiles to a JSON file.

        Args:
            profiles: Dictionary of table name to DataProfile
            output_path: Path to write the JSON file

        Raises:
            IOError: If the file cannot be written
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": "1.0",
            "generated_at": datetime.now().isoformat(),
            "data_dir": str(self.data_dir),
            "tables": {name: profile.to_dict() for name, profile in profiles.items()},
        }

        try:
            with open(output_path, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved profiles to {output_path}")
        except OSError as e:
            raise OSError(f"Failed to save profiles to {output_path}: {e}") from e

    def load_profiles(self, input_path: Path) -> dict[str, DataProfile]:
        """Load profiles from a JSON file.

        Args:
            input_path: Path to the JSON file

        Returns:
            Dictionary of table name to DataProfile

        Raises:
            FileNotFoundError: If the file does not exist
            ValueError: If the file format is invalid
        """
        input_path = Path(input_path)

        if not input_path.exists():
            raise FileNotFoundError(f"Profile file not found: {input_path}")

        try:
            with open(input_path) as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in profile file: {e}") from e

        if "tables" not in data:
            raise ValueError("Invalid profile file format: missing 'tables' key")

        profiles = {name: DataProfile.from_dict(table_data) for name, table_data in data["tables"].items()}

        logger.info(f"Loaded {len(profiles)} profiles from {input_path}")
        return profiles

    def get_data_signature(self) -> str:
        """Get the data signature for all parquet files in the data directory.

        Useful for checking if cached profiles are still valid.

        Returns:
            MD5 hash of all file modification times
        """
        parquet_files = list(self.data_dir.glob("*.parquet"))
        return self._compute_data_signature(parquet_files)
