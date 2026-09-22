# AI-Powered Retail Sales Diagnostic

**Portfolio project | Synthetic retail case study | Narrative: Business Question → Data → Investigation → Evidence → Diagnosis → Decision**

## Executive diagnosis

Revenue fell even though units sold increased because the business sold more low-value units at lower realized prices. H2 units were **48.3% higher** than H1, while revenue was **-14.8% lower**. Average selling price fell **-33.1%**, average discount rose **159.5%**, and the product mix shifted toward Essentials. Profit declined **-23.4%** and average margin declined **-7.5%**.

The evidence supports a **value dilution mechanism** rather than a volume problem: mix moved toward lower-price products, paid acquisition generated relatively low-margin volume with heavier discounting, and regional and segment performance diverged. These are associations in the synthetic data, not proof that any one lever caused the decline.

## 1. Business question

**Why did revenue fall despite increasing sales volume?** The decision is whether to protect volume at any cost or redirect growth toward profitable volume. This analysis treats revenue as the product of units, realized price, and mix, then checks whether the same changes explain profit and margin.

## 2. Data

The raw dataset contains **4,611 rows** across 12 months, 8 products, 4 categories, 4 regions, 3 customer segments, and 4 acquisition channels. Each row is a product-region-segment-channel-month grain. Measures include Date, Month, Quarter, Product, Category, Region, Customer Segment, Units Sold, Revenue, Cost, Profit, Discount, Acquisition Channel, ASP, and Profit Margin.

The generator intentionally added **8 removable or repairable quality issues** so the project can demonstrate profiling and cleaning rather than assuming pristine data. The raw file includes duplicates, missing keys, inconsistent labels, invalid dates, impossible discounts, zero units, negative revenue, cost above revenue, an outlying revenue value, and a broken profit identity.

### Data-quality actions

| Issue | Treatment | Rationale |
|---|---|---|
| Invalid date or missing product/channel | Dropped row | Cannot safely assign the business grain |
| Exact duplicate business key | Kept first record | Prevents double counting |
| Inconsistent region/category casing | Standardized labels; category restored from product mapping | Preserves taxonomy consistency |
| Zero units or non-positive revenue | Removed or median-imputed revenue within comparable group | Avoids undefined ASP and unusable sales records |
| Discount outside 0–60% | Clipped to plausible operating range | Prevents impossible net-price behavior |
| Cost below zero or above revenue | Repaired to 62% of revenue | Restores coherent cost/profit logic while flagging the rule |
| Extreme revenue outlier | Flagged and capped at 99.9th percentile | Limits leverage on aggregate conclusions |
| Profit, ASP, margin | Recomputed | Enforces identities rather than trusting source fields |

Full schema profiling is in `outputs/schema_profile.csv`; the audit trail is in `outputs/validation_log.csv`.

## 3. Investigation

The analysis compares H1 with H2, uses monthly trends, decomposes product-level revenue changes into volume, price, and interaction effects, compares dimensions, and flags robust outliers. Hypotheses were tested as directional comparisons rather than causal experiments.

## 4. Evidence

### KPI movement

| KPI | H1 | H2 | Change |
|---|---:|---:|---:|
| Revenue | $5,859,664 | $4,991,223 | -14.8% |
| Units sold | 96,230 | 142,680 | 48.3% |
| Average selling price | $91.02 | $60.86 | -33.1% |
| Cost | $3,093,931 | $2,872,980 | -7.1% |
| Profit | $2,765,734 | $2,118,243 | -23.4% |
| Average margin | 46.7% | 43.2% | -7.5% |
| Average discount | 10.1% | 26.2% | 159.5% |

![Monthly KPI trends](outputs/figures/monthly_kpis.png)

### Hypothesis findings

**Pricing and discounting.** ASP declined while discounting increased. This is direct evidence of weaker realized value per unit. The alternative explanation is that customers selected cheaper products, so the observed ASP decline combines transaction discounting with mix. Confidence: **high for the descriptive finding; medium for the mechanism**.

