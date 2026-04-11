"""
ERCOT BESS Valuation Dashboard
Run with:  streamlit run dashboard/app.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

import config
from data.loader import load_lmp
from revenue.calculator import simulate_annual_revenue, annualize
from valuation.dcf import build_cash_flows, compute_returns, irr_sensitivity


# ── Page config ───────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ERCOT BESS Valuation",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom theme ──────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Base ── */
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background-color: #0b0f1a; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background-color: #111827;
    border-right: 1px solid #1f2937;
}
[data-testid="stSidebar"] .stMarkdown h1,
[data-testid="stSidebar"] .stMarkdown h2,
[data-testid="stSidebar"] .stMarkdown h3 { color: #e2e8f0; font-size: 0.75rem; letter-spacing: 0.08em; text-transform: uppercase; }
[data-testid="stSidebar"] label { color: #94a3b8 !important; font-size: 0.78rem; }
[data-testid="stSidebar"] .stSlider [data-testid="stTickBar"] { display: none; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background-color: #111827;
    border-bottom: 1px solid #1f2937;
    gap: 0;
    padding: 0;
}
.stTabs [data-baseweb="tab"] {
    background-color: transparent;
    color: #64748b;
    border-radius: 0;
    padding: 0.75rem 1.5rem;
    font-size: 0.82rem;
    font-weight: 500;
    letter-spacing: 0.02em;
    border-bottom: 2px solid transparent;
}
.stTabs [data-baseweb="tab"]:hover { color: #e2e8f0; background-color: transparent; }
.stTabs [aria-selected="true"] {
    color: #10b981 !important;
    background-color: transparent !important;
    border-bottom: 2px solid #10b981 !important;
}

/* ── Metric cards ── */
[data-testid="stMetric"] {
    background-color: #111827;
    border: 1px solid #1f2937;
    border-radius: 6px;
    padding: 1rem 1.25rem;
}
[data-testid="stMetricLabel"]  { color: #64748b !important; font-size: 0.72rem !important; letter-spacing: 0.06em; text-transform: uppercase; }
[data-testid="stMetricValue"]  { color: #f1f5f9 !important; font-size: 1.5rem !important; font-weight: 600; font-family: 'JetBrains Mono', monospace; }
[data-testid="stMetricDelta"]  { color: #10b981 !important; font-size: 0.78rem !important; }

/* ── Dataframe ── */
[data-testid="stDataFrame"] { background-color: #111827; border-radius: 6px; }
.dvn-scroller { background-color: #111827 !important; }

/* ── Info / caption boxes ── */
[data-testid="stAlert"] {
    background-color: #0f2231;
    border: 1px solid #164e63;
    border-radius: 6px;
    color: #7dd3fc;
}
.stCaption { color: #475569 !important; font-size: 0.75rem !important; }

/* ── General text ── */
h1 { color: #f1f5f9 !important; font-weight: 700; letter-spacing: -0.02em; }
h2 { color: #e2e8f0 !important; font-weight: 600; font-size: 1.1rem !important; letter-spacing: -0.01em; }
h3 { color: #cbd5e1 !important; font-weight: 500; font-size: 0.9rem !important; }
p, li, .stMarkdown { color: #94a3b8; font-size: 0.85rem; line-height: 1.6; }
hr { border-color: #1f2937 !important; }

/* ── Selectbox / inputs ── */
[data-testid="stSelectbox"] > div > div {
    background-color: #1f2937;
    border: 1px solid #374151;
    color: #e2e8f0;
    border-radius: 4px;
}
</style>
""", unsafe_allow_html=True)


