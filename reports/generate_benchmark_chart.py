"""Generate Altair-style benchmark results charts for Genie Space evaluation."""

import altair as alt
import pandas as pd
from pathlib import Path

# ---------------------------------------------------------------------------
# Color palette
# ---------------------------------------------------------------------------
GREEN = "#59a14f"
BLUE = "#4c78a8"
AMBER = "#e89a3e"
RED = "#e15759"
TEAL = "#76b7b2"
GRAY = "#98a2ab"
TEXT_DARK = "#2d3436"
TEXT_MID = "#636e72"
TEXT_LIGHT = "#95a5a6"

# ---------------------------------------------------------------------------
# Shared Altair config helper
# ---------------------------------------------------------------------------
def style(chart):
    return (
        chart
        .configure(font="Helvetica Neue, Helvetica, Arial, sans-serif")
        .configure_view(strokeWidth=0)
        .configure_axis(
            grid=True,
            gridColor="#eeeeee",
            gridDash=[2, 4],
            domainColor="#cccccc",
            tickColor="#cccccc",
            labelColor=TEXT_MID,
            labelFontSize=11,
            titleColor=TEXT_DARK,
            titleFontSize=11,
            titleFontWeight="normal",
        )
        .configure_title(
            fontSize=14,
            fontWeight="bold",
            color=TEXT_DARK,
            anchor="start",
            offset=10,
        )
        .configure_legend(
            labelFontSize=11,
            symbolSize=80,
            titleFontSize=0,
            orient="top",
        )
    )


# ====================================================================
# Chart 1 — Score Distribution (stacked bar)
# ====================================================================
score_df = pd.DataFrame([
    {"Score": "Correct (40)", "Count": 40, "order": 1},
    {"Score": "Partial (7)", "Count": 7, "order": 2},
    {"Score": "Wrong (3)", "Count": 3, "order": 3},
])

c1_bar = (
    alt.Chart(score_df)
    .mark_bar(cornerRadiusEnd=4, height=40)
    .encode(
        x=alt.X("Count:Q", stack="zero",
                 title="Number of Questions",
                 scale=alt.Scale(domain=[0, 52]),
                 axis=alt.Axis(tickCount=6)),
        color=alt.Color(
            "Score:N",
            scale=alt.Scale(
                domain=["Correct (40)", "Partial (7)", "Wrong (3)"],
                range=[GREEN, AMBER, RED],
            ),
            legend=alt.Legend(direction="horizontal", orient="top"),
        ),
        order="order:Q",
        tooltip=["Score:N", "Count:Q"],
    )
    .properties(width=450, height=65, title="Score Distribution (n = 50)")
)

c1 = style(c1_bar)


# ====================================================================
# Chart 2 — Accuracy by Complexity (grouped bar)
# ====================================================================
comp_order = ["Simple", "Moderate", "Complex", "Expert"]
complexity_df = pd.DataFrame([
    {"Complexity": "Simple",   "Metric": "Strict",       "Accuracy": 85.0},
    {"Complexity": "Simple",   "Metric": "With Partial",  "Accuracy": 90.0},
    {"Complexity": "Moderate", "Metric": "Strict",       "Accuracy": 73.3},
    {"Complexity": "Moderate", "Metric": "With Partial",  "Accuracy": 83.3},
    {"Complexity": "Complex",  "Metric": "Strict",       "Accuracy": 80.0},
    {"Complexity": "Complex",  "Metric": "With Partial",  "Accuracy": 85.0},
    {"Complexity": "Expert",   "Metric": "Strict",       "Accuracy": 80.0},
    {"Complexity": "Expert",   "Metric": "With Partial",  "Accuracy": 90.0},
])

c2_bars = (
    alt.Chart(complexity_df)
    .mark_bar(cornerRadiusEnd=4)
    .encode(
        y=alt.Y("Complexity:N", sort=comp_order, title=None),
        x=alt.X("Accuracy:Q", title="Accuracy %",
                 scale=alt.Scale(domain=[0, 100]),
                 axis=alt.Axis(tickCount=6)),
        color=alt.Color(
            "Metric:N",
            scale=alt.Scale(
                domain=["Strict", "With Partial"],
                range=[BLUE, GREEN],
            ),
            legend=alt.Legend(direction="horizontal", orient="top"),
        ),
        yOffset=alt.YOffset("Metric:N"),
        tooltip=["Complexity:N", "Metric:N", alt.Tooltip("Accuracy:Q", format=".1f")],
    )
    .properties(width=350, height=180, title="Accuracy by Complexity Level")
)