**Product and category mix.** The largest product decline was **Premium Audio**, with revenue changing **-35.7%** while the strongest unit growth was **Eco Basics** at **81.5%**. At category level, **Electronics** revenue changed **-35.0%**, while Essentials grew revenue **21.2%**. This pattern is consistent with value dilution. The alternative explanation is demand seasonality or inventory availability. Confidence: **medium-high** because the shift appears in both product and category tables.

**Region.** All regions lost revenue while units rose, but **West** had the largest revenue decline at **-16.4%** and units still changed **47.3%**. This is evidence of broad value pressure with regional variation, not proof of a region-caused decline. Alternative explanations include local seasonality and different product mix. Confidence: **medium**.

**Customer segment.** **Value Seekers** had the largest segment revenue decline at **-15.8%** despite unit growth of **46.9%**. Premium remains important for value recovery because its baseline ASP is higher, but the period comparison alone cannot establish that segment mix caused the aggregate decline. Alternative explanation: segment definitions may be behaviorally assigned and could move over time. Confidence: **medium**.

**Acquisition channel.** **Paid Social** had the largest margin deterioration at **-7.8%** and ASP changed **-34.3%**. Paid Social also had the largest channel revenue decline at **-16.6%**. The evidence supports a channel-quality concern, but not a causal claim about media effectiveness because there is no randomized holdout or spend data. Confidence: **medium**.

![Product mix](outputs/figures/product_mix.png)

![Channel margin](outputs/figures/channel_margin.png)

### Largest combinations and anomalies

The strongest negative combinations are available in `outputs/product_revenue_bridge.csv`, the dimension analysis files, and `outputs/anomalies_top50.csv`. Product-level bridge logic identifies whether a revenue change is more consistent with fewer units, lower ASP, or an interaction of both. The anomaly file uses a robust z-score on revenue, ASP, margin, and discount; it is a triage list, not proof of fraud or error.

## 5. Diagnosis

The most defensible diagnosis is a four-part chain:

1. **What changed:** unit volume rose, but revenue, ASP, profit, and margin fell.
2. **Where it changed:** growth concentrated in lower-value Essentials and Value Seeker demand; paid channels carried weaker economics; region and segment outcomes were heterogeneous.
3. **How material it was:** the H1-to-H2 KPI table quantifies the aggregate movement, while product and dimension tables quantify the concentration of change.
4. **Likely mechanism:** higher discounts and lower-priced product mix reduced realized revenue per unit. The same mix and channel pattern reduced contribution per unit, so additional volume did not offset value dilution.

This is a data-supported business diagnosis, not a causal attribution. A stronger causal test would require controlled discount experiments, media spend and conversion data, inventory availability, and stable segment definitions.

## 6. Decision and recommendations

1. **Set a margin floor for paid acquisition promotions.** Pause or redesign paid offers that fall below the floor. The reason is that paid channels combine weaker margin with heavier discounting. Affected segment: Value Seekers entering through Paid Social and Paid Search. Risk/trade-off: lower short-term units. Monitor contribution margin after media cost, not revenue alone.

2. **Rebalance promotions toward bundles and trade-up paths.** Pair Essentials with Home or Electronics products and test graduated offers instead of blanket discounts. The reason is to preserve the volume engine while increasing basket value. Affected segment: Value Seekers and Mainstream. Risk/trade-off: bundle complexity and possible cannibalization. Monitor bundle ASP, attach rate, and margin.

3. **Protect high-value product availability and merchandising.** Give Premium Audio, Pro Camera, and Luxury Set clearer placement and inventory coverage. The reason is that high-ticket products have disproportionate revenue and profit leverage. Affected segment: Premium and Mainstream customers. Risk/trade-off: slower turns and inventory exposure. Monitor in-stock rate, revenue mix, and weeks of supply.

4. **Create a weekly value-quality dashboard.** Track units, ASP, discount, contribution margin, product mix, and channel mix together. The reason is that volume-only reporting would miss the failure mode. Affected segment: all commercial teams. Risk/trade-off: more governance overhead. Monitor alert breaches and experiment readouts.

