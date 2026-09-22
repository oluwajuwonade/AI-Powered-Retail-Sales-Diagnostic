# AI-Powered Retail Sales Diagnostic

A reusable portfolio project that explains why revenue can decline while units sold increase.

## Run

```bash
python build_project.py
```

Outputs are written to `data/` and `outputs/`. The main deliverable is `outputs/AI_Powered_Retail_Sales_Diagnostic_Report.md`; `outputs/dashboard.html` is a lightweight dashboard narrative.

## Project design

The generator creates a monthly product-region-segment-channel grain with intentional data-quality defects. The pipeline profiles the raw file, applies documented cleaning rules, validates business identities, builds KPI and dimension tables, decomposes product revenue changes, flags anomalies, creates charts, and writes the report and content system.

## Causal limits

This is a synthetic observational case. Findings describe patterns in the generated data. They do not establish causation. Controlled discount and channel tests would be needed for causal attribution.