# ── Header banner ─────────────────────────────────────────────────────────
st.markdown("""
<div style="
    background: linear-gradient(90deg, #0f2231 0%, #0b1a2e 60%, #0b0f1a 100%);
    border-bottom: 1px solid #164e63;
    padding: 1.5rem 2rem 1.25rem;
    margin: -1rem -1rem 1.5rem -1rem;
">
    <div style="display:flex; align-items:center; gap:0.75rem; margin-bottom:0.25rem;">
        <span style="font-size:1.5rem;">⚡</span>
        <span style="font-size:1.4rem; font-weight:700; color:#f1f5f9; letter-spacing:-0.02em;">
            ERCOT BESS Valuation
        </span>
        <span style="
            background:#164e63; color:#38bdf8; font-size:0.65rem;
            font-weight:600; letter-spacing:0.08em; padding:2px 8px;
            border-radius:99px; text-transform:uppercase; margin-left:0.5rem;
        ">ERCOT · Real-Time Market</span>
    </div>
    <p style="color:#475569; font-size:0.78rem; margin:0; font-family:'JetBrains Mono',monospace;">
        Battery dispatch simulation · Revenue stacking · Acquisition underwriting
        &nbsp;|&nbsp; Summer 2024 · Winter 2024-25 · Summer 2025
    </p>
</div>
""", unsafe_allow_html=True)


# ── Plotly dark template ───────────────────────────────────────────────────
CHART_THEME = dict(
    template="plotly_dark",
    paper_bgcolor="#111827",
    plot_bgcolor="#111827",
    font=dict(family="Inter", color="#94a3b8", size=11),
)

# ── Sidebar ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Season & Hub")
    season = st.selectbox("Season", list(config.SEASONS.keys()),
                          index=list(config.SEASONS.keys()).index(config.DEFAULT_SEASON),
                          label_visibility="collapsed")
    hub = st.selectbox("Hub", config.HUBS, index=config.HUBS.index(config.DEFAULT_HUB),
                       label_visibility="collapsed")

    st.divider()
    st.markdown("### Battery Specs")
    capacity_mwh = st.slider("Capacity (MWh)",    20,  500, config.CAPACITY_MWH,  step=10)
    power_mw     = st.slider("Power Rating (MW)",  10,  250, config.POWER_MW,      step=5)
    rte          = st.slider("Round-Trip Eff. (%)", 70,  95, int(config.ROUND_TRIP_EFF * 100)) / 100
    soc_min      = st.slider("Min SoC (%)",          5,  20, int(config.SOC_MIN * 100)) / 100
    soc_max      = st.slider("Max SoC (%)",          80, 95, int(config.SOC_MAX * 100)) / 100
    annual_deg   = st.slider("Degradation (%/yr)",   1,   4, int(config.ANNUAL_DEGRADATION * 100)) / 100

    st.divider()
    st.markdown("### Dispatch")
    charge_pct     = st.slider("Charge threshold (pct)",    10, 40, config.CHARGE_PCT)
    discharge_pct  = st.slider("Discharge threshold (pct)", 60, 90, config.DISCHARGE_PCT)
    ancillary_rate = st.slider("Ancillary rate ($/MW-hr)",   3, 20, int(config.ANCILLARY_RATE_PER_MW_HR))

    st.divider()
    st.markdown("### Project Finance")
    capex_per_kwh    = st.slider("CapEx ($/kWh)",     180, 380, config.CAPEX_PER_KWH,    step=10)
    opex_per_mw_year = st.slider("OpEx ($/MW/yr)",  5_000, 25_000, config.OPEX_PER_MW_YEAR, step=1_000)
    debt_ratio       = st.slider("Debt Ratio (%)",     30,  70, int(config.DEBT_RATIO * 100)) / 100
    debt_rate        = st.slider("Debt Rate (%)",       4,  10, int(config.DEBT_RATE  * 100), step=1) / 100
    project_life     = st.slider("Project Life (yrs)", 15,  25, config.PROJECT_LIFE)


# ── Data helpers ──────────────────────────────────────────────────────────
@st.cache_data
def get_lmp(hub, season):
    return load_lmp(hub, season)

def run_season(hub, season):
    lmp_df = get_lmp(hub, season)
    result = simulate_annual_revenue(
        lmp=lmp_df["lmp"],
        power_mw=power_mw, capacity_mwh=capacity_mwh,
        round_trip_eff=rte, soc_min=soc_min, soc_max=soc_max,
        annual_degradation=annual_deg,
        charge_pct=charge_pct, discharge_pct=discharge_pct,
        ancillary_rate=ancillary_rate,
    )
    ann      = annualize(result, data_months=3)
    dispatch = result["dispatch_df"].copy()
    dispatch["datetime"] = lmp_df["datetime"].values
    return lmp_df, ann, dispatch

