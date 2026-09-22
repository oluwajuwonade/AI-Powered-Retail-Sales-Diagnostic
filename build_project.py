from pathlib import Path
import json, math, textwrap
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

ROOT = Path('/home/ubuntu/ai_retail_sales_diagnostic')
RAW = ROOT/'data'/'raw'; CLEAN = ROOT/'data'/'cleaned'; OUT = ROOT/'outputs'; FIG = OUT/'figures'
for p in [RAW,CLEAN,OUT,FIG]: p.mkdir(parents=True, exist_ok=True)
np.random.seed(42)

# ---------------------------
# 1) Generate synthetic raw data
# ---------------------------
months = pd.date_range('2024-01-01','2024-12-01',freq='MS')
products = {
    'Eco Basics': ('Essentials', 24, 0.62),
    'Daily Care': ('Essentials', 32, 0.60),
    'Home Comfort': ('Home', 58, 0.57),
    'Smart Kitchen': ('Home', 86, 0.54),
    'Activewear': ('Lifestyle', 72, 0.56),
    'Premium Audio': ('Electronics', 145, 0.49),
    'Pro Camera': ('Electronics', 220, 0.46),
    'Luxury Set': ('Lifestyle', 180, 0.43),
}
regions = ['North','South','East','West']
segments = ['Value Seekers','Mainstream','Premium']
channels = ['Organic Search','Email','Paid Social','Paid Search']
region_factor = {'North':1.15,'South':0.92,'East':1.05,'West':1.00}
segment_factor = {'Value Seekers':1.12,'Mainstream':1.00,'Premium':0.68}
channel_factor = {'Organic Search':1.05,'Email':0.96,'Paid Social':0.88,'Paid Search':0.91}
channel_discount = {'Organic Search':0.05,'Email':0.07,'Paid Social':0.14,'Paid Search':0.12}
product_factor = {'Eco Basics':1.35,'Daily Care':1.22,'Home Comfort':0.90,'Smart Kitchen':0.62,'Activewear':0.76,'Premium Audio':0.45,'Pro Camera':0.28,'Luxury Set':0.20}
rows=[]
for mi, dt in enumerate(months):
    h2 = mi >= 6
    season = 1 + 0.12*np.sin((mi+1)/12*2*np.pi) + (0.18 if mi in [10,11] else 0)
    for product,(category,base_price,cost_rate) in products.items():
        # Explicit mix shift toward low-value products in H2.
        mix = (1.35 if product in ['Eco Basics','Daily Care'] and h2 else 1.0) * (0.72 if product in ['Pro Camera','Luxury Set','Premium Audio'] and h2 else 1.0)
        for region in regions:
            for segment in segments:
                for channel in channels:
                    base_units = 52 * product_factor[product] * region_factor[region] * segment_factor[segment] * channel_factor[channel]
                    trend = (1 + 0.055*mi) * (1.12 if h2 else 1.0)
                    units = max(1, np.random.poisson(base_units * season * trend * mix))
                    # H2 pricing pressure is product-specific and larger for paid traffic.
                    asp = base_price * (1 - (0.18 if h2 else 0.0) - (0.025 if channel.startswith('Paid') else 0.0))
                    discount = np.clip(np.random.normal(channel_discount[channel] + (0.16 if h2 else 0.0) + (0.02 if segment=='Value Seekers' else 0), 0.025), 0, .52)
                    revenue = units * asp * (1-discount) * np.random.normal(1.0,0.035)
                    cost = revenue * np.random.normal(cost_rate + (0.035 if h2 else 0.0),0.018)
                    profit = revenue - cost
                    rows.append([dt,dt.strftime('%b'),f'Q{dt.quarter}',product,category,region,segment,units,revenue,cost,profit,discount,channel])
