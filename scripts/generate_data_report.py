#!/usr/bin/env python
"""Generate interactive HTML report for Velocity Motors dataset.

Reads parquet files from the generated dataset and produces a self-contained
HTML report with interactive Plotly charts across six analytical dimensions.

Usage:
    uv run python scripts/generate_data_report.py
    uv run python scripts/generate_data_report.py --data-dir data/velocity_motors
    uv run python scripts/generate_data_report.py --data-dir data/velocity_motors --output report.html
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

CORE_MAKES = ["Ford", "Toyota", "Honda", "Chevrolet", "BMW", "Mercedes-Benz"]

PLOTLY_CDN = "https://cdn.plot.ly/plotly-2.35.2.min.js"


def load_table(data_dir: Path, name: str) -> pd.DataFrame | None:
    """Load a parquet table, returning None if it doesn't exist."""
    path = data_dir / f"{name}.parquet"
    if not path.exists():
        print(f"  Warning: {path} not found, skipping related sections")
        return None
    df = pd.read_parquet(path)
    print(f"  Loaded {name}: {len(df):,} rows")
    return df


def format_currency(value: float) -> str:
    """Format a dollar value for display."""
    if value >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"${value / 1_000:.0f}k"
    return f"${value:,.0f}"


def build_summary_stats(
    orders: pd.DataFrame,
    salespersons: pd.DataFrame | None,
    vehicles: pd.DataFrame | None,
    territories: pd.DataFrame | None,
) -> str:
    """Build summary statistics as HTML metric cards."""
    orders = orders.copy()
    orders["order_date"] = pd.to_datetime(orders["order_date"])
    valid_totals = orders["order_total"].dropna()
    valid_totals = valid_totals[valid_totals > 0]

    metrics = [
        ("Total Orders", f"{len(orders):,}"),
        ("Total Revenue", format_currency(valid_totals.sum())),
        ("Avg Deal Value", format_currency(valid_totals.mean()) if len(valid_totals) > 0 else "N/A"),
        (
            "Date Range",
            f"{orders['order_date'].min().strftime('%b %Y')} — {orders['order_date'].max().strftime('%b %Y')}",
        ),
    ]

    if salespersons is not None:
        metrics.append(("Salespeople", f"{salespersons['salesperson_id'].nunique():,}"))
    if vehicles is not None:
        n_models = vehicles.groupby(["make", "model"]).ngroups
        metrics.append(("Vehicle Models", f"{n_models:,}"))
    if territories is not None:
        active = territories[territories["is_active"] == True] if "is_active" in territories.columns else territories  # noqa: E712
        metrics.append(("Territories", f"{len(active):,}"))

    cards_html = ""
    for label, value in metrics:
        cards_html += f"""
        <div style="flex:1; min-width:140px; background:#f8f9fa; border-radius:8px;
                    padding:20px 16px; text-align:center; border:1px solid #e9ecef;">
            <div style="font-size:1.6em; font-weight:700; color:#2c3e50;">{value}</div>
            <div style="font-size:0.85em; color:#6c757d; margin-top:4px;">{label}</div>
        </div>"""

    return f'<div style="display:flex; gap:12px; flex-wrap:wrap;">{cards_html}</div>'


def build_revenue_time_series(orders: pd.DataFrame) -> str | None:
    """Build dual-axis monthly revenue and order volume chart."""
    orders = orders.copy()
    orders["order_date"] = pd.to_datetime(orders["order_date"])
    orders["month"] = orders["order_date"].dt.to_period("M").astype(str)

    # All orders for count
    monthly_counts = orders.groupby("month").size().reset_index(name="order_count")

    # Non-cancelled for revenue
    revenue_orders = orders[orders["status"] != "Cancelled"]
    monthly_revenue = revenue_orders.groupby("month")["order_total"].sum().reset_index()

    monthly = monthly_counts.merge(monthly_revenue, on="month", how="left").fillna(0)
    monthly = monthly.sort_values("month")

    if monthly.empty:
        return None

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(
            x=monthly["month"],
            y=monthly["order_count"],
            name="Order Count",
            marker_color="#3498db",
            opacity=0.7,
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=monthly["month"],
            y=monthly["order_total"],
            name="Revenue",
            mode="lines+markers",
            line={"color": "#e74c3c", "width": 2.5},
            marker={"size": 6},
        ),
        secondary_y=True,
    )

    fig.update_layout(
        title="Monthly Revenue & Order Volume",
        template="plotly_white",
        autosize=True,
        height=450,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
        margin={"l": 60, "r": 60, "t": 80, "b": 60},
    )
    fig.update_yaxes(title_text="Order Count", secondary_y=False)
    fig.update_yaxes(title_text="Revenue ($)", secondary_y=True)

    return fig.to_html(full_html=False, include_plotlyjs=False)


