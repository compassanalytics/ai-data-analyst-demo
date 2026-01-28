"""Evaluation Reporter for the Genie Testing and Evaluation Framework.

This module provides report generation capabilities for evaluation results,
supporting Markdown, HTML, and JSON output formats with customizable templates.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from src.evaluation.evaluator import EvaluationResults


class EvaluationReporter:
    """Generate reports from evaluation results.

    Provides template-based report generation with lazy-loaded Jinja2 environments.
    HTML templates use autoescape for security (content may come from LLM).

    Example:
        >>> from src.evaluation.evaluator import GenieEvaluator, EvaluationResults
        >>> reporter = EvaluationReporter()
        >>> markdown = reporter.generate_markdown(results, title="Q4 Evaluation")
        >>> html = reporter.generate_html(results, title="Q4 Dashboard")
    """

    def __init__(self) -> None:
        """Initialize the reporter."""
        self._md_env = None
        self._html_env = None

    @property
    def md_template_env(self):
        """Lazy-load Markdown Jinja2 environment (NO autoescape).

        Markdown output doesn't require HTML escaping since it's plain text.

        Returns:
            Jinja2 Environment configured for Markdown templates
        """
        if self._md_env is None:
            import jinja2

            self._md_env = jinja2.Environment(
                loader=jinja2.PackageLoader("src", "templates"),
                autoescape=False,  # Markdown doesn't need escaping
                trim_blocks=True,
                lstrip_blocks=True,
            )
            self._register_filters(self._md_env)
        return self._md_env

    @property
    def html_template_env(self):
        """Lazy-load HTML Jinja2 environment (autoescape ENABLED).

        Security: HTML escaping is enabled because content may come from LLM
        responses or user input.

        Returns:
            Jinja2 Environment configured for HTML templates with autoescape
        """
        if self._html_env is None:
            import jinja2

            self._html_env = jinja2.Environment(
                loader=jinja2.PackageLoader("src", "templates"),
                autoescape=True,  # Security: escape LLM content
                trim_blocks=True,
                lstrip_blocks=True,
            )
            self._register_filters(self._html_env)
        return self._html_env

    def _register_filters(self, env) -> None:
        """Register custom Jinja2 filters on an environment.

        Args:
            env: Jinja2 Environment to add filters to
        """
        env.filters["format_percent"] = self._format_percent
        env.filters["format_number"] = self._format_number
        env.filters["format_duration"] = self._format_duration

    @staticmethod
    def _format_percent(value: float, decimals: int = 1) -> str:
        """Format a number as a percentage.

        Args:
            value: Number to format (0-100 scale)
            decimals: Number of decimal places

        Returns:
            Formatted percentage string
        """
        try:
            return f"{value:.{decimals}f}%"
        except (ValueError, TypeError):
            return str(value)

    @staticmethod
    def _format_number(value, decimals: int = 0) -> str:
        """Format a number with thousands separators.

        Args:
            value: Number to format
            decimals: Number of decimal places

        Returns:
            Formatted number string with thousands separators
        """
        try:
            return f"{value:,.{decimals}f}"
        except (ValueError, TypeError):
            return str(value)

    @staticmethod
    def _format_duration(ms: float) -> str:
        """Format milliseconds as a human-readable duration.

        Args:
            ms: Duration in milliseconds

        Returns:
            Formatted duration string (e.g., "1.23s", "500ms")
        """
        try:
            if ms >= 1000:
                return f"{ms / 1000:.2f}s"
            return f"{ms:.0f}ms"
        except (ValueError, TypeError):
            return str(ms)

    def _get_render_context(
        self,
        results: "EvaluationResults",
        title: Optional[str] = None,
        max_detailed_results: int = 50,
    ) -> dict:
        """Build the template rendering context.

        Args:
            results: EvaluationResults to render
            title: Optional title override
            max_detailed_results: Maximum number of detailed results to include

        Returns:
            Dictionary context for Jinja2 template rendering
        """
        return {
            "results": results.results[:max_detailed_results] if results.results else [],
            "all_results": results.results,
            "summary": results.summary,
            "title": title or "Genie Evaluation Report",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_results": len(results.results) if results.results else 0,
            "max_detailed_results": max_detailed_results,
            "truncated": len(results.results) > max_detailed_results if results.results else False,
        }

    def generate_markdown(
        self,
        results: "EvaluationResults",
        title: Optional[str] = None,
        max_detailed_results: int = 50,
    ) -> str:
        """Generate a Markdown report from evaluation results.

        Args:
            results: EvaluationResults to convert to Markdown
            title: Optional title for the report
            max_detailed_results: Maximum detailed results to include

        Returns:
            Formatted Markdown string
        """
        template = self.md_template_env.get_template("evaluation_report.md.jinja2")
        return template.render(**self._get_render_context(results, title, max_detailed_results))

    def generate_html(
        self,
        results: "EvaluationResults",
        title: Optional[str] = None,
        max_detailed_results: int = 50,
    ) -> str:
        """Generate an HTML dashboard from evaluation results.

        Args:
            results: EvaluationResults to convert to HTML
            title: Optional title for the dashboard
            max_detailed_results: Maximum detailed results to include

        Returns:
            Complete HTML document string
        """
        template = self.html_template_env.get_template("evaluation_report.html.jinja2")
        return template.render(**self._get_render_context(results, title, max_detailed_results))

    def generate_json(
        self,
        results: "EvaluationResults",
        pretty: bool = True,
    ) -> str:
        """Generate a JSON export of evaluation results.

        Args:
            results: EvaluationResults to convert to JSON
            pretty: If True, format with indentation

        Returns:
            JSON string
        """
        data = results.to_dict()
        data["generated_at"] = datetime.now().isoformat()

        if pretty:
            return json.dumps(data, indent=2, default=str)
        return json.dumps(data, default=str)

    def save_reports(
        self,
        results: "EvaluationResults",
        output_dir: str,
        formats: Optional[list[str]] = None,
        filename_prefix: str = "evaluation",
        title: Optional[str] = None,
        max_detailed_results: int = 50,
    ) -> dict[str, Path]:
        """Save reports in multiple formats to files.

        Creates the output directory if it doesn't exist. Files are named
        with the prefix and a timestamp to ensure uniqueness.

        Args:
            results: EvaluationResults to save
            output_dir: Directory to save reports in
            formats: List of formats to generate ("md", "html", "json")
            filename_prefix: Prefix for output filenames
            title: Optional title for the reports
            max_detailed_results: Maximum detailed results to include

        Returns:
            Dictionary mapping format to saved file path
        """
        formats = formats or ["md", "html", "json"]
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        saved_files: dict[str, Path] = {}

        for fmt in formats:
            if fmt == "md":
                content = self.generate_markdown(results, title, max_detailed_results)
                file_path = output_path / f"{filename_prefix}_{timestamp}.md"
                file_path.write_text(content, encoding="utf-8")
                saved_files["md"] = file_path

            elif fmt == "html":
                content = self.generate_html(results, title, max_detailed_results)
                file_path = output_path / f"{filename_prefix}_{timestamp}.html"
                file_path.write_text(content, encoding="utf-8")
                saved_files["html"] = file_path

            elif fmt == "json":
                content = self.generate_json(results)
                file_path = output_path / f"{filename_prefix}_{timestamp}.json"
                file_path.write_text(content, encoding="utf-8")
                saved_files["json"] = file_path

        return saved_files