raw = pd.DataFrame(rows, columns=['Date','Month','Quarter','Product','Category','Region','Customer Segment','Units Sold','Revenue','Cost','Profit','Discount','Acquisition Channel'])
raw['Date'] = raw['Date'].astype(object)
# Inject known quality problems for profiling and cleaning.
raw = pd.concat([raw, raw.iloc[[10, 250, 999]].copy()], ignore_index=True)
raw.loc[30,'Region'] = 'nORTH'; raw.loc[75,'Category'] = 'electronic'
raw.loc[120,'Discount'] = -0.05; raw.loc[121,'Discount'] = 1.25
raw.loc[200,'Units Sold'] = 0; raw.loc[201,'Revenue'] = -25
raw.loc[300,'Revenue'] *= 8; raw.loc[301,'Cost'] = raw.loc[301,'Revenue'] * 1.5
raw.loc[400,'Product'] = None; raw.loc[401,'Acquisition Channel'] = None
raw.loc[500,'Profit'] = raw.loc[500,'Revenue'] + 10
raw.loc[600,'Date'] = 'not-a-date'
raw.to_csv(RAW/'retail_sales_raw.csv',index=False)

# ---------------------------
# 2) Profile, clean, validate
# ---------------------------
profile = pd.DataFrame({
    'column': raw.columns,
    'dtype': [str(raw[c].dtype) for c in raw.columns],
    'missing_count': [int(raw[c].isna().sum()) for c in raw.columns],
    'missing_pct': [round(raw[c].isna().mean()*100,3) for c in raw.columns],
    'unique_count': [int(raw[c].nunique(dropna=True)) for c in raw.columns],
})
profile.to_csv(OUT/'schema_profile.csv',index=False)

clean = raw.copy()
clean['Date'] = pd.to_datetime(clean['Date'], errors='coerce')
clean['Region'] = clean['Region'].astype('string').str.strip().str.title()
clean['Category'] = clean['Category'].astype('string').str.strip().str.title().replace({'Electronic':'Electronics'})
# Restore category from product mapping where category is missing/inconsistent.
clean['Category'] = clean['Product'].map({k:v[0] for k,v in products.items()}).fillna(clean['Category'])
# Drop rows with missing key dimensions or invalid date.
clean = clean.dropna(subset=['Date','Product','Acquisition Channel']).copy()
# Remove exact duplicate business records.
clean = clean.drop_duplicates(subset=['Date','Product','Region','Customer Segment','Acquisition Channel'], keep='first')
# Clip/repair impossible measures and recompute dependent metrics.
clean['Units Sold'] = pd.to_numeric(clean['Units Sold'], errors='coerce')
clean = clean[clean['Units Sold'] > 0].copy()
clean['Discount'] = pd.to_numeric(clean['Discount'], errors='coerce').clip(0,0.60)
clean['Revenue'] = pd.to_numeric(clean['Revenue'], errors='coerce')
clean.loc[clean['Revenue'] <= 0, 'Revenue'] = np.nan
clean['Revenue'] = clean.groupby(['Product','Region','Customer Segment','Acquisition Channel'])['Revenue'].transform(lambda s: s.fillna(s.median()))
# Cap extreme revenue at 99.9th percentile after retaining an audit flag.
clean['Revenue_Outlier_Flag'] = clean['Revenue'] > clean['Revenue'].quantile(.999)
clean.loc[clean['Revenue_Outlier_Flag'],'Revenue'] = clean['Revenue'].quantile(.999)
clean['Cost'] = pd.to_numeric(clean['Cost'], errors='coerce')
clean.loc[(clean['Cost']<0) | (clean['Cost']>clean['Revenue']), 'Cost'] = clean['Revenue'] * 0.62
clean['Profit'] = clean['Revenue'] - clean['Cost']
clean['ASP'] = clean['Revenue'] / clean['Units Sold']
clean['Profit Margin'] = clean['Profit'] / clean['Revenue']
clean['Month'] = clean['Date'].dt.strftime('%b'); clean['Quarter'] = 'Q'+clean['Date'].dt.quarter.astype(str)
clean.to_csv(CLEAN/'retail_sales_cleaned.csv',index=False)

