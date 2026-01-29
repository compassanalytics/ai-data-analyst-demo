"""Progressive difficulty benchmark report generator.

This module provides report generation for tiered benchmark results,
with support for Markdown, HTML, and JSON output formats.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .suite import TieredBenchmarkResult

# Tier name mapping
TIER_NAMES = {1: "Simple", 2: "Moderate", 3: "Complex", 4: "Expert", 5: "Adversarial"}


class ProgressiveReporter:
    """Generate tier-by-tier accuracy reports with visualization.

    Follows BenchmarkReporter patterns with lazy-loaded Jinja2 environments.
    HTML templates use autoescape for security.

    Example:
        >>> reporter = ProgressiveReporter()
        >>> markdown = reporter.generate_markdown(result, title="Q4 Progressive")
        >>> html = reporter.generate_html(result, title="Q4 Dashboard")
    """

    def __init__(self) -> None:
        """Initialize the reporter."""
        self._md_env = None
        self._html_env = None

    @property
    def md_template_env(self):
        """Lazy-load Markdown Jinja2 environment (NO autoescape).

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

        Returns:
            Jinja2 Environment configured for HTML templates with autoescape
        """
        if self._html_env is None:
            import jinja2

            self._html_env = jinja2.Environment(
                loader=jinja2.PackageLoader("src", "templates"),
                autoescape=True,  # Security: escape content
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
        env.filters["tier_name"] = self._tier_name
        env.filters["accuracy_class"] = self._accuracy_class
        env.filters["format_number"] = self._format_number
        env.filters["progress_bar"] = self._progress_bar
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
    def _tier_name(tier: int) -> str:
        """Get human-readable tier name.

        Args:
            tier: Tier number (1-5)

        Returns:
            Tier name string
        """
        return TIER_NAMES.get(tier, f"Tier {tier}")

    @staticmethod
    def _accuracy_class(value: float) -> str:
        """Return CSS class based on accuracy level.

        Args:
            value: Accuracy value (0-100)

        Returns:
            CSS class name: "accuracy-high", "accuracy-medium", "accuracy-low"
        """
        try:
            if value >= 80:
                return "accuracy-high"
            elif value >= 50:
                return "accuracy-medium"
            return "accuracy-low"
        except (TypeError, ValueError):
            return "accuracy-low"

    @staticmethod
    def _format_number(value: float, decimals: int = 0) -> str:
        """Format a number with thousands separators.

        Args:
            value: Number to format
            decimals: Number of decimal places

        Returns:
            Formatted number string
        """
        try:
            if decimals == 0:
                return f"{int(value):,}"
            return f"{float(value):,.{decimals}f}"
        except (TypeError, ValueError):
            return str(value)

    @staticmethod
    def _progress_bar(value: float, width: int = 20) -> str:
        """Generate ASCII progress bar.

        Args:
            value: Percentage value (0-100)
            width: Total width of progress bar

        Returns:
            ASCII progress bar string
        """
        try:
            value = min(100, max(0, float(value)))
            filled = int(value / 100 * width)
            empty = width - filled
            return "[" + "#" * filled + "-" * empty + "]"
        except (TypeError, ValueError):
            return "[" + "-" * width + "]"

    def _get_render_context(
        self,
        result: TieredBenchmarkResult,
        title: str | None = None,
    ) -> dict[str, Any]:
        """Build the template rendering context.

        Args:
            result: TieredBenchmarkResult to render
            title: Optional title override

        Returns:
            Dictionary context for Jinja2 template rendering
        """
        # Build tier data for charts
        tier_data = []
        for tier in range(1, 6):
            tr = result.tier_results.get(tier)
            if tr:
                tier_data.append(
                    {
                        "tier": tier,
                        "name": TIER_NAMES.get(tier, f"Tier {tier}"),
                        "accuracy": round(tr.accuracy, 1),
                        "queries": tr.queries_count,
                        "correct": tr.correct_count,
                        "partial": tr.partial_count,
                        "wrong": tr.wrong_count,
                        "failed": tr.failed_count,
                    }
                )

        return {
            "result": result,
            "tier_results": result.tier_results,
            "tier_data": tier_data,
            "overall_accuracy": result.overall_accuracy,
            "capability_score": result.capability_score,
            "safety_score": result.safety_score,
            "total_queries": result.total_queries,
            "title": title or "Progressive Difficulty Benchmark Report",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "tier_names": TIER_NAMES,
        }

    def generate_markdown(
        self,
        result: TieredBenchmarkResult,
        title: str | None = None,
    ) -> str:
        """Generate a Markdown report from benchmark result.

        Args:
            result: TieredBenchmarkResult to convert to Markdown
            title: Optional title for the report

        Returns:
            Formatted Markdown string
        """
        template = self.md_template_env.get_template("progressive_report.md.jinja2")
        context = self._get_render_context(result, title)
        return template.render(**context)

    def generate_html(
        self,
        result: TieredBenchmarkResult,
        title: str | None = None,
    ) -> str:
        """Generate an HTML dashboard from benchmark result.

        Args:
            result: TieredBenchmarkResult to convert to HTML
            title: Optional title for the dashboard

        Returns:
            Complete HTML document string
        """
        template = self.html_template_env.get_template("progressive_report.html.jinja2")
        context = self._get_render_context(result, title)
        return template.render(**context)

    def generate_json(
        self,
        result: TieredBenchmarkResult,
        pretty: bool = True,
    ) -> str:
        """Generate a JSON export of benchmark result.

        Args:
            result: TieredBenchmarkResult to convert to JSON
            pretty: If True, format with indentation

        Returns:
            JSON string
        """
        data = result.to_dict()
        data["generated_at"] = datetime.now().isoformat()

        # Add computed summary fields
        data["summary"] = {
            "overall_accuracy": result.overall_accuracy,
            "capability_score": result.capability_score,
            "safety_score": result.safety_score,
            "total_queries": result.total_queries,
            "tier_breakdown": {
                tier: {
                    "name": TIER_NAMES.get(tier, f"Tier {tier}"),
                    "accuracy": tr.accuracy,
                    "queries": tr.queries_count,
                }
                for tier, tr in result.tier_results.items()
                if tr.queries_count > 0
            },
        }

        if pretty:
            return json.dumps(data, indent=2, default=str)
        return json.dumps(data, default=str)

    def save_reports(
        self,
        result: TieredBenchmarkResult,
        output_dir: str | Path,
        formats: list[str] | None = None,
        filename_prefix: str = "progressive",
        title: str | None = None,
    ) -> dict[str, Path]:
        """Save reports in multiple formats to files.

        Args:
            result: TieredBenchmarkResult to save
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
                content = self.generate_markdown(result, title)
                file_path = output_path / f"{filename_prefix}_{timestamp}.md"
                file_path.write_text(content, encoding="utf-8")
                saved_files["md"] = file_path

            elif fmt == "html":
                content = self.generate_html(result, title)
                file_path = output_path / f"{filename_prefix}_{timestamp}.html"
                file_path.write_text(content, encoding="utf-8")
                saved_files["html"] = file_path

            elif fmt == "json":
                content = self.generate_json(result)
                file_path = output_path / f"{filename_prefix}_{timestamp}.json"
                file_path.write_text(content, encoding="utf-8")
                saved_files["json"] = file_path

        return saved_files
