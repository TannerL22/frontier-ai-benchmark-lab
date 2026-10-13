"""Observatory design system and view adapters; no second calculation engine.

UI dependencies are imported lazily so CSV and catalog adapters stay lightweight.
All interpolated content is escaped, including source and reviewer supplied text.
"""
from io import StringIO
import csv
from html import escape

COLORS = ["#9b9cff", "#55d6be", "#e9b969", "#7eb7f8", "#cf9bf5", "#ee8ea6", "#c5cfdd", "#77c7d9"]

LAB_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
:root {
  --bg-canvas:#0b0e14; --bg-surface:#11151e; --bg-elevated:#181d29;
  --border-subtle:#272e3c; --text-primary:#eef0f7; --text-secondary:#a0aabc;
  --accent-primary:#9b9cff; --accent-emerald:#55d6be; --accent-amber:#e9b969; --accent-rose:#ee8ea6;
  --font-ui:'Inter',system-ui,sans-serif; --font-mono:'JetBrains Mono',monospace;
}
.stApp {background:var(--bg-canvas); color:var(--text-primary); font-family:var(--font-ui)}
[data-testid="stMainBlockContainer"] {max-width:1480px; padding:2.4rem 3rem 4rem}
[data-testid="stVerticalBlock"] {gap:1rem}
[data-testid="stSidebar"] {background:var(--bg-surface); border-right:1px solid var(--border-subtle)}
[data-testid="stSidebarUserContent"] {padding-top:2rem}
[data-testid="stHeader"] {background:transparent}
#MainMenu, footer, [data-testid="stToolbarActions"], [data-testid="stAppDeployButton"] {display:none}
h1,h2,h3,h4 {font-family:var(--font-ui); letter-spacing:-.035em; color:var(--text-primary)}
h1 {font-weight:700!important; font-size:2rem!important; padding-top:.25rem!important}
h2 {font-size:1.4rem!important} h3 {font-size:1.1rem!important}
p,li {line-height:1.65} [data-testid="stCaptionContainer"] {color:var(--text-secondary)}
code,pre,[data-testid="stDataFrame"], [data-testid="stMetricValue"] {font-family:var(--font-mono); font-variant-numeric:tabular-nums}
[data-testid="stDataFrame"] {border:1px solid var(--border-subtle); border-radius:10px; overflow:hidden}
[data-testid="stPlotlyChart"] {border:1px solid var(--border-subtle); border-radius:14px; overflow:hidden; background:var(--bg-surface)}
[data-testid="stExpander"], [data-testid="stForm"], [data-testid="stVerticalBlockBorderWrapper"] {border-color:var(--border-subtle)!important; border-radius:12px}
[data-testid="stAlert"] {border:1px solid var(--border-subtle); border-radius:10px; font-size:.9rem; background:var(--bg-surface)!important}
[data-testid="stAlertContainer"] {background:transparent!important}
[data-testid="stAlert"]:has([data-testid="stAlertContentWarning"]) {border-color:#e9b96940; background:#e9b96908!important}
[data-testid="stAlert"]:has([data-testid="stAlertContentError"]) {border-color:#ee8ea650; background:#ee8ea608!important}
[data-testid="stAlert"] p {font-size:.84rem; color:var(--text-secondary)}
[data-testid="stButton"] button, [data-testid="stDownloadButton"] button, [data-testid="stLinkButton"] a {border-radius:8px; transition:background .15s,border-color .15s; font-weight:500}
[data-testid="stButton"] button:hover, [data-testid="stDownloadButton"] button:hover {border-color:var(--accent-primary)}
[data-testid="stSidebar"] [role="radiogroup"] {gap:.25rem}
[data-testid="stSidebar"] [role="radiogroup"] label {padding:.4rem .65rem; border-radius:7px; transition:background .15s}
[data-testid="stSidebar"] [role="radiogroup"] label:hover {background:var(--bg-elevated)}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {background:#9b9cff15; color:var(--accent-primary)}
[data-baseweb="tab-list"] {gap:5px; background:var(--bg-surface); border:1px solid var(--border-subtle); border-radius:10px; padding:5px; flex-wrap:wrap}
[data-baseweb="tab"] {height:38px; padding:0 16px; border-radius:7px; color:var(--text-secondary); transition:background .15s}
[data-baseweb="tab"][aria-selected="true"] {background:var(--bg-elevated); color:var(--text-primary)}
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] {display:none}
.lab-brand {display:flex; gap:10px; align-items:center; margin-bottom:1.5rem; font-weight:600; letter-spacing:-.02em}
.lab-mark {display:grid; place-items:center; width:30px; height:30px; background:#9b9cff17; border:1px solid #9b9cff55; border-radius:8px; color:var(--accent-primary); font-size:19px}
.lab-eyebrow {font-size:.65rem; font-weight:600; letter-spacing:.16em; text-transform:uppercase; color:var(--text-secondary)}
.lab-hero {position:relative; background:radial-gradient(ellipse at 85% 0%,#9b9cff14,transparent 65%),var(--bg-surface); border:1px solid var(--border-subtle); border-radius:16px; padding:27px 30px; margin-bottom:.35rem; overflow:hidden}
.lab-hero-top {display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap}
.lab-hero h1 {font-size:clamp(1.65rem,3vw,2.55rem)!important; margin:12px 0 7px; padding:0!important; line-height:1.15}
.lab-hero p {margin:0; max-width:830px; color:var(--text-secondary); font-size:.9rem}
.lab-context {display:flex; gap:18px; flex-wrap:wrap; padding-top:19px; margin-top:20px; border-top:1px solid var(--border-subtle); color:var(--text-secondary); font-size:.73rem}
.lab-mono {font-family:var(--font-mono); font-variant-numeric:tabular-nums}
.lab-badge {display:inline-flex; align-items:center; gap:6px; font-size:.66rem; font-weight:500; line-height:1.5; padding:4px 9px; border-radius:5px; color:var(--accent-primary); background:#9b9cff14; border:1px solid #9b9cff38; white-space:normal}
.lab-badge::before {content:''; width:5px; height:5px; border-radius:50%; background:currentColor; flex-shrink:0}
.lab-badge.verified {color:var(--accent-emerald); background:#55d6be10; border-color:#55d6be35}
.lab-badge.pending {color:var(--accent-amber); background:#e9b96910; border-color:#e9b96935}
.lab-badge.issue {color:var(--accent-rose); background:#ee8ea610; border-color:#ee8ea635}
.lab-kpis {display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:12px; margin:8px 0 12px}
.lab-kpi {padding:20px; background:linear-gradient(145deg,#181d2944,transparent),var(--bg-surface); border:1px solid var(--border-subtle); border-radius:12px; min-width:0}
.lab-kpi > .lab-eyebrow {min-height:2.8em; line-height:1.4}
.lab-kpi-value {font-family:var(--font-mono); font-size:clamp(1.5rem,2.5vw,2rem); font-weight:500; letter-spacing:-.06em; line-height:1.35; margin:11px 0 10px; font-variant-numeric:tabular-nums; overflow-wrap:anywhere}
.lab-kpi-caption {font-size:.72rem; line-height:1.6; color:var(--text-secondary); margin-top:10px}
.lab-section {display:flex; align-items:baseline; gap:16px; justify-content:space-between; flex-wrap:wrap; margin:12px 0 2px}
.lab-section h2 {font-size:1.1rem!important; margin:0; padding:0!important; letter-spacing:-.02em}
.lab-section span {font-size:.7rem; color:var(--text-secondary)}
.lab-callout {display:flex; gap:16px; align-items:flex-start; padding:17px 20px; background:var(--bg-surface); border:1px solid var(--border-subtle); border-radius:10px; margin-bottom:8px}
.lab-callout p {margin:0; font-size:.82rem; color:var(--text-secondary)}
.lab-callout strong {display:block; color:var(--text-primary); font-weight:500; margin-bottom:4px}
.lab-digest {color:var(--text-secondary); font: .69rem var(--font-mono); overflow-wrap:anywhere; line-height:1.7}
@media (max-width:850px) {
 [data-testid="stMainBlockContainer"] {padding:1.5rem 1rem 3rem}
 .lab-hero {padding:22px 20px} .lab-kpis {grid-template-columns:repeat(2,minmax(0,1fr))}
 .lab-kpi {padding:15px} .lab-context {gap:10px} .lab-callout {flex-direction:column; gap:8px}
}
@media (prefers-reduced-motion:reduce) {*,*::before,*::after {transition:none!important}}
"""


def inject_lab_theme_css():
    import streamlit as st
    st.html("<style>" + LAB_CSS + "</style>")


def badge(label, tone="neutral"):
    tone = tone if tone in {"neutral", "verified", "pending", "issue"} else "neutral"
    return f'<span class="lab-badge {tone}">{escape(str(label))}</span>'


def render_hero(title, subtitle, *, eyebrow="Frontier AI · Research observatory", release="", status="", tone="verified", context=()):
    import streamlit as st
    labels = '<span class="lab-mono">' + badge(release) + '</span> ' + badge(status, tone)
    details = "".join(f'<span>{escape(str(label))} <span class="lab-mono">{escape(str(value))}</span></span>' for label, value in context)
    st.html(f'<header class="lab-hero"><div class="lab-hero-top"><span class="lab-eyebrow">{escape(eyebrow)}</span><div>{labels}</div></div>'
            f'<h1>{escape(title)}</h1><p>{escape(subtitle)}</p><div class="lab-context">{details}</div></header>')


def render_kpi_grid(cards):
    """Cards accept label/value/caption and an optional status/tone; values are descriptive."""
    import streamlit as st
    body = "".join(
        f'<article class="lab-kpi"><div class="lab-eyebrow">{escape(str(card["label"]))}</div>'
        f'<div class="lab-kpi-value">{escape(str(card["value"]))}</div>'
        + (badge(card["status"], card.get("tone", "neutral")) if card.get("status") else "")
        + f'<div class="lab-kpi-caption">{escape(str(card.get("caption", "")))}</div></article>'
        for card in cards)
    st.html('<section class="lab-kpis" aria-label="Key indicators">' + body + '</section>')


def render_section(title, detail=""):
    import streamlit as st
    st.html(f'<div class="lab-section"><h2>{escape(title)}</h2><span>{escape(detail)}</span></div>')


def render_audit_callout(title, text, status="Verified", tone="verified", digest=""):
    import streamlit as st
    fingerprint = f'<div class="lab-digest">SHA-256 · {escape(digest)}</div>' if digest else ""
    st.html(f'<div class="lab-callout">{badge(status, tone)}<div><p><strong>{escape(title)}</strong>{escape(text)}</p>{fingerprint}</div></div>')


def theme_plotly(fig, *, height=440):
    """One theme for every chart; preserves traces and analytical values."""
    domain_colors = dict(zip(("Professional", "Coding", "Science", "Knowledge", "Context", "Multimodal", "Games"), COLORS))
    for index, trace in enumerate(fig.data):
        if trace.type in {"bar", "scatter"} and getattr(trace, "mode", None) != "lines":
            if isinstance(trace.marker.color, str) or trace.marker.color is None:
                trace.marker.color = domain_colors.get(trace.name, COLORS[index % len(COLORS)])
    fig.update_layout(
        template="plotly_dark", colorway=COLORS, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", size=12, color="#a0aabc"),
        title=dict(text=fig.layout.title.text or "", font=dict(size=15, color="#eef0f7")), height=height,
        margin=dict(t=55 if fig.layout.title.text else 30, l=25, r=25, b=40),
        hoverlabel=dict(bgcolor="#181d29", bordercolor="#303849", font=dict(family="Inter", color="#eef0f7")),
        legend=dict(title_text="", orientation="h", y=-.2),
    )
    fig.update_xaxes(gridcolor="#272e3c", zerolinecolor="#394153", tickfont=dict(family="JetBrains Mono", size=10))
    fig.update_yaxes(gridcolor="#272e3c", zerolinecolor="#394153", tickfont=dict(size=11))
    return fig


def identity_columns():
    import streamlit as st
    return {"Rank": st.column_config.NumberColumn(pinned=True, width="small", format="%d"),
            "Model": st.column_config.TextColumn(pinned=True, width="medium"),
            "Benchmark": st.column_config.TextColumn(pinned=True, width="medium")}


def rank_shift(value):
    """Positive means moving up relative to the full-roster baseline."""
    return f"▲ +{value}" if value > 0 else f"▼ {value}" if value < 0 else "—"


def csv_export(rows):
    if not rows:
        return ""
    stream = StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def system_record(evidence, benchmark, model):
    if evidence.catalog:
        return evidence.catalog.details(benchmark.id, model)
    return {"evidence_status": "historical_record_not_individually_rechecked_here",
            "original_run_id": "unknown", "inclusion_reason": "Frozen historical evidence",
            "system": {"reasoning_effort": "unknown", "harness": "unknown", "fallback_policy": "unknown",
                       "model_snapshot": "unknown", "endpoint": "unknown", "resource_budget": "unknown",
                       "evaluation_date": "unknown", "reported_configuration": benchmark.config},
            "source": {"url": benchmark.source, "observed_on": "unknown", "capture_type": "inherited_link",
                       "qualification": benchmark.provenance},
            "uncertainty": {"type": "not_captured", "qualification": "Historical source uncertainty not reconstructed"}}
