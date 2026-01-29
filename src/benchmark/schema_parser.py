"""Schema Parser for LLM-Powered Benchmark System.

This module extracts domain context from YAML Genie Space configurations
to provide rich context for LLM query generation.
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

# Common metric-related keywords for inference
METRIC_KEYWORDS = frozenset(
    {
        "amount",
        "price",
        "cost",
        "revenue",
        "sales",
        "total",
        "sum",
        "count",
        "quantity",
        "qty",
        "balance",
        "profit",
        "margin",
        "rate",
        "ratio",
        "percentage",
        "percent",
        "avg",
        "average",
        "min",
        "max",
        "value",
        "fee",
        "discount",
        "tax",
        "weight",
        "score",
        "rating",
        "duration",
        "size",
        "volume",
    }
)

# Common key column patterns
KEY_PATTERNS = (
    re.compile(r".*_id$", re.IGNORECASE),
    re.compile(r".*_key$", re.IGNORECASE),
    re.compile(r"^id$", re.IGNORECASE),
    re.compile(r"^pk$", re.IGNORECASE),
    re.compile(r"^fk_.*", re.IGNORECASE),
)


@dataclass
class ColumnInfo:
    """Information about a table column.

    Attributes:
        name: Column name
        data_type: SQL data type (if known)
        description: Human-readable description
        is_key: Whether this is a key column (primary or foreign)
        is_metric: Whether this is a metric/measure column
    """

    name: str
    data_type: str | None = None
    description: str | None = None
    is_key: bool = False
    is_metric: bool = False


@dataclass
class TableInfo:
    """Information about a database table.

    Attributes:
        name: Just the table name (without catalog/schema)
        full_identifier: Full catalog.schema.table identifier
        columns: List of column information
        description: Human-readable description of the table
    """

    name: str
    full_identifier: str
    columns: list[ColumnInfo] = field(default_factory=list)
    description: str | None = None


@dataclass
class RelationshipInfo:
    """Information about a table relationship/join.

    Attributes:
        left_table: Full identifier of the left table
        right_table: Full identifier of the right table
        join_keys: List of join key specifications (e.g., ["col1=col2"] or ["col"])
        relationship_type: Type of relationship (e.g., "one-to-many", "many-to-many")
    """

    left_table: str
    right_table: str
    join_keys: list[str]
    relationship_type: str = "unknown"


@dataclass
class DomainContext:
    """Complete domain context extracted from a schema configuration.

    This dataclass aggregates all information needed to generate
    contextually-relevant benchmark queries for a domain.

    Attributes:
        domain_name: Name of the domain (from config title)
        tables: List of table information
        relationships: List of table relationships
        business_rules: Extracted business rules from instructions
        metrics: List of identified metrics
        sample_questions: Sample questions from the config
        example_sqls: Example SQL queries with their questions
    """

    domain_name: str
    tables: list[TableInfo] = field(default_factory=list)
    relationships: list[RelationshipInfo] = field(default_factory=list)
    business_rules: list[str] = field(default_factory=list)
    metrics: list[str] = field(default_factory=list)
    sample_questions: list[str] = field(default_factory=list)
    example_sqls: list[dict] = field(default_factory=list)

    def get_table_names(self) -> list[str]:
        """Get list of all table names (short names without catalog/schema).

        Returns:
            List of table names
        """
        return [table.name for table in self.tables]

    def get_all_column_names(self) -> list[str]:
        """Get list of all column names across all tables.

        Returns:
            List of column names (may contain duplicates from different tables)
        """
        columns: list[str] = []
        for table in self.tables:
            columns.extend(col.name for col in table.columns)
        return columns

    def to_prompt_context(self) -> str:
        """Format the domain context as a string for LLM prompts.

        Returns:
            Formatted string containing all domain context information
        """
        sections = []

        # Domain header
        sections.append(f"# Domain: {self.domain_name}\n")

        # Tables section
        if self.tables:
            sections.append("## Tables\n")
            for table in self.tables:
                table_desc = f"- **{table.full_identifier}**"
                if table.description:
                    table_desc += f": {table.description}"
                sections.append(table_desc)

                if table.columns:
                    col_strs = []
                    for col in table.columns:
                        col_info = col.name
                        annotations = []
                        if col.is_key:
                            annotations.append("KEY")
                        if col.is_metric:
                            annotations.append("METRIC")
                        if col.data_type:
                            annotations.append(col.data_type)
                        if annotations:
                            col_info += f" ({', '.join(annotations)})"
                        col_strs.append(col_info)
                    sections.append(f"  Columns: {', '.join(col_strs)}")
            sections.append("")

        # Relationships section
        if self.relationships:
            sections.append("## Relationships\n")
            for rel in self.relationships:
                join_desc = ", ".join(rel.join_keys)
                sections.append(f"- {rel.left_table} <-> {rel.right_table} ON ({join_desc})")
            sections.append("")

        # Business rules section
        if self.business_rules:
            sections.append("## Business Rules\n")
            for rule in self.business_rules:
                sections.append(f"- {rule}")
            sections.append("")

        # Metrics section
        if self.metrics:
            sections.append("## Key Metrics\n")
            sections.append(", ".join(self.metrics))
            sections.append("")

        # Sample questions section
        if self.sample_questions:
            sections.append("## Sample Questions\n")
            for i, question in enumerate(self.sample_questions, 1):
                sections.append(f"{i}. {question}")
            sections.append("")

        # Example SQLs section
        if self.example_sqls:
            sections.append("## Example SQL Queries\n")
            for example in self.example_sqls:
                sections.append(f"Question: {example.get('question', '')}")
                sections.append(f"```sql\n{example.get('sql', '').strip()}\n```\n")

        return "\n".join(sections)


class SchemaParser:
    """Parse YAML schema configs into DomainContext for LLM query generation.

    This class reads Genie Space YAML configuration files and extracts
    structured domain context that can be used to generate relevant
    benchmark queries.

    Example:
        >>> parser = SchemaParser("configs/sales_space.yaml")
        >>> context = parser.parse()
        >>> print(context.to_prompt_context())
    """

    def __init__(self, schema_path: str | Path):
        """Initialize the schema parser.

        Args:
            schema_path: Path to the YAML schema configuration file
        """
        self.schema_path = Path(schema_path)
        self._raw_config: dict | None = None

    def parse(self) -> DomainContext:
        """Parse schema and extract domain context.

        Returns:
            DomainContext containing all extracted information

        Raises:
            FileNotFoundError: If the schema file doesn't exist
            yaml.YAMLError: If the YAML is invalid
        """
        config = self._load_yaml()
        self._raw_config = config

        # Extract domain name from title
        domain_name = config.get("title", "Unknown Domain")

        # Extract all components
        tables = self._extract_tables()
        relationships = self._extract_relationships()
        business_rules = self._extract_business_rules()
        sample_questions = self._extract_sample_questions()
        example_sqls = self._extract_example_sqls()

        # Infer metrics from tables and instructions
        metrics = self._infer_metrics(tables, config.get("instructions", ""))

        return DomainContext(
            domain_name=domain_name,
            tables=tables,
            relationships=relationships,
            business_rules=business_rules,
            metrics=metrics,
            sample_questions=sample_questions,
            example_sqls=example_sqls,
        )

    def _load_yaml(self) -> dict:
        """Load YAML file with environment variable substitution.

        Returns:
            Parsed YAML content as dictionary

        Raises:
            FileNotFoundError: If the file doesn't exist
            yaml.YAMLError: If the YAML is invalid
        """
        if not self.schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {self.schema_path}")

        with open(self.schema_path, encoding="utf-8") as f:
            content = f.read()

        # Substitute environment variables
        content = self._substitute_env_vars(content)

        return yaml.safe_load(content) or {}

    def _substitute_env_vars(self, content: str) -> str:
        """Replace ${VAR} with environment variable values.

        Unlike the strict version in genie_space_manager.py, this version
        allows missing environment variables (replaces with empty string)
        since we're only parsing for schema information, not deployment.

        Args:
            content: String content with potential ${VAR} patterns

        Returns:
            Content with environment variables substituted
        """
        pattern = r"\$\{([^}]+)\}"

        def replace(match: re.Match) -> str:
            var_name = match.group(1)
            return os.environ.get(var_name, "")

        return re.sub(pattern, replace, content)

    def _extract_tables(self) -> list[TableInfo]:
        """Extract table information from config.

        Returns:
            List of TableInfo objects
        """
        if self._raw_config is None:
            return []

        tables = []
        table_configs = self._raw_config.get("tables", [])

        # Also try to extract column hints from instructions
        column_hints = self._extract_column_hints_from_instructions()

        for table_config in table_configs:
            identifier = table_config.get("identifier", "")
            if not identifier:
                continue

            # Parse catalog.schema.table format
            parts = identifier.split(".")
            if len(parts) == 3:
                table_name = parts[2]
            else:
                table_name = identifier

            # Get columns from hints if available
            columns = column_hints.get(table_name, [])

            # Get description from hints
            description = self._get_table_description(table_name)

            tables.append(
                TableInfo(
                    name=table_name,
                    full_identifier=identifier,
                    columns=columns,
                    description=description,
                )
            )

        return tables

    def _extract_column_hints_from_instructions(self) -> dict[str, list[ColumnInfo]]:
        """Extract column information from instructions text.

        Parses patterns like "table_name.column_name" or "table: col1, col2, col3"
        from the instructions field.

        Returns:
            Dictionary mapping table names to lists of ColumnInfo
        """
        if self._raw_config is None:
            return {}

        instructions = self._raw_config.get("instructions", "")
        if not instructions:
            return {}

        table_columns: dict[str, list[ColumnInfo]] = {}

        # Pattern 1: table.column references (e.g., "orders.o_totalprice")
        column_ref_pattern = r"(\w+)\.([a-z_][a-z0-9_]*)"
        for match in re.finditer(column_ref_pattern, instructions, re.IGNORECASE):
            table_name = match.group(1).lower()
            column_name = match.group(2)

            # Skip common non-column references
            if table_name in ("e", "ex", "eg", "i"):
                continue

            if table_name not in table_columns:
                table_columns[table_name] = []

            # Check if column already exists
            existing_names = {c.name for c in table_columns[table_name]}
            if column_name not in existing_names:
                is_key = any(p.match(column_name) for p in KEY_PATTERNS)
                is_metric = self._is_metric_column(column_name)
                table_columns[table_name].append(
                    ColumnInfo(
                        name=column_name,
                        is_key=is_key,
                        is_metric=is_metric,
                    )
                )

        # Pattern 2: "table: col1, col2, col3" format in table descriptions
        table_desc_pattern = r"-\s*(\w+):\s*([^\n]+(?:with|containing|has)?[^\n]*)"
        for match in re.finditer(table_desc_pattern, instructions):
            table_name = match.group(1).lower()
            desc = match.group(2)

            # Extract column names from description
            col_pattern = r"[a-z]_[a-z_]+|[a-z]+_[a-z]+"
            for col_match in re.finditer(col_pattern, desc, re.IGNORECASE):
                column_name = col_match.group(0)

                if table_name not in table_columns:
                    table_columns[table_name] = []

                existing_names = {c.name for c in table_columns[table_name]}
                if column_name not in existing_names:
                    is_key = any(p.match(column_name) for p in KEY_PATTERNS)
                    is_metric = self._is_metric_column(column_name)
                    table_columns[table_name].append(
                        ColumnInfo(
                            name=column_name,
                            is_key=is_key,
                            is_metric=is_metric,
                        )
                    )

        return table_columns

    def _get_table_description(self, table_name: str) -> str | None:
        """Extract table description from instructions.

        Args:
            table_name: Name of the table

        Returns:
            Description string or None
        """
        if self._raw_config is None:
            return None

        instructions = self._raw_config.get("instructions", "")
        if not instructions:
            return None

        # Look for "- table_name: description" pattern
        pattern = rf"-\s*{re.escape(table_name)}:\s*([^\n]+)"
        match = re.search(pattern, instructions, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        return None

    def _is_metric_column(self, column_name: str) -> bool:
        """Check if a column name suggests it's a metric.

        Args:
            column_name: Name of the column

        Returns:
            True if the column appears to be a metric
        """
        name_lower = column_name.lower()
        return any(keyword in name_lower for keyword in METRIC_KEYWORDS)

    def _extract_relationships(self) -> list[RelationshipInfo]:
        """Extract relationships from join_specs.

        Returns:
            List of RelationshipInfo objects
        """
        if self._raw_config is None:
            return []

        relationships = []
        join_specs = self._raw_config.get("join_specs", [])

        for spec in join_specs:
            left_table = spec.get("left_table", "")
            right_table = spec.get("right_table", "")
            join_keys = spec.get("join_keys", [])

            if left_table and right_table:
                relationships.append(
                    RelationshipInfo(
                        left_table=left_table,
                        right_table=right_table,
                        join_keys=join_keys,
                        relationship_type="unknown",
                    )
                )

        return relationships

    def _extract_business_rules(self) -> list[str]:
        """Parse instructions field for business rules.

        Extracts rules from common section headers like:
        - "Business Rules:"
        - "Rules:"
        - Bullet points under relevant sections

        Returns:
            List of business rule strings
        """
        if self._raw_config is None:
            return []

        instructions = self._raw_config.get("instructions", "")
        if not instructions:
            return []

        rules = []

        # Split into lines for processing
        lines = instructions.split("\n")

        # State tracking for section parsing
        in_rules_section = False
        section_headers = {
            "business rules",
            "rules",
            "metrics definitions",
            "metrics",
            "definitions",
        }

        for line in lines:
            line_stripped = line.strip()

            # Check for section headers
            header_match = re.match(r"^([^:]+):\s*$", line_stripped)
            if header_match:
                section_name = header_match.group(1).lower()
                in_rules_section = any(header in section_name for header in section_headers)
                continue

            # Empty line resets section context (simple heuristic)
            if not line_stripped:
                # Keep section context for a bit
                continue

            # Check for another section starting
            if re.match(r"^[A-Z][^:]+:", line_stripped) and not line_stripped.startswith("-"):
                in_rules_section = False
                continue

            # Extract bullet points from rules sections
            if in_rules_section and line_stripped.startswith("-"):
                rule = line_stripped[1:].strip()
                if rule and len(rule) > 10:  # Filter out very short items
                    rules.append(rule)

        return rules

    def _extract_sample_questions(self) -> list[str]:
        """Extract sample questions from config.

        Returns:
            List of question strings
        """
        if self._raw_config is None:
            return []

        questions = []
        sample_questions = self._raw_config.get("sample_questions", [])

        for sq in sample_questions:
            question_list = sq.get("question", [])
            if isinstance(question_list, list):
                questions.extend(question_list)
            elif isinstance(question_list, str):
                questions.append(question_list)

        return questions

    def _extract_example_sqls(self) -> list[dict]:
        """Extract example SQL queries from config.

        Returns:
            List of dicts with 'question' and 'sql' keys
        """
        if self._raw_config is None:
            return []

        examples = []
        example_sqls = self._raw_config.get("example_sqls", [])

        for example in example_sqls:
            question = example.get("question", "")
            sql = example.get("sql", "")
            if question and sql:
                examples.append({"question": question, "sql": sql})

        return examples

    def _infer_metrics(self, tables: list[TableInfo], instructions: str) -> list[str]:
        """Infer metric names from tables and instructions.

        Args:
            tables: List of extracted tables
            instructions: Instructions text to search

        Returns:
            List of metric names/definitions
        """
        metrics = []

        # Extract from table columns
        for table in tables:
            for col in table.columns:
                if col.is_metric:
                    metrics.append(f"{table.name}.{col.name}")

        # Extract metric definitions from instructions
        if instructions:
            # Pattern: "- MetricName = formula" or "- MetricName: definition"
            metric_pattern = r"-\s*([A-Z][a-zA-Z\s]+)\s*[=:]\s*([^\n]+)"
            for match in re.finditer(metric_pattern, instructions):
                metric_name = match.group(1).strip()
                metric_def = match.group(2).strip()
                # Only include if it looks like a metric definition
                if any(keyword in metric_def.lower() for keyword in ["sum", "count", "avg", "average", "/", "*", "+"]):
                    metrics.append(f"{metric_name} = {metric_def}")

        return metrics

    def get_schema_hash(self) -> str:
        """Generate hash of schema for versioning.

        Returns:
            MD5 hash of the raw YAML content
        """
        if not self.schema_path.exists():
            return ""

        with open(self.schema_path, "rb") as f:
            content = f.read()

        return hashlib.md5(content).hexdigest()

    def get_raw_config(self) -> dict | None:
        """Get the raw parsed configuration.

        Returns:
            The raw config dict, or None if not yet parsed
        """
        return self._raw_config
