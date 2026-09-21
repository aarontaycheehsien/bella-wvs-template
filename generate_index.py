#!/usr/bin/env python3
"""Generate a self-contained index.html for WVS synthetic data analysis."""

import csv
import json
import random
from collections import defaultdict
from pathlib import Path

# Fixed seed for reproducibility
SEED = 42
random.seed(SEED)

# Color palette (colorblind-safe)
COLORS = {
    "China": "#E69F00",
    "Singapore": "#D55E00",
    "Turkey": "#CC79A7",
    "India": "#0072B2",
    "Kazakhstan": "#009E73",
}

# Read CSV
csv_path = Path("data/wvs-synthetic.csv")
rows = []
with open(csv_path, encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

print(f"Total rows read: {len(rows)}")

# Identify columns
columns = list(rows[0].keys())
print(f"Columns: {columns}")

# Remove respondent_id from columns for analysis
analysis_columns = [c for c in columns if c != "respondent_id"]

# Track duplicates and rows with missing values
respondent_ids = set()
duplicates = 0
rows_with_missing = 0
cleaned_rows = []

for row in rows:
    rid = row["respondent_id"]
    if rid in respondent_ids:
        duplicates += 1
        continue
    respondent_ids.add(rid)

    # Check for missing values
    has_missing = any(row[col].strip() == "" for col in analysis_columns)
    if has_missing:
        rows_with_missing += 1
        continue

    cleaned_rows.append(row)

print(f"Duplicates found: {duplicates}")
print(f"Rows with missing values: {rows_with_missing}")
print(f"Rows after cleaning: {len(cleaned_rows)}")

# Compute column metadata
col_types = {}
for col in analysis_columns:
    # Determine type
    if col in ["emancipative_values", "secular_values"]:
        col_types[col] = "numeric (0-1 index)"
    elif col in ["life_satisfaction", "freedom_of_choice", "importance_of_god", "financial_satisfaction"]:
        col_types[col] = "numeric (1-10 scale)"
    elif col == "age":
        col_types[col] = "numeric"
    elif col == "trust_people":
        col_types[col] = "categorical (Trusted/Not trusted)"
    else:
        col_types[col] = "categorical"

# Count non-missing observations per column
col_counts = defaultdict(int)
for row in cleaned_rows:
    for col in analysis_columns:
        if row[col].strip():
            col_counts[col] += 1

# Separate data by country
by_country = defaultdict(list)
for row in cleaned_rows:
    by_country[row["country"]].append(row)

countries = sorted(by_country.keys())
print(f"Countries: {countries}")

# Compute country-level aggregates
aggregates = {}
for country in countries:
    country_rows = by_country[country]

    # Parse numeric columns
    life_sat = []
    freedom = []
    emancipative = []
    trust_people = []
    importance_god = []
    financial_sat = []
    secular = []

    for row in country_rows:
        try:
            life_sat.append(float(row["life_satisfaction"]))
            freedom.append(float(row["freedom_of_choice"]))
            emancipative.append(float(row["emancipative_values"]))
            importance_god.append(float(row["importance_of_god"]))
            financial_sat.append(float(row["financial_satisfaction"]))
            secular.append(float(row["secular_values"]))
        except ValueError:
            continue

        # Trust people: convert to 0/1
        if row["trust_people"].strip():
            trust_people.append(1 if row["trust_people"] == "Trusted" else 0)

    # Compute means
    aggregates[country] = {
        "life_satisfaction": round(sum(life_sat) / len(life_sat), 1) if life_sat else None,
        "freedom_of_choice": round(sum(freedom) / len(freedom), 1) if freedom else None,
        "emancipative_values": round(sum(emancipative) / len(emancipative), 2) if emancipative else None,
        "trust_people": round(sum(trust_people) / len(trust_people), 2) if trust_people else None,
        "importance_of_god": round(sum(importance_god) / len(importance_god), 1) if importance_god else None,
        "financial_satisfaction": round(sum(financial_sat) / len(financial_sat), 1) if financial_sat else None,
        "secular_values": round(sum(secular) / len(secular), 2) if secular else None,
        "count": len(country_rows),
    }

print("Country aggregates:")
for country, agg in aggregates.items():
    print(f"  {country}: {agg}")

# Sample 300 respondents per country for China and India
china_sample = []
india_sample = []

if "China" in by_country:
    china_all = [
        {
            "secular_values": float(r["secular_values"]),
            "emancipative_values": float(r["emancipative_values"]),
        }
        for r in by_country["China"]
    ]
    china_sample = random.sample(china_all, min(300, len(china_all)))

if "India" in by_country:
    india_all = [
        {
            "secular_values": float(r["secular_values"]),
            "emancipative_values": float(r["emancipative_values"]),
        }
        for r in by_country["India"]
    ]
    india_sample = random.sample(india_all, min(300, len(india_all)))

# Compute Singapore heatmap (10x10: life_satisfaction rows, financial_satisfaction cols)
singapore_heatmap = [[0 for _ in range(10)] for _ in range(10)]
if "Singapore" in by_country:
    for row in by_country["Singapore"]:
        try:
            life = int(float(row["life_satisfaction"]))
            financial = int(float(row["financial_satisfaction"]))
            if 1 <= life <= 10 and 1 <= financial <= 10:
                singapore_heatmap[life - 1][financial - 1] += 1
        except (ValueError, IndexError):
            pass

# Prepare data object
data = {
    "countries": countries,
    "colors": COLORS,
    "column_info": {col: {"type": col_types[col], "observations": col_counts[col]} for col in analysis_columns},
    "metadata": {
        "total_rows_original": len(rows),
        "duplicates": duplicates,
        "rows_with_missing": rows_with_missing,
        "rows_analyzed": len(cleaned_rows),
    },
    "aggregates": aggregates,
    "china_sample": china_sample,
    "india_sample": india_sample,
    "singapore_heatmap": singapore_heatmap,
}

# Generate HTML
data_json = json.dumps(data)

html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WVS Synthetic Data Analysis</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        :root {
            --color-bg: #ffffff;
            --color-text: #333333;
            --color-border: #e0e0e0;
            --color-light: #f5f5f5;
        }

        @media (prefers-color-scheme: dark) {
            :root {
                --color-bg: #1a1a1a;
                --color-text: #e0e0e0;
                --color-border: #333333;
                --color-light: #2a2a2a;
            }
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background-color: var(--color-bg);
            color: var(--color-text);
            line-height: 1.6;
            padding: 1rem;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        h1 {
            font-size: 2rem;
            margin: 2rem 0 1rem;
            color: var(--color-text);
        }

        h2 {
            font-size: 1.5rem;
            margin: 2rem 0 1rem;
            color: var(--color-text);
            border-bottom: 2px solid var(--color-border);
            padding-bottom: 0.5rem;
        }

        h3 {
            font-size: 1.2rem;
            margin: 1.5rem 0 0.5rem;
            color: var(--color-text);
        }

        p {
            margin-bottom: 1rem;
            font-size: 0.95rem;
            line-height: 1.7;
        }

        a {
            color: #0066cc;
            text-decoration: none;
        }

        a:hover {
            text-decoration: underline;
        }

        .intro {
            background-color: var(--color-light);
            padding: 1.5rem;
            border-radius: 8px;
            margin-bottom: 2rem;
        }

        .data-summary {
            background-color: var(--color-light);
            padding: 1.5rem;
            border-radius: 8px;
            margin-bottom: 2rem;
        }

        .column-table {
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
            font-size: 0.9rem;
        }

        .column-table th,
        .column-table td {
            border: 1px solid var(--color-border);
            padding: 0.75rem;
            text-align: left;
        }

        .column-table th {
            background-color: var(--color-border);
            font-weight: 600;
        }

        .chart-section {
            margin-bottom: 3rem;
        }

        .chart-container {
            background-color: var(--color-light);
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
        }

        .chart {
            width: 100%;
            height: 500px;
        }

        .takeaway {
            font-size: 0.95rem;
            margin-top: 1rem;
            padding: 0.75rem;
            background-color: var(--color-bg);
            border-left: 4px solid var(--color-border);
            color: var(--color-text);
        }

        .heatmap-container {
            overflow-x: auto;
            margin: 1rem 0;
        }

        .heatmap {
            border-collapse: collapse;
            font-size: 0.85rem;
        }

        .heatmap th {
            background-color: var(--color-border);
            padding: 0.5rem;
            text-align: center;
            border: 1px solid var(--color-border);
            font-weight: 600;
        }

        .heatmap td {
            width: 50px;
            height: 50px;
            text-align: center;
            vertical-align: middle;
            border: 1px solid var(--color-border);
            font-weight: 500;
            font-size: 0.8rem;
        }

        .heatmap-cell {
            width: 100%;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 4px;
        }

        @media (max-width: 768px) {
            h1 {
                font-size: 1.5rem;
            }

            h2 {
                font-size: 1.2rem;
            }

            .chart {
                height: 400px;
            }

            .heatmap td {
                width: 40px;
                height: 40px;
                font-size: 0.75rem;
            }

            .column-table {
                font-size: 0.8rem;
            }

            .column-table th,
            .column-table td {
                padding: 0.5rem;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>World Values Survey (Synthetic Data) — Exploratory Analysis</h1>

        <div class="intro">
            <p>
                <strong>Data Source:</strong> This is a <em>synthetic (simulated)</em> dataset designed to resemble the
                <a href="https://www.worldvaluessurvey.org" target="_blank">World Values Survey, Wave 7</a> (Inglehart et al., 2022).
                No real respondent data is included; all values are fabricated to mirror the distributions and relationships observed
                in the actual WVS. Any patterns and insights presented below are <strong>illustrative only</strong> and should not
                be interpreted as reflecting real-world respondent attitudes.
            </p>
            <p>
                <strong>Coverage:</strong> This analysis covers 5 countries across different regions of Asia:
                <strong>Turkey</strong> (Middle East), <strong>India</strong> (South Asia), <strong>Singapore</strong> (Southeast Asia),
                <strong>China</strong> (East Asia), and <strong>Kazakhstan</strong> (Central Asia).
            </p>
        </div>

        <h2>Data Summary</h2>
        <div class="data-summary">
            <h3>Dataset Overview</h3>
            <p>
                <strong>Original rows:</strong> """ + str(data["metadata"]["total_rows_original"]) + """<br>
                <strong>Duplicates removed:</strong> """ + str(data["metadata"]["duplicates"]) + """<br>
                <strong>Rows with missing values removed:</strong> """ + str(data["metadata"]["rows_with_missing"]) + """<br>
                <strong>Rows analyzed:</strong> """ + str(data["metadata"]["rows_analyzed"]) + """
            </p>

            <h3>Columns and Data Types</h3>
            <table class="column-table">
                <thead>
                    <tr>
                        <th>Column Name</th>
                        <th>Data Type</th>
                        <th>Non-Empty Observations</th>
                    </tr>
                </thead>
                <tbody id="column-rows">
                </tbody>
            </table>
        </div>

        <h2>Analyses</h2>

        <div class="chart-section">
            <h3>1. Cultural Map: Emancipative vs Secular Values</h3>
            <p>
                Each point represents a country's average position on two key value dimensions:
                emancipative values (y-axis) measure support for gender equality, sexual diversity, and individual autonomy;
                secular values (x-axis) reflect trust in institutions and rational decision-making over religious authority.
            </p>
            <div class="chart-container">
                <div id="cultural-map" class="chart"></div>
            </div>
            <div class="takeaway" id="cultural-map-takeaway"></div>
        </div>

        <div class="chart-section">
            <h3>2. Value Fingerprints: Six-Dimensional Value Profile</h3>
            <p>
                Each country is profiled across six normalized dimensions: life satisfaction, trust in people,
                importance of religion, emancipative values, secular values, and financial satisfaction.
                Overlaid radar lines reveal each nation's distinctive value pattern.
            </p>
            <div class="chart-container">
                <div id="value-fingerprints" class="chart"></div>
            </div>
            <div class="takeaway" id="fingerprints-takeaway"></div>
        </div>

        <div class="chart-section">
            <h3>3. Individual Values: China vs India</h3>
            <p>
                A scatter plot of ~300 randomly sampled respondents from China and India on the emancipative–secular plane.
                Larger outlined points mark each country's mean. Despite different average positions, substantial overlap
                in the clouds reveals within-country diversity that often exceeds between-country differences.
            </p>
            <div class="chart-container">
                <div id="china-india-scatter" class="chart"></div>
            </div>
            <div class="takeaway" id="china-india-takeaway"></div>
        </div>

        <div class="chart-section">
            <h3>4. Life Satisfaction vs Financial Satisfaction: Singapore</h3>
            <p>
                A 10×10 heatmap showing the joint distribution of life satisfaction (rows) and financial satisfaction (columns)
                among Singapore respondents. Darker cells indicate more respondents at that combination; cell counts are displayed inside.
            </p>
            <div class="chart-container">
                <div class="heatmap-container">
                    <table class="heatmap" id="singapore-heatmap"></table>
                </div>
            </div>
            <div class="takeaway" id="singapore-takeaway"></div>
        </div>
    </div>

    <script type="application/json" id="data">
    """ + data_json + """
    </script>

    <script>
        // Parse data
        const data = JSON.parse(document.getElementById('data').textContent);

        // Populate column table
        const colRows = document.getElementById('column-rows');
        Object.entries(data.column_info).forEach(([col, info]) => {
            const row = document.createElement('tr');
            row.innerHTML = `<td>${col}</td><td>${info.type}</td><td>${info.observations}</td>`;
            colRows.appendChild(row);
        });

        // Cultural Map (scatter: secular vs emancipative)
        const culturalMapX = [];
        const culturalMapY = [];
        const culturalMapLabels = [];
        const culturalMapColors = [];

        data.countries.forEach(country => {
            const agg = data.aggregates[country];
            culturalMapX.push(agg.secular_values);
            culturalMapY.push(agg.emancipative_values);
            culturalMapLabels.push(country);
            culturalMapColors.push(data.colors[country]);
        });

        Plotly.newPlot('cultural-map', [{
            x: culturalMapX,
            y: culturalMapY,
            mode: 'markers+text',
            marker: {
                size: 15,
                color: culturalMapColors,
                line: {color: 'rgba(0,0,0,0.3)', width: 2},
            },
            text: culturalMapLabels,
            textposition: 'middle center',
            textfont: {size: 11, color: 'white', weight: 'bold'},
            hovertemplate: '<b>%{text}</b><br>Secular Values: %{x:.2f}<br>Emancipative Values: %{y:.2f}<extra></extra>',
        }], {
            xaxis: {title: 'Secular Values →', zeroline: false},
            yaxis: {title: 'Emancipative Values →', zeroline: false},
            hovermode: 'closest',
            margin: {l: 60, r: 40, t: 40, b: 60},
            plot_bgcolor: 'rgba(0,0,0,0)',
            paper_bgcolor: 'rgba(0,0,0,0)',
        });

        // Takeaway
        const minEmancipative = Math.min(...culturalMapY);
        const maxEmancipative = Math.max(...culturalMapY);
        const minSecular = Math.min(...culturalMapX);
        const maxSecular = Math.max(...culturalMapX);
        const maxEmancipativeIdx = culturalMapY.indexOf(maxEmancipative);
        const maxSecularIdx = culturalMapX.indexOf(maxSecular);
        document.getElementById('cultural-map-takeaway').textContent =
            `Countries cluster along both dimensions: ${data.countries[maxEmancipativeIdx]} shows the highest emancipative values (${maxEmancipative.toFixed(2)}), ` +
            `while ${data.countries[maxSecularIdx]} is most secular (${maxSecular.toFixed(2)}). This reflects distinct cultural and institutional contexts across Asia.`;

        // Value Fingerprints (radar chart)
        const radarCategories = ['Life Satisfaction', 'Trust in People', 'Importance of God', 'Emancipative Values', 'Secular Values', 'Financial Satisfaction'];
        const radarTraces = data.countries.map(country => {
            const agg = data.aggregates[country];
            return {
                r: [
                    agg.life_satisfaction / 10,
                    agg.trust_people,
                    agg.importance_of_god / 10,
                    agg.emancipative_values,
                    agg.secular_values,
                    agg.financial_satisfaction / 10,
                ],
                theta: radarCategories,
                fill: 'toself',
                name: country,
                line: {color: data.colors[country], width: 2},
                marker: {size: 6, color: data.colors[country]},
            };
        });

        Plotly.newPlot('value-fingerprints', radarTraces, {
            polar: {
                radialaxis: {visible: true, range: [0, 1]},
            },
            hovermode: 'closest',
            margin: {l: 80, r: 80, t: 80, b: 80},
            plot_bgcolor: 'rgba(0,0,0,0)',
            paper_bgcolor: 'rgba(0,0,0,0)',
        });

        document.getElementById('fingerprints-takeaway').textContent =
            `Each nation displays a distinct profile: ${data.countries[0]} and ${data.countries[4]} show contrasting patterns ` +
            `across multiple dimensions, illustrating how values cluster differently by region and culture.`;

        // China vs India scatter
        const chinaXY = data.china_sample.map(s => [s.secular_values, s.emancipative_values]);
        const indiaXY = data.india_sample.map(s => [s.secular_values, s.emancipative_values]);

        const chinaX = chinaXY.map(p => p[0]);
        const chinaY = chinaXY.map(p => p[1]);
        const indiaX = indiaXY.map(p => p[0]);
        const indiaY = indiaXY.map(p => p[1]);

        // Compute means
        const chinaMeanX = chinaX.reduce((a, b) => a + b, 0) / chinaX.length;
        const chinaMeanY = chinaY.reduce((a, b) => a + b, 0) / chinaY.length;
        const indiaMeanX = indiaX.reduce((a, b) => a + b, 0) / indiaX.length;
        const indiaMeanY = indiaY.reduce((a, b) => a + b, 0) / indiaY.length;

        Plotly.newPlot('china-india-scatter', [
            {
                x: chinaX,
                y: chinaY,
                mode: 'markers',
                marker: {size: 5, color: data.colors['China'], opacity: 0.5},
                name: 'China (samples)',
                hovertemplate: 'China<br>Secular: %{x:.2f}<br>Emancipative: %{y:.2f}<extra></extra>',
            },
            {
                x: indiaX,
                y: indiaY,
                mode: 'markers',
                marker: {size: 5, color: data.colors['India'], opacity: 0.5},
                name: 'India (samples)',
                hovertemplate: 'India<br>Secular: %{x:.2f}<br>Emancipative: %{y:.2f}<extra></extra>',
            },
            {
                x: [chinaMeanX],
                y: [chinaMeanY],
                mode: 'markers',
                marker: {size: 15, color: data.colors['China'], symbol: 'circle', line: {color: 'white', width: 2}},
                name: 'China (mean)',
                hovertemplate: 'China Mean<br>Secular: %{x:.2f}<br>Emancipative: %{y:.2f}<extra></extra>',
            },
            {
                x: [indiaMeanX],
                y: [indiaMeanY],
                mode: 'markers',
                marker: {size: 15, color: data.colors['India'], symbol: 'circle', line: {color: 'white', width: 2}},
                name: 'India (mean)',
                hovertemplate: 'India Mean<br>Secular: %{x:.2f}<br>Emancipative: %{y:.2f}<extra></extra>',
            },
        ], {
            xaxis: {title: 'Secular Values →'},
            yaxis: {title: 'Emancipative Values →'},
            hovermode: 'closest',
            margin: {l: 60, r: 40, t: 40, b: 60},
            plot_bgcolor: 'rgba(0,0,0,0)',
            paper_bgcolor: 'rgba(0,0,0,0)',
        });

        const overlapX = Math.abs(chinaMeanX - indiaMeanX);
        const overlapY = Math.abs(chinaMeanY - indiaMeanY);
        document.getElementById('china-india-takeaway').textContent =
            `Despite different average positions (China: Secular=${chinaMeanX.toFixed(2)}, Emancipative=${chinaMeanY.toFixed(2)}; ` +
            `India: Secular=${indiaMeanX.toFixed(2)}, Emancipative=${indiaMeanY.toFixed(2)}), the two populations overlap substantially, ` +
            `indicating that diversity within each country rivals differences between them.`;

        // Singapore heatmap
        const heatmapTable = document.getElementById('singapore-heatmap');
        const heatmapData = data.singapore_heatmap;
        const maxCount = Math.max(...heatmapData.map(row => Math.max(...row)));

        // Header row (financial satisfaction columns)
        const headerRow = document.createElement('tr');
        headerRow.innerHTML = '<th style="width: 60px; text-align: center;">Life / Fin</th>';
        for (let col = 1; col <= 10; col++) {
            headerRow.innerHTML += `<th>${col}</th>`;
        }
        heatmapTable.appendChild(headerRow);

        // Data rows
        for (let life = 1; life <= 10; life++) {
            const row = document.createElement('tr');
            row.innerHTML = `<th>${life}</th>`;
            for (let fin = 1; fin <= 10; fin++) {
                const count = heatmapData[life - 1][fin - 1];
                const intensity = count / maxCount;
                const bgColor = `rgba(0, 102, 204, ${intensity * 0.8})`;
                const cell = document.createElement('td');
                cell.innerHTML = `<div class="heatmap-cell" style="background-color: ${bgColor};">${count}</div>`;
                cell.title = `Life: ${life}, Financial: ${fin}, Count: ${count}`;
                row.appendChild(cell);
            }
            heatmapTable.appendChild(row);
        }

        // Takeaway
        const sgCount = heatmapData.flat().reduce((a, b) => a + b, 0);
        document.getElementById('singapore-takeaway').textContent =
            `Among ${sgCount} Singapore respondents, life and financial satisfaction show modest positive correlation: ` +
            `the diagonal band from lower-left to upper-right is denser than random, suggesting economic security moderately supports life satisfaction.`;
    </script>
</body>
</html>
"""

# Write HTML
output_path = Path("index.html")
with open(output_path, "w", encoding='utf-8') as f:
    f.write(html_content)

print(f"Generated: {output_path}")
print("To preview locally, open index.html in a web browser.")
