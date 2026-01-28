"""Genie Space Manager - Infrastructure-as-Code for Databricks Genie Spaces.

This module provides a high-level interface for managing Databricks Genie Spaces
via the REST API, enabling infrastructure-as-code workflows for AI/BI configuration.

Note: The Genie Space Create/Update APIs are in Beta as of early 2025.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field, field_validator


class SampleQuestion(BaseModel):
    """A sample question for the Genie Space.

    Attributes:
        id: Unique identifier for the question
        question: List of question variations (usually single item)
    """

    id: str
    question: list[str]


class TableSource(BaseModel):
    """A table data source for the Genie Space.

    Attributes:
        identifier: Fully qualified table name (catalog.schema.table)
    """

    identifier: str

    @field_validator("identifier")
    @classmethod
    def validate_identifier(cls, v: str) -> str:
        """Validate the table identifier format."""
        parts = v.split(".")
        if len(parts) != 3:
            raise ValueError(
                f"Table identifier must be in 'catalog.schema.table' format, got: {v}"
            )
        return v


class JoinSpec(BaseModel):
    """Specification for how tables should be joined.

    Attributes:
        left_table: Fully qualified name of the left table
        right_table: Fully qualified name of the right table
        join_keys: List of column names to join on
    """

    left_table: str
    right_table: str
    join_keys: list[str]


class ExampleSQL(BaseModel):
    """An example SQL query with its natural language question.

    Attributes:
        question: Natural language question
        sql: Corresponding SQL query
    """

    question: str
    sql: str


class GenieSpaceConfig(BaseModel):
    """Configuration for a Genie Space.

    Attributes:
        title: Display title for the Genie Space
        description: Optional description of the space's purpose
        warehouse_id: SQL Warehouse ID to use for queries
        parent_path: Workspace path where the space will be created
        tables: List of tables available in the space
        sample_questions: List of example questions for users
        instructions: Business rules and context for the AI
        example_sqls: Example SQL queries for the AI to learn from
        join_specs: Specifications for how tables should be joined
    """

    title: str
    description: Optional[str] = None
    warehouse_id: str
    parent_path: str = Field(
        description="Workspace path (e.g., /Workspace/Shared/genie-spaces)"
    )
    tables: list[TableSource]
    sample_questions: list[SampleQuestion] = Field(default_factory=list)
    instructions: Optional[str] = None
    example_sqls: list[ExampleSQL] = Field(default_factory=list)
    join_specs: list[JoinSpec] = Field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: str | Path, substitute_env: bool = True) -> GenieSpaceConfig:
        """Load configuration from a YAML file.

        Args:
            path: Path to the YAML configuration file
            substitute_env: Whether to substitute ${VAR} with environment variables

        Returns:
            GenieSpaceConfig instance

        Raises:
            FileNotFoundError: If the config file doesn't exist
            ValueError: If the config is invalid
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")

        with open(path, "r") as f:
            content = f.read()

        # Substitute environment variables if requested
        if substitute_env:
            content = cls._substitute_env_vars(content)

        data = yaml.safe_load(content)
        return cls.model_validate(data)

    @staticmethod
    def _substitute_env_vars(content: str) -> str:
        """Substitute ${VAR} patterns with environment variable values.

        Args:
            content: String content with potential ${VAR} patterns

        Returns:
            Content with environment variables substituted
        """
        pattern = r"\$\{([^}]+)\}"

        def replace(match: re.Match) -> str:
            var_name = match.group(1)
            value = os.environ.get(var_name)
            if value is None:
                raise ValueError(
                    f"Environment variable '{var_name}' is not set. "
                    f"Please set it or remove the reference from the config."
                )
            return value

        return re.sub(pattern, replace, content)

    def to_yaml(self, path: str | Path) -> None:
        """Save configuration to a YAML file.

        Args:
            path: Path to save the YAML configuration
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        data = self.model_dump(exclude_none=True)
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)


class GenieSpaceManager:
    """Manage Databricks Genie Spaces via the REST API.

    This class provides CRUD operations for Genie Spaces, enabling
    infrastructure-as-code workflows for AI/BI configuration.

    Note: Create and Update operations are in Beta as of early 2025.

    Example:
        >>> from databricks.sdk import WorkspaceClient
        >>> manager = GenieSpaceManager()
        >>> config = GenieSpaceConfig.from_yaml("my_space.yaml")
        >>> space_id = manager.create_space(config)
        >>> print(f"Created space: {space_id}")
    """

    # API endpoints
    _BASE_PATH = "/api/2.0/genie/spaces"

    def __init__(
        self,
        workspace_client: Optional[Any] = None,
        profile: Optional[str] = None,
    ):
        """Initialize the Genie Space Manager.

        Args:
            workspace_client: Optional WorkspaceClient instance.
                              If not provided, creates one using default auth.
            profile: Optional Databricks CLI profile name to use for authentication.
                     Ignored if workspace_client is provided.
        """
        self._client = workspace_client
        self._profile = profile

    @property
    def client(self) -> Any:
        """Get or create the WorkspaceClient.

        Returns:
            WorkspaceClient instance
        """
        if self._client is None:
            from databricks.sdk import WorkspaceClient

            if self._profile:
                self._client = WorkspaceClient(profile=self._profile)
            else:
                self._client = WorkspaceClient()
        return self._client

    def _build_serialized_space(self, config: GenieSpaceConfig) -> dict[str, Any]:
        """Build the serialized_space JSON structure from config.

        The structure follows the Genie API schema. Based on API exploration,
        the minimal structure is:
        - data_sources.tables: list of table identifiers

        Args:
            config: GenieSpaceConfig instance

        Returns:
            Dictionary structure for the serialized_space field
        """
        # Minimal structure that Genie API accepts
        # Version 1 is required by the ExportConverter
        # Tables must be sorted alphabetically by identifier
        sorted_tables = sorted(config.tables, key=lambda t: t.identifier)
        serialized: dict[str, Any] = {
            "version": 1,
            "data_sources": {
                "tables": [{"identifier": t.identifier} for t in sorted_tables]
            },
        }

        # Sample questions go in config block
        # IDs must be lowercase 32-hex UUIDs without hyphens
        if config.sample_questions:
            import hashlib
            serialized["config"] = {
                "sample_questions": [
                    {
                        # Generate deterministic UUID from question ID for reproducibility
                        "id": hashlib.md5(q.id.encode()).hexdigest(),
                        "question": q.question
                    }
                    for q in config.sample_questions
                ]
            }

        # Note: instructions, example_sqls, and join_specs may need to be
        # configured through the Genie UI after space creation, as the API
        # schema for these fields is not fully documented in public docs.

        return serialized

    def create_space(self, config: GenieSpaceConfig, dry_run: bool = False) -> str:
        """Create a new Genie Space.

        Args:
            config: Configuration for the new space
            dry_run: If True, only print what would be created

        Returns:
            The space_id of the created space

        Raises:
            Exception: If the API call fails
        """
        request_body = {
            "title": config.title,
            "warehouse_id": config.warehouse_id,
            "parent_path": config.parent_path,
            "serialized_space": json.dumps(self._build_serialized_space(config)),
        }

        if config.description:
            request_body["description"] = config.description

        if dry_run:
            print("DRY RUN - Would create Genie Space with:")
            print(json.dumps(request_body, indent=2))
            return "dry-run-space-id"

        response = self.client.api_client.do(
            method="POST",
            path=self._BASE_PATH,
            body=request_body,
        )

        space_id = response.get("space_id")
        if not space_id:
            raise ValueError(f"No space_id in response: {response}")

        return space_id

    def update_space(
        self, space_id: str, config: GenieSpaceConfig, dry_run: bool = False
    ) -> None:
        """Update an existing Genie Space.

        Args:
            space_id: ID of the space to update
            config: New configuration for the space
            dry_run: If True, only print what would be updated

        Raises:
            Exception: If the API call fails
        """
        request_body = {
            "title": config.title,
            "warehouse_id": config.warehouse_id,
            "serialized_space": json.dumps(self._build_serialized_space(config)),
        }

        if config.description:
            request_body["description"] = config.description

        if dry_run:
            print(f"DRY RUN - Would update Genie Space {space_id} with:")
            print(json.dumps(request_body, indent=2))
            return

        self.client.api_client.do(
            method="PUT",
            path=f"{self._BASE_PATH}/{space_id}",
            body=request_body,
        )

    def get_space(self, space_id: str) -> dict[str, Any]:
        """Get details of a Genie Space.

        Args:
            space_id: ID of the space to retrieve

        Returns:
            Dictionary containing space details

        Raises:
            Exception: If the space doesn't exist or API call fails
        """
        response = self.client.api_client.do(
            method="GET",
            path=f"{self._BASE_PATH}/{space_id}",
        )
        return response

    def delete_space(self, space_id: str, dry_run: bool = False) -> None:
        """Move a Genie Space to trash.

        Args:
            space_id: ID of the space to delete
            dry_run: If True, only print what would be deleted

        Raises:
            Exception: If the API call fails
        """
        if dry_run:
            print(f"DRY RUN - Would delete (trash) Genie Space: {space_id}")
            return

        self.client.api_client.do(
            method="DELETE",
            path=f"{self._BASE_PATH}/{space_id}",
        )

    def list_spaces(self) -> list[dict[str, Any]]:
        """List all Genie Spaces in the workspace.

        Returns:
            List of dictionaries containing space summaries

        Raises:
            Exception: If the API call fails
        """
        response = self.client.api_client.do(
            method="GET",
            path=self._BASE_PATH,
        )
        return response.get("spaces", [])

    def deploy_from_config(
        self,
        config_path: str | Path,
        space_id: Optional[str] = None,
        dry_run: bool = False,
    ) -> str:
        """Deploy a Genie Space from a YAML configuration file.

        If space_id is provided, updates the existing space.
        Otherwise, creates a new space.

        Args:
            config_path: Path to the YAML configuration file
            space_id: Optional existing space ID to update
            dry_run: If True, only print what would be done

        Returns:
            The space_id of the created/updated space
        """
        config = GenieSpaceConfig.from_yaml(config_path)

        if space_id:
            self.update_space(space_id, config, dry_run=dry_run)
            if not dry_run:
                print(f"Updated Genie Space: {space_id}")
            return space_id
        else:
            new_space_id = self.create_space(config, dry_run=dry_run)
            if not dry_run:
                print(f"Created Genie Space: {new_space_id}")
            return new_space_id

    def export_space(self, space_id: str, output_path: str | Path) -> None:
        """Export a Genie Space configuration to a YAML file.

        Args:
            space_id: ID of the space to export
            output_path: Path to save the YAML configuration
        """
        space_data = self.get_space(space_id)

        # Parse serialized_space if present
        serialized_space_str = space_data.get("serialized_space", "{}")
        serialized_space = json.loads(serialized_space_str)

        # Build config from space data
        tables = []
        for table in serialized_space.get("data_sources", {}).get("tables", []):
            tables.append(TableSource(identifier=table.get("identifier", "")))

        sample_questions = []
        for sq in serialized_space.get("config", {}).get("sample_questions", []):
            sample_questions.append(
                SampleQuestion(id=sq.get("id", ""), question=sq.get("question", []))
            )

        example_sqls = []
        for ex in serialized_space.get("instructions", {}).get(
            "example_question_sqls", []
        ):
            example_sqls.append(
                ExampleSQL(question=ex.get("question", ""), sql=ex.get("sql", ""))
            )

        join_specs = []
        for js in serialized_space.get("instructions", {}).get("join_specs", []):
            join_specs.append(
                JoinSpec(
                    left_table=js.get("left_table", ""),
                    right_table=js.get("right_table", ""),
                    join_keys=js.get("join_keys", []),
                )
            )

        config = GenieSpaceConfig(
            title=space_data.get("title", ""),
            description=space_data.get("description"),
            warehouse_id=space_data.get("warehouse_id", ""),
            parent_path=space_data.get("parent_path", ""),
            tables=tables,
            sample_questions=sample_questions,
            instructions=serialized_space.get("config", {}).get("instructions"),
            example_sqls=example_sqls,
            join_specs=join_specs,
        )

        config.to_yaml(output_path)
        print(f"Exported Genie Space to: {output_path}")