lmp_df, annual, dispatch_df = run_season(hub, season)
lmp_series = lmp_df["lmp"]


# ── Colour constants ──────────────────────────────────────────────────────
C_GREEN  = "#10b981"
C_AMBER  = "#f59e0b"
C_BLUE   = "#38bdf8"
C_RED    = "#f87171"
C_MUTED  = "#334155"

ACTION_COLOUR = {"charge": C_BLUE, "discharge": C_GREEN, "idle": C_MUTED}


# ═══════════════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4 = st.tabs([
    "  Dispatch Simulation  ",
    "  Revenue Analysis  ",
    "  Seasonal Comparison  ",
    "  Acquisition Valuation  ",
])


# ── Tab 1: Dispatch ───────────────────────────────────────────────────────
with tab1:
    st.markdown(f"#### Dispatch Simulation &nbsp;·&nbsp; {season} &nbsp;·&nbsp; {hub}")
    st.markdown(
        "A **bang-bang controller with deadband** — a control-systems concept applied to price-driven "
        "dispatch. Charge when price is below the low threshold, discharge above the high threshold, "
        "hold idle (earning ancillary services capacity payments) in the deadband."
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Usable Capacity",      f"{capacity_mwh * (soc_max - soc_min):.0f} MWh")
    col2.metric("Round-Trip Eff.",       f"{rte*100:.0f}%")
    col3.metric("SoC Window",           f"{int(soc_min*100)} – {int(soc_max*100)}%")
    col4.metric("Battery Type",          f"C{power_mw/capacity_mwh:.1f}  ({capacity_mwh/power_mw:.0f}-hr)")

    # Most volatile week
    weekly_vol      = dispatch_df.set_index("datetime")["lmp"].resample("W").std()
    best_week_start = weekly_vol.idxmax() - pd.Timedelta(days=6)
    wk = dispatch_df[
        (dispatch_df["datetime"] >= best_week_start) &
        (dispatch_df["datetime"] <  best_week_start + pd.Timedelta(days=7))
    ]

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.6, 0.4],
        subplot_titles=["LMP  ($/MWh)", "State of Charge  (%)"],
        vertical_spacing=0.06,
    )

    for action, colour in ACTION_COLOUR.items():
        mask = wk["action"] == action
        fig.add_trace(go.Bar(
            x=wk.loc[mask, "datetime"], y=wk.loc[mask, "lmp"],
            marker_color=colour, name=action.capitalize(), legendgroup=action,
        ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=wk["datetime"], y=wk["soc"] * 100,
        line=dict(color=C_GREEN, width=1.5),
        fill="tozeroy", fillcolor="rgba(16,185,129,0.08)",
        name="SoC %", showlegend=False,
    ), row=2, col=1)

    for level, colour, label in [
        (soc_min*100, C_RED,   "Min SoC"),
        (soc_max*100, C_AMBER, "Max SoC"),
    ]:
        fig.add_hline(y=level, line_dash="dot", line_color=colour,
                      annotation_text=label, annotation_font_color=colour,
                      row=2, col=1)

    fig.update_layout(
        height=480, barmode="relative",
        legend=dict(orientation="h", y=1.05, x=0, font_size=11),
        margin=dict(l=0, r=0, t=40, b=0),
        **CHART_THEME,
    )
    fig.update_yaxes(gridcolor="#1f2937", zerolinecolor="#1f2937")
    fig.update_xaxes(gridcolor="#1f2937")
    st.plotly_chart(fig, use_container_width=True)

    st.info(
        "**Why SoC limits matter:** Operating a Li-ion cell below 10% or above 90% "
        "accelerates electrode degradation and shortens calendar life. "
        "Enforcing these bounds in the model produces more conservative — and more credible — "
        "revenue estimates for a 20-year underwrite."
    )