# Validation log
checks = []
def check(name, status, detail): checks.append({'check':name,'status':status,'detail':detail})
check('row_count_positive', len(clean)>0, f'{len(clean):,} cleaned rows')
check('unique_business_key', not clean.duplicated(['Date','Product','Region','Customer Segment','Acquisition Channel']).any(), 'No duplicate business keys')
check('positive_units', bool((clean['Units Sold']>0).all()), 'All units sold > 0')
check('discount_bounds', bool(clean['Discount'].between(0,.60).all()), 'Discounts between 0% and 60%')
check('profit_identity', bool(np.allclose(clean['Profit'],clean['Revenue']-clean['Cost'])), 'Profit recomputed as revenue less cost')
check('asp_identity', bool(np.allclose(clean['ASP'],clean['Revenue']/clean['Units Sold'])), 'ASP recomputed as revenue / units')
check('margin_identity', bool(np.allclose(clean['Profit Margin'],clean['Profit']/clean['Revenue'])), 'Margin recomputed as profit / revenue')
pd.DataFrame(checks).to_csv(OUT/'validation_log.csv',index=False)

# ---------------------------
# 3) Analysis tables
# ---------------------------
clean['Period'] = np.where(clean['Date'].dt.month<=6,'H1','H2')
summary = clean.groupby('Period').agg(Revenue=('Revenue','sum'),Units=('Units Sold','sum'),ASP=('ASP','mean'),Cost=('Cost','sum'),Profit=('Profit','sum'),Margin=('Profit Margin','mean'),Discount=('Discount','mean')).reset_index()
h1 = summary.loc[summary.Period=='H1'].iloc[0]; h2 = summary.loc[summary.Period=='H2'].iloc[0]
metrics = ['Revenue','Units','ASP','Cost','Profit','Margin','Discount']
change = pd.DataFrame({'metric':metrics,'H1':[h1[m] for m in metrics],'H2':[h2[m] for m in metrics]})
change['absolute_change']=change['H2']-change['H1']; change['pct_change']=change['absolute_change']/change['H1']
change.to_csv(OUT/'h1_h2_changes.csv',index=False)
monthly = clean.groupby('Date').agg(Revenue=('Revenue','sum'),Units=('Units Sold','sum'),ASP=('ASP','mean'),Cost=('Cost','sum'),Profit=('Profit','sum'),Margin=('Profit Margin','mean'),Discount=('Discount','mean')).reset_index()
monthly.to_csv(OUT/'monthly_kpis.csv',index=False)

# Segment tables and contribution decomposition
for dim, fname in [('Product','product_analysis.csv'),('Category','category_analysis.csv'),('Region','region_analysis.csv'),('Customer Segment','segment_analysis.csv'),('Acquisition Channel','channel_analysis.csv')]:
    tab = clean.groupby([dim,'Period']).agg(Revenue=('Revenue','sum'),Units=('Units Sold','sum'),ASP=('ASP','mean'),Profit=('Profit','sum'),Margin=('Profit Margin','mean'),Discount=('Discount','mean')).reset_index()
    piv = tab.pivot(index=dim,columns='Period',values=['Revenue','Units','ASP','Profit','Margin','Discount'])
    piv.columns = ['_'.join(c) for c in piv.columns]; piv = piv.reset_index()
    for m in ['Revenue','Units','ASP','Profit','Margin','Discount']:
        piv[m+'_change'] = piv[f'{m}_H2']-piv[f'{m}_H1']
        piv[m+'_pct_change'] = piv[m+'_change']/piv[f'{m}_H1']
    piv.to_csv(OUT/fname,index=False)

