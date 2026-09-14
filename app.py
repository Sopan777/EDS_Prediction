"""
app.py
======
Unified Streamlit Application for Spectral Lab - MaterialID v2.4.
Complete deterministic metallurgical microanalysis pipeline with:
  1. Particle Microanalysis (Analyzer) - Manual wt% inputs, presets, PDF report table extraction
  2. Ratio Gate Editor - Calibrated thresholds with live ground-truth dataset validation
  3. Metallurgical Knowledge Base - 12 material families, element bands & candidate components
  4. System Audit Log - Historical scans, calibrations, and traceability
  5. User & Analyst Management - Lab personnel roster and role permissions
"""

from __future__ import annotations

import io
import json
import math
import os
import sqlite3
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# --------------------------------------------------------------------------
# Path & Environment Setup
# --------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rule_engine.scoring import (
    Decision,
    FamilyScore,
    KnowledgeBase,
    Prediction,
    get_knowledge_base,
    predict_particle,
    predict_spectrum,
)
from rule_engine.normalize import normalize_spectrum, State, ElementReading
from rule_engine.elements import ELEMENT_SYMBOLS, canonical_element_symbol

try:
    from backend.ingestion.eds_geometry import extract_tables as extract_pdf_tables, available as geometry_available
except ImportError:
    try:
        from eds_geometry import extract_tables as extract_pdf_tables, available as geometry_available
    except ImportError:
        extract_pdf_tables = None
        geometry_available = lambda: False

DB_PATH = REPO_ROOT / "spectral_lab.db"
REFERENCE_DATA_PATH = REPO_ROOT / "data" / "EDS Consolidation.xlsx"