def build_vehicle_model_performance(orders: pd.DataFrame, vehicles: pd.DataFrame) -> str | None:
    """Build quarterly vehicle model performance grouped bar chart."""
    orders = orders.copy()
    orders["order_date"] = pd.to_datetime(orders["order_date"])

    merged = orders.merge(vehicles[["vehicle_id", "make", "model"]], on="vehicle_id", how="inner")
    merged = merged[merged["make"].isin(CORE_MAKES)]

    if merged.empty:
        return None

    merged["quarter"] = merged["order_date"].dt.to_period("Q").astype(str)
    merged["make_model"] = merged["make"] + " " + merged["model"]

    # Order by total volume descending
    model_totals = merged.groupby("make_model").size().sort_values(ascending=False)
    model_order = model_totals.index.tolist()

    grouped = merged.groupby(["make_model", "quarter"]).size().reset_index(name="count")

    fig = px.bar(
        grouped,
        x="make_model",
        y="count",
        color="quarter",
        barmode="group",
        title="Vehicle Model Performance by Quarter",
        labels={"make_model": "Model", "count": "Orders", "quarter": "Quarter"},
        category_orders={"make_model": model_order},
    )

    fig.update_layout(
        template="plotly_white",
        autosize=True,
        height=500,
        xaxis_tickangle=-45,
        margin={"l": 60, "r": 40, "t": 80, "b": 120},
    )

    return fig.to_html(full_html=False, include_plotlyjs=False)


def build_salesperson_performance(orders: pd.DataFrame, salespersons: pd.DataFrame) -> str | None:
    """Build ranked salesperson revenue bar chart."""
    merged = orders.merge(salespersons[["salesperson_id", "name"]], on="salesperson_id", how="inner")
    revenue = merged.groupby("name")["order_total"].sum().reset_index()
    revenue = revenue.sort_values("order_total", ascending=False)

    if revenue.empty:
        return None

    mean_revenue = revenue["order_total"].mean()

    has_tiers = "performance_tier" in salespersons.columns
    if has_tiers:
        tier_map = salespersons.drop_duplicates("name").set_index("name")["performance_tier"]
        revenue["tier"] = revenue["name"].map(tier_map).fillna("unknown")
        color_map = {"top": "#2ecc71", "middle": "#3498db", "bottom": "#e74c3c", "unknown": "#95a5a6"}
        fig = px.bar(
            revenue,
            x="name",
            y="order_total",
            color="tier",
            title="Salesperson Performance — Total Revenue",
            labels={"name": "Salesperson", "order_total": "Revenue ($)", "tier": "Performance Tier"},
            color_discrete_map=color_map,
        )
    else:
        fig = px.bar(
            revenue,
            x="name",
            y="order_total",
            title="Salesperson Performance — Total Revenue",
            labels={"name": "Salesperson", "order_total": "Revenue ($)"},
            color_discrete_sequence=["#3498db"],
        )

    fig.add_hline(
        y=mean_revenue,
        line_dash="dash",
        line_color="#e74c3c",
        annotation_text=f"Mean: {format_currency(mean_revenue)}",
        annotation_position="top right",
    )

    fig.update_layout(
        template="plotly_white",
        autosize=True,
        height=500,
        xaxis_tickangle=-45,
        margin={"l": 60, "r": 40, "t": 80, "b": 140},
    )

    return fig.to_html(full_html=False, include_plotlyjs=False)