c2_labels = (
    alt.Chart(complexity_df)
    .mark_text(dx=14, fontSize=11, fontWeight="bold", color=TEXT_MID)
    .encode(
        y=alt.Y("Complexity:N", sort=comp_order),
        x="Accuracy:Q",
        text=alt.Text("Accuracy:Q", format=".0f"),
        yOffset=alt.YOffset("Metric:N"),
    )
)

c2 = style(c2_bars + c2_labels)


# ====================================================================
# Chart 3 — Accuracy by Category (horizontal bar, color-coded)
# ====================================================================
cat_rows = [
    ("Business Logic",        100.0, 8),
    ("Temporal Confusion",    100.0, 5),
    ("Aggregation Ambiguity", 95.5,  11),
    ("Cryptic Codes",         87.5,  8),
    ("Trick Questions",       80.0,  5),
    ("Join Complexity",       70.0,  10),
    ("Ambiguous Columns",     66.7,  3),
]
cat_df = pd.DataFrame(cat_rows, columns=["Category", "Accuracy", "n"])
cat_df["Tier"] = cat_df["Accuracy"].apply(
    lambda v: "High (>= 90%)" if v >= 90 else ("Mid (>= 70%)" if v >= 70 else "Low (< 70%)")
)
# Sort index for Altair (descending accuracy)
cat_sort = cat_df.sort_values("Accuracy", ascending=False)["Category"].tolist()

c3_bars = (
    alt.Chart(cat_df)
    .mark_bar(cornerRadiusEnd=4)
    .encode(
        y=alt.Y("Category:N", sort=cat_sort, title=None),
        x=alt.X("Accuracy:Q",
                 title="Accuracy % (with partial credit)",
                 scale=alt.Scale(domain=[0, 110]),
                 axis=alt.Axis(tickCount=6)),
        color=alt.Color(
            "Tier:N",
            scale=alt.Scale(
                domain=["High (>= 90%)", "Mid (>= 70%)", "Low (< 70%)"],
                range=[GREEN, AMBER, RED],
            ),
            legend=alt.Legend(direction="horizontal", orient="top"),
        ),
        tooltip=["Category:N", alt.Tooltip("Accuracy:Q", format=".1f"), "n:Q"],
    )
    .properties(width=350, height=220, title="Accuracy by Failure Category")
)

c3_pct = (
    alt.Chart(cat_df)
    .mark_text(dx=18, fontSize=12, fontWeight="bold", color=TEXT_MID)
    .encode(
        y=alt.Y("Category:N", sort=cat_sort),
        x="Accuracy:Q",
        text=alt.Text("pct_label:N"),
    )
    .transform_calculate(
        pct_label="datum.Accuracy == 100 ? '100%' : format(datum.Accuracy, '.1f') + '%'"
    )
)

c3_n = (
    alt.Chart(cat_df)
    .mark_text(dx=48, fontSize=10, color=TEXT_LIGHT)
    .encode(
        y=alt.Y("Category:N", sort=cat_sort),
        x="Accuracy:Q",
        text=alt.Text("n_label:N"),
    )
    .transform_calculate(n_label="'n=' + datum.n")
)

c3 = style(c3_bars + c3_pct + c3_n)


# ====================================================================
# Chart 4 — Key Metrics (text panel)
# ====================================================================
metrics = pd.DataFrame([
    {"row": 0, "value": "80%",   "label": "Overall Accuracy",    "clr": GREEN},
    {"row": 1, "value": "87%",   "label": "With Partial Credit", "clr": TEAL},
    {"row": 2, "value": "92%",   "label": "SQL Generation Rate", "clr": BLUE},
    {"row": 3, "value": "0",     "label": "Failures",            "clr": GREEN},
    {"row": 4, "value": "15.4s", "label": "Avg Response Time",   "clr": TEXT_MID},
])

c4_vals = (
    alt.Chart(metrics)
    .mark_text(fontSize=32, fontWeight="bold")
    .encode(
        y=alt.Y("row:O", axis=None, sort="ascending",
                 scale=alt.Scale(padding=0.4)),
        text="value:N",
        color=alt.Color("clr:N", scale=None),
    )
)

c4_labels = (
    alt.Chart(metrics)
    .mark_text(fontSize=12, dy=26, color=TEXT_LIGHT)
    .encode(
        y=alt.Y("row:O", axis=None, sort="ascending"),
        text="label:N",
    )
)