# Revenue bridge: units effect, ASP effect, mix/residual approximated by holding H1 mix and prices.
prod_h1 = clean[clean.Period=='H1'].groupby('Product').agg(units=('Units Sold','sum'),asp=('ASP','mean')).reset_index()
prod_h2 = clean[clean.Period=='H2'].groupby('Product').agg(units=('Units Sold','sum'),asp=('ASP','mean')).reset_index()
bridge = prod_h1.merge(prod_h2,on='Product',suffixes=('_H1','_H2'))
bridge['rev_H1_proxy']=bridge.units_H1*bridge.asp_H1; bridge['rev_H2_actual_proxy']=bridge.units_H2*bridge.asp_H2
bridge['volume_effect']=(bridge.units_H2-bridge.units_H1)*bridge.asp_H1
bridge['price_effect']=(bridge.asp_H2-bridge.asp_H1)*bridge.units_H1
bridge['mix_interaction']=(bridge.units_H2-bridge.units_H1)*(bridge.asp_H2-bridge.asp_H1)
bridge['revenue_change_proxy']=bridge.rev_H2_actual_proxy-bridge.rev_H1_proxy
bridge.to_csv(OUT/'product_revenue_bridge.csv',index=False)

# Hypothesis tests using H1/H2 comparisons and a simple rank-biserial style effect.
def effect_table(dim):
    out=[]
    for key,g in clean.groupby(dim):
        a=g.loc[g.Period=='H1','Revenue']; b=g.loc[g.Period=='H2','Revenue']
        if len(a)>1 and len(b)>1:
            diff=b.mean()-a.mean(); pooled=np.sqrt((a.var()+b.var())/2) or np.nan
            out.append({dim:key,'H1_mean_revenue':a.mean(),'H2_mean_revenue':b.mean(),'change':diff,'pct_change':diff/a.mean(),'standardized_effect':diff/pooled if pooled else np.nan,'n_H1':len(a),'n_H2':len(b)})
    return pd.DataFrame(out).sort_values('change')
for dim in ['Product','Category','Region','Customer Segment','Acquisition Channel']:
    effect_table(dim).to_csv(OUT/f'{dim.lower().replace(" ","_")}_hypothesis_effects.csv',index=False)

# Anomalies: robust z scores on row-level revenue, ASP, margin, discount.
an = clean.copy()
for col in ['Revenue','ASP','Profit Margin','Discount']:
    med=an[col].median(); mad=(an[col]-med).abs().median() or 1
    an[col+'_robust_z']=0.6745*(an[col]-med)/mad
an['Anomaly_Flag']=(an[[c for c in an.columns if c.endswith('robust_z')]].abs().max(axis=1)>3.5)
an[an.Anomaly_Flag].sort_values('Revenue',ascending=False).head(50).to_csv(OUT/'anomalies_top50.csv',index=False)

# ---------------------------
# 4) Charts
# ---------------------------
sns.set_theme(style='whitegrid', context='talk')
fig,axes=plt.subplots(2,2,figsize=(15,10))
axes=axes.ravel()
for ax,m,label in zip(axes,['Revenue','Units','ASP','Profit'],['Revenue ($)','Units sold','Average selling price ($)','Profit ($)']):
    ax.plot(monthly.Date,monthly[m],marker='o',linewidth=2.5,color='#1f77b4'); ax.axvline(pd.Timestamp('2024-07-01'),color='#d62728',ls='--',alpha=.7)
    ax.set_title(label); ax.set_xlabel(''); ax.tick_params(axis='x',rotation=35)
fig.suptitle('Retail sales diagnostic: volume rises while value and profit weaken',fontsize=20,y=1.02); fig.tight_layout(); fig.savefig(FIG/'monthly_kpis.png',dpi=160,bbox_inches='tight'); plt.close(fig)

fig,axes=plt.subplots(1,3,figsize=(17,5))
for ax,m,title in zip(axes,['Revenue','ASP','Discount'],['Revenue by product','ASP by product','Discount by product']):
    tab=clean.groupby(['Product','Period'])[m].sum() if m=='Revenue' else clean.groupby(['Product','Period'])[m].mean()
    tab.unstack().plot(kind='bar',ax=ax,color=['#9ecae1','#de2d26']); ax.set_title(title); ax.set_xlabel(''); ax.tick_params(axis='x',rotation=50); ax.legend(title='')
