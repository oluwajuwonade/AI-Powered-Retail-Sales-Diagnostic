<!-- PORTFOLIO-CONTEXT
Oluwajuwon Adediji | Data & Quantitative Analyst | Decision Intelligence | AI-Powered Analytics
Portfolio: https://oluwajuwonade.vercel.app
-->

# AI-Powered Retail Sales Diagnostic

> **Decision question:** Why did revenue decline despite increasing sales volume?

A reproducible decision-intelligence case study that turns messy retail operating data into a quantified business diagnosis, executive narrative, and action framework.

## Why this project exists

Revenue can weaken even when units sold increase. The purpose of this project is to distinguish volume growth from changes in price, mix, discounts, product performance, channel, region, and customer segment.

## Analytical workflow

`Raw data → Quality audit → KPI layer → EDA → Anomaly detection → Segmentation → Revenue decomposition → Business diagnosis → Recommendations`

The pipeline creates a monthly product-region-segment-channel grain with intentional data-quality defects, profiles the raw file, applies documented cleaning rules, validates business identities, builds KPI and dimension tables, decomposes revenue changes, flags anomalies, generates charts, and produces a decision report.

## Key analytical questions

1. Did revenue change because of volume, price/mix, discounts, or product/channel mix?
2. Which products, regions, segments, or channels explain the movement?
3. Which anomalies or data-quality issues could distort the KPI story?
4. Which business actions are supported by the observed evidence?

## Evidence and outputs

The main deliverables are:

- Executive-style diagnostic report
- KPI and dimension tables
- Revenue-change decomposition
- Anomaly outputs
- Analytical charts
- Lightweight dashboard narrative
- Reproducible generated data and code

Run:

```bash
python build_project.py
```

Outputs are written to `data/` and `outputs/`.

## Decision framing

The project separates:

**Observed facts** — measured patterns in the generated dataset.

**Assumptions** — explicit rules used to generate or transform the data.

**Interpretation** — business explanations consistent with the observed patterns.

**Recommendations** — actions linked to measurable drivers.

## Important limitations

This is a **synthetic observational case**. Findings describe patterns in the generated data and do not establish causation. Controlled discount, pricing, and channel experiments would be required for causal attribution.

## Technical stack

Python · pandas · NumPy · statistical analysis · data visualization · reproducible reporting

## Portfolio role

**Tier 1 — Flagship Business Decision Analytics**

This is the primary demonstration of my ability to move from data preparation to business diagnosis and decision support.

## Related portfolio projects

- [Financial Planning & Scenario Modelling](https://github.com/oluwajuwonade/financial-modelling-starter-system)
- [Pricing & ROI Decision Engine](https://github.com/oluwajuwonade/pricing-roi-analytics-engine)
- [Data Quality & Analytics Assurance](https://github.com/oluwajuwonade/data-quality-audit-toolkit)
- [Credit Risk & FICO Segmentation](https://github.com/oluwajuwonade/credit-risk-fico-segmentation)

## Reproducibility

The project is designed so the dataset, transformations, analysis, charts, and report can be regenerated from the repository.

## Author

**Oluwajuwon Adediji**  
Data & Quantitative Analyst | Decision Intelligence | AI-Powered Analytics
