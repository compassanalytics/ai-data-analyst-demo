"""Benchmark comparison report generator.

This module provides report generation capabilities for benchmark comparisons,
supporting Markdown, HTML, and JSON output formats with customizable templates.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .models import BenchmarkComparison


class BenchmarkReporter:
    """Generate benchmark comparison reports.

    Follows EvaluationReporter patterns with lazy-loaded Jinja2 environments.
    HTML templates use autoescape for security (content may come from LLM).

    Example:
        >>> from src.benchmark.models import BenchmarkComparison
        >>> reporter = BenchmarkReporter()
        >>> markdown = reporter.generate_markdown(comparison, title="Q4 Benchmark")
        >>> html = reporter.generate_html(comparison, title="Q4 Dashboard")
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

        Includes delta formatting filters for benchmark comparisons.

        Args:
            env: Jinja2 Environment to add filters to
        """
        env.filters["format_percent"] = self._format_percent
        env.filters["format_number"] = self._format_number
        env.filters["format_duration"] = self._format_duration
        env.filters["format_delta"] = self._format_delta
        env.filters["delta_class"] = self._delta_class
        env.filters["abs"] = abs

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
            return f"{float(value):.{decimals}f}%"
        except (TypeError, ValueError):
            return str(value)

    @staticmethod
    def _format_number(value: float, decimals: int = 0) -> str:
        """Format a number with thousands separators.

        Args:
            value: Number to format
            decimals: Number of decimal places

        Returns:
            Formatted number string with thousands separators
        """
        try:
            if decimals == 0:
                return f"{int(value):,}"
            return f"{float(value):,.{decimals}f}"
        except (TypeError, ValueError):
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
        except (TypeError, ValueError):
            return str(ms)

    @staticmethod
    def _format_delta(value: float) -> str:
        """Format delta value with +/- sign.

        Args:
            value: Delta value to format

        Returns:
            Formatted delta string with sign (e.g., "+5.2%", "-3.1%")
        """
        try:
            if value > 0:
                return f"+{value:.1f}%"
            return f"{value:.1f}%"
        except (TypeError, ValueError):
            return str(value)

    @staticmethod
    def _delta_class(value: float) -> str:
        """Return CSS class based on delta direction.

        Args:
            value: Delta value to classify

        Returns:
            CSS class name: "improvement", "regression", or "unchanged"
        """
        try:
            if value > 0:
                return "improvement"
            elif value < 0:
                return "regression"
            return "unchanged"
        except (TypeError, ValueError):
            return "unchanged"

    def _get_render_context(
        self,
        comparison: BenchmarkComparison,
        title: str | None = None,
    ) -> dict[str, Any]:
        """Build the template rendering context.

        Args:
            comparison: BenchmarkComparison to render
            title: Optional title override

        Returns:
            Dictionary context for Jinja2 template rendering
        """
        return {
            "comparison": comparison,
            "baseline": comparison.baseline,
            "enhanced": comparison.enhanced,
            "accuracy_delta": comparison.accuracy_delta,
            "accuracy_delta_percent": comparison.accuracy_delta_percent,
            "category_improvements": comparison.category_improvements,
            "regressions": comparison.regressions,
            "improvements": comparison.improvements,
            "unchanged": comparison.unchanged,
            "title": title or "Benchmark Comparison Report",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "has_regressions": comparison.has_regressions(),
            "total_queries": len(comparison.baseline.results) if comparison.baseline.results else 0,
        }

    def generate_markdown(
        self,
        comparison: BenchmarkComparison,
        title: str | None = None,
    ) -> str:
        """Generate a Markdown report from benchmark comparison.

        Args:
            comparison: BenchmarkComparison to convert to Markdown
            title: Optional title for the report

        Returns:
            Formatted Markdown string
        """
        template = self.md_template_env.get_template("benchmark_report.md.jinja2")
        context = self._get_render_context(comparison, title)
        return template.render(**context)

    def generate_html(
        self,
        comparison: BenchmarkComparison,
        title: str | None = None,
    ) -> str:
        """Generate an HTML dashboard from benchmark comparison.

        Args:
            comparison: BenchmarkComparison to convert to HTML
            title: Optional title for the dashboard

        Returns:
            Complete HTML document string
        """
        template = self.html_template_env.get_template("benchmark_report.html.jinja2")
        context = self._get_render_context(comparison, title)
        return template.render(**context)

    def generate_json(
        self,
        comparison: BenchmarkComparison,
        pretty: bool = True,
    ) -> str:
        """Generate a JSON export of benchmark comparison.

        Args:
            comparison: BenchmarkComparison to convert to JSON
            pretty: If True, format with indentation

        Returns:
            JSON string
        """
        data = comparison.to_dict()
        data["generated_at"] = datetime.now().isoformat()

        if pretty:
            return json.dumps(data, indent=2, default=str)
        return json.dumps(data, default=str)

    def save_reports(
        self,
        comparison: BenchmarkComparison,
        output_dir: str | Path,
        formats: list[str] | None = None,
        filename_prefix: str = "benchmark",
        title: str | None = None,
    ) -> dict[str, Path]:
        """Save reports in multiple formats to files.

        Creates the output directory if it doesn't exist. Files are named
        with the prefix and a timestamp to ensure uniqueness.

        Args:
            comparison: BenchmarkComparison to save
            output_dir: Directory to save reports in
            formats: List of formats to generate ("md", "html", "json")
            filename_prefix: Prefix for output filenames
            title: Optional title for the reports

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
                content = self.generate_markdown(comparison, title)
                file_path = output_path / f"{filename_prefix}_{timestamp}.md"
                file_path.write_text(content, encoding="utf-8")
                saved_files["md"] = file_path

            elif fmt == "html":
                content = self.generate_html(comparison, title)
                file_path = output_path / f"{filename_prefix}_{timestamp}.html"
                file_path.write_text(content, encoding="utf-8")
                saved_files["html"] = file_path

            elif fmt == "json":
                content = self.generate_json(comparison)
                file_path = output_path / f"{filename_prefix}_{timestamp}.json"
                file_path.write_text(content, encoding="utf-8")
                saved_files["json"] = file_path

        return saved_files