def build_territory_comparison(
    orders: pd.DataFrame, salespersons: pd.DataFrame, territories: pd.DataFrame
) -> str | None:
    """Build ranked territory average deal value bar chart."""
    cols = ["salesperson_id", "territory_id"]
    merged = orders.merge(salespersons[cols], on="salesperson_id", how="inner")

    t_cols = ["territory_id", "territory_name", "division_name"]
    has_strength = "market_strength" in territories.columns
    if has_strength:
        t_cols.append("market_strength")

    merged = merged.merge(territories[t_cols], on="territory_id", how="inner")

    if merged.empty:
        return None

    territory_stats = (
        merged.groupby(["territory_name", "division_name"] + (["market_strength"] if has_strength else []))[
            "order_total"
        ]
        .mean()
        .reset_index()
    )
    territory_stats = territory_stats.sort_values("order_total", ascending=False)

    if has_strength:
        territory_stats["market_label"] = territory_stats["market_strength"].map(
            lambda v: "high" if v >= 1.2 else ("low" if v <= 0.8 else "medium")
        )
        color_map = {"high": "#2ecc71", "medium": "#f39c12", "low": "#e74c3c"}
        fig = px.bar(
            territory_stats,
            x="territory_name",
            y="order_total",
            color="market_label",
            title="Territory Comparison — Average Deal Value",
            labels={
                "territory_name": "Territory",
                "order_total": "Avg Deal Value ($)",
                "market_label": "Market Strength",
            },
            color_discrete_map=color_map,
        )
    else:
        fig = px.bar(
            territory_stats,
            x="territory_name",
            y="order_total",
            color="division_name",
            title="Territory Comparison — Average Deal Value",
            labels={"territory_name": "Territory", "order_total": "Avg Deal Value ($)", "division_name": "Division"},
        )

    fig.update_layout(
        template="plotly_white",
        autosize=True,
        height=500,
        xaxis_tickangle=-45,
        margin={"l": 60, "r": 40, "t": 80, "b": 120},
    )

    return fig.to_html(full_html=False, include_plotlyjs=False)


def build_distribution_plots(orders: pd.DataFrame, vehicles: pd.DataFrame | None) -> str | None:
    """Build histogram subplots for key numeric distributions."""
    deal_values = orders["order_total"].dropna()
    deal_values = deal_values[deal_values > 0]

    discounts = orders["discount_amount"].dropna()
    discounts = discounts[discounts > 0]

    has_vehicles = vehicles is not None
    n_cols = 3 if has_vehicles else 2
    titles = ["Deal Values (order_total)", "Discount Distribution"]
    if has_vehicles:
        titles.append("Vehicle MSRP")

    fig = make_subplots(rows=1, cols=n_cols, subplot_titles=titles)

    fig.add_trace(
        go.Histogram(x=deal_values, nbinsx=40, marker_color="#3498db", name="Deal Values"),
        row=1,
        col=1,
    )

    if len(discounts) > 0:
        fig.add_trace(
            go.Histogram(x=discounts, nbinsx=30, marker_color="#2ecc71", name="Discounts"),
            row=1,
            col=2,
        )

    if has_vehicles:
        msrp = vehicles["msrp"].dropna()
        fig.add_trace(
            go.Histogram(x=msrp, nbinsx=30, marker_color="#e74c3c", name="MSRP"),
            row=1,
            col=n_cols,
        )

    fig.update_layout(
        template="plotly_white",
        showlegend=False,
        autosize=True,
        height=400,
        margin={"l": 50, "r": 40, "t": 60, "b": 50},
    )

    return fig.to_html(full_html=False, include_plotlyjs=False)


def build_html(sections: list[tuple[str, str]], data_dir: str) -> str:
    """Assemble the full HTML report."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sections_html = ""
    for title, content in sections:
        sections_html += f"""
    <section style="margin-bottom:40px; padding-bottom:32px; border-bottom:1px solid #e9ecef;">
        <h2 style="color:#2c3e50; font-size:1.4em; margin-bottom:16px;">{title}</h2>
        {content}
    </section>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Velocity Motors — Data Distribution Report</title>
    <script src="{PLOTLY_CDN}"></script>
    <style>
        body {{
            font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 24px;
            background: #fff;
            color: #333;
            line-height: 1.5;
        }}
        header {{
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 2px solid #2c3e50;
        }}
        header h1 {{
            color: #2c3e50;
            font-size: 2em;
            margin: 0 0 8px 0;
        }}
        header p {{
            color: #6c757d;
            margin: 2px 0;
            font-size: 0.9em;
        }}
        footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e9ecef;
            color: #6c757d;
            font-size: 0.85em;
        }}
        footer code {{
            background: #f8f9fa;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.9em;
        }}
        .js-plotly-plot {{
            width: 100% !important;
        }}
    </style>
