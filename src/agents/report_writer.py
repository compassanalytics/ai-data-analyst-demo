"""Report Writer - Generate Markdown and HTML reports from synthesis results.

This module provides a ReportWriter class for generating formatted reports
from SynthesisResult objects. Supports both Markdown and HTML (dashboard) outputs
with Jinja2 templates.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from src.config import Config

if TYPE_CHECKING:
    from src.agents.synthesizer_agent import SynthesisResult


@dataclass
class ReportConfig:
    """Configuration for report generation.

    Attributes:
        title: Optional title for the report (defaults to generic title)
        include_timestamp: Whether to include generation timestamp
        max_table_rows: Maximum rows to display in tables
    """

    title: Optional[str] = None
    include_timestamp: bool = True
    max_table_rows: int = 10


class ReportWriter:
    """Generate Markdown and HTML reports from SynthesisResult.

    Provides template-based report generation with lazy-loaded Jinja2 environments.
    HTML templates use autoescape for security (content may come from LLM).

    Example:
        >>> from src.agents.synthesizer_agent import SynthesizerAgent, SynthesisResult
        >>> from src.config import Config
        >>> config = Config(mock_mode=True)
        >>> writer = ReportWriter(config)
        >>> # Assuming you have a SynthesisResult object
        >>> markdown = writer.generate_markdown(result, title="Q4 Analysis")
        >>> html = writer.generate_html(result, title="Q4 Dashboard")
    """

    def __init__(
        self,
        config: Config,
        report_config: Optional[ReportConfig] = None,
    ) -> None:
        """Initialize the ReportWriter.

        Args:
            config: Application configuration instance
            report_config: Optional report configuration (defaults to ReportConfig())
        """
        self.config = config
        self.report_config = report_config or ReportConfig()
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
        env.filters["format_number"] = self._format_number
        env.filters["format_currency"] = self._format_currency

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
    def _format_currency(value, symbol: str = "$") -> str:
        """Format a number as currency with abbreviations for large values.

        Args:
            value: Number to format
            symbol: Currency symbol to use

        Returns:
            Formatted currency string (e.g., "$1.5M", "$500K", "$123.45")
        """
        try:
            if value >= 1_000_000:
                return f"{symbol}{value / 1_000_000:.1f}M"
            elif value >= 1_000:
                return f"{symbol}{value / 1_000:.1f}K"
            return f"{symbol}{value:,.2f}"
        except (ValueError, TypeError):
            return str(value)

    def _get_render_context(
        self,
        result: "SynthesisResult",
        title: Optional[str] = None,
    ) -> dict:
        """Build the template rendering context.

        Args:
            result: SynthesisResult to render
            title: Optional title override

        Returns:
            Dictionary context for Jinja2 template rendering
        """
        return {
            "result": result,
            "title": title or self.report_config.title,
            "generated_at": (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if self.report_config.include_timestamp
                else ""
            ),
            "config": self.report_config,
        }

    def generate_markdown(
        self,
        result: "SynthesisResult",
        title: Optional[str] = None,
    ) -> str:
        """Generate a Markdown report from a SynthesisResult.

        Args:
            result: SynthesisResult to convert to Markdown
            title: Optional title for the report

        Returns:
            Formatted Markdown string
        """
        template = self.md_template_env.get_template("report.md.jinja2")
        return template.render(**self._get_render_context(result, title))

    def generate_html(
        self,
        result: "SynthesisResult",
        title: Optional[str] = None,
    ) -> str:
        """Generate an HTML dashboard from a SynthesisResult.

        Args:
            result: SynthesisResult to convert to HTML
            title: Optional title for the dashboard

        Returns:
            Complete HTML document string
        """
        template = self.html_template_env.get_template("dashboard.html.jinja2")
        return template.render(**self._get_render_context(result, title))

    def save_report(
        self,
        result: "SynthesisResult",
        output_dir: str,
        filename_prefix: str = "report",
        title: Optional[str] = None,
    ) -> tuple[Path, Path]:
        """Save both Markdown and HTML reports to files.

        Creates the output directory if it doesn't exist. Files are named
        with the prefix and a timestamp to ensure uniqueness.

        Args:
            result: SynthesisResult to save
            output_dir: Directory to save reports in
            filename_prefix: Prefix for output filenames
            title: Optional title for the reports

        Returns:
            Tuple of (markdown_path, html_path) for the saved files
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Generate and save Markdown
        md_content = self.generate_markdown(result, title)
        md_path = output_path / f"{filename_prefix}_{timestamp}.md"
        md_path.write_text(md_content, encoding="utf-8")

        # Generate and save HTML
        html_content = self.generate_html(result, title)
        html_path = output_path / f"{filename_prefix}_{timestamp}.html"
        html_path.write_text(html_content, encoding="utf-8")

        return md_path, html_path