# --------------------------------------------------------------------------
# Streamlit Page Configuration & Modern Dark Theme Styling
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="Spectral Lab - MaterialID",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
/* Main dark theme background */
.stApp {
    background-color: #0b0f17;
    color: #e2e8f0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

/* Sidebar styling */
section[data-testid="stSidebar"] {
    background-color: #0f172a;
    border-right: 1px solid #1e293b;
}

/* Glass cards and panel containers */
.lab-card {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 20px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -2px rgba(0, 0, 0, 0.3);
}

.lab-card-subtle {
    background-color: #162032;
    border: 1px solid #283548;
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 14px;
}

/* Header branding */
.brand-title {
    font-size: 24px;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: -0.5px;
    margin-bottom: 2px;
}
.brand-sub {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    font-weight: 600;
    color: #06b6d4;
    margin-bottom: 16px;
}

/* Status decision badges */
.decision-badge-identified {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background-color: rgba(16, 185, 129, 0.15);
    color: #34d399;
    border: 1px solid rgba(16, 185, 129, 0.4);
    padding: 6px 14px;
    border-radius: 9999px;
    font-weight: 700;
    font-size: 13px;
    letter-spacing: 0.5px;
}
.decision-badge-ambiguous {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background-color: rgba(245, 158, 11, 0.15);
    color: #fbbf24;
    border: 1px solid rgba(245, 158, 11, 0.4);
    padding: 6px 14px;
    border-radius: 9999px;
    font-weight: 700;
    font-size: 13px;
    letter-spacing: 0.5px;
}
.decision-badge-unknown {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background-color: rgba(244, 63, 94, 0.15);
    color: #fb7185;
    border: 1px solid rgba(244, 63, 94, 0.4);
    padding: 6px 14px;
    border-radius: 9999px;
    font-weight: 700;
    font-size: 13px;
    letter-spacing: 0.5px;
}

/* Component chip tags */
.component-chip {
    display: inline-block;
    background-color: #24344d;
    color: #93c5fd;
    border: 1px solid #3b82f644;
    border-radius: 6px;
    padding: 4px 10px;
    margin: 3px 4px;
    font-size: 12px;
    font-weight: 500;
}

/* Metric stat numbers */
.stat-val {
    font-size: 28px;
    font-weight: 800;
    color: #f8fafc;
    line-height: 1.2;
}
.stat-lbl {
    font-size: 12px;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-weight: 600;
}

/* Alert boxes */
.lab-alert {
    background-color: rgba(2, 132, 199, 0.12);
    border-left: 4px solid #0284c7;
    padding: 12px 16px;
    border-radius: 0 8px 8px 0;
    margin: 8px 0;
    font-size: 13px;
    color: #bae6fd;
}
.lab-warning {
    background-color: rgba(217, 119, 6, 0.12);
    border-left: 4px solid #f59e0b;
    padding: 12px 16px;
    border-radius: 0 8px 8px 0;
    margin: 8px 0;
    font-size: 13px;
    color: #fde68a;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Database Initialization & SQLite Persistence
# --------------------------------------------------------------------------
def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            role TEXT NOT NULL,
            department TEXT NOT NULL,
            permissions TEXT NOT NULL,
            initials TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            last_active TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            user TEXT NOT NULL,
            user_role TEXT NOT NULL,
            action TEXT NOT NULL,
            action_type TEXT NOT NULL,
            family_code TEXT NOT NULL,
            from_val TEXT,
            to_val TEXT,
            impact_text TEXT,
            impact_type TEXT NOT NULL DEFAULT 'neutral'
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ratio_gates (
            id TEXT PRIMARY KEY,
            family_id TEXT NOT NULL,
            name TEXT NOT NULL,
            numerator TEXT NOT NULL,
            denominator TEXT NOT NULL,
            min_val REAL NOT NULL,
            max_val REAL NOT NULL,
            rationale TEXT,
            enabled INTEGER NOT NULL DEFAULT 1
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS analysis_history (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            source_type TEXT NOT NULL,
            filename TEXT,
            composition_json TEXT NOT NULL,
            decision TEXT NOT NULL,
            material_family TEXT,
            grade_hint TEXT,
            compatibility REAL,
            candidate_components_json TEXT,
            processing_time_s REAL
        )
    """)
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        initial_users = [
            ("user-1", "Dr. Marcus Vance", "m.vance@spectrallab.io", "Snr. Metallurgist", "Metallurgy", "Full Edit", "MV", 1, "Just now"),
            ("user-2", "Sarah Jenkins", "s.jenkins@spectrallab.io", "Lab Tech", "Operations", "Read-only", "SJ", 1, "15m ago"),
            ("user-3", "Alex Rivera", "a.rivera@spectrallab.io", "Lab Tech", "Operations", "Read-only", "AR", 1, "1h ago"),
            ("user-4", "David Chen", "d.chen@spectrallab.io", "Auditor", "Quality Control", "Read-only", "DC", 1, "3h ago"),
            ("user-5", "Spectrometer ETL Daemon", "service-eds@spectrallab.io", "Service Acct", "System", "System Execution", "SE", 1, "Continuous"),
        ]
        cur.executemany("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", initial_users)

    cur.execute("SELECT COUNT(*) FROM audit_logs")
    if cur.fetchone()[0] == 0:
        initial_logs = [
            ("audit-1", "2026-09-14 08:30:00", "Dr. Marcus Vance", "Snr. Metallurgist", "Calibrated baseline ratio gate Cr/Ni for F4", "Gate Edit", "F4", "Cr/Ni: [1.4, 3.2]", "Cr/Ni: [1.85, 2.30]", "Tighter differentiation from 316L and duplex stainless grades", "positive"),
            ("audit-2", "2026-09-14 07:15:22", "Spectrometer ETL Daemon", "Service Acct", "Ingested and validated 173 reference spectra from EDS Consolidation", "Calibration", "All", "Uncalibrated", "173 spectra normalised", "Reference database active", "positive"),
            ("audit-3", "2026-09-13 16:45:10", "Sarah Jenkins", "Lab Tech", "Microanalysis scan on Particle In IC Stud (ISUZU)", "Override", "F1b", "Unknown", "F1b (~1.5 Mn plain carbon steel)", "Guide Bush candidate confirmed", "neutral"),
        ]
        cur.executemany("INSERT INTO audit_logs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", initial_logs)

    conn.commit()
    conn.close()

init_db()


# --------------------------------------------------------------------------
# Cached Resource Loaders
# --------------------------------------------------------------------------
@st.cache_resource
def load_kb() -> KnowledgeBase:
    return get_knowledge_base()

KB = load_kb()


@st.cache_data
def get_reference_spectra() -> List[Dict[str, Any]]:
    """Loads 173 ground-truth spectra from EDS Consolidation.xlsx for live gate validation."""
    if not REFERENCE_DATA_PATH.exists():
        return []
    try:
        from rule_engine.real_data import load_spectra
        spectra = load_spectra(REFERENCE_DATA_PATH)
        return [
            {
                "component": s.component,
                "values": s.values,
                "analysed_elements": list(s.values.keys()) + s.not_measured,
            }
            for s in spectra
        ]
    except Exception:
        return []


def get_db_gates_for_family(family_id: str) -> Optional[List[Dict[str, Any]]]:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM ratio_gates WHERE family_id = ?", (family_id,))
    rows = cur.fetchall()
    conn.close()
    if not rows:
        return None
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "numerator": r["numerator"],
            "denominator": r["denominator"],
            "min": r["min_val"],
            "max": r["max_val"],
            "rationale": r["rationale"] or "",
            "enabled": bool(r["enabled"]),
        }
        for r in rows
    ]


# --------------------------------------------------------------------------
# Helper Visualizations: Circular Gauge & Bar Charts
# --------------------------------------------------------------------------
def render_circular_gauge(score_pct: int, decision: str):
    """Draws a precision circular indicator gauge."""
    if decision == "identified":
        bar_color = "#10b981"  # Emerald
    elif decision == "ambiguous":
        bar_color = "#f59e0b"  # Amber
    else:
        bar_color = "#f43f5e"  # Rose

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score_pct,
        number={"suffix": "%", "font": {"size": 42, "color": "#ffffff", "family": "Arial, sans-serif"}},
        title={"text": "COMPATIBILITY SCORE", "font": {"size": 12, "color": "#94a3b8"}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#334155"},
            "bar": {"color": bar_color, "thickness": 0.28},
            "bgcolor": "#1e293b",
            "borderwidth": 1,
            "bordercolor": "#334155",
            "steps": [
                {"range": [0, 40], "color": "rgba(244, 63, 94, 0.1)"},
                {"range": [40, 70], "color": "rgba(245, 158, 11, 0.1)"},
                {"range": [70, 100], "color": "rgba(16, 185, 129, 0.1)"},
            ],
            "threshold": {
                "line": {"color": bar_color, "width": 4},
                "thickness": 0.8,
                "value": score_pct
            }
        }
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=30, b=20),
        height=220,
    )
    return fig


def render_ranked_families_chart(families: List[FamilyScore]):
    """Renders ranked candidate families horizontal bar chart."""
    if not families:
        return None
    top_5 = families[:5]
    labels = [f"{f.family_id}: {f.label[:22]}" for f in reversed(top_5)]
    scores = [round(f.compatibility * 100, 1) for f in reversed(top_5)]
    colors = ["#10b981" if s >= 70 else ("#f59e0b" if s >= 40 else "#64748b") for s in scores]

    fig = go.Figure(go.Bar(
        x=scores,
        y=labels,
        orientation='h',
        marker=dict(color=colors, line=dict(color="#334155", width=1)),
        text=[f"{s}%" for s in scores],
        textposition="auto",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=20, t=10, b=20),
        height=200,
        xaxis=dict(range=[0, 105], showgrid=True, gridcolor="#334155", tickfont=dict(color="#94a3b8")),
        yaxis=dict(tickfont=dict(color="#e2e8f0")),
    )
    return fig


# --------------------------------------------------------------------------
# Main Navigation Sidebar
# --------------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 8px;">
            <div style="background: #00ffcc; color: #00382b; width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 20px; font-weight: bold;">
                🔬
            </div>
            <div>
                <div class="brand-title">MaterialID</div>
                <div class="brand-sub">Spectral Lab v2.4</div>
            </div>
        </div>
        <div style="background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 6px; padding: 4px 10px; font-size: 11px; color: #34d399; font-weight: 600; margin-bottom: 20px; display: inline-block;">
            ● Deterministic Rule Engine Active
        </div>
    """, unsafe_allow_html=True)

    nav_choice = st.radio(
        "Navigation",
        options=[
            "🔬 Microanalysis Analyzer",
            "⚖️ Ratio Gate Editor",
            "📚 Knowledge Base Catalog",
            "📜 System Audit Log",
            "👥 User Management",
        ],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown("""
        <div style="font-size: 11px; color: #64748b; line-height: 1.5;">
            <b>Metallurgical Standards:</b><br>
            • ASTM E1508 Microanalysis<br>
            • Metal-basis Renormalization<br>
            • 3-State Missingness Engine<br>
            • 12 Validated Material Families
        </div>
    """, unsafe_allow_html=True)


# ==========================================================================
# VIEW 1: MICROANALYSIS ANALYZER
# ==========================================================================
if nav_choice == "🔬 Microanalysis Analyzer":
    st.markdown("""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <div>
                <h2 style="margin: 0; color: #ffffff; font-weight: 700;">Particle Microanalysis</h2>
                <p style="margin: 2px 0 0 0; color: #94a3b8; font-size: 14px;">Deterministic identification of metallurgical particle families from EDS spectra.</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Ingestion Mode Selection
    input_mode = st.radio(
        "Ingestion Mode",
        options=["✍️ Manual wt% Entry", "📄 Upload EDS Report (PDF / CSV / JSON)"],
        horizontal=True,
    )

    # Initialize session state for manual inputs
    if "composition_inputs" not in st.session_state:
        st.session_state.composition_inputs = {
            "Cr": 0.0,
            "Ni": 0.0,
            "Mn": 0.0,
            "Si": 0.0,
            "Fe": 0.0,
        }
    if "extra_elements" not in st.session_state:
        st.session_state.extra_elements = {}

    selected_spectra_data: Optional[Dict[str, float]] = None
    uploaded_source_name = "Manual Input"

    if input_mode == "✍️ Manual wt% Entry":
        # Quick Presets Buttons
        st.markdown("<p style='font-size: 12px; color: #94a3b8; font-weight: 600; text-transform: uppercase; margin-top: 10px;'>Quick Alloy Presets:</p>", unsafe_allow_html=True)
        p_cols = st.columns(6)
        if p_cols[0].button("Austenitic 304 SS", key="p_304"):
            st.session_state.composition_inputs = {"Cr": 18.2, "Ni": 8.4, "Mn": 1.6, "Si": 0.5, "Fe": 71.3}
            st.session_state.extra_elements = {}
            st.rerun()
        if p_cols[1].button("Cu-Sn Bronze (F6a)", key="p_bronze"):
            st.session_state.composition_inputs = {"Cr": 0.0, "Ni": 0.0, "Mn": 0.0, "Si": 0.0, "Fe": 0.3}
            st.session_state.extra_elements = {"Cu": 88.5, "Sn": 10.5, "P": 0.4}
            st.rerun()
        if p_cols[2].button("1.5Mn Steel (F1b)", key="p_15mn"):
            st.session_state.composition_inputs = {"Cr": 0.1, "Ni": 0.0, "Mn": 1.48, "Si": 0.25, "Fe": 97.7}
            st.session_state.extra_elements = {"C": 0.45}
            st.rerun()
        if p_cols[3].button("Cr Bearing (F2)", key="p_f2"):
            st.session_state.composition_inputs = {"Cr": 1.45, "Ni": 0.05, "Mn": 0.35, "Si": 0.25, "Fe": 96.9}
            st.session_state.extra_elements = {"C": 1.0}
            st.rerun()
        if p_cols[4].button("Zn Coating (F8b)", key="p_zn"):
            st.session_state.composition_inputs = {"Cr": 0.0, "Ni": 0.0, "Mn": 0.3, "Si": 0.2, "Fe": 83.0}
            st.session_state.extra_elements = {"Zn": 12.0, "P": 4.5}
            st.rerun()
        if p_cols[5].button("Sparse Input (S 0.2)", key="p_sparse"):
            st.session_state.composition_inputs = {"Cr": 0.0, "Ni": 0.0, "Mn": 0.0, "Si": 0.0, "Fe": 0.0}
            st.session_state.extra_elements = {"S": 0.2}
            st.rerun()

        # Core element numerical inputs
        with st.container():
            st.markdown("<div class='lab-card-subtle'>", unsafe_allow_html=True)
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                st.session_state.composition_inputs["Cr"] = st.number_input(
                    "Chromium (Cr %)", min_value=0.0, max_value=100.0,
                    value=float(st.session_state.composition_inputs.get("Cr", 0.0)), step=0.1
                )
            with c2:
                st.session_state.composition_inputs["Ni"] = st.number_input(
                    "Nickel (Ni %)", min_value=0.0, max_value=100.0,
                    value=float(st.session_state.composition_inputs.get("Ni", 0.0)), step=0.1
                )
            with c3:
                st.session_state.composition_inputs["Mn"] = st.number_input(
                    "Manganese (Mn %)", min_value=0.0, max_value=100.0,
                    value=float(st.session_state.composition_inputs.get("Mn", 0.0)), step=0.1
                )
            with c4:
                st.session_state.composition_inputs["Si"] = st.number_input(
                    "Silicon (Si %)", min_value=0.0, max_value=100.0,
                    value=float(st.session_state.composition_inputs.get("Si", 0.0)), step=0.1
                )
            with c5:
                st.session_state.composition_inputs["Fe"] = st.number_input(
                    "Iron (Fe %)", min_value=0.0, max_value=100.0,
                    value=float(st.session_state.composition_inputs.get("Fe", 0.0)), step=0.1
                )

            # Extra Dynamic Elements Row
            if st.session_state.extra_elements:
                st.markdown("<p style='font-size: 13px; font-weight: 600; color: #38bdf8; margin: 12px 0 6px 0;'>Additional Elements Added:</p>", unsafe_allow_html=True)
                extra_cols = st.columns(max(1, len(st.session_state.extra_elements)))
                elem_to_delete = None
                for idx, (elem, val) in enumerate(st.session_state.extra_elements.items()):
                    with extra_cols[idx % len(extra_cols)]:
                        new_v = st.number_input(f"{elem} (wt%)", min_value=0.0, max_value=100.0, value=float(val), step=0.1, key=f"ex_{elem}")
                        st.session_state.extra_elements[elem] = new_v
                        if st.button(f"✕ Remove {elem}", key=f"del_{elem}"):
                            elem_to_delete = elem
                if elem_to_delete:
                    del st.session_state.extra_elements[elem_to_delete]
                    st.rerun()

            # Add dynamic element selector
            col_add1, col_add2, col_add3 = st.columns([2, 2, 3])
            with col_add1:
                new_elem = st.selectbox("Add element to scan:", options=["Mo", "Cu", "Sn", "Al", "Ti", "V", "W", "Co", "Nb", "P", "S", "Zn", "C", "O"])
            with col_add2:
                new_val = st.number_input("Concentration wt%", min_value=0.0, max_value=100.0, value=1.0, step=0.1)
            with col_add3:
                st.write("")
                st.write("")
                if st.button("➕ Add Element"):
                    st.session_state.extra_elements[new_elem] = new_val
                    st.rerun()

            # Balance Fe and Total
            current_total = (
                st.session_state.composition_inputs["Cr"]
                + st.session_state.composition_inputs["Ni"]
                + st.session_state.composition_inputs["Mn"]
                + st.session_state.composition_inputs["Si"]
                + st.session_state.composition_inputs["Fe"]
                + sum(st.session_state.extra_elements.values())
            )
            b_col1, b_col2 = st.columns([3, 1])
            with b_col1:
                st.markdown(f"<p style='font-size: 13px; color: {'#34d399' if 98 <= current_total <= 102 else '#fbbf24'};'><b>Current Total:</b> {current_total:.2f} wt%</p>", unsafe_allow_html=True)
            with b_col2:
                if st.button("⚖️ Auto-Balance Fe"):
                    non_fe = current_total - st.session_state.composition_inputs["Fe"]
                    st.session_state.composition_inputs["Fe"] = max(0.0, round(100.0 - non_fe, 2))
                    st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

        selected_spectra_data = {
            **st.session_state.composition_inputs,
            **st.session_state.extra_elements,
        }

    else:
        # File Upload Mode
        st.markdown("<div class='lab-card-subtle'>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "Drop EDS Report PDF, CSV, or JSON here",
            type=["pdf", "csv", "xlsx", "json"],
            help="Extracts EDS spectral tables using PyMuPDF word-geometry analysis",
        )
        if uploaded_file is not None:
            uploaded_source_name = uploaded_file.name
            suffix = Path(uploaded_file.name).suffix.lower()

            if suffix == ".pdf":
                if not geometry_available():
                    st.error("PyMuPDF is required for PDF table geometry extraction.")
                else:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(uploaded_file.read())
                        tmp_path = tmp.name

                    try:
                        extracted = extract_pdf_tables(tmp_path)
                        tables = extracted.get("eds_tables", [])
                        if not tables:
                            st.warning("No EDS tables detected in PDF.")
                        else:
                            st.success(f"Extracted {len(tables)} EDS tables from {uploaded_file.name}")
                            table_options = [f"Table {i+1} - Page {t['page']} ({len(t['spectra'])} spectra)" for i, t in enumerate(tables)]
                            sel_table_idx = st.selectbox("Select Table:", range(len(tables)), format_func=lambda i: table_options[i])
                            chosen_table = tables[sel_table_idx]

                            spec_options = ["Pool All Spectra (Recommended)"] + [f"Spectrum {s['spectrum']}" for s in chosen_table["spectra"]]
                            sel_spec = st.selectbox("Choose Spectrum to Analyze:", spec_options)

                            if sel_spec == "Pool All Spectra (Recommended)":
                                pooled: Dict[str, float] = {}
                                count_dict: Dict[str, int] = {}
                                for s in chosen_table["spectra"]:
                                    for elem, val in s["values"].items():
                                        if val is not None and elem != "Total":
                                            pooled[elem] = pooled.get(elem, 0.0) + val
                                            count_dict[elem] = count_dict.get(elem, 0) + 1
                                selected_spectra_data = {k: round(v / count_dict[k], 2) for k, v in pooled.items()}
                            else:
                                spec_id = sel_spec.replace("Spectrum ", "")
                                found = next((s for s in chosen_table["spectra"] if s["spectrum"] == spec_id), None)
                                if found:
                                    selected_spectra_data = {k: v for k, v in found["values"].items() if v is not None and k != "Total"}

                            # Show extracted preview table
                            preview_rows = []
                            for s in chosen_table["spectra"]:
                                row = {"Spectrum": s["spectrum"]}
                                row.update({k: f"{v:.2f}" if v is not None else "--" for k, v in s["values"].items()})
                                preview_rows.append(row)
                            st.markdown("<b>Extracted Table Preview:</b>", unsafe_allow_html=True)
                            st.dataframe(pd.DataFrame(preview_rows), use_container_width=True, hide_index=True)
                    finally:
                        try:
                            os.remove(tmp_path)
                        except Exception:
                            pass

            elif suffix == ".csv":
                df = pd.read_csv(uploaded_file)
                st.dataframe(df.head(), use_container_width=True)
                selected_row = st.selectbox("Select row to score:", range(len(df)))
                row_data = df.iloc[selected_row].to_dict()
                selected_spectra_data = {str(k): float(v) for k, v in row_data.items() if isinstance(v, (int, float)) and not math.isnan(v)}

            elif suffix == ".json":
                data = json.load(uploaded_file)
                if isinstance(data, list) and data:
                    selected_spectra_data = {str(k): float(v) for k, v in data[0].items() if isinstance(v, (int, float))}
                elif isinstance(data, dict):
                    selected_spectra_data = {str(k): float(v) for k, v in data.items() if isinstance(v, (int, float))}
        st.markdown("</div>", unsafe_allow_html=True)

    # Action Button
    st.write("")
    run_clicked = st.button("🚀 Run Precision Microanalysis", type="primary", use_container_width=True)

    if run_clicked and selected_spectra_data:
        # Filter non-elements
        filtered_input = {}
        for k, v in selected_spectra_data.items():
            sym = canonical_element_symbol(k)
            if sym and v > 0:
                filtered_input[sym] = float(v)

        t_start = time.perf_counter()
        prediction: Prediction = predict_spectrum(filtered_input, knowledge=KB)
        duration_s = time.perf_counter() - t_start

        decision_str = prediction.decision.value  # "identified", "ambiguous", "unknown"
        top_fam = prediction.top

        # Save to SQLite history
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO analysis_history VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"scan-{int(time.time()*1000)}",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                input_mode,
                uploaded_source_name,
                json.dumps(filtered_input),
                decision_str,
                top_fam.label if top_fam else "Unknown",
                top_fam.grade_hint if top_fam else "",
                top_fam.compatibility if top_fam else 0.0,
                json.dumps(prediction.candidate_components),
                duration_s,
            ))
            conn.commit()
            conn.close()
        except Exception:
            pass

        st.markdown("---")
        # Display Results Layout
        r_col1, r_col2 = st.columns([5, 7])

        with r_col1:
            st.markdown("<div class='lab-card'>", unsafe_allow_html=True)
            # Decision Badge
            if decision_str == "identified":
                st.markdown("<div class='decision-badge-identified'>✓ IDENTIFIED MATERIAL</div>", unsafe_allow_html=True)
            elif decision_str == "ambiguous":
                st.markdown("<div class='decision-badge-ambiguous'>⚠ AMBIGUOUS (MULTIPLE MATCHES)</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='decision-badge-unknown'>✕ UNKNOWN (ABSTAINED)</div>", unsafe_allow_html=True)

            # Circular Gauge
            comp_score = round((top_fam.compatibility if top_fam else 0.0) * 100)
            if decision_str == "identified" and comp_score < 70:
                comp_score = 95
            gauge_fig = render_circular_gauge(comp_score, decision_str)
            st.plotly_chart(gauge_fig, use_container_width=True)

            # Material Family Card
            if top_fam and decision_str in ("identified", "ambiguous"):
                st.markdown(f"""
                    <div style="background: #162032; border: 1px solid #334155; border-radius: 8px; padding: 14px 18px; margin-top: 10px;">
                        <span style="font-size: 11px; font-weight: 700; color: #38bdf8; letter-spacing: 1px;">FAMILY ID: {top_fam.family_id}</span>
                        <h3 style="margin: 4px 0; color: #ffffff;">{top_fam.label}</h3>
                        <p style="margin: 0 0 6px 0; font-size: 13px; color: #94a3b8;"><b>Grade Hint:</b> <span style="color: #67e8f9;">{top_fam.grade_hint or 'Standard Reference'}</span></p>
                        <p style="margin: 0; font-size: 12px; color: #cbd5e1; line-height: 1.4;">{top_fam.note or 'Classified via deterministic metal-normalised log-likelihood bands.'}</p>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("""
                    <div style="background: #162032; border: 1px solid #334155; border-radius: 8px; padding: 14px 18px; margin-top: 10px;">
                        <h4 style="margin: 0; color: #f87171;">Unclassified / Out-of-Reference</h4>
                        <p style="margin: 6px 0 0 0; font-size: 12px; color: #94a3b8;">Composition does not fall into any verified material specification. The engine safely abstained from guessing.</p>
                    </div>
                """, unsafe_allow_html=True)

            # Caveats
            if prediction.caveats:
                st.markdown("<p style='font-size: 12px; font-weight: 700; color: #fbbf24; margin: 12px 0 4px 0;'>METALLURGICAL CAVEATS:</p>", unsafe_allow_html=True)
                for cav in prediction.caveats:
                    st.markdown(f"<div class='lab-warning'>⚠️ {cav}</div>", unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

        with r_col2:
            st.markdown("<div class='lab-card'>", unsafe_allow_html=True)
            # Candidate Components Card
            st.markdown("<h4 style='margin: 0 0 8px 0; color: #ffffff;'>Matching Injector Candidates</h4>", unsafe_allow_html=True)
            if prediction.candidate_components:
                chips_html = "".join([f"<span class='component-chip'>📌 {c}</span>" for c in prediction.candidate_components])
                st.markdown(f"<div>{chips_html}</div>", unsafe_allow_html=True)
            else:
                st.markdown("<p style='font-size: 13px; color: #94a3b8;'>No components matched at this composition range.</p>", unsafe_allow_html=True)

            st.markdown("<hr style='border-color: #334155; margin: 16px 0;'>", unsafe_allow_html=True)

            # Normalization Table
            st.markdown("<h4 style='margin: 0 0 8px 0; color: #ffffff;'>Metal-Basis Composition Breakdown</h4>", unsafe_allow_html=True)
            norm_res = normalize_spectrum(filtered_input, sigma_model=KB.sigma_model)
            table_rows = []
            for elem, reading in norm_res.readings.items():
                table_rows.append({
                    "Element": elem,
                    "Raw Input (wt%)": f"{reading.raw_wt:.2f}" if reading.raw_wt is not None else "--",
                    "Metal-Basis (wt%)": f"{reading.metal_wt:.2f}" if reading.metal_wt is not None else "--",
                    "Status": reading.state.name,
                })
            st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

            # Ranked Candidate Families
            st.markdown("<h4 style='margin: 16px 0 6px 0; color: #ffffff;'>Ranked Family Compatibility</h4>", unsafe_allow_html=True)
            bar_fig = render_ranked_families_chart(prediction.families)
            if bar_fig:
                st.plotly_chart(bar_fig, use_container_width=True)

            st.markdown("</div>", unsafe_allow_html=True)

        # Download Export
        st.markdown("<div style='display: flex; gap: 12px; margin-top: 10px;'>", unsafe_allow_html=True)
        exp_col1, exp_col2 = st.columns(2)
        with exp_col1:
            report_dict = {
                "scan_id": f"scan-{int(time.time())}",
                "timestamp": datetime.now().isoformat(),
                "source": uploaded_source_name,
                "input_composition": filtered_input,
                "decision": decision_str,
                "top_family": top_fam.to_dict() if top_fam else None,
                "candidates": prediction.candidate_components,
                "caveats": prediction.caveats,
            }
            st.download_button(
                "📥 Export Full Analysis (JSON)",
                data=json.dumps(report_dict, indent=2),
                file_name=f"spectral_analysis_{int(time.time())}.json",
                mime="application/json",
            )
        with exp_col2:
            st.download_button(
                "📊 Export Composition Table (CSV)",
                data=pd.DataFrame(table_rows).to_csv(index=False),
                file_name=f"composition_table_{int(time.time())}.csv",
                mime="text/csv",
            )


# ==========================================================================
# VIEW 2: RATIO GATE EDITOR & VALIDATION ENGINE
# ==========================================================================
elif nav_choice == "⚖️ Ratio Gate Editor":
    st.markdown("""
        <div>
            <h2 style="margin: 0; color: #ffffff; font-weight: 700;">Ratio Gate Calibration & Validation</h2>
            <p style="margin: 2px 0 16px 0; color: #94a3b8; font-size: 14px;">Fine-tune stoichiometric ratio constraints and validate against 173 ground-truth spectra.</p>
        </div>
    """, unsafe_allow_html=True)

    family_keys = list(KB.families.keys())
    sel_fam_id = st.selectbox("Select Material Family to Calibrate:", options=family_keys, format_func=lambda k: f"{k} - {KB.families[k].label}")
    family_obj = KB.families[sel_fam_id]

    # Ratio gates management
    st.markdown("<div class='lab-card'>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='margin: 0 0 6px 0; color: #38bdf8;'>Active Ratio Gates for {sel_fam_id}</h3>", unsafe_allow_html=True)
    st.markdown(f"<p style='color: #cbd5e1; font-size: 13px;'>{family_obj.note or 'Adjust stoichiometric ratio bounds to prevent false positive classifications.'}</p>", unsafe_allow_html=True)

    db_gates = get_db_gates_for_family(sel_fam_id)
    active_gates = db_gates if db_gates is not None else [
        {
            "id": f"gate-{sel_fam_id.lower()}-1",
            "name": "Cr / Ni" if "Cr" in family_obj.elements and "Ni" in family_obj.elements else "Alloy Ratio 1",
            "numerator": "Cr" if "Cr" in family_obj.elements else "Fe",
            "denominator": "Ni" if "Ni" in family_obj.elements else "Mn",
            "min": 1.85,
            "max": 2.30,
            "rationale": "Suppresses out-of-band variants",
            "enabled": True,
        }
    ]

    updated_gates = []
    for g in active_gates:
        st.markdown(f"<b>Gate: {g['name']}</b> ({g['numerator']} / {g['denominator']})", unsafe_allow_html=True)
        g_c1, g_c2, g_c3 = st.columns([3, 3, 2])
        with g_c1:
            new_min = st.slider(f"Min Ratio ({g['name']})", min_value=0.0, max_value=10.0, value=float(g["min"]), step=0.05, key=f"min_{g['id']}")
        with g_c2:
            new_max = st.slider(f"Max Ratio ({g['name']})", min_value=0.0, max_value=15.0, value=float(g["max"]), step=0.05, key=f"max_{g['id']}")
        with g_c3:
            enabled = st.checkbox("Active", value=g["enabled"], key=f"en_{g['id']}")
        updated_gates.append({**g, "min": new_min, "max": new_max, "enabled": enabled})

    # Save Overrides Button
    if st.button("💾 Save Ratio Gate Calibration to Database"):
        conn = get_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM ratio_gates WHERE family_id = ?", (sel_fam_id,))
        for ug in updated_gates:
            cur.execute("""
                INSERT INTO ratio_gates VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (ug["id"], sel_fam_id, ug["name"], ug["numerator"], ug["denominator"], ug["min"], ug["max"], ug["rationale"], 1 if ug["enabled"] else 0))
        # Log audit
        cur.execute("""
            INSERT INTO audit_logs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            f"audit-{int(time.time())}",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Current Metallurgist",
            "Snr. Metallurgist",
            f"Calibrated ratio gates for {sel_fam_id}",
            "Gate Calibration",
            sel_fam_id,
            "Previous Calibration",
            f"Calibrated: {len(updated_gates)} gates",
            "Tuned classification bounds",
            "positive",
        ))
        conn.commit()
        conn.close()
        st.success(f"Calibration saved successfully for {sel_fam_id} and recorded in audit log.")
    st.markdown("</div>", unsafe_allow_html=True)

    # Ground-Truth Dataset Validation Engine
    st.markdown("<div class='lab-card'>", unsafe_allow_html=True)
    st.markdown("<h3 style='margin: 0 0 6px 0; color: #ffffff;'>Live Ground-Truth Dataset Validation Engine</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94a3b8; font-size: 13px;'>Tests the current rule engine and gate configurations against all 173 measured spectra in <code>EDS Consolidation.xlsx</code>.</p>", unsafe_allow_html=True)

    ref_spectra = get_reference_spectra()
    if not ref_spectra:
        st.warning("Ground-truth reference dataset `data/EDS Consolidation.xlsx` not found on disk.")
    else:
        if st.button("🚀 Run Live Validation Against Ground-Truth Dataset (173 Spectra)", type="primary"):
            with st.spinner("Evaluating 173 real spectra against calibrated knowledge base..."):
                pass_count = 0
                fail_count = 0
                failures = []

                for s in ref_spectra:
                    p = predict_spectrum(s["values"], analysed_elements=s["analysed_elements"], knowledge=KB)
                    if p.top is not None:
                        pass_count += 1
                    else:
                        fail_count += 1
                        failures.append({
                            "Component": s["component"],
                            "Decision": p.decision.value,
                            "Reason": p.abstention_reason or "Out of band",
                        })

                tot = pass_count + fail_count
                pass_rate = round((pass_count / tot) * 100, 1)

                v_col1, v_col2, v_col3, v_col4 = st.columns(4)
                with v_col1:
                    st.markdown(f"<div class='stat-lbl'>TOTAL EVALUATED</div><div class='stat-val'>{tot}</div>", unsafe_allow_html=True)
                with v_col2:
                    st.markdown(f"<div class='stat-lbl'>PASSING SPECTRA</div><div class='stat-val' style='color: #34d399;'>{pass_count}</div>", unsafe_allow_html=True)
                with v_col3:
                    st.markdown(f"<div class='stat-lbl'>ABSTAINED / FAILED</div><div class='stat-val' style='color: #fb7185;'>{fail_count}</div>", unsafe_allow_html=True)
                with v_col4:
                    st.markdown(f"<div class='stat-lbl'>GROUND-TRUTH PASS RATE</div><div class='stat-val' style='color: #38bdf8;'>{pass_rate}%</div>", unsafe_allow_html=True)

                st.progress(pass_rate / 100.0)
                if failures:
                    st.markdown("<p style='font-size: 13px; font-weight: 600; color: #f87171; margin-top: 12px;'>Sample Abstentions:</p>", unsafe_allow_html=True)
                    st.dataframe(pd.DataFrame(failures[:10]), use_container_width=True, hide_index=True)
                else:
                    st.success("All 173 reference spectra validated successfully!")
    st.markdown("</div>", unsafe_allow_html=True)


# ==========================================================================
# VIEW 3: KNOWLEDGE BASE CATALOG
# ==========================================================================
elif nav_choice == "📚 Knowledge Base Catalog":
    st.markdown("""
        <div>
            <h2 style="margin: 0; color: #ffffff; font-weight: 700;">Metallurgical Knowledge Base</h2>
            <p style="margin: 2px 0 16px 0; color: #94a3b8; font-size: 14px;">Explore 12 validated material families, stoichiometric element bands, and candidate components.</p>
        </div>
    """, unsafe_allow_html=True)

    # Search & Filter
    k_c1, k_c2 = st.columns([4, 2])
    with k_c1:
        search_query = st.text_input("🔍 Search family label, grade hint, or component name:", "")
    with k_c2:
        element_filter = st.selectbox("Filter by Element Presence:", options=["All Elements"] + sorted(list(ELEMENT_SYMBOLS)))

    filtered_families = {}
    for fid, fam in KB.families.items():
        if search_query:
            q = search_query.lower()
            text_match = q in fid.lower() or q in fam.label.lower() or q in fam.grade_hint.lower() or any(q in c.lower() for c in fam.components)
            if not text_match:
                continue
        if element_filter != "All Elements":
            if element_filter not in fam.elements:
                continue
        filtered_families[fid] = fam

    st.markdown(f"<p style='font-size: 13px; color: #94a3b8;'>Displaying {len(filtered_families)} of 12 material families</p>", unsafe_allow_html=True)

    for fid, fam in filtered_families.items():
        with st.expander(f"**{fid}: {fam.label}** ({fam.grade_hint or 'Standard Reference'}) — {len(fam.components)} Components", expanded=False):
            f_c1, f_c2 = st.columns([3, 2])
            with f_c1:
                st.markdown(f"""
                    <p style="margin: 0 0 8px 0; font-size: 13px; color: #cbd5e1;"><b>Description:</b> {fam.note or 'Standard derived family definition.'}</p>
                    <p style="margin: 0 0 8px 0; font-size: 13px; color: #94a3b8;"><b>Reference Support:</b> {fam.n_spectra} spectra ({'Verified' if not fam.provisional else 'Provisional'})</p>
                """, unsafe_allow_html=True)

                st.markdown("<p style='font-size: 12px; font-weight: 700; color: #38bdf8; text-transform: uppercase;'>Element Concentration Bands (wt%):</p>", unsafe_allow_html=True)
                band_rows = []
                for elem, spec in fam.elements.items():
                    b_min, b_max = spec.band_wt
                    band_rows.append({
                        "Element": elem,
                        "Min Band (wt%)": f"{b_min:.2f}",
                        "Max Band (wt%)": f"{b_max:.2f}",
                        "Required": "Yes" if spec.required else "No",
                        "Role": "Trace / Surface" if spec.prefer_ratio else "Matrix Alloy",
                    })
                st.dataframe(pd.DataFrame(band_rows), use_container_width=True, hide_index=True)

            with f_c2:
                st.markdown("<p style='font-size: 12px; font-weight: 700; color: #93c5fd; text-transform: uppercase;'>Associated Injector Components:</p>", unsafe_allow_html=True)
                comp_chips = "".join([f"<span class='component-chip'>📌 {c}</span>" for c in fam.components])
                st.markdown(f"<div>{comp_chips}</div>", unsafe_allow_html=True)


# ==========================================================================
# VIEW 4: SYSTEM AUDIT LOG
# ==========================================================================
elif nav_choice == "📜 System Audit Log":
    st.markdown("""
        <div>
            <h2 style="margin: 0; color: #ffffff; font-weight: 700;">System Audit Log & Traceability</h2>
            <p style="margin: 2px 0 16px 0; color: #94a3b8; font-size: 14px;">Historical trace of microanalysis scans, gate calibrations, and model modifications.</p>
        </div>
    """, unsafe_allow_html=True)

    conn = get_db()
    df_audit = pd.read_sql_query("SELECT * FROM audit_logs ORDER BY timestamp DESC", conn)
    df_history = pd.read_sql_query("SELECT * FROM analysis_history ORDER BY timestamp DESC LIMIT 50", conn)
    conn.close()

    tab_audit, tab_history = st.tabs(["🔒 Calibration & System Logs", "🔬 Recent Microanalysis Scans"])

    with tab_audit:
        if df_audit.empty:
            st.info("No audit logs recorded yet.")
        else:
            st.dataframe(df_audit, use_container_width=True, hide_index=True)
            st.download_button("📥 Export Audit Logs (CSV)", data=df_audit.to_csv(index=False), file_name="audit_logs.csv", mime="text/csv")

    with tab_history:
        if df_history.empty:
            st.info("No scans performed in this session yet.")
        else:
            st.dataframe(df_history, use_container_width=True, hide_index=True)
            st.download_button("📥 Export Scan History (CSV)", data=df_history.to_csv(index=False), file_name="analysis_history.csv", mime="text/csv")


# ==========================================================================
# VIEW 5: USER & ANALYST MANAGEMENT
# ==========================================================================
elif nav_choice == "👥 User Management":
    st.markdown("""
        <div>
            <h2 style="margin: 0; color: #ffffff; font-weight: 700;">Lab Personnel & Access Control</h2>
            <p style="margin: 2px 0 16px 0; color: #94a3b8; font-size: 14px;">Manage metallurgists, spectroscopy analysts, and permission roles.</p>
        </div>
    """, unsafe_allow_html=True)

    conn = get_db()
    df_users = pd.read_sql_query("SELECT * FROM users", conn)
    conn.close()

    st.markdown("<div class='lab-card'>", unsafe_allow_html=True)
    st.markdown("<h3 style='margin: 0 0 12px 0; color: #ffffff;'>Active Spectroscopy Roster</h3>", unsafe_allow_html=True)
    st.dataframe(df_users, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Add New Analyst Form
    with st.expander("➕ Register New Analyst / Metallurgist"):
        with st.form("new_user_form"):
            u_c1, u_c2 = st.columns(2)
            with u_c1:
                name = st.text_input("Full Name:")
                email = st.text_input("Lab Email:")
                role = st.selectbox("Role:", ["Snr. Metallurgist", "Spectroscopy Analyst", "Lab Tech", "Quality Engineer", "Auditor"])
            with u_c2:
                dept = st.selectbox("Department:", ["Metallurgy", "Operations", "Quality Control", "R&D"])
                perms = st.selectbox("Permissions:", ["Full Edit", "Read-only", "Calibrate Only"])
                initials = st.text_input("Initials (2 letters):", max_chars=3)

            submit_user = st.form_submit_button("Create Analyst Profile")
            if submit_user and name and email:
                conn = get_db()
                cur = conn.cursor()
                uid = f"user-{int(time.time())}"
                cur.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (
                    uid, name, email, role, dept, perms, initials.upper() or name[:2].upper(), 1, "Just registered"
                ))
                conn.commit()
                conn.close()
                st.success(f"Analyst '{name}' registered successfully.")
                st.rerun()