5. **Run controlled discount and channel tests.** Use matched geographies or audience holdouts before scaling spend. The reason is to separate correlation from causal lift. Affected segment: paid-acquisition cohorts. Risk/trade-off: slower learning and foregone short-term reach. Monitor incremental revenue, incremental profit, and confidence intervals.

## 7. Decision-oriented dashboard narrative

**KPI section:** Lead with revenue, units, ASP, profit, margin, and discount. Use H1 versus H2 cards and show both absolute and percentage changes.

**Trend section:** Show monthly revenue and units on aligned time axes. The key visual message is the divergence: volume trends upward while revenue and ASP trend downward.

**Driver section:** Use the product bridge to separate volume, price, and interaction effects. Add mix shares by category and channel.

**Diagnostic section:** Filter by region, segment, and acquisition channel. Surface anomaly flags and warn when a channel or segment grows units while losing margin.

**Decision section:** Display the five recommendations alongside thresholds, owners, and monitoring metrics. The dashboard should make “more units” an incomplete success criterion.

## 8. Reusable content system

### 12 short-form video concepts

| # | Hook | Visual sequence | Voiceover | On-screen text | Lesson | CTA |
|---:|---|---|---|---|---|---|
| 1 | “Revenue fell while units rose. Here’s the trap.” | KPI cards → diverging lines → ASP card | Explain value dilution | Volume is not value | Diagnose with units × realized price × mix | Save this framework |
| 2 | “The discount did not create the growth you think.” | Discount slider → margin decline | Show how discounts can buy low-quality volume | Discount up, margin down | Track contribution, not orders | Comment “margin” |
| 3 | “A product mix shift can hide inside a sales win.” | Product bars reorder from premium to essentials | Compare mix shares | More cheap units, less revenue | Decompose revenue by mix | Follow for part 2 |
| 4 | “Paid traffic grew. Profit did not.” | Channel tiles → margin bars | Contrast paid and organic economics | CAC is not the only cost | Add margin to channel reporting | Share with growth team |
| 5 | “Your ASP is a diagnostic alarm.” | ASP trend → discount trend | Explain ASP as realized value | ASP down = investigate mix and promo | Ask what changed underneath | Download the template |
| 6 | “Three checks before blaming demand.” | Date quality → inventory → mix | Walk through alternatives | Demand is not the only explanation | Separate signal from story | Save the checklist |
| 7 | “The revenue bridge executives actually need.” | Waterfall animation | Show volume, price, interaction | Where did the dollars go? | Attribute change transparently | Use this in your next review |
| 8 | “An anomaly is a question, not a verdict.” | Outlier dot → row detail | Explain robust z-score triage | Flag, investigate, don’t accuse | Anomaly detection needs context | Comment “audit” |
| 9 | “Premium customers can subsidize volume growth.” | Segment matrix → margin | Compare segments | Growth quality differs by segment | Segment economics matter | Follow for the matrix |
| 10 | “Why revenue dashboards fail.” | Revenue-only dashboard crossed out | Add units, ASP, discount, margin | One KPI can lie by omission | Build diagnostic dashboards | Get the dashboard outline |
| 11 | “A discount experiment beats an argument.” | Holdout groups → result | Explain causal testing | Correlation is not lift | Use controlled tests | Try this next quarter |
| 12 | “The decision is not ‘more sales’.” | Decision tree → recommendation cards | Reframe goal as profitable growth | Grow value, not just volume | Tie diagnosis to action | Send this to a decision-maker |

### 5 LinkedIn posts

1. **Revenue down, units up is not a contradiction.** It is often a value problem. In this case, ASP fell, discounts rose, and mix shifted toward lower-value products. The practical lesson: every sales KPI review should pair units with realized price, mix, and margin. **Question:** which metric catches value dilution fastest in your business?

2. **I built a diagnostic that refuses to call correlation causation.** It compares periods, decomposes product revenue into volume and price effects, flags anomalies, and records alternative explanations. The result is a better decision conversation: what changed, where, how material, and what test would prove the mechanism?