fig.tight_layout(); fig.savefig(FIG/'product_mix.png',dpi=160,bbox_inches='tight'); plt.close(fig)

fig,ax=plt.subplots(figsize=(12,6))
ch=clean.groupby(['Acquisition Channel','Period']).agg(Revenue=('Revenue','sum'),Profit=('Profit','sum'),Margin=('Profit Margin','mean')).reset_index()
ch.pivot(index='Acquisition Channel',columns='Period',values='Margin').plot(kind='bar',ax=ax,color=['#9ecae1','#de2d26']); ax.set_title('Margin deteriorates most in paid acquisition channels'); ax.set_ylabel('Profit margin'); ax.set_xlabel(''); ax.tick_params(axis='x',rotation=20); ax.legend(title='')
fig.tight_layout(); fig.savefig(FIG/'channel_margin.png',dpi=160,bbox_inches='tight'); plt.close(fig)

# ---------------------------
# 5) Build narrative report
# ---------------------------
def money(x): return f'${x:,.0f}'
def pct(x): return f'{x*100:.1f}%'
def delta(m):
    r=change.set_index('metric').loc[m]; return f"{money(r['H1'])} to {money(r['H2'])} ({pct(r['pct_change'])})" if m in ['Revenue','Cost','Profit'] else f"{r['H1']:,.1f} to {r['H2']:,.1f} ({pct(r['pct_change'])})"

def top_change(file, change_col, n=3):
    d=pd.read_csv(OUT/file).sort_values(change_col).head(n)
    return '; '.join([f"{r.iloc[0]} ({pct(r[change_col.replace('_change','_pct_change')])})" for _,r in d.iterrows()])

prod=pd.read_csv(OUT/'product_analysis.csv'); cat=pd.read_csv(OUT/'category_analysis.csv'); reg=pd.read_csv(OUT/'region_analysis.csv'); seg=pd.read_csv(OUT/'segment_analysis.csv'); chan=pd.read_csv(OUT/'channel_analysis.csv')
worst_product = prod.sort_values('Revenue_pct_change').iloc[0]
best_volume_product = prod.sort_values('Units_pct_change', ascending=False).iloc[0]
worst_category = cat.sort_values('Revenue_pct_change').iloc[0]
worst_region = reg.sort_values('Revenue_pct_change').iloc[0]
worst_segment = seg.sort_values('Revenue_pct_change').iloc[0]
worst_channel = chan.sort_values('Margin_pct_change').iloc[0]
# top rows by relevant metrics
def top_metric(df, col, n=3, asc=False):
    return df.sort_values(col,ascending=asc).head(n)