</head>
<body>
    <header>
        <h1>Velocity Motors — Data Distribution Report</h1>
        <p>Generated: {now}</p>
        <p>Data directory: <code>{data_dir}</code></p>
    </header>
    <main>
        {sections_html}
    </main>
    <footer>
        <p>Regenerate this report: <code>uv run python scripts/generate_data_report.py --data-dir {data_dir}</code></p>
        <p>Charts require an internet connection to load the Plotly library from CDN.
           For offline use, regenerate with the plotly JS bundled inline.</p>
    </footer>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser(
        description="Generate interactive HTML report for Velocity Motors dataset",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run python scripts/generate_data_report.py
  uv run python scripts/generate_data_report.py --data-dir data/velocity_motors
  uv run python scripts/generate_data_report.py --data-dir data/velocity_motors --output report.html
        """,
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("./dataset_generators/data/velocity_motors"),
        help="Directory containing parquet files (default: ./dataset_generators/data/velocity_motors)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output HTML file path (default: {data_dir}/report.html)",
    )
    args = parser.parse_args()

    data_dir = args.data_dir
    output_path = args.output or (data_dir / "report.html")

    if not data_dir.exists():
        print(f"Error: Data directory not found: {data_dir}")
        print("Generate data first: uv run python dataset_generators/generate_velocity_motors.py")
        sys.exit(1)

    print(f"Loading data from {data_dir}...")
    orders = load_table(data_dir, "orders")
    salespersons = load_table(data_dir, "salespersons")
    vehicles = load_table(data_dir, "vehicles")
    territories = load_table(data_dir, "territories")

    if orders is None:
        print("Error: orders.parquet is required but not found.")
        print("Generate data first: uv run python dataset_generators/generate_velocity_motors.py")
        sys.exit(1)

    sections: list[tuple[str, str]] = []

    # Section 1: Summary Statistics
    print("Building summary statistics...")
    try:
        summary = build_summary_stats(orders, salespersons, vehicles, territories)
        if summary:
            sections.append(("Summary Statistics", summary))
    except Exception as e:
        print(f"  Warning: summary statistics failed: {e}")

    # Section 2: Revenue & Orders Time Series
    print("Building revenue time series...")
    try:
        revenue_chart = build_revenue_time_series(orders)
        if revenue_chart:
            sections.append(("Revenue & Orders by Month", revenue_chart))
    except Exception as e:
        print(f"  Warning: revenue time series failed: {e}")

    # Section 3: Vehicle Model Performance
    if vehicles is not None:
        print("Building vehicle model performance...")
        try:
            model_chart = build_vehicle_model_performance(orders, vehicles)
            if model_chart:
                sections.append(("Vehicle Model Performance (Quarterly)", model_chart))
        except Exception as e:
            print(f"  Warning: vehicle model performance failed: {e}")

    # Section 4: Salesperson Performance
    if salespersons is not None:
        print("Building salesperson performance...")
        try:
            sp_chart = build_salesperson_performance(orders, salespersons)
            if sp_chart:
                sections.append(("Salesperson Performance Distribution", sp_chart))
        except Exception as e:
            print(f"  Warning: salesperson performance failed: {e}")

    # Section 5: Territory Comparison
    if salespersons is not None and territories is not None:
        print("Building territory comparison...")
        try:
            territory_chart = build_territory_comparison(orders, salespersons, territories)
            if territory_chart:
                sections.append(("Territory Comparison — Deal Value", territory_chart))
        except Exception as e:
            print(f"  Warning: territory comparison failed: {e}")

    # Section 6: Distribution Plots
    print("Building distribution plots...")
    try:
        dist_chart = build_distribution_plots(orders, vehicles)
        if dist_chart:
            sections.append(("Numeric Distributions", dist_chart))
    except Exception as e:
        print(f"  Warning: distribution plots failed: {e}")

    # Assemble and write HTML
    print("Assembling report...")
    html = build_html(sections, str(data_dir))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)

    print(f"\nReport generated: {output_path}")
    print(f"  Sections: {len(sections)}")
    print("  Open in browser to view interactive charts")


if __name__ == "__main__":
    main()
