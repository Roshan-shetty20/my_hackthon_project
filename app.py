"""
Crisis Command — Command Center Dashboard
Resilient Decision Intelligence for Emergency Response

SIMULATION DATA — No real emergency data is used.

Run with:  python -m streamlit run app.py
"""

import json
from pathlib import Path

import streamlit as st

from backend.models import Incident, Unit, RoadCondition, UnitType, UnitStatus
from backend.state import CrisisState, StateHistory
from backend.severity import assess_incident
from backend.planner import generate_candidate_plans
from backend.comparator import (
    compare_and_select,
    generate_why_explanation,
    calculate_decision_confidence,
    calculate_decision_debts,
)
from backend.resilience import evaluate_plan_resilience
from backend.replanner import apply_unit_breakdown, apply_road_block, apply_new_incident
from backend.simulator import DeterministicSimulator

def get_explanation_data(plan, state):
    if plan and hasattr(plan, "ai_explanation") and plan.ai_explanation:
        ai = plan.ai_explanation
        why_not_val = ai.get("why_not_alternatives", {})
        if isinstance(why_not_val, str):
            why_not_val = {p.id: why_not_val for p in state.candidate_plans}
        return {
            "why": ai.get("why_this_plan", ""),
            "tradeoff": ai.get("trade_off", ""),
            "why_not": why_not_val,
            "ai_summary": ai.get("summary", ""),
            "ai_risk": ai.get("risk", ""),
            "is_ai": True
        }
    else:
        return generate_why_explanation(state)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Crisis Command — Resilient Decision Intelligence",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Design system — Professional Command Center
# ---------------------------------------------------------------------------