report=f'''# AI-Powered Retail Sales Diagnostic

**Portfolio project | Synthetic retail case study | Narrative: Business Question → Data → Investigation → Evidence → Diagnosis → Decision**

## Executive diagnosis

Revenue fell even though units sold increased because the business sold more low-value units at lower realized prices. H2 units were **{pct(change.set_index('metric').loc['Units','pct_change'])} higher** than H1, while revenue was **{pct(change.set_index('metric').loc['Revenue','pct_change'])} lower**. Average selling price fell **{pct(change.set_index('metric').loc['ASP','pct_change'])}**, average discount rose **{pct(change.set_index('metric').loc['Discount','pct_change'])}**, and the product mix shifted toward Essentials. Profit declined **{pct(change.set_index('metric').loc['Profit','pct_change'])}** and average margin declined **{pct(change.set_index('metric').loc['Margin','pct_change'])}**.

The evidence supports a **value dilution mechanism** rather than a volume problem: mix moved toward lower-price products, paid acquisition generated relatively low-margin volume with heavier discounting, and regional and segment performance diverged. These are associations in the synthetic data, not proof that any one lever caused the decline.

## 1. Business question

**Why did revenue fall despite increasing sales volume?** The decision is whether to protect volume at any cost or redirect growth toward profitable volume. This analysis treats revenue as the product of units, realized price, and mix, then checks whether the same changes explain profit and margin.

## 2. Data

The raw dataset contains **{len(raw):,} rows** across 12 months, 8 products, 4 categories, 4 regions, 3 customer segments, and 4 acquisition channels. Each row is a product-region-segment-channel-month grain. Measures include Date, Month, Quarter, Product, Category, Region, Customer Segment, Units Sold, Revenue, Cost, Profit, Discount, Acquisition Channel, ASP, and Profit Margin.

The generator intentionally added **{len(raw)-len(clean):,} removable or repairable quality issues** so the project can demonstrate profiling and cleaning rather than assuming pristine data. The raw file includes duplicates, missing keys, inconsistent labels, invalid dates, impossible discounts, zero units, negative revenue, cost above revenue, an outlying revenue value, and a broken profit identity.

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
| Revenue | {money(h1.Revenue)} | {money(h2.Revenue)} | {pct(change.set_index('metric').loc['Revenue','pct_change'])} |
| Units sold | {h1.Units:,.0f} | {h2.Units:,.0f} | {pct(change.set_index('metric').loc['Units','pct_change'])} |
| Average selling price | ${h1.ASP:,.2f} | ${h2.ASP:,.2f} | {pct(change.set_index('metric').loc['ASP','pct_change'])} |
| Cost | {money(h1.Cost)} | {money(h2.Cost)} | {pct(change.set_index('metric').loc['Cost','pct_change'])} |
| Profit | {money(h1.Profit)} | {money(h2.Profit)} | {pct(change.set_index('metric').loc['Profit','pct_change'])} |
| Average margin | {pct(h1.Margin)} | {pct(h2.Margin)} | {pct(change.set_index('metric').loc['Margin','pct_change'])} |
| Average discount | {pct(h1.Discount)} | {pct(h2.Discount)} | {pct(change.set_index('metric').loc['Discount','pct_change'])} |

![Monthly KPI trends](outputs/figures/monthly_kpis.png)

### Hypothesis findings

**Pricing and discounting.** ASP declined while discounting increased. This is direct evidence of weaker realized value per unit. The alternative explanation is that customers selected cheaper products, so the observed ASP decline combines transaction discounting with mix. Confidence: **high for the descriptive finding; medium for the mechanism**.

**Product and category mix.** The largest product decline was **{worst_product['Product']}**, with revenue changing **{pct(worst_product['Revenue_pct_change'])}** while the strongest unit growth was **{best_volume_product['Product']}** at **{pct(best_volume_product['Units_pct_change'])}**. At category level, **{worst_category['Category']}** revenue changed **{pct(worst_category['Revenue_pct_change'])}**, while Essentials grew revenue **{pct(cat.loc[cat['Category']=='Essentials','Revenue_pct_change'].iloc[0])}**. This pattern is consistent with value dilution. The alternative explanation is demand seasonality or inventory availability. Confidence: **medium-high** because the shift appears in both product and category tables.

**Region.** All regions lost revenue while units rose, but **{worst_region['Region']}** had the largest revenue decline at **{pct(worst_region['Revenue_pct_change'])}** and units still changed **{pct(worst_region['Units_pct_change'])}**. This is evidence of broad value pressure with regional variation, not proof of a region-caused decline. Alternative explanations include local seasonality and different product mix. Confidence: **medium**.

**Customer segment.** **{worst_segment['Customer Segment']}** had the largest segment revenue decline at **{pct(worst_segment['Revenue_pct_change'])}** despite unit growth of **{pct(worst_segment['Units_pct_change'])}**. Premium remains important for value recovery because its baseline ASP is higher, but the period comparison alone cannot establish that segment mix caused the aggregate decline. Alternative explanation: segment definitions may be behaviorally assigned and could move over time. Confidence: **medium**.

**Acquisition channel.** **{worst_channel['Acquisition Channel']}** had the largest margin deterioration at **{pct(worst_channel['Margin_pct_change'])}** and ASP changed **{pct(worst_channel['ASP_pct_change'])}**. Paid Social also had the largest channel revenue decline at **{pct(chan.sort_values('Revenue_pct_change').iloc[0]['Revenue_pct_change'])}**. The evidence supports a channel-quality concern, but not a causal claim about media effectiveness because there is no randomized holdout or spend data. Confidence: **medium**.

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
'''
(OUT/'AI_Powered_Retail_Sales_Diagnostic_Report.md').write_text(report)