# ── Tab 2: Revenue ────────────────────────────────────────────────────────
with tab2:
    st.markdown(f"#### Revenue Stack &nbsp;·&nbsp; {season} &nbsp;·&nbsp; {hub}")
    st.markdown(
        "BESS projects earn from **two simultaneous streams**. Energy arbitrage is the visible one; "
        "ancillary services capacity payments are what actually make the project pencil at PE hurdle rates."
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Energy Arbitrage (ann.)",   f"${annual['energy_revenue']    / 1e6:.2f}M / yr")
    col2.metric("Ancillary Services (ann.)", f"${annual['ancillary_revenue'] / 1e6:.2f}M / yr")
    col3.metric("Total Revenue (ann.)",      f"${annual['total_revenue']     / 1e6:.2f}M / yr",
                delta=f"${annual['total_revenue'] / power_mw / 1e3:.0f}k per MW")

    # Monthly stacked revenue
    dispatch_df["month"] = pd.to_datetime(dispatch_df["datetime"]).dt.strftime("%b %Y")
    m_energy = dispatch_df.groupby("month")["energy_revenue"].sum().reset_index()
    m_ancill = dispatch_df.groupby("month").apply(
        lambda g: (g["action"] == "idle").sum() * power_mw * ancillary_rate
    ).reset_index(name="ancillary_revenue")
    m_rev = m_energy.merge(m_ancill, on="month")

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(name="Energy Arbitrage",   x=m_rev["month"], y=m_rev["energy_revenue"],    marker_color=C_BLUE,  marker_line_width=0))
    fig2.add_trace(go.Bar(name="Ancillary Services", x=m_rev["month"], y=m_rev["ancillary_revenue"], marker_color=C_AMBER, marker_line_width=0))
    fig2.update_layout(
        barmode="stack", height=340,
        yaxis_title="Revenue  ($)",
        title=dict(text="Monthly Revenue by Stream", font_size=12, font_color="#94a3b8"),
        legend=dict(orientation="h", y=1.08),
        margin=dict(l=0, r=0, t=50, b=0),
        **CHART_THEME,
    )
    fig2.update_yaxes(gridcolor="#1f2937")
    fig2.update_xaxes(gridcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig2, use_container_width=True)

    # LMP distribution
    st.markdown("#### LMP Distribution &nbsp;·&nbsp; Dispatch Thresholds")
    low_t  = np.percentile(lmp_series, charge_pct)
    high_t = np.percentile(lmp_series, discharge_pct)

    fig3 = go.Figure()
    fig3.add_trace(go.Histogram(
        x=lmp_series, nbinsx=100,
        marker_color=C_BLUE, marker_line_width=0, opacity=0.7,
        name="LMP frequency",
    ))
    for x, colour, label in [
        (low_t,  C_BLUE,  f"Charge  ≤  ${low_t:.0f}"),
        (high_t, C_GREEN, f"Discharge  ≥  ${high_t:.0f}"),
    ]:
        fig3.add_vline(x=x, line_dash="dash", line_color=colour, line_width=1.5,
                       annotation_text=label, annotation_font_color=colour,
                       annotation_font_size=11)
    fig3.update_layout(
        height=300, showlegend=False,
        xaxis_title="LMP  ($/MWh)", yaxis_title="Count",
        title=dict(text="Price Distribution — deadband between thresholds earns ancillary revenue",
                   font_size=11, font_color="#64748b"),
        margin=dict(l=0, r=0, t=40, b=0),
        **CHART_THEME,
    )
    fig3.update_yaxes(gridcolor="#1f2937")
    fig3.update_xaxes(gridcolor="#1f2937")
    st.plotly_chart(fig3, use_container_width=True)

    st.caption(
        "Ancillary rate is a blended proxy (~$8/MW-hr for ECRS + Reg-Up/Reg-Down) "
        "based on ERCOT published historical clearing price averages. "
        "A production underwriting model uses actual hourly ancillary clearing price time series."
    )