c4 = (
    (c4_vals + c4_labels)
    .properties(width=280, height=280, title="Key Metrics")
    .configure(font="Helvetica Neue, Helvetica, Arial, sans-serif")
    .configure_view(strokeWidth=0.5, stroke="#dddddd")
    .configure_title(
        fontSize=14,
        fontWeight="bold",
        color=TEXT_DARK,
        anchor="start",
        offset=10,
    )
)


# ====================================================================
# Save each panel individually, then compose with PIL
# ====================================================================
out_dir = Path(__file__).parent

# Save individual PNGs (kept for markdown embedding)
panel_names = [
    "benchmark_score_distribution",
    "benchmark_accuracy_by_complexity",
    "benchmark_accuracy_by_category",
    "benchmark_key_metrics",
]
charts = [c1, c2, c3, c4]
for chart, name in zip(charts, panel_names):
    chart.save(str(out_dir / f"{name}.png"), ppi=200)
    print(f"Saved: {out_dir / name}.png")

# Compose into 2x2 grid with PIL
from PIL import Image

imgs = [Image.open(out_dir / f"{name}.png") for name in panel_names]

# Uniform cell size — use the max dimensions
max_w = max(im.width for im in imgs)
max_h = max(im.height for im in imgs)

PAD = 40
TITLE_H = 80
canvas_w = max_w * 2 + PAD * 3
canvas_h = max_h * 2 + PAD * 3 + TITLE_H
canvas = Image.new("RGB", (canvas_w, canvas_h), "white")

# Title
from PIL import ImageDraw, ImageFont
draw = ImageDraw.Draw(canvas)
try:
    title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
except OSError:
    title_font = ImageFont.load_default()
title = "Genie Space Benchmark \u2014 50 Questions | Velocity Motors Dataset"
bbox = draw.textbbox((0, 0), title, font=title_font)
tw = bbox[2] - bbox[0]
draw.text(((canvas_w - tw) // 2, PAD), title, fill=TEXT_DARK, font=title_font)

# Place panels: top-left, top-right, bottom-left, bottom-right
positions = [
    (PAD, TITLE_H + PAD),
    (max_w + PAD * 2, TITLE_H + PAD),
    (PAD, TITLE_H + max_h + PAD * 2),
    (max_w + PAD * 2, TITLE_H + max_h + PAD * 2),
]
for img, (x, y) in zip(imgs, positions):
    # Center within cell
    offset_x = x + (max_w - img.width) // 2
    offset_y = y + (max_h - img.height) // 2
    canvas.paste(img, (offset_x, offset_y))

final_path = out_dir / "genie_benchmark_50q.png"
canvas.save(str(final_path), dpi=(200, 200))
print(f"Saved: {final_path}")

# ---------------------------------------------------------------------------
# Save interactive HTML — all 4 charts in a CSS grid dashboard
# ---------------------------------------------------------------------------
import json

specs = [c1.to_dict(), c2.to_dict(), c3.to_dict(), c4.to_dict()]

html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Genie Benchmark — 50 Questions</title>
<script src="https://cdn.jsdelivr.net/npm/vega@5"></script>
<script src="https://cdn.jsdelivr.net/npm/vega-lite@5"></script>
<script src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    background: #fafafa;
    color: #2d3436;
    padding: 32px 48px;
  }}
  h1 {{
    font-size: 22px;
    font-weight: 700;
    text-align: center;
    margin-bottom: 28px;
    color: #2d3436;
  }}
  .grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 32px 48px;
    max-width: 1300px;
    margin: 0 auto;
  }}
  .panel {{
    background: white;
    border-radius: 8px;
    padding: 20px 24px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
  }}
  .panel .vega-embed {{
    width: 100%;
  }}
  .panel .vega-embed details {{
    display: none;  /* hide the ... actions menu */
  }}
</style>
</head>
<body>
<h1>Genie Space Benchmark &mdash; 50 Questions | Velocity Motors Dataset</h1>
<div class="grid">
  <div class="panel" id="chart1"></div>
  <div class="panel" id="chart2"></div>
  <div class="panel" id="chart3"></div>
  <div class="panel" id="chart4"></div>
</div>
<script>
const opts = {{actions: false, renderer: "svg"}};
vegaEmbed("#chart1", {json.dumps(specs[0])}, opts);
vegaEmbed("#chart2", {json.dumps(specs[1])}, opts);
vegaEmbed("#chart3", {json.dumps(specs[2])}, opts);
vegaEmbed("#chart4", {json.dumps(specs[3])}, opts);
</script>
</body>
</html>
"""

html_path = out_dir / "genie_benchmark_50q.html"
html_path.write_text(html_content)
print(f"Saved: {html_path}")

# Individual panel PNGs are kept for markdown embedding
print("Done.")