st.markdown("""
<style>
  /* ── Google Font ── */
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

  /* ── Base ── */
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
  .stApp { background-color: #0d1117; }
  .main .block-container { padding-top: 0.5rem; padding-bottom: 2rem; max-width: 100%; }

  /* ── Header band ── */
  .cc-header {
    background: linear-gradient(135deg, #0f1923 0%, #111827 100%);
    border-bottom: 1px solid #1e3a5f;
    padding: 14px 24px;
    margin: -0.5rem -1rem 1rem -1rem;
    display: flex; align-items: center; justify-content: space-between;
  }
  .cc-title { font-size: 1.5rem; font-weight: 700; color: #e2e8f0; letter-spacing: 0.05em; }
  .cc-subtitle { font-size: 0.75rem; color: #94a3b8; margin-top: 2px; }
  .sim-badge {
    background: #1a2332; border: 1px solid #e97316; border-radius: 4px;
    color: #e97316; font-size: 0.7rem; font-weight: 600; letter-spacing: 0.08em;
    padding: 3px 8px;
  }
  .state-pill {
    background: #1a2332; border: 1px solid #2563eb; border-radius: 4px;
    color: #60a5fa; font-size: 0.75rem; font-weight: 600; padding: 4px 10px;
    font-family: 'JetBrains Mono', monospace;
  }
  .status-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%;
    background: #22c55e; margin-right: 6px; animation: pulse 2s infinite; }
  @keyframes pulse {
    0%,100% { opacity: 1; } 50% { opacity: 0.5; }
  }

  /* ── Command summary strip ── */
  .cmd-strip {
    background: #111827; border: 1px solid #1e293b; border-radius: 8px;
    padding: 12px 20px; margin-bottom: 16px;
    display: flex; gap: 32px; align-items: center;
  }
  .cmd-metric { text-align: center; }
  .cmd-metric-val { font-size: 1.6rem; font-weight: 700; color: #e2e8f0; line-height: 1; }
  .cmd-metric-val.critical { color: #ef4444; }
  .cmd-metric-val.ok { color: #22c55e; }
  .cmd-metric-val.warn { color: #f59e0b; }
  .cmd-metric-label { font-size: 0.65rem; color: #64748b; letter-spacing: 0.08em;
    text-transform: uppercase; margin-top: 2px; }

  /* ── Flow banner ── */
  .flow-banner {
    display: flex; align-items: center; justify-content: center; gap: 8px;
    padding: 8px 16px; background: #0f1923;
    border: 1px solid #1e293b; border-radius: 6px; margin-bottom: 12px;
  }
  .flow-step {
    font-size: 0.7rem; font-weight: 600; letter-spacing: 0.1em;
    padding: 4px 10px; border-radius: 3px; color: #94a3b8; background: #1e293b;
  }
  .flow-step.active { color: #e2e8f0; background: #1e3a5f; border: 1px solid #2563eb; }
  .flow-step.done { color: #22c55e; background: #052e16; border: 1px solid #166534; }
  .flow-arrow { color: #334155; font-size: 0.8rem; }

  /* ── Incident cards ── */
  .inc-card {
    background: #111827; border: 1px solid #1e293b; border-radius: 8px;
    padding: 12px 14px; margin-bottom: 8px;
  }
  .inc-card.critical { border-left: 3px solid #ef4444; }
  .inc-card.high     { border-left: 3px solid #f59e0b; }
  .inc-card.medium   { border-left: 3px solid #eab308; }
  .inc-card.low      { border-left: 3px solid #22c55e; }
  .inc-id { font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #64748b; }
  .inc-type { font-size: 0.9rem; font-weight: 600; color: #e2e8f0; margin: 2px 0; }
  .inc-loc { font-size: 0.72rem; color: #94a3b8; }
  .urg-badge {
    display: inline-block; font-size: 0.6rem; font-weight: 700; letter-spacing: 0.08em;
    padding: 2px 7px; border-radius: 3px; margin-right: 4px;
  }
  .urg-critical { background: #7f1d1d; color: #fca5a5; }
  .urg-high     { background: #78350f; color: #fcd34d; }
  .urg-medium   { background: #713f12; color: #fde68a; }
  .urg-low      { background: #14532d; color: #86efac; }
  .sev-score    { font-size: 0.65rem; color: #94a3b8; }

  /* ── Plan cards ── */
  .plan-header { font-size: 0.65rem; font-weight: 700; letter-spacing: 0.1em;
    text-transform: uppercase; color: #64748b; margin-bottom: 6px; }
  .plan-name { font-size: 1rem; font-weight: 700; color: #e2e8f0; }
  .plan-tag { font-size: 0.65rem; color: #94a3b8; margin-bottom: 8px; }
  .valid-badge { font-size: 0.65rem; font-weight: 700; padding: 2px 8px; border-radius: 3px;
    display: inline-block; margin-bottom: 6px; }
  .valid-ok   { background: #052e16; color: #22c55e; border: 1px solid #166534; }
  .valid-fail { background: #450a0a; color: #f87171; border: 1px solid #991b1b; }
  .plan-rec-border { border: 1px solid #2563eb; border-radius: 8px; padding: 12px;
    background: #0c1526; }
  .plan-norm-border { border: 1px solid #1e293b; border-radius: 8px; padding: 12px;
    background: #0f1117; }

  /* ── Resilience cells ── */
  .res-survived { color: #22c55e; font-weight: 600; }
  .res-degraded { color: #f59e0b; font-weight: 600; }
  .res-failed   { color: #ef4444; font-weight: 600; }

  /* ── Decision panel ── */
  .decision-panel {
    background: #0c1526; border: 1px solid #1e3a5f; border-radius: 10px; padding: 16px;
  }
  .rec-label { font-size: 0.65rem; color: #64748b; letter-spacing: 0.1em;
    text-transform: uppercase; margin-bottom: 4px; }
  .rec-name { font-size: 1.2rem; font-weight: 700; color: #60a5fa; }
  .rec-sub  { font-size: 0.75rem; color: #94a3b8; margin-bottom: 12px; }
  .why-box {
    background: #0f1923; border: 1px solid #1e293b; border-radius: 6px;
    padding: 10px 12px; margin-top: 8px;
  }
  .why-label { font-size: 0.62rem; font-weight: 700; letter-spacing: 0.1em;
    text-transform: uppercase; color: #64748b; margin-bottom: 4px; }
  .why-text { font-size: 0.78rem; color: #cbd5e1; }
  .tradeoff-text { font-size: 0.75rem; color: #f59e0b; }

  /* ── Confidence indicator ── */
  .conf-high   { color: #22c55e; font-weight: 700; }
  .conf-medium { color: #f59e0b; font-weight: 700; }
  .conf-low    { color: #ef4444; font-weight: 700; }

  /* ── Decision debt ── */
  .debt-card {
    background: #1c1008; border: 1px solid #78350f; border-radius: 6px;
    padding: 10px 12px; margin-top: 8px;
  }
  .debt-label { font-size: 0.62rem; font-weight: 700; letter-spacing: 0.08em;
    text-transform: uppercase; color: #f59e0b; margin-bottom: 4px; }
  .debt-spof-label { font-size: 0.62rem; font-weight: 700; letter-spacing: 0.08em;
    text-transform: uppercase; color: #ef4444; margin-bottom: 4px; }
  .debt-text { font-size: 0.75rem; color: #d97706; }
  .debt-impact { font-size: 0.72rem; color: #92400e; }

  /* ── Resilience lab ── */
  .rlab-header {
    background: #0c1a0c; border: 1px solid #166534; border-radius: 8px;
    padding: 14px 18px; margin-bottom: 12px;
  }
  .rlab-title { font-size: 1.1rem; font-weight: 700; color: #4ade80; }
  .rlab-sub   { font-size: 0.75rem; color: #86efac; margin-top: 2px; }
  .scenario-row {
    background: #0f1117; border: 1px solid #1e293b; border-radius: 6px;
    padding: 8px 12px; margin-bottom: 6px; display: flex;
    align-items: center; justify-content: space-between;
  }
  .scen-desc { font-size: 0.8rem; color: #cbd5e1; }
  .scen-badge { font-size: 0.65rem; font-weight: 700; padding: 2px 8px;
    border-radius: 3px; }
  .scen-survives { background: #052e16; color: #22c55e; border: 1px solid #166534; }
  .scen-degraded { background: #1c1208; color: #f59e0b; border: 1px solid #92400e; }
  .scen-fails    { background: #450a0a; color: #f87171; border: 1px solid #991b1b; }

  /* ── Timeline ── */
  .timeline-step {
    display: flex; gap: 12px; align-items: flex-start; margin-bottom: 8px;
  }
  .tl-dot { width: 10px; height: 10px; border-radius: 50%; background: #2563eb;
    margin-top: 4px; flex-shrink: 0; }
  .tl-dot.current { background: #22c55e; box-shadow: 0 0 6px #22c55e; }
  .tl-content { flex: 1; }
  .tl-ver { font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; color: #2563eb; }
  .tl-action { font-size: 0.8rem; color: #e2e8f0; }
  .tl-detail { font-size: 0.7rem; color: #64748b; }

  /* ── SPOF visual ── */
  .spof-box {
    background: #1a0505; border: 1px solid #7f1d1d; border-radius: 6px;
    padding: 10px 12px; margin-bottom: 8px;
  }
  .spof-unit { font-family: 'JetBrains Mono', monospace; font-size: 0.8rem;
    color: #ef4444; font-weight: 700; }
  .spof-arrow { color: #7f1d1d; font-size: 0.8rem; margin: 2px 0; }
  .spof-inc { font-size: 0.75rem; color: #fca5a5; }
  .spof-status { font-size: 0.65rem; font-weight: 700; color: #ef4444; margin-top: 4px; }

  /* ── Log entries ── */
  .log-entry {
    background: #0f1117; border-left: 2px solid #1e293b; padding: 6px 10px;
    margin-bottom: 4px; border-radius: 0 4px 4px 0;
  }
  .log-ver  { font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; color: #2563eb; }
  .log-agent { font-size: 0.7rem; font-weight: 600; color: #60a5fa; }
  .log-action { font-size: 0.78rem; color: #e2e8f0; }
  .log-detail { font-size: 0.7rem; color: #64748b; }

  /* ── Disruption panel ── */
  .disruption-panel {
    background: #130c0c; border: 1px solid #7f1d1d; border-radius: 8px;
    padding: 12px 14px; margin-top: 8px;
  }
  .dis-title { font-size: 0.7rem; font-weight: 700; letter-spacing: 0.1em;
    text-transform: uppercase; color: #ef4444; margin-bottom: 8px; }
  .dis-preview {
    background: #1c0f0f; border: 1px solid #450a0a; border-radius: 4px;
    padding: 8px 10px; margin-bottom: 8px; font-size: 0.72rem; color: #fca5a5;
  }

  /* ── Approval buttons ── */
  .stButton > button[kind="primary"] {
    background: #1a4d1a !important; border: 1px solid #166534 !important;
    color: #22c55e !important; font-weight: 600 !important;
  }
  .stButton > button[kind="primary"]:hover {
    background: #166534 !important; border-color: #22c55e !important;
  }

  /* ── Diff section ── */
  .diff-event {
    background: #0f1923; border: 1px solid #1e3a5f; border-radius: 6px;
    padding: 10px 12px; margin-bottom: 8px;
  }
  .diff-before-after {
    display: flex; gap: 12px;
  }
  .diff-col {
    flex: 1; background: #0f1117; border-radius: 5px; padding: 8px 10px;
  }
  .diff-col-label { font-size: 0.62rem; font-weight: 700; letter-spacing: 0.08em;
    text-transform: uppercase; margin-bottom: 4px; }
  .diff-col-before .diff-col-label { color: #ef4444; }
  .diff-col-after  .diff-col-label { color: #22c55e; }
  .diff-col-content { font-size: 0.78rem; color: #e2e8f0; }

  /* ── Sidebar ── */
  .css-1d391kg, [data-testid="stSidebar"] { background: #0c1117; }
  [data-testid="stSidebar"] hr { border-color: #1e293b; }

  /* ── Tabs ── */
  .stTabs [data-baseweb="tab-list"] { background: #0f1117; border-bottom: 1px solid #1e293b; }
  .stTabs [data-baseweb="tab"] { color: #64748b; font-size: 0.8rem; font-weight: 500; }
  .stTabs [aria-selected="true"] { color: #60a5fa !important; border-bottom-color: #2563eb !important; }

  /* ── Map ── */
  iframe { border-radius: 8px; }

  /* ── Metric override ── */
  [data-testid="metric-container"] { background: #111827; border: 1px solid #1e293b;
    border-radius: 8px; padding: 10px 14px; }

  /* ── Misc ── */
  hr { border-color: #1e293b; }
  .stInfo    { background: #0c1a2e !important; color: #93c5fd !important; border: 1px solid #1e3a5f !important; }
  .stSuccess { background: #052e16 !important; color: #86efac !important; border: 1px solid #166534 !important; }
  .stWarning { background: #1c1208 !important; color: #fde68a !important; border: 1px solid #92400e !important; }
  .stError   { background: #450a0a !important; color: #fca5a5 !important; border: 1px solid #991b1b !important; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------

def _load_json(name):
    path = Path(__file__).parent / "data" / name
    with open(path) as f:
        return json.load(f)


def _strip_comment(d):
    return {k: v for k, v in d.items() if k != "_comment"}


def init_state() -> CrisisState:
    incidents = [Incident(**_strip_comment(d)) for d in _load_json("incidents.json")]
    units = [Unit(**_strip_comment(d)) for d in _load_json("units.json")]
    roads = [RoadCondition(**_strip_comment(d)) for d in _load_json("roads.json")]
    for inc in incidents:
        assess_incident(inc)
    state = CrisisState(incidents=incidents, units=units, road_conditions=roads)
    state.log_action("System", "Crisis initialized", "3 incidents, 6 units loaded")
    return state


def _run_plans(state: CrisisState) -> CrisisState:
    """Generate → validate → compare → resilience → confidence → debt."""
    state = generate_candidate_plans(state)
    state = compare_and_select(state)
    for p in state.candidate_plans:
        if p.validation and p.validation.valid and len(p.assignments) > 0:
            res = evaluate_plan_resilience(p, state)
            state.resilience_results[p.id] = res
            if p.metrics:
                p.metrics.resilience_score = res.resilience_score
                p.metrics.fragility_index = res.fragility_index
    # Re-score after resilience fills in
    compare_and_select(state)
    state.decision_confidence = calculate_decision_confidence(state)
    state.decision_debts = calculate_decision_debts(state)
    return state


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

if "state" not in st.session_state:
    st.session_state.state = None
    st.session_state.history = StateHistory()

if "simulator" not in st.session_state:
    st.session_state.simulator = DeterministicSimulator()

if "feed_events" not in st.session_state:
    st.session_state.feed_events = []

if "weather_context" not in st.session_state:
    from backend.integrations.weather import get_weather
    # Default to center of our map area
    st.session_state.weather_context = get_weather(21.175, 72.830)

state: CrisisState = st.session_state.state
history: StateHistory = st.session_state.history
simulator: DeterministicSimulator = st.session_state.simulator
feed_events: list = st.session_state.feed_events
weather_context = st.session_state.weather_context


# ---------------------------------------------------------------------------
# Helper: current SEE→TEST→DECIDE→REPLAN step
# ---------------------------------------------------------------------------

def _flow_step() -> str:
    if state is None:
        return "none"
    if not state.candidate_plans:
        return "see"
    if not state.approved_plan:
        return "decide"
    if state.plan_diffs:
        return "replan"
    return "test"


flow = _flow_step()


# ---------------------------------------------------------------------------
# HEADER — use st.columns for reliable cross-version rendering
# ---------------------------------------------------------------------------

st.markdown("""
<div style="background:linear-gradient(135deg,#0f1923 0%,#111827 100%);
  border-bottom:1px solid #1e3a5f; padding:14px 8px 10px 8px; margin-bottom:6px;">
</div>
""", unsafe_allow_html=True)

hdr_l, hdr_m, hdr_r = st.columns([4, 3, 3])
with hdr_l:
    st.markdown(
        '<p style="font-size:1.4rem;font-weight:700;color:#e2e8f0;letter-spacing:0.05em;'
        'margin:0;padding:0;line-height:1.2;">🚨 CRISIS COMMAND</p>'
        '<p style="font-size:0.72rem;color:#94a3b8;margin:0;padding:0;">'
        'Resilient Decision Intelligence for Emergency Response</p>',
        unsafe_allow_html=True,
    )
with hdr_m:
    st.markdown(
        '<p style="font-size:0.7rem;font-weight:700;letter-spacing:0.08em;'
        'background:#1a2332;border:1px solid #e97316;border-radius:4px;'
        'color:#e97316;padding:4px 10px;display:inline-block;margin:4px 0;">'
        '⚠ SIMULATION MODE</p>',
        unsafe_allow_html=True,
    )
with hdr_r:
    ver_txt = f"STATE v{state.version}" if state else "NOT INITIALIZED"
    st.markdown(
        f'<p style="font-size:0.75rem;font-weight:600;font-family:monospace;'
        f'background:#1a2332;border:1px solid #2563eb;border-radius:4px;'
        f'color:#60a5fa;padding:4px 10px;display:inline-block;margin:4px 0;">{ver_txt}</p>'
        f'<span style="font-size:0.72rem;color:#22c55e;margin-left:8px;">● System Ready</span>',
        unsafe_allow_html=True,
    )

st.markdown('<hr style="border-color:#1e293b;margin:4px 0 8px 0;"/>', unsafe_allow_html=True)

# Flow banner — reliable column-based rendering
flow_cols = st.columns([1, 0.2, 1, 0.2, 1, 0.2, 1])
_step_colors = {
    "done":   ("#052e16", "#22c55e", "#166534"),
    "active": ("#0c1526", "#60a5fa", "#2563eb"),
    "":       ("#1e293b", "#64748b", "#334155"),
}

def _flow_label(label, status):
    bg, color, border = _step_colors.get(status, _step_colors[""])
    return (
        f'<div style="text-align:center;background:{bg};border:1px solid {border};'
        f'border-radius:4px;padding:5px 4px;font-size:0.68rem;font-weight:700;'
        f'letter-spacing:0.1em;color:{color};">{label}</div>'
    )

s = {
    "SEE":    "done" if flow in ("test","decide","replan") else ("active" if flow=="see" else ""),
    "TEST":   "done" if flow in ("decide","replan") else ("active" if flow=="test" else ""),
    "DECIDE": "done" if flow=="replan" else ("active" if flow=="decide" else ""),
    "REPLAN": "active" if flow=="replan" else "",
}
with flow_cols[0]: st.markdown(_flow_label("SEE", s["SEE"]), unsafe_allow_html=True)
with flow_cols[1]: st.markdown('<div style="text-align:center;color:#334155;padding-top:4px;">→</div>', unsafe_allow_html=True)
with flow_cols[2]: st.markdown(_flow_label("TEST", s["TEST"]), unsafe_allow_html=True)
with flow_cols[3]: st.markdown('<div style="text-align:center;color:#334155;padding-top:4px;">→</div>', unsafe_allow_html=True)
with flow_cols[4]: st.markdown(_flow_label("DECIDE", s["DECIDE"]), unsafe_allow_html=True)
with flow_cols[5]: st.markdown('<div style="text-align:center;color:#334155;padding-top:4px;">→</div>', unsafe_allow_html=True)
with flow_cols[6]: st.markdown(_flow_label("REPLAN", s["REPLAN"]), unsafe_allow_html=True)

st.markdown('<div style="margin-bottom:8px;"></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------------

with st.sidebar:
    weather_info = ""
    weather_title = "🌦 Open-Meteo"
    if weather_context and weather_context.available:
        weather_title = "🌦 Open-Meteo"
        weather_info = f"""
        Precipitation: {weather_context.precipitation} mm<br/>
        Rain: {weather_context.rain} mm<br/>
        Wind: {weather_context.wind_speed} km/h
        """
    else:
        weather_title = "🌦 Open-Meteo <span style='color:#ef4444'>(UNAVAILABLE - FALLBACK)</span>"
        weather_info = "Using deterministic baseline conditions."

    import os
    ors_title = "🗺 OpenRouteService"
    ors_info = "External route context available" if os.environ.get("ORS_API_KEY") else "<span style='color:#ef4444'>ORS_API_KEY missing - EXTERNAL UNAVAILABLE</span>"

    st.markdown(f"""
<div style="background:#111827;border:1px solid #1e293b;border-radius:6px;padding:12px;margin-bottom:12px;">
  <div style="font-size:0.65rem;font-weight:700;letter-spacing:0.1em;color:#64748b;margin-bottom:8px;">OPERATIONAL CONTEXT</div>
  
  <div style="font-size:0.75rem;font-weight:700;color:#94a3b8;margin-top:8px;">EXTERNAL</div>
  <div style="font-size:0.75rem;color:#3b82f6;margin-top:2px;">{weather_title}</div>
  <div style="font-size:0.7rem;color:#cbd5e1;padding-left:12px;">{weather_info}</div>
  
  <div style="font-size:0.75rem;font-weight:700;color:#94a3b8;margin-top:8px;">ROUTING CONTEXT</div>
  <div style="font-size:0.75rem;color:#3b82f6;margin-top:2px;">{ors_title}</div>
  <div style="font-size:0.7rem;color:#cbd5e1;padding-left:12px;">{ors_info}</div>

  <div style="font-size:0.75rem;font-weight:700;color:#94a3b8;margin-top:8px;">LOCAL OPERATIONAL ENGINE</div>
  <div style="font-size:0.75rem;color:#22c55e;margin-top:2px;">✓ Dijkstra</div>
  <div style="font-size:0.7rem;color:#cbd5e1;padding-left:12px;">Deterministic route logic active</div>

  <div style="font-size:0.75rem;font-weight:700;color:#94a3b8;margin-top:8px;">SIMULATION</div>
  <div style="font-size:0.75rem;color:#eab308;margin-top:2px;">🟡 Emergency incidents, Units, Road blocks, Breakdowns</div>

  <div style="font-size:0.75rem;font-weight:700;color:#94a3b8;margin-top:8px;">DERIVED</div>
  <div style="font-size:0.75rem;color:#60a5fa;margin-top:2px;">🔵 Severity, Allocation, Resilience, Replanning</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("### 🎛 Simulation Controls")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Reset", use_container_width=True):
            simulator.reset()
            st.session_state.feed_events = []
            st.session_state.state = init_state()
            st.session_state.history = StateHistory()
            st.rerun()
    with col2:
        if not state:
            if st.button("▶ Start / Ready", use_container_width=True, type="primary"):
                st.session_state.state = init_state()
                st.session_state.history = StateHistory()
                st.rerun()
        else:
            if simulator.has_next():
                if st.button("⏭ Step Event", use_container_width=True, type="primary"):
                    ev = simulator.next_event()
                    feed_events.append(ev)
                    
                    if ev.event_type == "weather_update":
                        state.log_action("Simulation", f"Weather Update: {ev.payload.get('description', '')}")
                    elif ev.event_type == "road_block":
                        state = apply_road_block(state, history, ev.payload["road_id"])
                        state.log_action("System", "Replanning Triggered", f"Road block: {ev.payload['road_id']}")
                    elif ev.event_type == "unit_failure":
                        state = apply_unit_breakdown(state, history, ev.payload["unit_id"])
                        state.log_action("System", "Replanning Triggered", f"Unit failure: {ev.payload['unit_id']}")
                    elif ev.event_type == "new_incident":
                        inc_data = ev.payload.copy()
                        
                        # Event Normalizer to Canonical Incident Schema
                        if "incident_id" in inc_data:
                            inc_data["id"] = inc_data.pop("incident_id")
                        if "location" not in inc_data and hasattr(ev, "location"):
                            inc_data["location"] = ev.location
                        if "lat" in inc_data:
                            inc_data["latitude"] = inc_data.pop("lat")
                        if "lon" in inc_data:
                            inc_data["longitude"] = inc_data.pop("lon")

                        inc = Incident(**inc_data)
                        state = apply_new_incident(state, history, inc)
                        state.log_action("System", "Replanning Triggered", f"New Incident: {inc.id}")
                    
                    state.decision_confidence = calculate_decision_confidence(state)
                    state.decision_debts = calculate_decision_debts(state)
                    st.session_state.state = state
                    st.rerun()
            else:
                st.button("✓ Complete", use_container_width=True, disabled=True)

    if state:
        st.markdown("---")
        st.markdown("#### ✅ Command Approval")
        if not state.candidate_plans:
            if st.button("📋 Generate & Evaluate Plans", use_container_width=True):
                state = _run_plans(state)
                st.session_state.state = state
                st.rerun()
        
        elif state.recommended_plan and not state.approved_plan:
            if st.button("✅ Approve Recommended Plan", use_container_width=True, type="primary"):
                state.approved_plan = state.recommended_plan
                state.log_action(
                    "Dispatcher",
                    f"Approved {state.recommended_plan.strategy_name}",
                    f"Score {state.recommended_plan.score}",
                )
                state.increment_version()
                history.save(state)
                st.session_state.state = state
                st.rerun()

        elif state.approved_plan:
            if st.button("❌ Reject Plan", use_container_width=True):
                old_name = state.approved_plan.strategy_name
                state.approved_plan = None
                state.log_action("Dispatcher", f"Rejected {old_name}")
                state.increment_version()
                st.session_state.state = state
                st.rerun()

    st.markdown("---")
    st.markdown("### 📡 Crisis Feed")
    if not feed_events:
        st.caption("Waiting for events...")
    else:
        for f_ev in reversed(feed_events):
            st.markdown(f"""
<div style="background:#0f1923; border-left:3px solid #3b82f6; padding:8px 10px; margin-bottom:8px; border-radius:4px;">
    <div style="font-family:monospace; font-size:0.7rem; color:#94a3b8;">{f_ev.timestamp}</div>
    <div style="font-size:0.75rem; font-weight:700; color:#e2e8f0; margin:2px 0;">{f_ev.event_type.replace('_', ' ').upper()}</div>
    <div style="font-size:0.65rem; color:#60a5fa; margin-bottom:4px; text-transform:uppercase;">SOURCE: {f_ev.source_type}</div>
    <div style="font-size:0.75rem; color:#cbd5e1;">{f_ev.payload.get('description') or f_ev.payload.get('type') or 'Event recorded'}</div>
</div>
""", unsafe_allow_html=True)
            
    st.markdown("---")
    st.caption(
        "This demonstration uses simulated incident and resource events. "
        "The normalized event interface is designed to accept authorized external operational feeds."
    )

# ---------------------------------------------------------------------------
# EMPTY STATE
# ---------------------------------------------------------------------------

if not state:
    st.markdown("""
<div style="text-align:center; padding: 80px 0;">
  <div style="font-size:3rem; margin-bottom:16px;">🚨</div>
  <div style="font-size:1.4rem; font-weight:700; color:#e2e8f0; margin-bottom:8px;">
    Crisis Command
  </div>
  <div style="font-size:0.95rem; color:#94a3b8; margin-bottom:4px;">
    Resilient Decision Intelligence for Emergency Response
  </div>
  <div style="font-size:0.8rem; color:#64748b; margin-top:16px; max-width:480px; margin-left:auto; margin-right:auto;">
    "Don't just find a response plan. Try to break it before reality does."
  </div>
  <div style="font-size:0.75rem; color:#334155; margin-top:24px;">
    Click <b>Initialize Crisis</b> in the sidebar to begin.
  </div>
</div>
""", unsafe_allow_html=True)
    st.stop()

# ---------------------------------------------------------------------------
# COMMAND SUMMARY STRIP
# ---------------------------------------------------------------------------

avail_count = sum(1 for u in state.units if u.status == UnitStatus.AVAILABLE)
crit_count = sum(1 for i in state.incidents if i.urgency and i.urgency.value == "CRITICAL")
reserve = 0
res_score = "—"
if state.recommended_plan:
    rec = state.recommended_plan
    if rec.metrics:
        reserve = rec.metrics.reserve_units
    if rec.id in state.resilience_results:
        res_score = f"{state.resilience_results[rec.id].resilience_score}/100"

conf_level = state.decision_confidence.level if state.decision_confidence else "—"

# Command summary strip using native st.metric for reliability
strip_cols = st.columns(7)
strip_cols[0].metric("Active Incidents", len(state.incidents))
strip_cols[1].metric("Critical", crit_count)
strip_cols[2].metric("Units Available", f"{avail_count}/{len(state.units)}")
strip_cols[3].metric("Reserve", reserve)
strip_cols[4].metric("Resilience", res_score)
strip_cols[5].metric("Confidence", conf_level)
strip_cols[6].metric("State", f"v{state.version}")
st.markdown('<hr style="border-color:#1e293b;margin:4px 0 8px 0;"/>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# THREE-COLUMN COMMAND CENTER
# ---------------------------------------------------------------------------

_STRATEGY_LABELS = {
    "NEAREST_FIRST": ("Plan A", "Fastest Response"),
    "SEVERITY_FIRST": ("Plan B", "Critical-First"),
    "BALANCED": ("Plan C", "Resilient Balance"),
}
_URG_CLASS = {"CRITICAL": "critical", "HIGH": "high", "MEDIUM": "medium", "LOW": "low"}

col_left, col_center, col_right = st.columns([3, 5, 4], gap="medium")

# ── LEFT: Incident Queue ──────────────────────────────────────────────────

with col_left:
    st.markdown("#### 📋 Incident Queue")

    # Build assignment map for ETA/unit display
    asgn_map = {}  # incident_id -> list of (unit_id, eta)
    plan_to_show = state.approved_plan or state.recommended_plan
    if plan_to_show:
        for a in plan_to_show.assignments:
            asgn_map.setdefault(a.incident_id, []).append((a.unit_id, a.eta_minutes))

    for inc in sorted(state.incidents, key=lambda x: -(x.severity or 0)):
        sev = inc.severity or 0
        urg = inc.urgency.value if inc.urgency else "UNKNOWN"
        urg_icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(urg, "⚪")
        reqs = ", ".join(f"{k.value} ×{v}" for k, v in inc.required_units.items())
        assigned = asgn_map.get(inc.id, [])

        # Urgency colors — inline only, no CSS classes
        urg_colors = {
            "CRITICAL": ("#7f1d1d", "#fca5a5", "#ef4444"),
            "HIGH":     ("#78350f", "#fcd34d", "#f59e0b"),
            "MEDIUM":   ("#713f12", "#fde68a", "#eab308"),
            "LOW":      ("#14532d", "#86efac", "#22c55e"),
        }
        bg_badge, fg_badge, border_left = urg_colors.get(urg, ("#1e293b", "#94a3b8", "#334155"))

        assigned_html = ""
        if assigned:
            unit_strs = " ".join(
                f'<span style="font-family:monospace;font-size:0.7rem;background:#0f1923;'
                f'border:1px solid #1e3a5f;border-radius:3px;padding:1px 5px;color:#60a5fa;">'
                f'{uid}</span>'
                for uid, _ in assigned
            )
            min_eta = min(e for _, e in assigned)
            assigned_html = (
                f'<div style="margin-top:4px;">{unit_strs} '
                f'<span style="font-size:0.7rem;color:#64748b;">ETA {min_eta:.1f} min</span></div>'
            )

        trapped_html = ""
        if inc.people_affected:
            trapped_txt = f" | Trapped: {inc.people_trapped}" if inc.people_trapped else ""
            trapped_html = (
                f'<div style="margin-top:2px;font-size:0.7rem;color:#94a3b8;">'
                f'Affected: {inc.people_affected}{trapped_txt}</div>'
            )

        st.markdown(f"""
<div style="background:#111827;border:1px solid #1e293b;border-left:3px solid {border_left};
  border-radius:8px;padding:12px 14px;margin-bottom:8px;">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;">
    <div>
      <div style="font-family:monospace;font-size:0.7rem;color:#64748b;">{inc.id}</div>
      <div style="font-size:0.9rem;font-weight:600;color:#e2e8f0;margin:2px 0;">{urg_icon} {inc.type}</div>
      <div style="font-size:0.72rem;color:#94a3b8;">📍 {inc.location}</div>
    </div>
    <div style="text-align:right;">
      <span style="display:inline-block;font-size:0.6rem;font-weight:700;letter-spacing:0.08em;
        padding:2px 7px;border-radius:3px;background:{bg_badge};color:{fg_badge};">{urg}</span>
      <div style="font-size:0.65rem;color:#94a3b8;margin-top:2px;">Severity {sev}/10</div>
    </div>
  </div>
  <div style="margin-top:6px;font-size:0.7rem;color:#64748b;">Requires: {reqs}</div>
  {trapped_html}
  {assigned_html}
</div>
""", unsafe_allow_html=True)


# ── CENTER: Map ───────────────────────────────────────────────────────────

with col_center:
    st.markdown("#### 🗺 Situation Map")
    st.caption("SIMULATION DATA — Map tiles: OpenStreetMap")

    try:
        import folium
        from streamlit_folium import st_folium

        m = folium.Map(
            location=[21.175, 72.830], zoom_start=13,
            tiles="OpenStreetMap",
        )

        # Incidents
        for inc in state.incidents:
            sev = inc.severity or 0
            color = "red" if sev >= 9 else "orange" if sev >= 7 else "beige" if sev >= 4 else "green"
            urg = inc.urgency.value if inc.urgency else "?"
            folium.CircleMarker(
                [inc.latitude, inc.longitude],
                radius=9 + sev,
                color=color, fill=True, fill_opacity=0.75, weight=2,
                popup=folium.Popup(
                    f"<b>{inc.id}</b><br>{inc.type}<br>Severity {sev} | {urg}<br>"
                    f"Affected: {inc.people_affected} | Trapped: {inc.people_trapped}",
                    max_width=200,
                ),
                tooltip=f"{inc.id}: {inc.type} [{urg}]",
            ).add_to(m)
            folium.map.Marker(
                [inc.latitude, inc.longitude],
                icon=folium.DivIcon(
                    html=f'<div style="font-size:9px;color:white;font-weight:bold;'
                         f'white-space:nowrap;text-shadow:1px 1px 2px black;">{inc.id}</div>',
                    icon_size=(60, 14), icon_anchor=(0, -5),
                ),
            ).add_to(m)

        # Units
        for unit in state.units:
            if unit.status == UnitStatus.BROKEN_DOWN:
                ucolor = "red"
            elif unit.status == UnitStatus.AVAILABLE:
                ucolor = "green"
            elif unit.status == UnitStatus.EN_ROUTE:
                ucolor = "blue"
            elif unit.status == UnitStatus.ON_SCENE:
                ucolor = "purple"
            else:
                ucolor = "gray"
                
            uicon = "plus-sign" if unit.type == UnitType.AMBULANCE else "home"
            # If unit is en_route, use its mission coordinates
            lat, lon = unit.latitude, unit.longitude
            for m_id, mission in state.active_missions.items():
                if mission.unit_id == unit.id and mission.status == "EN_ROUTE":
                    lat, lon = mission.current_latitude, mission.current_longitude
            
            folium.Marker(
                [lat, lon],
                popup=folium.Popup(
                    f"<b>{unit.id}</b><br>Type: {unit.type.value}<br>Status: {unit.status.value}",
                    max_width=160,
                ),
                tooltip=f"{unit.id} [{unit.status.value}]",
                icon=folium.Icon(color=ucolor, icon=uicon, prefix="glyphicon"),
            ).add_to(m)

        # Active missions and preview routes
        preview_route = st.session_state.get('preview_route')
        if preview_route and preview_route.waypoints:
            folium.PolyLine(
                preview_route.waypoints,
                color="#eab308", weight=4, opacity=0.8, dash_array="5",
                tooltip=f"PREVIEW: {preview_route.name} | ETA {preview_route.eta_minutes:.1f} min",
            ).add_to(m)
            
        for m_id, mission in state.active_missions.items():
            if mission.status == "EN_ROUTE":
                r = state.get_mission_route(m_id)
                if r and r.waypoints:
                    folium.PolyLine(
                        r.waypoints,
                        color="#3b82f6", weight=3, opacity=0.8,
                        tooltip=f"ACTIVE: {mission.unit_id} → {mission.incident_id} | ETA {mission.eta_minutes} min",
                    ).add_to(m)

        # Blocked roads
        for road in state.road_conditions:
            if road.blocked:
                folium.PolyLine(
                    [[road.from_lat, road.from_lon], [road.to_lat, road.to_lon]],
                    color="#ef4444", weight=5, dash_array="8",
                    tooltip=f"BLOCKED: {road.name}",
                ).add_to(m)

        # Legend
        legend_html = """
        <div style="position:fixed;bottom:20px;left:20px;z-index:9999;
            background:#111827;border:1px solid #1e293b;border-radius:6px;padding:8px 12px;
            font-family:Inter,sans-serif;font-size:11px;color:#94a3b8;">
          <div style="font-weight:700;color:#e2e8f0;margin-bottom:4px;">Legend</div>
          <div><span style="color:#ef4444;">●</span> CRITICAL Incident</div>
          <div><span style="color:#22c55e;">▲</span> Unit (Available)</div>
          <div><span style="color:#3b82f6;">▲</span> Unit (En-Route)</div>
          <div><span style="color:#3b82f6;">━</span> Active Route</div>
          <div><span style="color:#eab308;">╌</span> Preview Route</div>
          <div><span style="color:#ef4444;">╌</span> Blocked Road</div>
        </div>"""
        m.get_root().html.add_child(folium.Element(legend_html))

        st_folium(m, width=None, height=420, returned_objects=[])

    except ImportError:
        st.warning("Install folium and streamlit-folium for map view: `pip install folium streamlit-folium`")

# ── RIGHT: Command Decision Panel ────────────────────────────────────────

with col_right:
    st.markdown("#### 🎯 Command Decision")

    rec = state.recommended_plan
    approved = state.approved_plan

    if approved:
        label_a, label_b = _STRATEGY_LABELS.get(approved.strategy_name, ("Plan", approved.strategy_name))
        st.markdown(f"""
<div style="background:#0c1526;border:1px solid #1e3a5f;border-radius:10px;padding:16px;">
  <div style="font-size:0.65rem;color:#64748b;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:4px;">✅ APPROVED BY DISPATCHER</div>
  <div style="font-size:1.2rem;font-weight:700;color:#60a5fa;">{label_a} — {label_b}</div>
  <div style="font-size:0.75rem;color:#22c55e;margin-bottom:12px;">Active Plan</div>
""", unsafe_allow_html=True)
        plan = approved
    elif rec:
        label_a, label_b = _STRATEGY_LABELS.get(rec.strategy_name, ("Plan", rec.strategy_name))
        why_data = get_explanation_data(plan, state) if 'plan' in locals() and plan else get_explanation_data(state.recommended_plan, state)
        st.markdown(f"""
<div style="background:#0c1526;border:1px solid #1e3a5f;border-radius:10px;padding:16px;">
  <div style="font-size:0.65rem;color:#64748b;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:4px;">⭐ RECOMMENDED PLAN</div>
  <div style="font-size:1.2rem;font-weight:700;color:#60a5fa;">{label_a} — {label_b}</div>
  <div style="font-size:0.75rem;color:#94a3b8;margin-bottom:12px;">Awaiting dispatcher approval</div>
""", unsafe_allow_html=True)
        plan = rec

        # Why This Plan?
        if why_data["why"]:
            bullets = "".join(f"<div>✓ {part.strip()}</div>" for part in why_data["why"].split("|"))
            st.markdown(f"""
<div style="background:#0f1923;border:1px solid #1e293b;border-radius:6px;padding:10px 12px;margin-top:8px;">
  <div style="font-size:0.62rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#64748b;margin-bottom:4px;">Why this plan? { ' (AI GENERATED)' if why_data.get('is_ai') else '' }</div>
  <div style="font-size:0.78rem;color:#cbd5e1;">{bullets}</div>
</div>
""", unsafe_allow_html=True)

        # Trade-Off
        if why_data["tradeoff"]:
            bullets = "".join(f"<div>⚠ {part.strip()}</div>" for part in why_data["tradeoff"].split("|"))
            st.markdown(f"""
<div style="background:#0f1208;border:1px solid #78350f;border-radius:6px;padding:10px 12px;margin-top:8px;">
  <div style="font-size:0.62rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#f59e0b;margin-bottom:4px;">Trade-Off { ' (AI GENERATED)' if why_data.get('is_ai') else '' }</div>
  <div style="font-size:0.75rem;color:#f59e0b;">{bullets}</div>
</div>
""", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown("""
<div style="background:#0c1526;border:1px solid #1e3a5f;border-radius:10px;padding:16px;">
  <div style="text-align:center;padding:20px 0;color:#64748b;">
    <div style="font-size:1.5rem;margin-bottom:8px;">📋</div>
    <div>No plans generated yet.</div>
    <div style="font-size:0.75rem;margin-top:4px;">Click "Generate & Evaluate Plans"</div>
  </div>
</div>
""", unsafe_allow_html=True)
        plan = None

    # Metrics
    if plan and plan.metrics:
        st.markdown("")
        mc = st.columns(3)
        mc[0].metric("Coverage", f"{plan.metrics.total_covered}/{plan.metrics.total_incidents}")
        mc[1].metric("Avg ETA", f"{plan.metrics.average_eta} min")
        mc[2].metric("Reserve", plan.metrics.reserve_units)

        res = state.resilience_results.get(plan.id)
        if res:
            rc = st.columns(2)
            rc[0].metric("Resilience", f"{res.resilience_score}/100")
            rc[1].metric("Fragility", f"{res.fragility_index}%")

    # Human Attention Check
    if plan and plan.metrics and getattr(plan.metrics, "human_attention_required", False):
        attention_reasons = getattr(plan.metrics, "attention_reasons", [])
        bullets = "".join(f"<li>{r}</li>" for r in attention_reasons)
        st.markdown(f"""
<div style="background:#450a0a;border:1px solid #ef4444;border-radius:8px;padding:12px;margin-top:12px;">
  <div style="font-size:0.75rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#fca5a5;margin-bottom:4px;">⚠ HUMAN ATTENTION REQUIRED</div>
  <div style="font-size:0.8rem;color:#fecaca;">
    The deterministic engine has flagged this plan for manual review:
    <ul style="margin:4px 0 0 0;padding-left:20px;">{bullets}</ul>
  </div>
</div>
""", unsafe_allow_html=True)

    # Decision Confidence detail
    if state.decision_confidence:
        conf = state.decision_confidence
        conf_class = {"HIGH": "conf-high", "MEDIUM": "conf-medium", "LOW": "conf-low"}.get(conf.level, "")
        conf_icon = {"HIGH": "🟢", "MEDIUM": "🟡", "LOW": "🔴"}.get(conf.level, "")
        st.markdown(f"""
<div class="why-box" style="margin-top:8px;">
  <div class="why-label">Decision Confidence</div>
  <div class="{conf_class}" style="font-size:1rem;margin-bottom:4px;">{conf_icon} {conf.level} ({conf.passed_count}/{conf.total_count} checks)</div>
""", unsafe_allow_html=True)
        for f in conf.factors:
            icon = "✓" if f.passed else "✗"
            color = "#22c55e" if f.passed else "#ef4444"
            st.markdown(
                f'<div style="font-size:0.7rem;color:{color};">{icon} {f.label}'
                f'<span style="color:#64748b;"> — {f.detail}</span></div>',
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    # Decision Debt
    if state.decision_debts:
        for debt in state.decision_debts:
            spof_label = "⚠ SINGLE POINT OF FAILURE" if debt.is_spof else "⚠ DECISION DEBT"
            card_class = "debt-card"
            lbl_class = "debt-spof-label" if debt.is_spof else "debt-label"
            st.markdown(f"""
<div class="{card_class}">
  <div class="{lbl_class}">{spof_label}</div>
  <div class="debt-text">{debt.description}</div>
  <div style="margin-top:4px;font-size:0.72rem;color:#92400e;">If {debt.unit_id} fails:<br>{debt.failure_impact}</div>
</div>
""", unsafe_allow_html=True)

    # Approval buttons
    st.markdown("")
    if rec and not approved:
        if st.button("✅ APPROVE PLAN", use_container_width=True, type="primary", key="approve_btn"):
            state.approved_plan = rec
            state.log_action(
                "Dispatcher",
                f"Approved {rec.strategy_name}",
                f"Score {rec.score}",
            )
            state.increment_version()
            history.save(state)
            st.session_state.state = state
            st.rerun()
        if st.button("❌ Reject Plan", use_container_width=True, key="reject_btn"):
            state.log_action("Dispatcher", f"Rejected {rec.strategy_name}")
            state.recommended_plan = None
            state.increment_version()
            st.session_state.state = state
            st.rerun()
    elif approved:
        if st.button("❌ Revoke Approval", use_container_width=True, key="revoke_btn"):
            state.log_action("Dispatcher", f"Revoked approval of {approved.strategy_name}")
            state.approved_plan = None
            state.increment_version()
            st.session_state.state = state
            st.rerun()

# ---------------------------------------------------------------------------
# BOTTOM TABS
# ---------------------------------------------------------------------------

st.markdown("---")

tab_decide, tab_test, tab_replan, tab_log, tab_agents = st.tabs([
    "🔍 DECIDE — Plan Comparison",
    "🧪 TEST — Resilience Lab",
    "🔄 REPLAN — What Changed?",
    "📋 Action Log",
    "🤖 Agent Activity",
])

# ── DECIDE: Plan Comparison ───────────────────────────────────────────────

with tab_decide:
    if not state.candidate_plans:
        st.info("Generate plans first using the sidebar.")
    else:
        why_data = get_explanation_data(plan, state) if 'plan' in locals() and plan else get_explanation_data(state.recommended_plan, state)

        plans_html = '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-top:8px;">'

        for plan in state.candidate_plans:
            pid = plan.id
            label_a, label_b = _STRATEGY_LABELS.get(plan.strategy_name, ("Plan", plan.strategy_name))
            is_rec = state.recommended_plan and pid == state.recommended_plan.id
            valid = plan.validation and plan.validation.valid

            border_style = "border-color:#2563eb;background:#0c1526;" if is_rec else ""
            badge = "⭐ RECOMMENDED" if is_rec else ""

            valid_html = (
                '<span class="valid-badge valid-ok">✓ VALID</span>'
                if valid
                else '<span class="valid-badge valid-fail">✕ INVALID</span>'
            )

            metrics_html = ""
            if plan.metrics:
                m = plan.metrics
                crit = f'<span style="color:{"#22c55e" if m.critical_covered>0 else "#ef4444"};">{m.critical_covered}/{sum(1 for i in state.incidents if i.urgency and i.urgency.value=="CRITICAL")}</span>'
                metrics_html = f"""
<table style="width:100%;font-size:0.75rem;color:#cbd5e1;border-collapse:collapse;margin-top:6px;">
  <tr><td style="color:#64748b;padding:2px 0;">Coverage</td><td style="text-align:right;">{m.total_covered}/{m.total_incidents}</td></tr>
  <tr><td style="color:#64748b;padding:2px 0;">Critical</td><td style="text-align:right;">{crit}</td></tr>
  <tr><td style="color:#64748b;padding:2px 0;">Avg ETA</td><td style="text-align:right;">{m.average_eta} min</td></tr>
  <tr><td style="color:#64748b;padding:2px 0;">Reserve</td><td style="text-align:right;">{m.reserve_units}</td></tr>
  <tr><td style="color:#64748b;padding:2px 0;">Score</td><td style="text-align:right;font-weight:700;color:{"#22c55e" if (plan.score or 0)>0 else "#ef4444"};">{plan.score}</td></tr>
</table>"""

            res_html = ""
            res = state.resilience_results.get(pid)
            if res:
                spof = f'<div style="font-size:0.68rem;color:#ef4444;margin-top:2px;">SPOFs: {", ".join(res.single_points_of_failure)}</div>' if res.single_points_of_failure else ""
                r_color = "#22c55e" if res.resilience_score >= 70 else "#f59e0b" if res.resilience_score >= 40 else "#ef4444"
                res_html = f"""
<div style="margin-top:8px;background:#0f1117;border-radius:4px;padding:6px 8px;">
  <div style="font-size:0.62rem;color:#64748b;letter-spacing:0.08em;text-transform:uppercase;">Resilience</div>
  <div style="font-size:1.1rem;font-weight:700;color:{r_color};">{res.resilience_score}/100</div>
  <div style="font-size:0.68rem;color:#64748b;">Tested {res.scenarios_tested} scenarios</div>
  {spof}
</div>"""

            violation_html = ""
            if not valid and plan.validation and plan.validation.violations:
                v = plan.validation.violations[0]
                violation_html = f'<div style="font-size:0.7rem;color:#f87171;margin-top:4px;">✕ {v.message}</div>'

            why_not_html = ""
            if why_data["why_not"].get(pid):
                why_not_html = f'<div style="font-size:0.68rem;color:#64748b;margin-top:6px;border-top:1px solid #1e293b;padding-top:4px;">Why not? {why_data["why_not"][pid]}</div>'

            badge_html = f'<div style="font-size:0.65rem;color:#60a5fa;font-weight:700;margin-bottom:4px;">{badge}</div>' if badge else ""

            plans_html += f"""
<div style="background:#0f1117;border:1px solid #1e293b;border-radius:8px;padding:14px;{border_style}">
  {badge_html}
  <div style="font-size:0.65rem;color:#64748b;letter-spacing:0.1em;text-transform:uppercase;">{label_a}</div>
  <div style="font-size:1rem;font-weight:700;color:#e2e8f0;">{label_b}</div>
  <div style="margin:4px 0;">{valid_html}</div>
  {violation_html}
  {metrics_html}
  {res_html}
  {why_not_html}
</div>"""

        plans_html += "</div>"
        st.markdown(plans_html, unsafe_allow_html=True)

# ── TEST: Resilience Lab ──────────────────────────────────────────────────

with tab_test:
    st.markdown("""
<div class="rlab-header">
  <div class="rlab-title">🧪 Resilience Lab</div>
  <div class="rlab-sub">Try to break the plan. We stress-test responses against plausible disruptions before the commander commits.</div>
</div>
""", unsafe_allow_html=True)

    if not state.resilience_results:
        st.info("Generate plans first to run resilience stress-tests.")
    else:
        for pid, res in state.resilience_results.items():
            plan = next((p for p in state.candidate_plans if p.id == pid), None)
            if not plan:
                continue
            label_a, label_b = _STRATEGY_LABELS.get(plan.strategy_name, ("Plan", plan.strategy_name))

            # Summary counts
            survived = sum(1 for i in res.scenario_results if i.plan_still_valid and i.severity_impact == "NONE")
            degraded = sum(1 for i in res.scenario_results if not i.plan_still_valid or i.severity_impact in ("LOW","MEDIUM"))
            failed = sum(1 for i in res.scenario_results if i.severity_impact in ("HIGH","CRITICAL"))

            r_color = "#22c55e" if res.resilience_score >= 70 else "#f59e0b" if res.resilience_score >= 40 else "#ef4444"

            st.markdown(f"""
<div style="background:#0f1117;border:1px solid #1e293b;border-radius:8px;padding:14px;margin-bottom:12px;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
    <div>
      <span style="font-size:0.65rem;color:#64748b;text-transform:uppercase;letter-spacing:0.08em;">{label_a}</span>
      <div style="font-size:1rem;font-weight:700;color:#e2e8f0;">{label_b}</div>
    </div>
    <div style="text-align:right;">
      <div style="font-size:1.5rem;font-weight:700;color:{r_color};">{res.resilience_score}/100</div>
      <div style="font-size:0.65rem;color:#64748b;">Resilience Score</div>
    </div>
  </div>
  <div style="display:flex;gap:20px;margin-bottom:10px;">
    <div style="text-align:center;">
      <div style="font-size:1.3rem;font-weight:700;color:#94a3b8;">{res.scenarios_tested}</div>
      <div style="font-size:0.65rem;color:#64748b;">TESTED</div>
    </div>
    <div style="text-align:center;">
      <div style="font-size:1.3rem;font-weight:700;color:#22c55e;">{survived}</div>
      <div style="font-size:0.65rem;color:#64748b;">SURVIVED</div>
    </div>
    <div style="text-align:center;">
      <div style="font-size:1.3rem;font-weight:700;color:#f59e0b;">{degraded}</div>
      <div style="font-size:0.65rem;color:#64748b;">DEGRADED</div>
    </div>
    <div style="text-align:center;">
      <div style="font-size:1.3rem;font-weight:700;color:#ef4444;">{failed}</div>
      <div style="font-size:0.65rem;color:#64748b;">FAILED</div>
    </div>
  </div>
""", unsafe_allow_html=True)

            # SPOF visualization
            if res.single_points_of_failure:
                spof_html = '<div style="font-size:0.65rem;color:#64748b;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:4px;">⚠ Single Points of Failure</div>'
                for spof_uid in res.single_points_of_failure:
                    # Find affected incidents
                    dep_incs = [a.incident_id for a in plan.assignments if a.unit_id == spof_uid]
                    dep_labels = []
                    for iid in dep_incs:
                        inc = state.get_incident(iid)
                        if inc:
                            dep_labels.append(f"{inc.type} ({iid})")
                    chain = " → ".join(dep_labels) if dep_labels else "critical coverage"
                    spof_html += f"""
<div class="spof-box">
  <div class="spof-unit">{spof_uid}</div>
  <div class="spof-arrow">↓</div>
  <div class="spof-inc">{chain}</div>
  <div class="spof-status">✕ SINGLE POINT OF FAILURE — failure causes critical coverage loss</div>
</div>"""
                st.markdown(spof_html, unsafe_allow_html=True)

            # Scenario list
            st.markdown('<div style="margin-top:8px;">', unsafe_allow_html=True)
            for impact in res.scenario_results:
                if impact.plan_still_valid and impact.severity_impact == "NONE":
                    badge_cls, badge_txt = "scen-survives", "✓ SURVIVES"
                elif impact.severity_impact in ("HIGH", "CRITICAL") or (impact.uncovered_incidents and any(
                    state.get_incident(i) and state.get_incident(i).urgency and
                    state.get_incident(i).urgency.value in ("CRITICAL","HIGH")
                    for i in impact.uncovered_incidents
                )):
                    badge_cls, badge_txt = "scen-fails", "✕ FAILS"
                else:
                    badge_cls, badge_txt = "scen-degraded", "⚠ DEGRADED"

                detail = ""
                if impact.uncovered_incidents:
                    labels = []
                    for iid in impact.uncovered_incidents:
                        inc = state.get_incident(iid)
                        labels.append(inc.type if inc else iid)
                    detail = f" — Uncovered: {', '.join(labels)}"
                elif impact.eta_increase_minutes > 0:
                    detail = f" — ETA +{impact.eta_increase_minutes} min"

                st.markdown(f"""
<div class="scenario-row">
  <div>
    <span class="scen-desc">{impact.scenario.description}</span>
    <span style="font-size:0.68rem;color:#64748b;">{detail}</span>
  </div>
  <span class="scen-badge {badge_cls}">{badge_txt}</span>
</div>
""", unsafe_allow_html=True)

            st.markdown("</div></div>", unsafe_allow_html=True)

# ── REPLAN: What Changed? + Timeline ─────────────────────────────────────

with tab_replan:
    if not state.plan_diffs:
        st.info("No replanning events yet. Trigger a disruption (breakdown, road block, or new incident).")
    else:
        diff = state.plan_diffs[-1]

        # Event header
        st.markdown(f"""
<div class="diff-event">
  <div style="font-size:0.65rem;color:#64748b;text-transform:uppercase;letter-spacing:0.08em;">Event</div>
  <div style="font-size:1rem;font-weight:700;color:#f59e0b;">⚡ {diff.trigger}</div>
</div>
""", unsafe_allow_html=True)

        # Before / After
        if diff.changed_units or diff.newly_uncovered or diff.newly_covered:
            before_html = ""
            after_html = ""

            for c in diff.changed_units:
                inc = state.get_incident(c["incident"])
                inc_label = inc.type if inc else c["incident"]
                before_html += f'<div>{c["before_unit"]} → {inc_label} (ETA {c["before_eta"]:.1f} min)</div>'
                after_html += f'<div>{c["after_unit"]} → {inc_label} (ETA {c["after_eta"]:.1f} min)</div>'

            for iid in diff.newly_uncovered:
                inc = state.get_incident(iid)
                before_html += f'<div style="color:#22c55e;">{inc.type if inc else iid}: covered</div>'
                after_html += f'<div style="color:#ef4444;">{inc.type if inc else iid}: ✕ UNCOVERED</div>'

            for iid in diff.newly_covered:
                inc = state.get_incident(iid)
                before_html += f'<div style="color:#94a3b8;">{inc.type if inc else iid}: —</div>'
                after_html += f'<div style="color:#22c55e;">{inc.type if inc else iid}: ✓ NOW COVERED</div>'

            st.markdown(f"""
<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:8px;">
  <div style="background:#0f1117;border:1px solid #1e293b;border-radius:6px;padding:10px;">
    <div style="font-size:0.65rem;font-weight:700;letter-spacing:0.08em;color:#ef4444;margin-bottom:6px;">BEFORE</div>
    <div style="font-size:0.8rem;color:#e2e8f0;">{before_html}</div>
  </div>
  <div style="background:#0f1117;border:1px solid #1e293b;border-radius:6px;padding:10px;">
    <div style="font-size:0.65rem;font-weight:700;letter-spacing:0.08em;color:#22c55e;margin-bottom:6px;">AFTER</div>
    <div style="font-size:0.8rem;color:#e2e8f0;">{after_html}</div>
  </div>
</div>
""", unsafe_allow_html=True)

        # ETA changes
        if diff.eta_changes:
            eta_html = "".join(
                f'<div style="font-size:0.78rem;color:#e2e8f0;">'
                f'{(lambda i: i.type if i else iid)(state.get_incident(iid))}: '
                f'<span style="color:{"#ef4444" if delta>0 else "#22c55e"};">'
                f'{"+" if delta>0 else ""}{delta} min</span></div>'
                for iid, delta in diff.eta_changes.items()
            )
            st.markdown(f"""
<div style="background:#0f1117;border:1px solid #1e293b;border-radius:6px;padding:10px;margin-top:8px;">
  <div style="font-size:0.65rem;color:#64748b;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:4px;">ETA Changes</div>
  {eta_html}
</div>
""", unsafe_allow_html=True)

        # Impact analysis
        if getattr(state, "latest_impact_analysis", None):
            impact = state.latest_impact_analysis
            st.markdown(f"""
<div style="background:#1c0f0f;border:1px solid #7f1d1d;border-radius:8px;padding:12px;margin-top:12px;">
  <div style="font-size:0.75rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#fca5a5;margin-bottom:4px;">💥 INITIAL IMPACT ASSESSMENT</div>
  <div style="font-size:0.75rem;color:#fecaca;">Lost coverage: {', '.join(impact.get('lost_coverage', [])) or 'None'}</div>
  <div style="font-size:0.75rem;color:#fecaca;">Invalidated assignments: {', '.join(impact.get('invalidated_assignments', [])) or 'None'}</div>
</div>
""", unsafe_allow_html=True)

        # Reallocation Reasons
        if getattr(diff, "reallocation_reasons", []):
            reasons_html = ""
            for r in diff.reallocation_reasons:
                reasons_html += f"""
<div style="background:#0f1117;border-left:3px solid #f59e0b;padding:8px;margin-top:4px;font-size:0.75rem;color:#cbd5e1;">
  <strong>Incident {r.get('incident_id')}</strong>: {r.get('previous_unit')} → {r.get('new_unit')}
  <br/><span style="color:#64748b;">Trigger: {r.get('trigger')} | Severity: {r.get('incident_severity')} | Avail: {r.get('resource_availability')} | ETA impact: {r.get('eta_impact')}m</span>
  <br/><span style="color:#eab308;font-style:italic;">"{r.get('reason_for_change')}"</span>
</div>"""
            st.markdown(f"""
<div style="margin-top:8px;">
  <div style="font-size:0.65rem;color:#64748b;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:4px;">Explicit Reallocation Reasons</div>
  {reasons_html}
</div>
""", unsafe_allow_html=True)
            
        # Why changed
        st.markdown(f"""
<div class="why-box" style="margin-top:8px;">
  <div class="why-label">Why did we replan?</div>
  <div class="why-text">{diff.explanation.replace(chr(10), "<br>")}</div>
</div>
""", unsafe_allow_html=True)

    # Crisis Timeline
    st.markdown("---")
    st.markdown("#### ⏱ Crisis Timeline")

    all_versions = sorted({e.version for e in state.action_log})
    for ver in all_versions:
        entries = [e for e in state.action_log if e.version == ver]
        is_current = ver == state.version
        dot_class = "tl-dot current" if is_current else "tl-dot"
        ver_html = "".join(
            f'<div class="tl-action">{e.agent}: {e.action}</div>'
            f'{"<div class=\"tl-detail\">" + e.details + "</div>" if e.details else ""}'
            for e in entries[:2]
        )
        st.markdown(f"""
<div class="timeline-step">
  <div class="{dot_class}"></div>
  <div class="tl-content">
    <div class="tl-ver">STATE v{ver}{"  ← CURRENT" if is_current else ""}</div>
    {ver_html}
  </div>
</div>
""", unsafe_allow_html=True)

# ── Action Log ────────────────────────────────────────────────────────────

with tab_log:
    if state.action_log:
        for entry in reversed(state.action_log[-30:]):
            ts = entry.timestamp.split("T")[-1][:8] if "T" in entry.timestamp else entry.timestamp
            st.markdown(f"""
<div class="log-entry">
  <div style="display:flex;gap:8px;align-items:baseline;">
    <span class="log-ver">v{entry.version}</span>
    <span style="font-size:0.65rem;color:#334155;">{ts}</span>
    <span class="log-agent">[{entry.agent}]</span>
    <span class="log-action">{entry.action}</span>
  </div>
  {"<div class='log-detail'>" + entry.details + "</div>" if entry.details else ""}
</div>
""", unsafe_allow_html=True)
    else:
        st.info("No actions logged yet.")

# ── Agent Activity ────────────────────────────────────────────────────────

with tab_agents:
    st.markdown("""
<div style="font-size:0.72rem;color:#64748b;margin-bottom:12px;padding:8px 10px;
  background:#0f1117;border:1px solid #1e293b;border-radius:4px;">
  ⚠ <b>Honesty note:</b> All listed operations are performed by deterministic Python.
  LLM integration is stubbed for future work. No AI claims are fabricated.
</div>
""", unsafe_allow_html=True)

    agents = [
        ("💥 Impact Analysis Agent", "impact.py", "analyze_impact()"),
        ("🔍 Incident Assessment Agent", "severity.py", "assess_incident()"),
        ("📦 Resource Allocation Agent", "allocator.py", "generate_plan_a/b/c()"),
        ("🗺 Route / Logistics Agent", "route.py", "calculate_eta()"),
        ("🔒 Constraint Checker", "constraints.py", "validate_plan()"),
        ("🧪 Resilience Engine", "resilience.py", "evaluate_plan_resilience()"),
        ("📊 Plan Comparator", "comparator.py", "compare_and_select()"),
        ("🤖 Command / Planning Agent", "comparator.py", "generate_why_explanation()"),
        ("🔄 Replanner", "replanner.py", "apply_unit_breakdown() / apply_road_block()"),
        ("👤 Human Dispatcher", "app.py", "Approve / Reject"),
    ]

    for agent_name, module, fn in agents:
        # Check which agents have run based on action log
        relevant_logs = [e for e in state.action_log if any(
            kw in e.agent.lower() for kw in agent_name.lower().split()[1:2]
        )]
        ran = len(relevant_logs) > 0
        status_icon = "✓" if ran else "⏳"
        status_color = "#22c55e" if ran else "#64748b"
        last_action = relevant_logs[-1].action if relevant_logs else "Not yet run"

        st.markdown(f"""
<div style="background:#0f1117;border:1px solid #1e293b;border-radius:6px;
  padding:10px 14px;margin-bottom:6px;display:flex;justify-content:space-between;align-items:center;">
  <div>
    <div style="font-size:0.85rem;font-weight:600;color:#e2e8f0;">{agent_name}</div>
    <div style="font-size:0.68rem;color:#64748b;font-family:monospace;">{module} → {fn}</div>
    <div style="font-size:0.72rem;color:#94a3b8;margin-top:2px;">{last_action}</div>
  </div>
  <div style="font-size:1rem;color:{status_color};font-weight:700;">{status_icon}</div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Footer disclaimer
# ---------------------------------------------------------------------------

st.markdown("""
<div style="text-align:center;padding:16px 0;margin-top:24px;border-top:1px solid #1e293b;">
  <div style="font-size:0.65rem;color:#334155;">
    ⚠ SIMULATION DATA — Emergency incidents, units and disruptions are simulated for demonstration purposes only.
    No real emergency data is used. Public map tiles from OpenStreetMap contributors.
  </div>
  <div style="font-size:0.62rem;color:#1e293b;margin-top:4px;">
    Crisis Command | Team Rocket | GATEWAYS 2026
  </div>
</div>
""", unsafe_allow_html=True)