# ── Tab 3: Seasonal Comparison ────────────────────────────────────────────
with tab3:
    st.markdown("#### Seasonal Revenue Comparison &nbsp;·&nbsp; All Three Periods")
    st.markdown(
        "Summer delivers **consistent, predictable** revenue from the solar duck curve. "
        "Winter carries **higher variance** — mild years look similar to summer, "
        "but cold-snap events (cf. Uri 2021, Elliott 2022) can generate multiples of normal revenue. "
        "Both matter for a credible 20-year underwrite."
    )

    season_results = {}
    for s in config.SEASONS:
        _, ann_s, _ = run_season(hub, s)
        season_results[s] = ann_s

    # Summary table
    rows = []
    for s, ann_s in season_results.items():
        cf_s  = build_cash_flows(ann_s["total_revenue"], power_mw, capacity_mwh,
                                 capex_per_kwh, opex_per_mw_year, project_life,
                                 debt_ratio, debt_rate, annual_deg)
        ret_s = compute_returns(cf_s)
        rows.append({
            "Season":                 s,
            "Energy Rev ($M/yr)":     round(ann_s["energy_revenue"]    / 1e6, 2),
            "Ancillary Rev ($M/yr)":  round(ann_s["ancillary_revenue"] / 1e6, 2),
            "Total Rev ($M/yr)":      round(ann_s["total_revenue"]     / 1e6, 2),
            "Annual Cycles":          int(round(ann_s["cycles"])),
            "Equity IRR (%)":         round(ret_s["equity_irr"] * 100, 1),
            "MOIC":                   round(ret_s["moic"], 2),
        })

    summary_df = pd.DataFrame(rows).set_index("Season")
    st.dataframe(summary_df, use_container_width=True)

    # Stacked revenue comparison
    s_list = list(season_results.keys())
    fig5 = go.Figure()
    fig5.add_trace(go.Bar(
        name="Energy Arbitrage", x=s_list,
        y=[season_results[s]["energy_revenue"]    / 1e6 for s in s_list],
        marker_color=C_BLUE, marker_line_width=0,
    ))
    fig5.add_trace(go.Bar(
        name="Ancillary Services", x=s_list,
        y=[season_results[s]["ancillary_revenue"] / 1e6 for s in s_list],
        marker_color=C_AMBER, marker_line_width=0,
    ))
    fig5.update_layout(
        barmode="stack", height=320,
        yaxis_title="Annualised Revenue  ($M/yr)",
        title=dict(text=f"Revenue Stack by Season  ·  {hub}", font_size=12, font_color="#94a3b8"),
        legend=dict(orientation="h", y=1.08),
        margin=dict(l=0, r=0, t=50, b=0),
        **CHART_THEME,
    )
    fig5.update_yaxes(gridcolor="#1f2937")
    fig5.update_xaxes(gridcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig5, use_container_width=True)

    # LMP distribution overlay
    st.markdown(f"#### LMP Distribution Overlay &nbsp;·&nbsp; {hub}")
    SEASON_COLOURS = {
        "Summer 2024":    C_BLUE,
        "Winter 2024-25": "#a78bfa",
        "Summer 2025":    C_GREEN,
    }
    fig6 = go.Figure()
    for s in config.SEASONS:
        lmp_s = get_lmp(hub, s)["lmp"]
        fig6.add_trace(go.Histogram(
            x=lmp_s, name=s, nbinsx=80, opacity=0.5,
            marker_color=SEASON_COLOURS[s], marker_line_width=0,
            histnorm="probability density",
        ))
    fig6.update_layout(
        barmode="overlay", height=320,
        xaxis_title="LMP  ($/MWh)", yaxis_title="Density",
        title=dict(text="Price Distribution by Season  —  wider tail = more arbitrage upside",
                   font_size=11, font_color="#64748b"),
        legend=dict(orientation="h", y=1.08),
        margin=dict(l=0, r=0, t=50, b=0),
        **CHART_THEME,
    )
    fig6.update_yaxes(gridcolor="#1f2937")
    fig6.update_xaxes(gridcolor="#1f2937")
    st.plotly_chart(fig6, use_container_width=True)

    st.info(
        "**Underwriting takeaway:** Use summer data as the P50 revenue base. "
        "Winter upside from a weather event is the P90 scenario — real, but not bankable "
        "without historical precedent at the specific site. "
        "A conservative sponsor underwrites on summer; winter is unlevered upside."
    )