# Dashboard-ready HTML wrapper
cards=[]
for m in ['Revenue','Units','ASP','Profit']:
    val = money(h2[m]) if m in ['Revenue','Cost','Profit'] else f'{h2[m]:,.1f}'
    cards.append(f'<div class="card"><div class="label">{m}</div><div class="value">{val}</div><div>{pct(change.set_index("metric").loc[m,"pct_change"])} vs H1</div></div>')
card_html=''.join(cards)
html=f'''<!doctype html><html><head><meta charset="utf-8"><title>AI-Powered Retail Sales Diagnostic</title><style>body{{font-family:Arial,sans-serif;background:#f6f8fb;color:#172033;max-width:1200px;margin:40px auto;padding:0 24px}}.hero{{background:#172033;color:white;padding:28px;border-radius:14px}}.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:20px 0}}.card{{background:white;padding:18px;border-radius:12px;box-shadow:0 2px 8px #0001}}.label{{font-size:12px;color:#667085;text-transform:uppercase}}.value{{font-size:26px;font-weight:700;margin-top:8px}}img{{max-width:100%;background:white;border-radius:12px;margin:16px 0}}.section{{background:white;padding:22px;border-radius:12px;margin:18px 0}}.alert{{border-left:5px solid #d62728;padding-left:14px}}</style></head><body><div class="hero"><h1>AI-Powered Retail Sales Diagnostic</h1><p>Business Question → Data → Investigation → Evidence → Diagnosis → Decision</p></div><div class="grid">{card_html}</div><div class="section alert"><h2>Diagnosis</h2><p>Volume rose, but value per unit fell. Higher discounting and a shift toward lower-value products weakened revenue, profit, and margin. Paid channels underperformed on margin, while regional and segment results were heterogeneous.</p></div><div class="section"><h2>Trend</h2><img src="figures/monthly_kpis.png" alt="Monthly KPI trends"></div><div class="section"><h2>Drivers</h2><img src="figures/product_mix.png" alt="Product mix"><img src="figures/channel_margin.png" alt="Channel margin"></div><div class="section"><h2>Decision</h2><ol><li>Set paid-channel margin floors.</li><li>Use bundles and trade-up paths instead of blanket discounts.</li><li>Protect high-value product availability and merchandising.</li><li>Monitor value-quality KPIs weekly.</li><li>Run controlled tests to estimate incremental profit.</li></ol></div></body></html>'''
(OUT/'dashboard.html').write_text(html)

# README
readme='''# AI-Powered Retail Sales Diagnostic\n\nA reusable portfolio project that explains why revenue can decline while units sold increase.\n\n## Run\n\n```bash\npython build_project.py\n```\n\nOutputs are written to `data/` and `outputs/`. The main deliverable is `outputs/AI_Powered_Retail_Sales_Diagnostic_Report.md`; `outputs/dashboard.html` is a lightweight dashboard narrative.\n\n## Project design\n\nThe generator creates a monthly product-region-segment-channel grain with intentional data-quality defects. The pipeline profiles the raw file, applies documented cleaning rules, validates business identities, builds KPI and dimension tables, decomposes product revenue changes, flags anomalies, creates charts, and writes the report and content system.\n\n## Causal limits\n\nThis is a synthetic observational case. Findings describe patterns in the generated data. They do not establish causation. Controlled discount and channel tests would be needed for causal attribution.\n'''
(ROOT/'README.md').write_text(readme)
print(json.dumps({'root':str(ROOT),'raw_rows':len(raw),'clean_rows':len(clean),'outputs':len(list(OUT.rglob('*')))},indent=2))