3. **Paid acquisition can look healthy in an order report and unhealthy in a margin report.** The answer is not to cut paid channels blindly. It is to measure incremental profit after discounting and media cost, then run holdouts.

4. **A good dashboard is a decision instrument.** KPI tells you what moved. Trend tells you when. Driver tells you what contributed. Diagnostic tells you where. Decision tells you what to do next. Anything less is reporting, not diagnosis.

5. **Synthetic data is useful when the story is explicit and the cleaning is visible.** This case study deliberately contains duplicates, invalid values, inconsistent labels, and broken identities. The point is not to mimic a perfect dataset; it is to rehearse the reasoning required when the data is imperfect.

### 3 long-form YouTube concepts

1. **Why Revenue Fell While Units Rose: A Complete Retail Diagnostic.** Chapters: business question, data quality, KPI divergence, revenue bridge, mix and channel analysis, recommendations, causal limits.
2. **Build a Retail Sales Diagnostic in Python From Raw CSV to Executive Dashboard.** Chapters: synthetic generator, profiling, cleaning, validation, hypothesis tables, anomaly triage, chart design.
3. **The Difference Between Volume Growth and Profitable Growth.** Chapters: ASP, discounting, mix, segment economics, paid acquisition, experiment design, decision framework.

### 5 carousel concepts

1. **The volume illusion:** units up → ASP down → revenue down → margin down.
2. **Revenue bridge anatomy:** volume effect, price effect, mix interaction, residual.
3. **Data-quality checklist:** schema, missingness, duplicates, suspicious values, identities.
4. **Five questions for a falling-revenue business:** what changed, where, how much, why might it happen, what test comes next?
5. **From dashboard to decision:** KPI, trend, driver, diagnostic, decision.

### 10 hooks

1. Revenue fell while sales volume rose. Here is the hidden mechanism.
2. Your best growth metric may be hiding a margin problem.
3. Before blaming demand, check these three dimensions.
4. The fastest way to find value dilution in retail data.
5. Discounts can increase units and still destroy revenue quality.
6. This is why paid traffic can look successful until you add margin.
7. A dashboard that only shows revenue is incomplete.
8. An outlier is not a conclusion. It is an investigation queue.
9. Mix shift is the silent reason many sales reports mislead.
10. The right question is not “Did we sell more?”

### 10 CTAs

1. Save this diagnostic framework for your next business review.
2. Comment “bridge” and I’ll share the decomposition logic.
3. Follow for the next part on controlled discount tests.
4. Send this to someone who reports volume without margin.
5. Download the reusable project files.
6. Comment with the KPI you use to measure growth quality.
7. Subscribe for the full Python walkthrough.
8. Share this with your commercial analytics team.
9. Try the five-question checklist on your last revenue decline.
10. Bookmark this before your next quarterly planning session.

### 5 portfolio case-study sections

1. **Business problem and stakes:** revenue declined despite rising units, creating a misleading growth narrative.
2. **Data engineering:** generated a realistic retail grain, injected defects, profiled the schema, and documented cleaning rules.
3. **Analytical investigation:** compared H1 and H2, decomposed product revenue changes, tested segment hypotheses, and detected anomalies.
4. **Diagnosis and decision:** identified value dilution from ASP, discounting, mix, and channel economics without overstating causality.
5. **Impact and reuse:** translated the analysis into a dashboard narrative, recommendations, monitoring metrics, and a content system.

## Files and reproducibility

Run `python build_project.py` from the project root to regenerate raw data, cleaned data, analysis tables, charts, and this report. The raw and cleaned CSVs are intentionally included so the cleaning work can be inspected independently.

## References

[1]: https://pandas.pydata.org/docs/ "Pandas documentation"
[2]: https://numpy.org/doc/ "NumPy documentation"
[3]: https://matplotlib.org/stable/contents.html "Matplotlib documentation"
[4]: https://seaborn.pydata.org/ "Seaborn documentation"