# ── Tab 4: Valuation ──────────────────────────────────────────────────────
with tab4:
    st.markdown(f"#### Acquisition Underwriting &nbsp;·&nbsp; {season} &nbsp;·&nbsp; {hub}")
    st.markdown(
        "Translates simulated revenue into investor-level returns — "
        "the output an acquisitions team produces before committing capital to a BESS asset."
    )

    cf  = build_cash_flows(
        annual_revenue=annual["total_revenue"],
        power_mw=power_mw, capacity_mwh=capacity_mwh,
        capex_per_kwh=capex_per_kwh, opex_per_mw_year=opex_per_mw_year,
        project_life=project_life, debt_ratio=debt_ratio,
        debt_rate=debt_rate, annual_degradation=annual_deg,
    )
    ret = compute_returns(cf)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total CapEx",   f"${cf['capex']/1e6:.1f}M")
    col2.metric("Equity Cheque", f"${cf['equity']/1e6:.1f}M")
    col3.metric("Equity IRR",    f"{ret['equity_irr']*100:.1f}%")
    col4.metric("Equity MOIC",   f"{ret['moic']:.2f}×")

    # IRR heatmap
    st.markdown("#### Equity IRR Sensitivity &nbsp;·&nbsp; CapEx vs Revenue Scenario")
    capex_range = [200, 230, 260, 290, 320]
    price_mults = [0.70, 0.85, 1.00, 1.15, 1.30]
    grid = irr_sensitivity(
        annual_revenue=annual["total_revenue"],
        power_mw=power_mw, capacity_mwh=capacity_mwh,
        opex_per_mw_year=opex_per_mw_year, project_life=project_life,
        debt_ratio=debt_ratio, debt_rate=debt_rate,
        annual_degradation=annual_deg,
        capex_range=capex_range, price_multipliers=price_mults,
    )

    z = [[grid[pm][cpx] * 100 for cpx in capex_range] for pm in price_mults]
    text_vals = [[f"{v:.1f}%" for v in row] for row in z]

    fig7 = go.Figure(go.Heatmap(
        z=z,
        x=[f"${c}/kWh" for c in capex_range],
        y=[f"{int(pm*100)}% rev" for pm in price_mults],
        text=text_vals, texttemplate="%{text}",
        textfont=dict(size=12, family="JetBrains Mono"),
        colorscale=[
            [0.0,  "#7f1d1d"],
            [0.25, "#991b1b"],
            [0.45, "#92400e"],
            [0.55, "#065f46"],
            [0.75, "#047857"],
            [1.0,  "#10b981"],
        ],
        zmin=0, zmax=25,
        showscale=True,
        colorbar=dict(title="IRR %", tickfont_size=10, thickness=12, len=0.8),
    ))
    fig7.update_layout(
        height=310,
        xaxis=dict(title="All-in CapEx  ($/kWh)", side="bottom"),
        yaxis=dict(title="Revenue scenario"),
        margin=dict(l=0, r=60, t=20, b=0),
        **CHART_THEME,
    )
    st.plotly_chart(fig7, use_container_width=True)

    # DCF table
    st.markdown("#### Year-by-Year Cash Flow Schedule")
    dcf_df = pd.DataFrame(cf["rows"]).set_index("Year")
    st.dataframe(dcf_df.style.format("${:,.2f}M"), use_container_width=True)

    st.caption(
        "Pre-tax model — excludes ITC/MACRS. "
        "The IRA's 30% ITC on standalone storage rises to 40% with domestic content qualification "
        "(relevant given domestic content supply arrangements now active across utility-scale BESS projects); tax equity monetisation is a separate structuring layer."
    )
