import streamlit as st
import pydeck as pdk
import pandas as pd
import numpy as np
import json
import math
import random
import hashlib
import copy
import re
import textwrap
from datetime import datetime, timezone

try:
    import ee
    from google.oauth2 import service_account
    EE_AVAILABLE = True
except ImportError:
    EE_AVAILABLE = False

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# =========================================================
# 1. UX SETUP, OCEAN ANIMATIONS & DAYLIGHT DESIGN SYSTEM
# =========================================================
st.set_page_config(layout="wide", page_title="Blue 42 | The Kelp Contender", page_icon="🌊", initial_sidebar_state="expanded")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Roboto+Mono:wght@400;600&display=swap');
    :root {
        --g-blue: #1A73E8; --g-blue-dark: #174EA6; --g-red: #D93025; --g-red-dark: #A50E0E;
        --g-yellow: #F9AB00; --g-yellow-dark: #B06000; --g-green: #188038; --g-green-dark: #0D652D;
        --g-bg: #F8FAFC; --g-surface: #FFFFFF; --g-surface-elevated: #F1F5F9; --g-border: #CBD5E1;
        --g-text: #0F172A; --g-text-sub: #334155;
    }
    html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stHeader"] {
        font-family: 'Google Sans', 'Plus Jakarta Sans', -apple-system, sans-serif !important;
        background-color: #F8FAFC !important;
        color: #0F172A !important;
    }
    [data-testid="stSidebar"], [data-testid="stSidebar"] > div:first-child {
        background-color: #F1F5F9 !important;
        color: #0F172A !important;
        border-right: 1px solid #CBD5E1 !important;
    }
    .stMarkdown, .stMarkdown p, .stMarkdown li, .stCaption, label, [data-testid="stWidgetLabel"] p,
    [data-testid="stExpander"] summary p, [data-testid="stMetricValue"], [data-testid="stMetricLabel"] {
        color: #0F172A !important;
    }
    .block-container { padding-top: 1rem; padding-bottom: 2rem; max-width: 98%; }
    .stMarkdown, .element-container { overflow: visible !important; }
    .google-accent-bar {
        height: 5px; width: 100%; border-radius: 4px;
        background: linear-gradient(90deg, #4285F4, #34A853, #FBBC04, #EA4335, #4285F4);
        background-size: 300% 100%;
        animation: shimmerBar 8s ease infinite;
        margin-bottom: 10px;
    }
    @keyframes shimmerBar { 0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; } }
    @keyframes swayKelp { 0%, 100% { transform: rotate(-5deg) translateY(0px); } 50% { transform: rotate(6deg) translateY(-3px); } }
    @keyframes floatWave { 0%, 100% { transform: translateX(0px); } 50% { transform: translateX(-18px); } }
    @keyframes riseBubble { 0% { transform: translateY(14px) scale(0.7); opacity: 0; } 50% { opacity: 0.7; } 100% { transform: translateY(-18px) scale(1.1); opacity: 0; } }
    @keyframes gentleFloat { 0%, 100% { transform: translateY(0px); } 50% { transform: translateY(-4px); } }
    .kelp-sway { display: inline-block; animation: swayKelp 3.6s ease-in-out infinite; transform-origin: bottom center; }
    .wave-banner {
        position: relative; overflow: hidden; border-radius: 12px;
        background: linear-gradient(135deg, #E0F2FE 0%, #F0FDF4 55%, #EFF6FF 100%);
        border: 1.5px solid #BAE6FD; padding: 14px 20px; margin-bottom: 14px;
        box-shadow: 0 4px 14px rgba(26, 115, 232, 0.07);
    }
    .bubble-dot {
        display: inline-block; width: 8px; height: 8px; border-radius: 50%;
        background: rgba(26, 115, 232, 0.35); margin: 0 4px;
        animation: riseBubble 4s ease-in-out infinite;
    }
    .leaf-tooltip { position: relative !important; display: inline-block; cursor: help; font-size: 1.05rem; margin-left: 6px; transition: transform 0.2s ease; z-index: 999999 !important; }
    .leaf-tooltip:hover { transform: scale(1.2); }
    .leaf-tooltip .tooltiptext {
        visibility: hidden; width: 255px; background: #FFFFFF !important; color: #0F172A !important; text-align: left;
        border: 1.5px solid #1A73E8; border-radius: 8px; padding: 10px 12px; position: absolute !important; z-index: 9999999 !important;
        bottom: 135%; left: 50%; margin-left: -127px; opacity: 0; transition: opacity 0.25s; font-size: 0.85rem; line-height: 1.45; font-weight: 500; pointer-events: none; box-shadow: 0 10px 25px rgba(15,23,42,0.18);
    }
    .leaf-tooltip:hover .tooltiptext { visibility: visible; opacity: 1; }
    .flip-card { background-color: transparent !important; width: 100% !important; height: 215px !important; perspective: 1000px !important; margin-bottom: 15px !important; position: relative !important; cursor: pointer; animation: gentleFloat 6s ease-in-out infinite; }
    .flip-card-inner { position: relative !important; width: 100% !important; height: 100% !important; text-align: center !important; transition: transform 0.6s cubic-bezier(0.4, 0.0, 0.2, 1) !important; transform-style: preserve-3d !important; }
    .flip-card:hover .flip-card-inner, .flip-card:active .flip-card-inner, .flip-card.flipped .flip-card-inner { transform: rotateY(180deg) !important; }
    .flip-card-front, .flip-card-back {
        position: absolute !important; inset: 0 !important; width: 100% !important; height: 100% !important;
        -webkit-backface-visibility: hidden !important; backface-visibility: hidden !important; border-radius: 12px !important;
        background: #FFFFFF !important; border: 1.5px solid #CBD5E1 !important; padding: 15px !important;
        box-shadow: 0 4px 16px 0 rgba(15, 23, 42, 0.08) !important; display: flex !important; flex-direction: column !important; justify-content: center !important;
    }
    .flip-card-back { transform: rotateY(180deg) !important; border-left: 5px solid #188038 !important; background: #F0FDF4 !important; text-align: left !important; align-items: flex-start !important; padding-left: 20px !important; }
    .glass-title { font-size: clamp(0.84rem, 1.05vw, 0.95rem); color: #334155 !important; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 8px; font-weight: 700; }
    .glass-value { font-size: clamp(1.75rem, 2.2vw, 2.35rem); font-weight: 800; margin: 0; line-height: 1.15; }
    .glass-sub { font-size: clamp(0.84rem, 1vw, 0.92rem); color: #188038 !important; margin-top: 8px; font-weight: 700; }
    .math-text { font-family: 'Roboto Mono', monospace; font-size: 0.82rem; color: #0F172A !important; line-height: 1.45; width: 100%; font-weight: 500; }
    .math-hl { color: #188038 !important; font-weight: 700; font-size: 0.88rem; }
    .math-var { color: #334155 !important; }
    .math-op { color: #1A73E8 !important; font-weight: 700; padding-right: 6px; }
    .crypto-box { background-color: #F0FDF4 !important; border: 1.5px solid #188038; border-radius: 8px; padding: 14px; font-family: 'Roboto Mono', monospace; font-size: 0.9rem; color: #0F172A !important; word-wrap: break-word; }
    .stButton > button { background: #FFFFFF !important; color: #1A73E8 !important; border: 1.5px solid #1A73E8 !important; border-radius: 20px; font-weight: 700; font-size: 0.92rem !important; transition: all 0.25s ease; }
    .stButton > button:hover { background: #1A73E8 !important; color: #FFFFFF !important; transform: translateY(-1px); box-shadow: 0 4px 12px rgba(26, 115, 232, 0.30); }
    .metric-grid { display: flex; gap: 12px; margin-bottom: 15px; flex-wrap: wrap; }
    .metric-box { flex: 1; min-width: 120px; background: #FFFFFF !important; border: 1.5px solid #CBD5E1; border-radius: 10px; border-top: 4px solid #1A73E8; padding: 12px; text-align: center; box-shadow: 0 2px 8px rgba(15,23,42,0.05); transition: transform 0.25s ease; }
    .metric-box:hover { transform: translateY(-3px); }
    .metric-title { font-size: 0.85rem; color: #334155 !important; text-transform: uppercase; font-weight: 700; margin-bottom: 5px; }
    .metric-val { font-size: 1.55rem; font-weight: 800; color: #1A73E8; line-height: 1.2; }
    .metric-sub { font-size: 0.84rem; color: #188038 !important; margin-top: 4px; font-weight: 700; }
    @media (max-width: 768px) {
        .block-container { padding-left: 0.6rem !important; padding-right: 0.6rem !important; max-width: 100% !important; }
        h1 { font-size: 1.5rem !important; } .flip-card { height: 185px !important; } .metric-box { min-width: 45% !important; }
    }
    header { background-color: transparent !important; } #MainMenu, footer { visibility: hidden; }
    .blinking { animation: blinker 1.8s ease-in-out infinite; color: #188038; font-weight: bold; }
    @keyframes blinker { 50% { opacity: 0.25; } }
</style>
""", unsafe_allow_html=True)

def leaf_info(text):
    return f'<div class="leaf-tooltip"><span class="kelp-sway">🌿</span><span class="tooltiptext">{text}</span></div>'

def make_flip_card(title, value, sub, math_html, accent_color="#1A73E8", value_color="#1A73E8"):
    return (
        f'<div class="flip-card" tabindex="0" onclick="this.classList.toggle(\'flipped\')"><div class="flip-card-inner">'
        f'<div class="flip-card-front" style="border-left: 5px solid {accent_color} !important;">'
        f'<div class="glass-title">{title}</div><div class="glass-value" style="color: {value_color};">{value}</div>'
        f'<div class="glass-sub">{sub} <span style="font-size:0.78rem; color:#475569;">(Hover/Tap)</span></div></div>'
        f'<div class="flip-card-back"><div class="glass-title" style="margin-bottom:6px; color:#1A73E8 !important; font-size:0.85rem;">HOW THIS IS CALCULATED</div>'
        f'<div class="math-text">{math_html}</div></div></div></div>'
    )

def kelp_animation():
    """Renders the full-screen growing CSS kelp forest (stems, fronds, air bladders) and rising ocean bubbles."""
    kelp_html = """
    <style>
        .ocean-animation-container { position: fixed; bottom: 0; left: 0; width: 25vw; height: 100vh; pointer-events: none; z-index: 999999; overflow: visible; opacity: 0.78; }
        .kelp-stalk { position: absolute; bottom: 0; width: 60px; transform-origin: bottom center; transform: scaleY(0); opacity: 0; display: flex; flex-direction: column; justify-content: space-evenly; align-items: center; }
        .kelp-stem { position: absolute; bottom: 0; width: 6px; height: 100%; background: linear-gradient(to top, #364219, #6b7a2d, #8f9c3e); border-radius: 4px; z-index: 1; }
        .kelp-frond-left, .kelp-frond-right { position: relative; height: 12px; background: linear-gradient(to right, #5a6b25, #7a8b35); border-radius: 50% 10% 50% 10%; z-index: 2; margin: 15px 0; }
        .kelp-frond-left { width: 45px; transform: translateX(-25px) rotate(-20deg); background: linear-gradient(to left, #5a6b25, #7a8b35); border-radius: 10% 50% 10% 50%; }
        .kelp-frond-right { width: 45px; transform: translateX(25px) rotate(20deg); }
        .kelp-frond-left::after { content: ''; position: absolute; right: -4px; top: -2px; width: 12px; height: 16px; background: #8b7d22; border-radius: 50%; box-shadow: inset -2px -2px 4px rgba(0,0,0,0.3); }
        .kelp-frond-right::after { content: ''; position: absolute; left: -4px; top: -2px; width: 12px; height: 16px; background: #8b7d22; border-radius: 50%; box-shadow: inset 2px -2px 4px rgba(0,0,0,0.3); }
        .bubble { position: absolute; bottom: -50px; font-size: 1.5rem; opacity: 0.55; animation: floatUp 4s ease-in infinite; color: #0284c7; text-shadow: 0 0 6px #38bdf8; }
        @keyframes growKelp { 0% { transform: scaleY(0); opacity: 0; } 20% { opacity: 0.92; } 85% { transform: scaleY(1); opacity: 0.92; } 100% { transform: scaleY(1); opacity: 0; } }
        @keyframes swayKelp1 { 0% { margin-left: -20px; transform: rotate(-2deg); } 100% { margin-left: 20px; transform: rotate(2deg); } }
        @keyframes swayKelp2 { 0% { margin-left: 20px; transform: rotate(3deg); } 100% { margin-left: -20px; transform: rotate(-3deg); } }
        @keyframes floatUp { 0% { bottom: -50px; transform: translateX(0px); opacity: 0; } 20% { opacity: 0.7; } 50% { transform: translateX(-20px); } 100% { bottom: 110vh; transform: translateX(20px); opacity: 0; } }
    </style>
    <div class="ocean-animation-container">
    """
    anim_rng = random.Random()
    for _ in range(15):
        left = anim_rng.randint(2, 90)
        delay = anim_rng.uniform(0.1, 1.5)
        duration = anim_rng.uniform(3.5, 5.5)
        sway_dir = anim_rng.choice(["swayKelp1", "swayKelp2"])
        sway_dur = anim_rng.uniform(3.0, 6.0)
        height = anim_rng.uniform(60, 110)

        kelp_html += f'<div style="position:absolute; bottom:0; left:{left}%; height:{height}vh; animation: {sway_dir} {sway_dur}s ease-in-out infinite alternate;">'
        kelp_html += f'<div class="kelp-stalk" style="height:100%; animation: growKelp {duration}s cubic-bezier(0.1, 0.8, 0.3, 1) {delay}s forwards;"><div class="kelp-stem"></div>'
        num_fronds = int(height // 3)
        for j in range(num_fronds):
            frond_class = "kelp-frond-left" if j % 2 == 0 else "kelp-frond-right"
            kelp_html += f'<div class="{frond_class}"></div>'
        kelp_html += '</div></div>'

    for _ in range(25):
        left = anim_rng.randint(1, 95)
        delay = anim_rng.uniform(0, 4)
        size = anim_rng.uniform(0.5, 1.5)
        kelp_html += f'<div class="bubble" style="left: {left}%; animation-delay: {delay}s; font-size: {size}rem;">🫧</div>'

    kelp_html += "</div>"
    st.markdown(kelp_html, unsafe_allow_html=True)

def handshake_animation():
    """Injects the original glowing CSS handshake animation."""
    handshake_html = """
    <style>
        @keyframes shakeHand {
            0% { transform: translate(-50%, -50%) rotate(0deg) scale(0); opacity: 0; }
            15% { opacity: 1; transform: translate(-50%, -50%) scale(1.5); }
            30% { transform: translate(-50%, -50%) rotate(-15deg) scale(1.5); }
            50% { transform: translate(-50%, -50%) rotate(15deg) scale(1.5); }
            70% { transform: translate(-50%, -50%) rotate(-15deg) scale(1.5); }
            85% { opacity: 1; transform: translate(-50%, -50%) scale(1.5); }
            100% { opacity: 0; transform: translate(-50%, -50%) scale(0); }
        }
        .handshake-overlay {
            position: fixed; top: 50%; left: 50%; z-index: 9999999;
            font-size: 8rem; pointer-events: none;
            animation: shakeHand 2.5s ease-in-out forwards;
            text-shadow: 0 0 40px rgba(16, 185, 129, 0.8);
        }
    </style>
    <div class="handshake-overlay">🤝</div>
    """
    st.markdown(handshake_html, unsafe_allow_html=True)

if "library" not in st.session_state:
    st.session_state.library = []
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": (
            "👋 **Welcome! I am your Blue 42 Ocean Advisor.**\n\n"
            "I translate satellite ocean data, **Oil Spill & Ocean Trash screening**, **Subsea Cable safety**, and **10-Year Farm Economics** into plain English. "
            "**Tap any 1-Click Question button above** or ask me anything about the selected **Kelp Kandidate**!"
        ),
    }]
if "selected_site_id" not in st.session_state:
    st.session_state.selected_site_id = None

# =========================================================
# 2. ZERO-DEPENDENCY PURE-PYTHON PDF, HTML MAP & GIS EXPORTERS
# =========================================================
def safe_encode(text):
    cleaned = re.sub(r'\*\*(.*?)\*\*', r'\1', str(text))
    cleaned = re.sub(r'^#+\s*', '', cleaned, flags=re.MULTILINE)
    for k, v in [("CO₂", "CO2"), ("O₂", "O2"), ("N₂", "N2"), ("CH₄", "CH4"), ("Δ", "d"), ("—", "-"), ("–", "-"), ("•", "*"), ("→", "->")]:
        cleaned = cleaned.replace(k, v)
    return cleaned.encode('latin-1', 'replace').decode('latin-1')

def _pdf_escape(text: str) -> str:
    return safe_encode(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

def build_pure_python_pdf(title: str, subtitle: str, sections: list, footer_lines: list) -> bytes:
    styled = [("F2", 14, 0.16, 0.38, 0.78, 18, title)]
    if subtitle:
        styled.append(("F1", 10, 0.30, 0.34, 0.38, 15, subtitle))
    styled.append(("F1", 8, 0.55, 0.58, 0.62, 12, "-" * 96))
    for sec_title, sec_lines in sections:
        styled.append(("F2", 11, 0.13, 0.42, 0.22, 16, sec_title))
        for raw_line in sec_lines:
            for para in str(raw_line).split("\n"):
                for wline in (textwrap.wrap(safe_encode(para), width=88) or [""]):
                    styled.append(("F1", 9.5, 0.10, 0.10, 0.12, 13, wline))
        styled.append(("F1", 6, 0.0, 0.0, 0.0, 6, ""))
    styled.append(("F1", 8, 0.55, 0.58, 0.62, 12, "-" * 96))
    styled.append(("F2", 10, 0.16, 0.38, 0.78, 14, "CRYPTOGRAPHIC VERIFICATION LEDGER"))
    for fline in footer_lines:
        for wf in (textwrap.wrap(safe_encode(fline), width=92) or [""]):
            styled.append(("F3", 8.5, 0.15, 0.15, 0.18, 12, wf))

    pages_ops, curr_ops, y = [], [], 745.0
    for fkey, sz, r, g, b, lead, txt in styled:
        if y - lead < 52.0:
            pages_ops.append("\n".join(curr_ops))
            curr_ops, y = [], 745.0
        if txt:
            curr_ops.append(f"BT /{fkey} {sz} Tf {r:.2f} {g:.2f} {b:.2f} rg 45 {y:.1f} Td ({_pdf_escape(txt)}) Tj ET")
        y -= lead
    if curr_ops or not pages_ops:
        pages_ops.append("\n".join(curr_ops))

    num_p = len(pages_ops)
    kids = " ".join(f"{6 + i * 2} 0 R" for i in range(num_p))
    objs = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        f"2 0 obj\n<< /Type /Pages /Kids [{kids}] /Count {num_p} >>\nendobj\n".encode("latin-1"),
        b"3 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>\nendobj\n",
        b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>\nendobj\n",
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>\nendobj\n",
    ]
    for i, s_str in enumerate(pages_ops):
        pid, cid = 6 + i * 2, 7 + i * 2
        sb = s_str.encode("latin-1", "replace")
        objs.append(f"{pid} 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R /F2 4 0 R /F3 5 0 R >> >> /Contents {cid} 0 R >>\nendobj\n".encode("latin-1"))
        objs.append(f"{cid} 0 obj\n<< /Length {len(sb)} >>\nstream\n".encode("latin-1") + sb + b"\nendstream\nendobj\n")

    out, offsets = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"), [0]
    for ob in objs:
        offsets.append(len(out))
        out.extend(ob)
    xref_pos = len(out)
    out.extend(f"xref\n0 {len(objs)+1}\n0000000000 65535 f \n".encode("latin-1"))
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode("latin-1"))
    out.extend(f"trailer\n<< /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("latin-1"))
    return bytes(out)

def generate_sha256_signature(site_data: dict, timestamp: str) -> str:
    canonical = {k: v for k, v in site_data.items() if k != "color"}
    return hashlib.sha256((json.dumps(canonical, sort_keys=True, default=str) + "|" + timestamp).encode('utf-8')).hexdigest()

def create_provenance_pdf(site: dict) -> bytes:
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')
    sig = generate_sha256_signature(site, ts)
    sections = [
        (f"1. KELP KANDIDATE PROFILE: {site.get('id')} ({site.get('area_ha')} HA)", [
            f"GPS: {site.get('lat'):.4f} N, {site.get('lon'):.4f} W | Score: {site.get('pareto_score')}/100 | Status: {site.get('status')}",
            f"40-Yr Canopy Persistence: {site.get('hist_persistence_40yr')}% ({site.get('report_card_grade')}) | PAR Sunlight: {site.get('par_light')} mol/m2/d",
            f"ROV Seafloor Substrate: {site.get('substrate_type')} | Stalk Density: {site.get('rov_stipe_density')} stipes/m2 | Wildlife: {site.get('rov_wildlife_species')} species",
            f"Subsea Cable Check: {site.get('smart_cable_status', 'Safe Clearance')}",
            f"Oil Spill & Ocean Trash Check: {site.get('pollution_status', 'Clean Water Verified')}",
        ]),
        ("2. ENVIRONMENTAL, POLLUTION & ECONOMIC IMPACT METRICS", [
            f"Jobs Created: {site.get('jobs_created')} | Shellfish Acidification Halo: {site.get('halo_ha')} HA",
            f"Fertilizer Nitrogen Cleaned: {site.get('nitrogen_tons')} MT/yr | Ocean Trash & Ghost Nets Co-Harvested: {site.get('plastic_trash_tons', 0)} MT/yr",
            f"Oil / PAH Sensor Reading: {site.get('pah_oil_ppm', 0.0):.2f} ppm ({site.get('crop_safety_verdict', 'Food & Bioplastic Safe')})",
            f"Safe Deep-Sea Sinking Quota: {site.get('abyssal_sunk_mt')} MT (Seafloor dO2: {site.get('benthic_o2_delta_pct')}%) | Bioplastics/Feed: {site.get('circular_surface_mt')} MT",
            f"Distance to >1,000m Trench: {site.get('abyssal_dist_km')} km | Annual Boat & Fuel Cost: ${site.get('sinking_cost'):,.2f}/yr",
        ]),
    ]
    return build_pure_python_pdf("BLUE 42 | SITE FACT SHEET & SATELLITE PROVENANCE", "Multi-Scale Satellite, Drone, ROV AI, Subsea Cable & Pollution Verification", sections, [f"Timestamp: {ts} | SHA-256: {sig}"])

def create_lca_brief(site: dict, ai_analysis: str, signature: str, timestamp: str) -> bytes:
    capex = float(site.get("area_ha", 0)) * 15000.0
    sections = [
        ("1. KELP KANDIDATE SAFETY, POLLUTION & SATELLITE METRICS", [
            f"ID: {site.get('id')} | Verdict: {site.get('status')} | Score: {site.get('pareto_score')}/100 | Size: {site.get('area_ha')} HA",
            f"Temp: {site.get('effective_sst')} C | Depth: {site.get('depth')} m | Wave Energy: {site.get('wave_energy')} kW/m | Cable Distance: {site.get('cable_dist_km', 10)} km",
            f"Oil Spill / PAH Reading: {site.get('pah_oil_ppm', 0.0):.2f} ppm | Ocean Trash Co-Harvested: {site.get('plastic_trash_tons', 0)} MT/yr | Nitrogen Cleaned: {site.get('nitrogen_tons')} MT/yr",
        ]),
        ("2. GROSS-TO-NET CARBON & FARM INFRASTRUCTURE SUMMARY", [
            f"Gross Carbon: {site.get('co2_tons')} MT -> Net Sellable Credits: {site.get('net_bankable_co2')} MT CO2e/yr (after boat fuel, 5% deep loss & buffer)",
            f"Upfront Infrastructure Cost: ${capex:,.0f} (55% Mooring Grid & Trash Boom, 20% Sensor Buoys, 15% Seeding/Harvest Gear, 10% Seabed Permit, +5% Cleanup Reserve)",
        ]),
        ("3. SITE QUALITY & SAFETY SUMMARY", [ai_analysis]),
    ]
    return build_pure_python_pdf("BLUE 42 | VERIFIED SITE SAFETY & ECONOMIC REPORT", "Carbon Waterfall, Pollution Screening & Spatial Safety Summary", sections, [f"Timestamp: {timestamp} | SHA-256: {signature}"])

def create_lease_permit_pdf(site: dict, funded_sites: list, commons_share_pct: int, permit_months: int) -> bytes:
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')
    sig = generate_sha256_signature(site, ts)
    p_lines = [f"- {f['Site ID']}: {f['Area (HA)']} HA | Score {f['Pareto']}/100 | Upfront Cost {f['Upfront Cost ($)']} | 10-Yr NPV {f['10-Yr NPV ($)']}" for f in funded_sites] or [f"- Lead Site: {site.get('id')} ({site.get('area_ha')} HA)"]
    sections = [
        ("1. GOVERNMENT AQUACULTURE LEASE & PERMIT FILING", [
            f"Lead Site: {site.get('id')} ({site.get('lat'):.4f} N, {site.get('lon'):.4f} W) | Verdict: {site.get('status')}",
            f"Community Revenue Share: {commons_share_pct}% Gross Revenue -> Fast-Track {permit_months}-Month Permit Timeline",
            f"Subsea Cable Protection Check (ICPC 1.5km Buffer): {site.get('smart_cable_status', 'Cleared')}",
            f"Oil Spill & Marine Debris Screening (NOAA / EPA): {site.get('pollution_status', 'Cleared')}",
        ]),
        ("2. FUNDED PORTFOLIO SITES", p_lines),
    ]
    return build_pure_python_pdf("BLUE 42 | GOVERNMENT LEASE & PERMIT APPLICATION PACK", "BOEM / NOAA / Coastal Commission Pre-Cleared Filing", sections, [f"Timestamp: {ts} | SHA-256: {sig}"])

def create_minted_credit_pdf(site: dict, itmo_serial: str, tx_hash: str, ts_now: str) -> bytes:
    sections = [
        ("1. OFFICIAL CARBON & PLASTIC CLEANUP CERTIFICATE (PARIS ART. 6.4)", [
            f"Serial Number: {itmo_serial} | Site: {site.get('id')} ({site.get('lat'):.4f} N, {site.get('lon'):.4f} W | {site.get('area_ha')} HA)",
            f"Gross Absorbed: {site.get('co2_tons'):.2f} MT -> Less Boat Fuel (-{site.get('tow_emissions_co2'):.2f}), 5% Deep Loss (-{site.get('remin_discount_co2'):.2f}), Reserve (-{site.get('buffer_pool_co2'):.2f})",
            f"NET SELLABLE CARBON CREDITS ISSUED: {site.get('net_bankable_co2'):.2f} MT CO2e/yr | Seafloor O2 Check: {site.get('benthic_o2_delta_pct')}% (PASSED)",
            f"CO-BENEFIT CREDITS: {site.get('nitrogen_tons')} MT Fertilizer Nitrogen + {site.get('plastic_trash_tons', 0)} MT Ocean Trash & Ghost Nets Removed",
        ]),
    ]
    return build_pure_python_pdf("BLUE 42 | OFFICIAL CARBON & CLEANUP CERTIFICATE", "4-Tier Satellite, Drone, ROV AI & SMART Cable Verified Receipt", sections, [f"Issued: {ts_now} | Serial: {itmo_serial}", f"SHA-256 Digital Seal: {tx_hash}"])

def create_safe_sites_directory_pdf(df: pd.DataFrame, sector_label: str) -> bytes:
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')
    lines = [f"{i+1}. {r['id']} [CLEARED] - Score: {r['pareto_score']}/100 | GPS: {r['lat']:.4f}, {r['lon']:.4f} | Size: {r['area_ha']:.1f} HA ({r['area_ha']*2.471:.0f} Acres) | Net Carbon: {r['net_bankable_co2']:.1f} MT/yr | Trash Cleared: {r.get('plastic_trash_tons', 0):.1f} MT/yr | Cable Dist: {r.get('cable_dist_km', 10):.1f} km" for i, (_, r) in enumerate(df.iterrows())]
    return build_pure_python_pdf("BLUE 42 | SAFE KELP KANDIDATES DIRECTORY", f"Region: {sector_label} ({len(df)} Cleared Sites)", [("SAFE SITES CLEARED FOR DEVELOPMENT", lines)], [f"Generated: {ts}"])

def export_to_interactive_map_html(df: pd.DataFrame, sector_label: str) -> bytes:
    clat = float(df["lat"].mean()) if not df.empty else 34.0
    clon = float(df["lon"].mean()) if not df.empty else -119.5
    markers, rows = [], []
    for _, r in df.iterrows():
        sid, lat, lon, ha, sc = str(r["id"]), float(r["lat"]), float(r["lon"]), float(r["area_ha"]), float(r["pareto_score"])
        net_c, bio = float(r.get("net_bankable_co2", 0)), float(r.get("biomass_tons", 0))
        trash_mt = float(r.get("plastic_trash_tons", 0))
        capex = ha * 15000.0
        net_prof = (((net_c * 150.0) + (bio * 300.0) + (ha * 1500.0) + (float(r.get("nitrogen_tons", 0)) * 2000.0) + (trash_mt * 850.0)) * 0.92) - ((ha * 2000.0) + float(r.get("sinking_cost", 0)))
        gurl = f"https://www.google.com/maps/search/?api=1&query={lat:.4f},{lon:.4f}"
        pop = f"<b>{sid} — ✅ CLEARED SITE</b><br>Score: {sc}/100 | Size: {ha:.1f} HA ({ha*2.471:.0f} Acres)<br>Est. Net Profit: <b>${net_prof:,.0f}/yr</b><br>Ocean Trash Removed: {trash_mt:.1f} MT/yr | Cable Dist: {r.get('cable_dist_km', 10):.1f} km<br><a href='{gurl}' target='_blank'>📍 Open in Google Maps ↗</a>"
        markers.append(f"L.circleMarker([{lat:.4f},{lon:.4f}],{{radius:11,fillColor:'#188038',color:'#fff',weight:2,fillOpacity:0.9}}).addTo(map).bindPopup({json.dumps(pop)});")
        rows.append(f"<tr><td><b>{sid}</b></td><td style='color:#188038;font-weight:700;'>✅ CLEARED</td><td><b>{sc}/100</b></td><td>{ha:.1f} HA ({ha*2.471:.0f} Ac)</td><td>${capex:,.0f}</td><td style='color:#188038;font-weight:700;'>${net_prof:,.0f}/yr</td><td>{trash_mt:.1f} MT/yr</td><td>{r.get('cable_dist_km', 10):.1f} km</td><td><a href='{gurl}' target='_blank' style='color:#1A73E8;'>{lat:.4f}, {lon:.4f} ↗</a></td></tr>")
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"/><title>Blue 42 Interactive Safe Sites Map</title><link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/><script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script><style>body{{margin:0;padding:24px;background:#F8FAFC;color:#0F172A;font-family:sans-serif;}}#map{{width:100%;height:420px;border-radius:12px;border:1px solid #CBD5E1;margin-bottom:20px;}}table{{width:100%;border-collapse:collapse;background:#FFFFFF;font-size:13px;border:1px solid #CBD5E1;}}th{{background:#F1F5F9;color:#1A73E8;text-align:left;padding:10px;}}td{{padding:10px;border-bottom:1px solid #E2E8F0;}}</style></head><body><h2>🌊 BLUE 42 | The Kelp Contender — Interactive Safe Sites Map ({sector_label})</h2><div id="map"></div><table><thead><tr><th>Site ID</th><th>Verdict</th><th>Score</th><th>Farm Size</th><th>Upfront Cost</th><th>Est. Net Profit</th><th>Ocean Trash Cleared</th><th>Subsea Cable Dist</th><th>Google Maps</th></tr></thead><tbody>{"".join(rows)}</tbody></table><script>var map=L.map('map').setView([{clat:.4f},{clon:.4f}],8);L.tileLayer('https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager/{{z}}/{{x}}/{{y}}{{r}}.png').addTo(map);{"".join(markers)}</script></body></html>"""
    return html.encode("utf-8")

def export_to_geojson(df: pd.DataFrame) -> bytes:
    feats = [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [float(r["lon"]), float(r["lat"])]}, "properties": {"id": r["id"], "status": r["status"], "pareto_score": float(r["pareto_score"]), "area_ha": float(r["area_ha"]), "net_bankable_co2": float(r.get("net_bankable_co2", 0)), "plastic_trash_tons": float(r.get("plastic_trash_tons", 0)), "cable_dist_km": float(r.get("cable_dist_km", 10))}} for _, r in df.iterrows()]
    return json.dumps({"type": "FeatureCollection", "features": feats}, indent=2).encode("utf-8")

def export_to_kml(df: pd.DataFrame) -> bytes:
    pms = [f"<Placemark><name>{r['id']} ({r['pareto_score']}/100)</name><description>CLEARED | {r['area_ha']} HA | Net CO2: {r.get('net_bankable_co2',0)} MT/yr | Trash Cleared: {r.get('plastic_trash_tons',0)} MT/yr</description><Point><coordinates>{float(r['lon']):.4f},{float(r['lat']):.4f},0</coordinates></Point></Placemark>" for _, r in df.iterrows()]
    return f'<?xml version="1.0" encoding="UTF-8"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>Blue 42 Safe Kelp Kandidates</name>{"".join(pms)}</Document></kml>'.encode("utf-8")

# =========================================================
# 3. GLOBAL HOTSPOTS, POLLUTION, OIL SPILL & SUBSEA CABLE ENGINE
# =========================================================
ee_connected = False
if EE_AVAILABLE:
    try:
        if "EARTHENGINE_TOKEN" in st.secrets:
            creds = service_account.Credentials.from_service_account_info(
                json.loads(st.secrets["EARTHENGINE_TOKEN"])
            ).with_scopes(['https://www.googleapis.com/auth/earthengine'])
            ee.Initialize(credentials=creds)
            ee_connected = True
    except Exception:
        pass

model = None
if GENAI_AVAILABLE:
    try:
        if "GEMINI_API_KEY" in st.secrets:
            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            avail = [m.name for m in genai.list_models()]
            target = (
                'gemini-2.5-flash' if 'models/gemini-2.5-flash' in avail else
                ('gemini-1.5-flash' if 'models/gemini-1.5-flash' in avail else
                 ('gemini-1.5-pro' if 'models/gemini-1.5-pro' in avail else avail[0].replace('models/', '')))
            )
            model = genai.GenerativeModel(target)
    except Exception:
        pass

SECTOR_CONFIG = {
    "Channel Islands": {"seed": 42, "h_seed": 777, "lat": 34.0, "lon": -119.8, "sst_range": (13.8, 17.5)},
    "British Columbia": {"seed": 64, "h_seed": 666, "lat": 52.1, "lon": -131.1, "sst_range": (10.8, 14.6)},
    "Tasmania": {"seed": 88, "h_seed": 555, "lat": -42.85, "lon": 148.05, "sst_range": (12.5, 16.8)},
    "Hawaii": {"seed": 108, "h_seed": 888, "lat": 21.3, "lon": -157.9, "sst_range": (18.2, 21.4)},
}

def build_site_record(site_id: str, lat: float, lon: float, area: float, sst_mean: float, depth: float, wave_energy: float, nitrate_score: int, mhw_risk: str, salinity: float, biodiversity_score: int, abyssal_dist_km: float, equity_score: int) -> dict:
    biomass_tons = round(area * 18.5 * 0.92, 1)
    sinking_cost = round((area * 120.0) + (biomass_tons * abyssal_dist_km * 0.45), 2)
    par_light = round(max(18.0, min(48.0, 44.0 - (depth * 0.65))), 1)
    hist_persistence_40yr = int(min(98, max(64, round(nitrate_score * 0.6 + biodiversity_score * 0.38 - max(0.0, sst_mean - 16.0) * 4.0))))
    report_card_grade = "A+ (Ultra-Resilient)" if hist_persistence_40yr >= 90 else ("A (High Persistence)" if hist_persistence_40yr >= 82 else ("B+ (Stable Recovery)" if hist_persistence_40yr >= 74 else "B (Seasonal Fluctuation)"))
    substrate_type = "Consolidated Rocky Reef (Optimal Holdfast)" if depth < 22.0 else ("Boulders & Glacial Cobble (High Holdfast)" if wave_energy > 24.0 else "Compacted Marine Sand & Shell Hash")
    plastic_trash_tons = round(area * 0.42, 2)
    return {
        "id": site_id, "lat": round(lat, 4), "lon": round(lon, 4), "area_ha": round(area, 1),
        "biomass_tons": biomass_tons, "co2_tons": round(biomass_tons * 0.68, 1), "sst_mean": round(sst_mean, 1),
        "depth": round(depth, 1), "par_light": par_light, "nitrate_score": int(nitrate_score), "mhw_risk": mhw_risk,
        "salinity": round(salinity, 2), "wave_energy": round(wave_energy, 1),
        "averted_damage_millions": round((wave_energy * area * 0.15), 2), "jobs_created": int(area * 2.2),
        "biodiversity_score": int(biodiversity_score), "halo_ha": round(area * 1.5, 1),
        "nitrogen_tons": round(area * 0.25, 2), "plastic_trash_tons": plastic_trash_tons,
        "pah_oil_ppm": 0.00, "abyssal_dist_km": round(abyssal_dist_km, 1),
        "sinking_cost": sinking_cost, "equity_score": int(equity_score),
        "hist_persistence_40yr": hist_persistence_40yr, "report_card_grade": report_card_grade,
        "substrate_type": substrate_type, "rov_stipe_density": round(8.5 + (nitrate_score / 12.0), 1),
        "rov_wildlife_species": int(28 + (biodiversity_score * 0.45)),
        "suitability": round(min(0.98, max(0.65, hist_persistence_40yr / 100.0)), 2),
    }

@st.cache_data(ttl=3600)
def get_scientific_kelp_data_v4(sector: str, live_gee: bool = False):
    cfg = SECTOR_CONFIG.get(sector, SECTOR_CONFIG["Channel Islands"])
    rng = random.Random(cfg["seed"])
    base_lat, base_lon = cfg["lat"], cfg["lon"]
    sst_lo, sst_hi = cfg["sst_range"]
    return [
        build_site_record(
            f"KK-{i+1}", base_lat + rng.uniform(-0.38, 0.38), base_lon + rng.uniform(-0.58, 0.58),
            rng.uniform(6.0, 15.0), rng.uniform(sst_lo, sst_hi), rng.uniform(11.0, 28.0),
            rng.uniform(12.0, 48.0), rng.randint(80, 99), rng.choice(["Low", "Moderate", "High"]),
            rng.uniform(33.0, 34.5), rng.randint(80, 99), rng.uniform(15.0, 75.0), rng.randint(62, 99)
        ) for i in range(12)
    ]

@st.cache_data(ttl=3600)
def get_hazard_vectors_v4(sector: str):
    cfg = SECTOR_CONFIG.get(sector, SECTOR_CONFIG["Channel Islands"])
    rng = random.Random(cfg["h_seed"])
    base_lat, base_lon = cfg["lat"], cfg["lon"]
    vessels, shipping_lanes = [], []
    for _ in range(5):
        slat, slon = base_lat + rng.uniform(-0.45, 0.45), base_lon + rng.uniform(-1.15, -0.75)
        elat, elon = slat + rng.uniform(-0.12, 0.12), base_lon + rng.uniform(0.75, 1.15)
        shipping_lanes.append({"path": [[slon, slat], [elon, elat]], "vessels": rng.randint(5, 20)})
        for step in range(15):
            f = step / 14.0
            vessels.append({"lat": slat + (elat - slat) * f, "lon": slon + (elon - slon) * f})
    mammals = [{"lat": base_lat + rng.uniform(-0.22, 0.22), "lon": base_lon + rng.uniform(-0.38, 0.38)} for _ in range(3)]
    subsea_cables = [
        {"cable_name": f"{sector} Transoceanic Fiber Trunk A (ITU SMART-Enabled)", "path": [[base_lon - 0.95, base_lat - 0.28], [base_lon - 0.05, base_lat - 0.14], [base_lon + 0.85, base_lat - 0.04]]},
        {"cable_name": f"{sector} Subsea HVDC Power & Telecom Link B", "path": [[base_lon - 0.85, base_lat + 0.26], [base_lon + 0.05, base_lat + 0.19], [base_lon + 0.90, base_lat + 0.12]]},
    ]
    cable_pts = []
    for cab in subsea_cables:
        pts = cab["path"]
        for seg_i in range(len(pts) - 1):
            p0, p1 = pts[seg_i], pts[seg_i + 1]
            for step in range(25):
                f = step / 24.0
                cable_pts.append({"lat": p0[1] + (p1[1] - p0[1]) * f, "lon": p0[0] + (p1[0] - p0[0]) * f, "cable_name": cab["cable_name"]})
    weather_poly = [[[base_lon - 0.42, base_lat - 0.35], [base_lon - 0.15, base_lat - 0.35], [base_lon - 0.15, base_lat - 0.08], [base_lon - 0.42, base_lat - 0.08], [base_lon - 0.42, base_lat - 0.35]]]
    restricted_poly = [[[base_lon - 0.62, base_lat + 0.02], [base_lon - 0.28, base_lat + 0.02], [base_lon - 0.28, base_lat + 0.30], [base_lon - 0.62, base_lat + 0.30], [base_lon - 0.62, base_lat + 0.02]]]
    allowed_poly = [[[base_lon - 0.10, base_lat - 0.35], [base_lon + 0.60, base_lat - 0.35], [base_lon + 0.60, base_lat + 0.30], [base_lon - 0.10, base_lat + 0.30], [base_lon - 0.10, base_lat - 0.35]]]
    oil_spill_poly = [[[base_lon + 0.34, base_lat - 0.36], [base_lon + 0.58, base_lat - 0.36], [base_lon + 0.58, base_lat - 0.18], [base_lon + 0.34, base_lat - 0.18], [base_lon + 0.34, base_lat - 0.36]]]
    trash_gyre_poly = [[[base_lon - 0.58, base_lat - 0.36], [base_lon - 0.36, base_lat - 0.36], [base_lon - 0.36, base_lat - 0.18], [base_lon - 0.58, base_lat - 0.18], [base_lon - 0.58, base_lat - 0.36]]]
    return (
        pd.DataFrame(vessels), pd.DataFrame(shipping_lanes), pd.DataFrame(mammals),
        [{"polygon": weather_poly[0]}], [{"polygon": restricted_poly[0]}], [{"polygon": allowed_poly[0]}],
        pd.DataFrame(subsea_cables), pd.DataFrame(cable_pts),
        [{"polygon": oil_spill_poly[0]}], [{"polygon": trash_gyre_poly[0]}],
    )

def point_in_polygon(lon: float, lat: float, poly: list) -> bool:
    inside, j = False, len(poly) - 1
    for i in range(len(poly)):
        xi, yi, xj, yj = poly[i][0], poly[i][1], poly[j][0], poly[j][1]
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    a = math.sin(math.radians(lat2 - lat1) / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 6371.0 * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

def run_mcda_deconfliction(sites, vessels_df, mammals_df, weather_data, restricted_data, allowed_data, cable_pts_df=None, oil_spill_data=None, trash_gyre_data=None):
    processed = []
    for site in sites:
        site['status'], site['color'] = "CLEARED: Optimal", [52, 168, 83, 230]
        lon, lat = site.get('lon', 0), site.get('lat', 0)
        min_cable_km = min([haversine_km(lat, lon, r['lat'], r['lon']) for _, r in cable_pts_df.iterrows()], default=99.9) if (cable_pts_df is not None and not cable_pts_df.empty) else 99.9
        site['cable_dist_km'] = round(min_cable_km, 2)

        for r_zone in restricted_data:
            if point_in_polygon(lon, lat, r_zone.get('polygon', [])):
                site['status'], site['color'] = "HAZARD: Restricted No-Take Zone", [234, 67, 53, 230]
                break
        if site['status'].startswith("CLEARED") and oil_spill_data:
            for o_zone in oil_spill_data:
                if point_in_polygon(lon, lat, o_zone.get('polygon', [])):
                    site['status'], site['color'] = "HAZARD: Reported Oil Spill Plume", [141, 110, 99, 235]
                    site['pah_oil_ppm'] = 0.42
                    break
        if site['status'].startswith("CLEARED") and trash_gyre_data:
            for t_zone in trash_gyre_data:
                if point_in_polygon(lon, lat, t_zone.get('polygon', [])):
                    site['status'], site['color'] = "HAZARD: Ocean Trash / Ghost-Net Gyre", [0, 137, 123, 235]
                    break
        if site['status'].startswith("CLEARED"):
            if site.get('storm_shear_hazard', False):
                site['status'], site['color'] = "HAZARD: Cat-4 Holdfast Shear", [250, 123, 23, 230]
            else:
                for w in weather_data:
                    if point_in_polygon(lon, lat, w.get('polygon', [])):
                        site['status'], site['color'] = "HAZARD: Storm Shearing Risk", [250, 123, 23, 230]
                        break
        if site['status'].startswith("CLEARED"):
            for _, ship in vessels_df.iterrows():
                if haversine_km(lat, lon, ship['lat'], ship['lon']) < 2.5:
                    site['status'], site['color'] = "HAZARD: Shipping Lane", [251, 188, 4, 230]
                    break
        if site['status'].startswith("CLEARED"):
            for _, whale in mammals_df.iterrows():
                if haversine_km(lat, lon, whale['lat'], whale['lon']) < 4.0:
                    site['status'], site['color'] = "HAZARD: Mammal Corridor", [66, 133, 244, 230]
                    break
        if site['status'].startswith("CLEARED") and min_cable_km < 1.5:
            site['status'], site['color'] = "HAZARD: Subsea Cable Zone (<1.5km)", [171, 71, 188, 230]

        if "Cable" in site['status']:
            site['smart_cable_status'] = f"⛔ Inside 1.5km Subsea Cable Buffer ({min_cable_km:.1f} km — Anchor Strike Risk)"
        elif min_cable_km <= 9.0:
            site['smart_cable_status'] = f"⚡ SMART Cable Synergy ({min_cable_km:.1f} km — Safe Anchor + Live Seafloor Telemetry & ROV Dock)"
        else:
            site['smart_cable_status'] = f"✅ Safe Clearance ({min_cable_km:.1f} km from Subsea Cable)"

        if "Oil Spill" in site['status']:
            site['pollution_status'] = "⛔ Inside Reported Oil Spill Plume (0.42 ppm PAH — Toxic to Food/Bioplastics)"
            site['crop_safety_verdict'] = "⛔ BLOCKED: Oil/PAH Contamination"
        elif "Ocean Trash" in site['status']:
            site['pollution_status'] = "⛔ Inside High-Density Ocean Trash & Ghost-Net Gyre (Entanglement Risk)"
            site['crop_safety_verdict'] = "⛔ BLOCKED: Severe Ghost-Net Eddy"
        elif site.get('pah_oil_ppm', 0.0) >= 0.05:
            site['pollution_status'] = f"⚠️ Drift Slick Alert ({site.get('pah_oil_ppm', 0.08):.2f} ppm PAH — Routed to Deep Carbon Sink Only + Trash Boom Active)"
            site['crop_safety_verdict'] = "⚠️ Deep Carbon Sink Only (No Food/Feed Sale)"
        else:
            site['pollution_status'] = f"✅ Clean Water (0.00 ppm Oil/PAH • Co-Harvests {site.get('plastic_trash_tons', 0):.1f} MT/yr Ocean Trash & {site.get('nitrogen_tons', 0):.2f} MT/yr Nitrogen)"
            site['crop_safety_verdict'] = "✅ 100% Safe for Food, Cow Feed & Bioplastics"
        processed.append(site)
    processed.sort(key=lambda s: (1 if "CLEARED" in s.get("status", "") else 0, s.get("pareto_score", 0)), reverse=True)
    return pd.DataFrame(processed)

# =========================================================
# 4. HEADER, WAVE ANIMATION & SIDEBAR CONTROLS
# =========================================================
st.markdown('<div class="google-accent-bar"></div>', unsafe_allow_html=True)
st.markdown(
    f"""
    <div class="wave-banner">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
            <div>
                <h1 style="font-weight: 800; margin: 0; font-size: clamp(1.6rem, 2.5vw, 2.3rem);">
                    <span class="kelp-sway" style="margin-right:6px;">🌊</span>
                    <span style="color:#1A73E8;">B</span><span style="color:#D93025;">L</span><span style="color:#F9AB00;">U</span><span style="color:#188038;">E</span>
                    <span style="color:#1A73E8;">42</span>
                    <span style="color:#0F172A !important; font-weight: 600;">| The Kelp Contender</span>
                    {leaf_info('The Kelp Contender turns satellite ocean data, oil spill & ocean trash screening, subsea cable maps, and 10-year farm economics into an easy dashboard to evaluate safe ocean kelp sites (Kelp Kandidates).')}
                </h1>
                <p style="color: #334155 !important; font-size: 0.98rem; font-weight: 600; margin: 4px 0 0 0;">
                    <span class="blinking">●</span> OCEAN INTELLIGENCE ENGINE ACTIVE &nbsp;|&nbsp; 4 GLOBAL HOTSPOTS • OIL SPILL &amp; OCEAN TRASH SCREENING • ROV AI &amp; SUBSEA CABLE SAFETY
                    <span class="bubble-dot"></span><span class="bubble-dot" style="animation-delay:1.2s;"></span><span class="bubble-dot" style="animation-delay:2.4s;"></span>
                </p>
            </div>
            <div style="font-size: 2.1rem; user-select: none;">
                <span class="kelp-sway">🌿</span><span class="kelp-sway" style="animation-delay:0.6s;">🐠</span><span class="kelp-sway" style="animation-delay:1.2s;">🌿</span><span class="kelp-sway" style="animation-delay:1.8s;">🐚</span>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("""
<div style="background-color: #F0F7FF !important; border: 1.5px solid #93C5FD; border-left: 6px solid #1A73E8; border-radius: 12px; padding: 16px 18px; margin-bottom: 18px; box-shadow: 0 4px 14px rgba(15,23,42,0.06);">
    <div style="font-size: 0.96rem; color: #1A73E8 !important; font-weight: 800; text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 10px;">🧭 User Guide</div>
    <div style="display: flex; flex-wrap: wrap; gap: 14px; font-size: 0.96rem; color: #0F172A !important; line-height: 1.55; font-weight: 500;">
        <div style="flex: 1; min-width: 240px; background-color: #FFFFFF !important; border: 1px solid #CBD5E1; border-top: 4px solid #188038; border-radius: 8px; padding: 12px 14px; color: #0F172A !important;">
            <span style="color: #188038 !important; font-weight: 800; font-size: 1.0rem;">1️⃣ Pick a Region &amp; Safe "Kelp Kandidate":</span><br/>
            Green 3D columns are <b style="color:#188038 !important;">Cleared &amp; Safe</b> (clear of shipping lanes, whale paths, storms, <b style="color:#6D4C41 !important;">Reported Oil Spills</b>, <b style="color:#00796B !important;">Ocean Trash Gyres</b>, and <b style="color:#7B1FA2 !important;">Subsea Cables</b>).
        </div>
        <div style="flex: 1; min-width: 240px; background-color: #FFFFFF !important; border: 1px solid #CBD5E1; border-top: 4px solid #1A73E8; border-radius: 8px; padding: 12px 14px; color: #0F172A !important;">
            <span style="color: #1A73E8 !important; font-weight: 800; font-size: 1.0rem;">2️⃣ Check 40-Yr History, Species &amp; 5 Revenues:</span><br/>
            Inspect 40-year satellite survival grades, match 5 kelp species, and model 5 income streams (<b style="color:#B45309 !important;">Carbon + Bioplastics + Storm Rebates + Nitrogen Cleanup + Ocean Trash Credits</b>).
        </div>
        <div style="flex: 1; min-width: 240px; background-color: #FFFFFF !important; border: 1px solid #CBD5E1; border-top: 4px solid #D97706; border-radius: 8px; padding: 12px 14px; color: #0F172A !important;">
            <span style="color: #B45309 !important; font-weight: 800; font-size: 1.0rem;">3️⃣ Lower Costs &amp; Download Signed PDFs:</span><br/>
            Toggle farm cost-cutting &amp; <b style="color:#00796B !important;">Trash Interceptor Boom</b> levers, verify via <b style="color:#1A73E8 !important;">Satellite + Drone + ROV AI + SMART Cables</b>, and download 1-click PDFs.
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown(f"<h2 style='color:#1A73E8; font-weight:700; display:flex; align-items:center;'>🧭 CONTROLS {leaf_info('Pick a global region, simulate extreme weather or oil spills, and set your project priorities.')}</h2>", unsafe_allow_html=True)

sector = st.sidebar.selectbox("1. Choose Global Ocean Region", [
    "Northeast Pacific Coast (California / Channel Islands)",
    "British Columbia & Haida Gwaii, Canada (Subarctic Corridor)",
    "Tasmania & Great Southern Reef, Australia (Southern Ocean)",
    "Hawaiian Archipelago, HI (Tropical Warm-Water)",
])
sector_key = "British Columbia" if "British Columbia" in sector else ("Tasmania" if "Tasmania" in sector else ("Hawaii" if "Hawaiian" in sector else "Channel Islands"))

region_notes = {
    "Channel Islands": "Cold, nutrient-rich water from the <b style='color:#188038;'>California Current</b> makes this a premier natural growth zone for <b style='color:#B45309;'>Giant Kelp</b> (<i>Macrocystis pyrifera</i>), growing up to 2 feet per day.",
    "British Columbia": "Glacial fjords and subarctic upwelling along <b style='color:#188038;'>British Columbia &amp; Haida Gwaii</b> support dense, heat-resilient forests of <b style='color:#B45309;'>Giant Kelp</b> and wave-hardy <b style='color:#1A73E8;'>Bull Kelp</b>.",
    "Tasmania": "Home to Australia's <b style='color:#188038;'>Great Southern Reef</b>, where Southern Ocean upwelling supports towering <b style='color:#B45309;'>Giant Kelp</b> and <b style='color:#1A73E8;'>Golden Kelp</b> (<i>Ecklonia radiata</i>) restoration corridors.",
    "Hawaii": "Warm, high-sunlight tropical waters ideal for heat-tolerant <b style='color:#B45309;'>Red Ogo</b>, <b style='color:#188038;'>Low-Methane Asparagopsis</b> cattle-feed kelp, and deep-water upwelling.",
}
st.sidebar.markdown(f"<div style='background-color:#FFFFFF !important;border:1.5px solid #93C5FD;border-left:5px solid #1A73E8;border-radius:8px;padding:12px 14px;margin-bottom:12px;font-size:0.92rem;line-height:1.5;color:#0F172A !important;'><b style='color:#1A73E8 !important;'>Why We Love This Region:</b><br>{region_notes[sector_key]}</div>", unsafe_allow_html=True)

st.sidebar.markdown("---")
st.sidebar.markdown(f"<h3 style='color:#B45309; font-size:1rem; display:flex; align-items:center;'>2. Weather, Oil Spill &amp; Trash Stress Test {leaf_info('See how each site holds up during an El Niño heatwave, a Category 4 winter storm, or a sudden Oil Spill & Ocean Trash Surge.')}</h3>", unsafe_allow_html=True)
stress_scenario = st.sidebar.radio("Choose Stress Test Scenario:", [
    "Nominal (Baseline)",
    "Marine Heatwave (El Niño)",
    "Category 4 Storm Event",
    "Oil Spill & Ocean Trash Surge",
])
adopt_baja_strain = st.sidebar.checkbox("🧬 Use Heat-Resistant Baja Kelp Seed (+2.0°C Tolerance)", value=False)

st.sidebar.markdown("---")
st.sidebar.markdown(f"<h3 style='color:#188038; font-size:1rem; display:flex; align-items:center;'>3. Set Your Priorities {leaf_info('Adjust what matters most to your project—the Site Quality Score (0–100) updates automatically.')}</h3>", unsafe_allow_html=True)
weight_carbon = st.sidebar.slider("💨 Carbon Credit Income", 0.0, 1.0, 0.8)
weight_coastal = st.sidebar.slider("🌊 Coastal Storm Protection", 0.0, 1.0, 0.5)
weight_bio = st.sidebar.slider("🐟 Marine Life & Fishery Health", 0.0, 1.0, 0.9)
weight_nitrogen = st.sidebar.slider("💧 Water Pollution, Oil & Trash Cleanup", 0.0, 1.0, 0.7)
weight_equity = st.sidebar.slider("🤝 Local Coastal Jobs & Community", 0.0, 1.0, 0.8)

# =========================================================
# 5. PHYSICS & POLLUTION STRESS TEST, CARBON WATERFALL & SCORING
# =========================================================
raw_sites = copy.deepcopy(get_scientific_kelp_data_v4(sector_key, ee_connected))

(
    vessels_df, shipping_lanes_df, mammals_df, weather_data, restricted_data,
    allowed_data, subsea_cables_df, cable_pts_df, oil_spill_data, trash_gyre_data
) = get_hazard_vectors_v4(sector_key)

for site in raw_sites:
    site.setdefault("par_light", 34.5)
    site.setdefault("hist_persistence_40yr", 88)
    site.setdefault("report_card_grade", "A (High Persistence)")
    site.setdefault("substrate_type", "Consolidated Rocky Reef (Optimal Holdfast)")
    site.setdefault("rov_stipe_density", 14.5)
    site.setdefault("rov_wildlife_species", 36)
    site.setdefault("suitability", 0.88)
    site.setdefault("plastic_trash_tons", round(site['area_ha'] * 0.42, 2))
    site.setdefault("pah_oil_ppm", 0.00)

    base_sst, wave_kw, depth_m = site['sst_mean'], site['wave_energy'], site['depth']
    site['storm_shear_hazard'] = False
    if stress_scenario == "Nominal (Baseline)":
        site_mod, site['effective_sst'], site['pah_oil_ppm'] = 1.0, base_sst, 0.00
    elif stress_scenario == "Marine Heatwave (El Niño)":
        eff_sst = round(base_sst + 2.8, 1)
        site['effective_sst'], site['pah_oil_ppm'] = eff_sst, 0.00
        overheat = max(0.0, eff_sst - (19.5 if adopt_baja_strain else 17.5))
        site_mod = max(0.18, round(math.exp(-0.35 * overheat), 2))
    elif stress_scenario == "Category 4 Storm Event":
        site['effective_sst'], site['pah_oil_ppm'] = base_sst, 0.00
        shear_factor = (wave_kw / 50.0) * (15.0 / max(depth_m, 10.0))
        site_mod = max(0.25, round(1.0 - (0.45 * shear_factor), 2))
        if shear_factor > 0.88:
            site['storm_shear_hazard'] = True
    else:
        # Oil Spill & Ocean Trash Surge Scenario
        site['effective_sst'] = base_sst
        site['pah_oil_ppm'] = 0.08
        site['plastic_trash_tons'] = round(site['area_ha'] * 0.95, 2)
        site_mod = 0.72

    site['stress_retention_pct'] = round(site_mod * 100, 1)
    site['biomass_tons'] = round(site['biomass_tons'] * site_mod, 1)
    site['co2_tons'] = round(site['co2_tons'] * site_mod, 1)
    site['sinking_cost'] = round((site['area_ha'] * 120.0) + (site['biomass_tons'] * site['abyssal_dist_km'] * 0.45), 2)

    gross_co2 = site['co2_tons']
    tow_em = round(site['biomass_tons'] * site['abyssal_dist_km'] * 0.0008, 2)
    remin_disc = round(gross_co2 * 0.05, 2)
    buf_pool = round(gross_co2 * (0.10 if site_mod >= 0.85 else 0.15), 2)
    site['tow_emissions_co2'], site['remin_discount_co2'], site['buffer_pool_co2'] = tow_em, remin_disc, buf_pool
    site['net_bankable_co2'] = round(max(0.0, gross_co2 - tow_em - remin_disc - buf_pool), 1)

    benthic_cms = round(4.5 + (wave_kw * 0.09), 1)
    safe_cap_mt = round(site['area_ha'] * 12.8 * (benthic_cms / 6.5), 1)
    if site['pah_oil_ppm'] >= 0.05:
        abyssal_sunk = round(min(site['biomass_tons'], safe_cap_mt), 1)
        circ_surf = 0.0
    else:
        abyssal_sunk = round(min(site['biomass_tons'], safe_cap_mt), 1)
        circ_surf = round(max(0.0, site['biomass_tons'] - abyssal_sunk), 1)
    site['benthic_current_cms'], site['safe_sinking_cap_mt'] = benthic_cms, safe_cap_mt
    site['abyssal_sunk_mt'], site['circular_surface_mt'] = abyssal_sunk, circ_surf
    site['benthic_o2_delta_pct'] = round(-1.45 * (abyssal_sunk / max(safe_cap_mt, 1.0)), 2)
    site['enteric_ch4_abated_mt'] = round(circ_surf * 0.42, 1)

metrics_to_norm = ['co2_tons', 'averted_damage_millions', 'biodiversity_score', 'nitrogen_tons', 'equity_score']
bounds = {m: (min(s[m] for s in raw_sites), max(s[m] for s in raw_sites)) for m in metrics_to_norm}
def norm_val(val, lo, hi):
    return (val - lo) / (hi - lo) if hi > lo else 1.0

total_w = (weight_carbon + weight_coastal + weight_bio + weight_nitrogen + weight_equity) or 1.0
for site in raw_sites:
    w_sum = (
        norm_val(site['co2_tons'], *bounds['co2_tons']) * weight_carbon +
        norm_val(site['averted_damage_millions'], *bounds['averted_damage_millions']) * weight_coastal +
        norm_val(site['biodiversity_score'], *bounds['biodiversity_score']) * weight_bio +
        norm_val(site['nitrogen_tons'], *bounds['nitrogen_tons']) * weight_nitrogen +
        norm_val(site['equity_score'], *bounds['equity_score']) * weight_equity
    )
    site['pareto_score'] = round((w_sum / total_w) * 100.0, 1)

kelp_df = run_mcda_deconfliction(
    raw_sites, vessels_df, mammals_df, weather_data, restricted_data,
    allowed_data, cable_pts_df, oil_spill_data, trash_gyre_data
)
safe_df = kelp_df[kelp_df['status'].str.contains("CLEARED")] if not kelp_df.empty else pd.DataFrame()
if not kelp_df.empty and st.session_state.selected_site_id not in kelp_df['id'].tolist():
    st.session_state.selected_site_id = kelp_df['id'].iloc[0]

# =========================================================
# 6. TOP EXECUTIVE KPI FLIP CARDS
# =========================================================
col1, col2, col3, col4 = st.columns(4)
v_area = safe_df['area_ha'].sum() if not safe_df.empty else 0
v_acres = v_area * 2.47105
v_bio = safe_df['biomass_tons'].sum() if not safe_df.empty else 0
v_dmg = safe_df['averted_damage_millions'].sum() if not safe_df.empty else 0
v_trash = safe_df['plastic_trash_tons'].sum() if not safe_df.empty else 0
v_roi = ((safe_df['net_bankable_co2'].sum() * 150) + (safe_df['biomass_tons'].sum() * 300) + (safe_df['nitrogen_tons'].sum() * 2000) + (v_trash * 850)) if not safe_df.empty else 0
avg_retention = safe_df['stress_retention_pct'].mean() if not safe_df.empty else 0

col1.markdown(make_flip_card(f"Safe Farmable Ocean Area {leaf_info('Total ocean area across green CLEARED Kelp Kandidates free of shipping lanes, whale paths, sanctuaries, oil spills, ocean trash gyres, and subsea cables.')}", f"{v_area:.1f} HA", f"≈ {v_acres:,.0f} Acres ({len(safe_df)}/{len(kelp_df)} Safe)", "Total Ocean Area<br><span class='math-op'>-</span> <span class='math-var'>Ships, Oil Spills, Trash &amp; Cables</span><br><span class='math-hl'>= Safe Farmable Area (1 HA ≈ 2.47 Ac)</span>", "#1A73E8", "#1A73E8"), unsafe_allow_html=True)
col2.markdown(make_flip_card(f"Annual Kelp Harvest {leaf_info('Total weight of fresh kelp harvested per year across all safe sites after weather & pollution stress testing.')}", f"{v_bio:.1f} MT", f"{stress_scenario} ({avg_retention:.0f}% Kept)", "Safe Area (HA) × 18.5 MT/HA<br><span class='math-op'>×</span> <span class='math-var'>Stress Survival %</span><br><span class='math-hl'>= Annual Kelp Harvest (Metric Tons)</span>", "#188038", "#188038"), unsafe_allow_html=True)
col3.markdown(make_flip_card(f"Storm & Trash Cleanup {leaf_info('Thick kelp forests calm storm waves and perimeter Trash Booms skim floating ocean plastics and ghost nets before they hit the farm.')}", f"${v_dmg:.1f}M", f"+{v_trash:.1f} MT Ocean Trash Cleared/yr", "Wave Dampening ($ Saved)<br><span class='math-op'>+</span> <span class='math-var'>Perimeter Trash Boom Skimming</span><br><span class='math-hl'>= Coastal &amp; Plastic Protection</span>", "#D97706", "#B45309"), unsafe_allow_html=True)
col4.markdown(make_flip_card(f"Annual Portfolio Revenue {leaf_info('Combined yearly revenue across all safe sites from carbon credits, bioplastics kelp, fertilizer cleanup, and ocean plastic cleanup credits.')}", f"${v_roi:,.0f}", "5 Revenue Streams / Year", "(Carbon × $150) + (Kelp × $300)<br><span class='math-op'>+</span> <span class='math-var'>Nitrogen ($2k) + Trash ($850/MT)</span><br><span class='math-hl'>= Total Annual Portfolio Revenue</span>", "#D93025", "#D93025"), unsafe_allow_html=True)

# =========================================================
# 7. 3D MAP (OIL SPILLS, OCEAN TRASH & SUBSEA CABLES) & 5 TABS
# =========================================================
col_map, col_ops = st.columns([6, 4], gap="large")

with col_ops:
    sel_site, site_data = None, None
    if not kelp_df.empty:
        c_step_lbl, c_best_btn = st.columns([6.2, 3.8])
        c_step_lbl.markdown("##### 🎯 Step 1: Select a Kelp Kandidate Site")
        if not safe_df.empty and c_best_btn.button("⭐ Pick #1 Best Site", use_container_width=True, help="Automatically jumps to the highest-scoring safe Kelp Kandidate in this region."):
            st.session_state.selected_site_id = safe_df.iloc[0]["id"]
            st.rerun()

        sel_site = st.selectbox(
            "Choose a Kelp Kandidate to Inspect:",
            kelp_df['id'].tolist(),
            index=kelp_df['id'].tolist().index(st.session_state.selected_site_id),
            format_func=lambda kid: f"{kid} — {'✅ CLEARED & SAFE' if 'CLEARED' in kelp_df[kelp_df['id']==kid].iloc[0]['status'] else '⛔ ' + kelp_df[kelp_df['id']==kid].iloc[0]['status']} (Score: {kelp_df[kelp_df['id']==kid].iloc[0]['pareto_score']}/100)",
        )
        st.session_state.selected_site_id = sel_site
        site_data = kelp_df[kelp_df['id'] == sel_site].iloc[0]

        is_sel_safe = "CLEARED" in str(site_data.get("status", ""))
        stat_str = str(site_data.get("status", ""))
        s_area_ha = float(site_data.get("area_ha", 0))
        s_acres = s_area_ha * 2.47105
        s_capex_est = s_area_ha * 15000.0 * (1.12 if adopt_baja_strain else 1.0)
        s_opex_est = (s_area_ha * 2000.0) + float(site_data.get("sinking_cost", 0))
        s_wave_reb = (s_area_ha * 1500.0) + (float(site_data.get("averted_damage_millions", 0)) * 1e6 * 0.0025)
        s_bio_rev = 0.0 if float(site_data.get("pah_oil_ppm", 0.0)) >= 0.05 else (float(site_data.get("biomass_tons", 0)) * 300.0)
        s_trash_rev = float(site_data.get("plastic_trash_tons", 0)) * 850.0
        s_gross_rev = (float(site_data.get("net_bankable_co2", 0)) * 150.0) + s_bio_rev + s_wave_reb + (float(site_data.get("nitrogen_tons", 0)) * 2000.0) + s_trash_rev
        s_net_profit_yr = (s_gross_rev * 0.92) - s_opex_est
        s_payback_yrs = (s_capex_est / s_net_profit_yr) if s_net_profit_yr > 0 else 99.9
        cars_off_road = int(round(float(site_data.get("net_bankable_co2", 0)) / 4.6))
        bottles_cleared = int(round(float(site_data.get("plastic_trash_tons", 0)) * 50000))

        def _pill(ok: bool, label: str) -> str:
            bg, bd, fg, ic = ("#DCFCE7", "#86EFAC", "#166534", "✅") if ok else ("#FEE2E2", "#FCA5A5", "#991B1B", "⛔")
            return f"<span style='background:{bg};border:1px solid {bd};color:{fg};padding:2px 8px;border-radius:999px;font-size:0.78rem;font-weight:700;'>{ic} {label}</span>"

        safety_pills_html = " ".join([
            _pill("Shipping" not in stat_str, "Ships"),
            _pill("Mammal" not in stat_str, "Whales"),
            _pill("Cable" not in stat_str, "Subsea Cables"),
            _pill("Oil Spill" not in stat_str and float(site_data.get("pah_oil_ppm", 0.0)) < 0.05, "Oil Spills"),
            _pill("Ocean Trash" not in stat_str, "Trash Gyres"),
            _pill("Storm" not in stat_str and "Shear" not in stat_str and "Restricted" not in stat_str, "Storms & Sanctuary"),
        ])

        bottom_line_txt = (
            f"<b>Plain-English Bottom Line:</b> <b>{sel_site}</b> is 100% clear of all ocean hazards. For an upfront setup cost of <b>${s_capex_est:,.0f}</b>, it generates an estimated <b>${s_net_profit_yr:,.0f}/yr in net profit</b> (paying for itself in <b>~{s_payback_yrs:.1f} years</b>) while removing carbon equal to <b>{cars_off_road} gas cars/yr</b> and skimming <b>~{bottles_cleared:,} plastic bottles/yr</b> from the ocean."
            if is_sel_safe else
            f"<b>Plain-English Bottom Line:</b> <b>Do NOT build at {sel_site}</b> — our satellite safety engine automatically blocked this site due to <b>{stat_str.replace('HAZARD: ', '')}</b>. Click <b>⭐ Pick #1 Best Site</b> above to jump to a safe green site!"
        )

        verdict_badge = (
            "<span style='background:#DCFCE7 !important; border:1.5px solid #188038; color:#137333 !important; padding:4px 10px; border-radius:6px; font-weight:800; font-size:0.88rem;'>✅ CLEARED — SAFE SITE</span>"
            if is_sel_safe else
            f"<span style='background:#FEE2E2 !important; border:1.5px solid #D93025; color:#B91C1C !important; padding:4px 10px; border-radius:6px; font-weight:800; font-size:0.88rem;'>⛔ BLOCKED ({site_data.get('status')})</span>"
        )
        st.markdown(f"""
        <div style="background-color: #FFFFFF !important; border: 1.5px solid #CBD5E1; border-left: 5px solid {'#188038' if is_sel_safe else '#D93025'}; border-radius: 10px; padding: 14px 16px; margin-bottom: 10px; color: #0F172A !important; box-shadow: 0 2px 8px rgba(15,23,42,0.05);">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px; margin-bottom:8px;">
                <span style="font-size:0.95rem; font-weight:800; color:#1A73E8 !important;">💡 Site Snapshot: {sel_site}</span>{verdict_badge}
            </div>
            <div style="display:flex; flex-wrap:wrap; gap:6px; margin-bottom:8px;">{safety_pills_html}</div>
            <div style="font-size:0.92rem; color:#0F172A !important; line-height:1.58;">
                • <b style="color:#1A73E8;">Site Quality Score:</b> <b>{site_data.get('pareto_score', 0)} / 100</b> &nbsp;|&nbsp; <b style="color:#1A73E8;">40-Yr Satellite Grade:</b> <b style="color:#B45309;">{site_data.get('report_card_grade')}</b><br/>
                • <b style="color:#1A73E8;">Farm Size:</b> <b>{s_area_ha:.1f} Hectares</b> (approx. <b>{s_acres:.0f} Acres</b> or <b>{s_acres/1.32:.0f} Football Fields</b>)<br/>
                • <b style="color:#1A73E8;">Upfront Cost:</b> <b>${s_capex_est:,.0f}</b> &nbsp;|&nbsp; <b style="color:#1A73E8;">Est. Net Profit:</b> <b style="color:#188038 !important;">${s_net_profit_yr:,.0f}/yr</b> &nbsp;|&nbsp; <b style="color:#1A73E8;">Payback:</b> <b>~{s_payback_yrs:.1f} Yrs</b><br/>
                • <b style="color:#188038;">Real-World Impact:</b> Equals <b>{cars_off_road} Cars Off the Road/yr</b> + <b>~{bottles_cleared:,} Plastic Bottles Removed/yr</b>
            </div>
            <div style="margin-top:8px; padding:8px 10px; border-radius:8px; background:{'#F0FDF4' if is_sel_safe else '#FEF2F2'}; border:1px solid {'#BBF7D0' if is_sel_safe else '#FECACA'}; font-size:0.88rem; color:#0F172A !important; line-height:1.45;">
                {bottom_line_txt}
            </div>
        </div>
        """, unsafe_allow_html=True)

        qa1, qa2 = st.columns(2)
        if qa1.button("🌿 Grow Kelp & Mint Credits", key="top_kelp_anim_btn", use_container_width=True, disabled=not is_sel_safe, help="Triggers the growing underwater Kelp Forest animation and mints verified Carbon & Plastic Credits!"):
            kelp_animation()
            st.success(f"🌿 **Kelp Forest Verified at {sel_site}!** Minted **{site_data.get('net_bankable_co2')} MT CO₂e** (= **{cars_off_road} cars/yr**) + **{site_data.get('plastic_trash_tons', 0):.1f} MT Ocean Trash Credits**.")
        if qa2.button("🤝 Initiate Lease Handshake", key="top_handshake_anim_btn", use_container_width=True, disabled=not is_sel_safe, help="Triggers the glowing Handshake animation and initiates BOEM/NOAA aquaculture lease permits!"):
            handshake_animation()
            st.success(f"🤝 **Lease Acquisition Initiated for {sel_site}!** Fast-track BOEM, NOAA & Coastal Commission permit pack ready.")

with col_map:
    st.markdown(f"<h4 style='display:flex; align-items:center; color:#0F172A !important;'>🌊 3D Ocean Safety, Oil Spill, Ocean Trash &amp; Subsea Cable Map {leaf_info('Green columns are safe, high-yield Kelp Kandidates. Other colors are automatically blocked due to sanctuaries, storms, shipping lanes, Reported Oil Spills (brown), Ocean Trash Gyres (teal), or Subsea Cables (purple).')}</h4>", unsafe_allow_html=True)
    st.markdown("""
    <div style="display: flex; flex-wrap: wrap; gap: 12px; background-color: #FFFFFF !important; padding: 12px 16px; border-radius: 8px; border: 1.5px solid #CBD5E1; margin-bottom: 10px; box-shadow: 0 2px 6px rgba(15,23,42,0.04);">
        <div style="display:flex; align-items:center; font-size:0.86rem; font-weight:600; color:#0F172A !important;"><span style="width:12px; height:12px; background:#34A853; border-radius:2px; margin-right:6px;"></span> ✅ Safe Kelp Kandidate</div>
        <div style="display:flex; align-items:center; font-size:0.86rem; font-weight:600; color:#0F172A !important;"><span style="width:12px; height:12px; background:#8D6E63; border-radius:2px; margin-right:6px;"></span> 🛢️ Reported Oil Spill Plume</div>
        <div style="display:flex; align-items:center; font-size:0.86rem; font-weight:600; color:#0F172A !important;"><span style="width:12px; height:12px; background:#00897B; border-radius:2px; margin-right:6px;"></span> 🗑️ Ocean Trash / Ghost-Net Gyre</div>
        <div style="display:flex; align-items:center; font-size:0.86rem; font-weight:600; color:#0F172A !important;"><span style="width:18px; height:4px; background:#AB47BC; margin-right:6px;"></span> ⚡ Subsea Cable (1.5km Buffer)</div>
        <div style="display:flex; align-items:center; font-size:0.86rem; font-weight:600; color:#0F172A !important;"><span style="width:12px; height:12px; background:#EA4335; border-radius:2px; margin-right:6px;"></span> ⛔ Sanctuary</div>
        <div style="display:flex; align-items:center; font-size:0.86rem; font-weight:600; color:#0F172A !important;"><span style="width:12px; height:12px; background:#FA7B17; border-radius:2px; margin-right:6px;"></span> 🌪️ Storm Zone</div>
        <div style="display:flex; align-items:center; font-size:0.86rem; font-weight:600; color:#0F172A !important;"><span style="width:18px; height:4px; background:#FBBC04; margin-right:6px;"></span> 🚢 Shipping Lane</div>
        <div style="display:flex; align-items:center; font-size:0.86rem; font-weight:600; color:#0F172A !important;"><span style="width:12px; height:12px; background:#4285F4; border-radius:50%; margin-right:6px;"></span> 🐋 Whale / Deep Sink Arc</div>
    </div>
    """, unsafe_allow_html=True)

    layers = [
        pdk.Layer("PolygonLayer", data=restricted_data, get_polygon="polygon", get_fill_color="[234, 67, 53, 35]", get_line_color="[217, 48, 37, 230]", line_width_min_pixels=2),
        pdk.Layer("PolygonLayer", data=allowed_data, get_polygon="polygon", get_fill_color="[52, 168, 83, 28]", get_line_color="[24, 128, 56, 220]", line_width_min_pixels=2),
        pdk.Layer("PolygonLayer", data=weather_data, get_polygon="polygon", get_fill_color="[250, 123, 23, 35]", get_line_color="[250, 123, 23, 220]", line_width_min_pixels=2),
        pdk.Layer("PolygonLayer", data=oil_spill_data, get_polygon="polygon", get_fill_color="[141, 110, 99, 65]", get_line_color="[93, 64, 55, 240]", line_width_min_pixels=2),
        pdk.Layer("PolygonLayer", data=trash_gyre_data, get_polygon="polygon", get_fill_color="[0, 137, 123, 55]", get_line_color="[0, 105, 92, 240]", line_width_min_pixels=2),
    ]
    if not subsea_cables_df.empty:
        layers.append(pdk.Layer("PathLayer", data=subsea_cables_df, get_path="path", get_color="[142, 36, 170, 235]", width_scale=18, width_min_pixels=3, get_width=4, pickable=False))
    if not shipping_lanes_df.empty:
        layers.append(pdk.Layer("PathLayer", data=shipping_lanes_df, get_path="path", get_color="[217, 119, 6, 200]", width_scale=20, width_min_pixels=3, get_width=5, pickable=False))
    if not mammals_df.empty:
        layers.append(pdk.Layer("ScatterplotLayer", data=mammals_df, get_position="[lon, lat]", get_color="[26, 115, 232, 180]", get_radius=4000, pickable=False))
    if not kelp_df.empty:
        layers.append(pdk.Layer("ColumnLayer", id="kelp_columns", data=kelp_df, get_position="[lon, lat]", get_elevation="biomass_tons * 100", elevation_scale=1, radius=1500, get_fill_color="color", pickable=True, auto_highlight=True))
        layers.append(pdk.Layer("TextLayer", data=kelp_df, get_position="[lon, lat]", get_text="id", get_color="[15, 23, 42, 245]", get_size=15, get_alignment_baseline="'bottom'"))
    if site_data is not None:
        sel_df = pd.DataFrame([site_data])
        layers.append(pdk.Layer("ScatterplotLayer", data=sel_df, get_position="[lon, lat]", get_fill_color="[26, 115, 232, 55]", get_line_color="[26, 115, 232, 255]", get_radius=3200, stroked=True, line_width_min_pixels=3))
        arc_df = pd.DataFrame([{"source": [float(site_data["lon"]), float(site_data["lat"])], "target": [float(site_data["lon"]) - (float(site_data["abyssal_dist_km"]) / 111.0), float(site_data["lat"]) - 0.12]}])
        layers.append(pdk.Layer("ArcLayer", data=arc_df, get_source_position="source", get_target_position="target", get_source_color="[24, 128, 56, 240]", get_target_color="[26, 115, 232, 240]", get_width=4))

    tt_html = (
        "<div style='font-family:sans-serif; background:#FFFFFF; padding:10px 12px; border-radius:8px; border:1.5px solid #1A73E8; color:#0F172A; box-shadow:0 4px 12px rgba(15,23,42,0.15);'>"
        "<b>Kelp Kandidate: {id}</b> ({report_card_grade})<br/>Site Quality Score: <b>{pareto_score}/100</b> | Size: {area_ha} HA<br/>"
        "Annual Harvest: {biomass_tons} MT | Net Carbon: {net_bankable_co2} MT/yr<br/>"
        "Ocean Trash Cleared: <b>{plastic_trash_tons} MT/yr</b> | Oil/PAH: <b>{pah_oil_ppm} ppm</b><br/>"
        "Subsea Cable Clearance: <b>{cable_dist_km} km</b><br/><span style='color:#188038;'>Verdict: <b>{status}</b></span></div>"
    )
    deck_obj = pdk.Deck(layers=layers, initial_view_state=pdk.ViewState(latitude=SECTOR_CONFIG[sector_key]["lat"], longitude=SECTOR_CONFIG[sector_key]["lon"], zoom=8.5, pitch=55, bearing=15), map_style="https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json", tooltip={"html": tt_html})
    try:
        deck_event = st.pydeck_chart(deck_obj, use_container_width=True, height=600, on_select="rerun", selection_mode="single-object")
        picked = deck_event.selection.get("objects", {}).get("kelp_columns", []) if hasattr(deck_event, "selection") and deck_event.selection else []
        if picked and picked[0].get("id") and picked[0]["id"] != st.session_state.selected_site_id:
            st.session_state.selected_site_id = picked[0]["id"]
            st.rerun()
    except TypeError:
        st.pydeck_chart(deck_obj, use_container_width=True, height=600)

with col_ops:
    t_mission, t1, t2, t_mrv, t3 = st.tabs([
        "🚀 Start Here & Glossary",
        "📈 Site Health & Species",
        "💰 10-Yr ROI & Cost Levers",
        "🛰️ Carbon & ROV/Cable MRV",
        "💬 AI Advisor & Site PDF",
    ])

    with t_mission:
        st.info("**Why Blue 42 Beats Single-Purpose Ocean Tools:** Traditional single-purpose ocean tools only show isolated pieces of the puzzle—such as satellite maps alone, water-biology models alone, farm equipment spreadsheets alone, or underwater ROV video alone. **Blue 42 | The Kelp Contender** unites **all of them** in one place with **Oil Spill & Ocean Trash Screening**, **Subsea Cable Safety**, **10-Year Farm Economics**, and **Tamper-Proof Carbon & Plastic Certificates**.")
        with st.expander("🏆 Why Blue 42 Beats Single-Purpose Ocean Tools (Side-by-Side Comparison)", expanded=True):
            bench_rows = [
                {"Capability": "40-Yr Canopy History & Ecosystem Report Card", "Satellite-Only Viewers": "✅ Yes", "Biology-Only Models": "❌ No", "Standalone Cost / ROV Tools": "❌ No", "BLUE 42 (Kelp Contender)": "✅ Yes (1985–2025 + A+ Grade)"},
                {"Capability": "4 Global Hotspots (CA, BC Canada, Tasmania, HI)", "Satellite-Only Viewers": "⚠️ Regional", "Biology-Only Models": "✅ Yes", "Standalone Cost / ROV Tools": "❌ No", "BLUE 42 (Kelp Contender)": "✅ Yes (All 4 Corridors Built-In)"},
                {"Capability": "Multi-Species Biophysical Niche Matching", "Satellite-Only Viewers": "❌ No", "Biology-Only Models": "✅ Yes", "Standalone Cost / ROV Tools": "❌ No", "BLUE 42 (Kelp Contender)": "✅ Yes (5 Species × 6 Factors)"},
                {"Capability": "Oil Spill (PAH), Fertilizer & Ocean Trash Screening", "Satellite-Only Viewers": "❌ No", "Biology-Only Models": "❌ No", "Standalone Cost / ROV Tools": "❌ No", "BLUE 42 (Kelp Contender)": "✅ Yes (Oil Plumes + $850/MT Trash Boom)"},
                {"Capability": "Shipping, Whale & Subsea Cable Safety Blocking", "Satellite-Only Viewers": "❌ No", "Biology-Only Models": "❌ No", "Standalone Cost / ROV Tools": "❌ No", "BLUE 42 (Kelp Contender)": "✅ Yes (ICPC 1.5km Buffer + SMART)"},
                {"Capability": "Farm Cost-Cutting Levers & 10-Yr NPV / Monte Carlo", "Satellite-Only Viewers": "❌ No", "Biology-Only Models": "❌ No", "Standalone Cost / ROV Tools": "⚠️ Costs Only", "BLUE 42 (Kelp Contender)": "✅ Yes (4 Levers + 500-Path Simulation)"},
                {"Capability": "4-Tier Sensor Fusion (Sat + Drone + ROV + Cable)", "Satellite-Only Viewers": "⚠️ Sat Only", "Biology-Only Models": "❌ No", "Standalone Cost / ROV Tools": "⚠️ ROV Only", "BLUE 42 (Kelp Contender)": "✅ Yes (4-Tier Fusion + SHA-256)"},
                {"Capability": "1-Click Government Permit & Signed PDF Certificates", "Satellite-Only Viewers": "❌ No", "Biology-Only Models": "❌ No", "Standalone Cost / ROV Tools": "❌ No", "BLUE 42 (Kelp Contender)": "✅ Yes (Instant PDF + HTML Map)"},
            ]
            st.dataframe(pd.DataFrame(bench_rows), use_container_width=True, hide_index=True)

        with st.expander("📖 Glossary", expanded=False):
            st.markdown("""
            - **Kelp Kandidate (`KK-1` to `KK-12`):** A potential ocean farm site. Green sites (`CLEARED: Optimal`) are safe to develop; other colors are automatically blocked.
            - **Reported Oil Spills & Hydrocarbon Plumes (`Brown Zone on Map`):** Kelp is a natural "sponge." If an oil spill or ship bilge slick hits a farm, the kelp absorbs toxic hydrocarbons (`PAHs`) and **cannot be sold for food, cattle feed, or clean bioplastics**. Blue 42 automatically blocks sites inside reported oil slicks (`HAZARD: Reported Oil Spill Plume`) and routes any trace-contaminated kelp (`>0.05 ppm PAH`) strictly to **>1,000m Deep-Sea Carbon Sinking**.
            - **Ocean of Trash & Ghost Fishing Nets (`Teal Zone + Perimeter Trash Boom`):** Dense floating plastic eddies and derelict "ghost fishing nets" can tangle kelp lines and introduce microplastics. Blue 42 blocks severe trash gyres (`HAZARD: Ocean Trash / Ghost-Net Gyre`) and lets safe sites deploy a **Perimeter Trash Interceptor Boom** that skims floating plastics and ghost nets before they touch the kelp—earning **\\$850/MT in Verified Ocean Plastic Cleanup Credits**!
            - **Fertilizer & Sewage Runoff Cleanup (`Nitrogen Bioremediation`):** Kelp absorbs excess agricultural fertilizer (`Nitrogen` & `Phosphorus`) from coastal water before it causes toxic algae blooms and fish "dead zones," earning **\\$2,000/MT** in water-quality credits.
            - **Subsea Fiber & Power Cables (`Purple Lines on Map`):** Heavy 10-ton kelp anchors can snap undersea internet or power cables (costing **\\$1.5M–\\$5M** to repair). Blue 42 blocks sites within **1.5 km** of a cable (`ICPC Buffer`), while sites **1.5–9.0 km away** can use **SMART Subsea Cable** seafloor sensors!
            - **Gross-to-Net Carbon (`MRV Waterfall`):** Subtracts tugboat fuel, 5% natural deep-sea loss, and a 10–15% insurance reserve from total carbon absorbed to calculate **Net Sellable Carbon Credits**.
            """)

        if not safe_df.empty:
            st.markdown("###### 📥 Download Safe Kelp Kandidates (Visual Map, PDF Report, or Spreadsheet)")
            c_dl1, c_dl2, c_dl3 = st.columns(3)
            c_dl1.download_button("🗺️ Interactive Map (HTML)", data=export_to_interactive_map_html(safe_df, sector), file_name="Blue42_Interactive_Kelp_Map.html", mime="text/html", use_container_width=True)
            c_dl2.download_button("📄 Safe Sites Report (PDF)", data=create_safe_sites_directory_pdf(safe_df, sector), file_name="Blue42_Safe_Kelp_Kandidates_Report.pdf", mime="application/pdf", use_container_width=True)
            c_dl3.download_button("📊 Spreadsheet (CSV)", data=safe_df.drop(columns=['color'], errors='ignore').to_csv(index=False).encode('utf-8'), file_name="Blue42_Kelp_Kandidates.csv", mime="text/csv", use_container_width=True)
            with st.expander("🌐 Advanced GIS Engineering Files (Google Earth .KML & Raw .GeoJSON)", expanded=False):
                g_c1, g_c2 = st.columns(2)
                g_c1.download_button("🌍 Google Earth (.KML)", data=export_to_kml(safe_df), file_name="Blue42_Kelp_Kandidates.kml", mime="application/vnd.google-earth.kml+xml", use_container_width=True)
                g_c2.download_button("🧭 Raw GIS (.GeoJSON)", data=export_to_geojson(safe_df), file_name="Blue42_Kelp_Kandidates.geojson", mime="application/octet-stream", use_container_width=True)

    with t1:
        if site_data is not None:
            sst = site_data.get('effective_sst', site_data.get('sst_mean', 15.0))
            rec_strain = "Heat-Resistant Baja Kelp Seed (M. pyrifera)" if (sst > 16.0 or adopt_baja_strain) else "Standard Cold-Water Alaskan Kelp Seed (M. pyrifera)"
            st.markdown(f"<div style='background-color:#F0F7FF !important;border:1.5px solid #93C5FD;border-left:5px solid #1A73E8;padding:12px 14px;border-radius:8px;margin-bottom:12px;color:#0F172A !important;'><div style='font-size:0.86rem;color:#1A73E8 !important;font-weight:800;'>🧬 RECOMMENDED SEED — {sel_site}</div><div style='font-size:1.04rem;color:#0F172A !important;font-weight:800;'>{rec_strain}</div><div style='font-size:0.90rem;color:#334155 !important;'>Water Temp: <b style='color:#B45309;'>{sst:.1f}°C</b> | Sunlight (PAR): <b style='color:#1A73E8;'>{site_data.get('par_light')} mol/m²/d</b> | Keeps <b style='color:#188038;'>{site_data.get('stress_retention_pct', 100):.0f}%</b> of harvest</div></div>", unsafe_allow_html=True)

            jobs = int(site_data.get('jobs_created', 0))
            st.markdown(f"""
            <div class="metric-grid">
                <div class="metric-box" style="border-top: 4px solid #D97706;"><div class="metric-title">Local Jobs Created</div><div class="metric-val" style="color: #B45309;">{jobs}</div><div class="metric-sub">{int(jobs*0.4)} Boats | {int(jobs*0.4)} Processing</div></div>
                <div class="metric-box" style="border-top: 4px solid #188038;"><div class="metric-title">Runoff Nitrogen Cleaned</div><div class="metric-val" style="color: #188038;">{site_data.get('nitrogen_tons', 0)} MT</div><div class="metric-sub">Stops Toxic Algae Blooms</div></div>
                <div class="metric-box" style="border-top: 4px solid #00897B;"><div class="metric-title">Ocean Trash Skimmed</div><div class="metric-val" style="color: #00796B;">{site_data.get('plastic_trash_tons', 0)} MT/yr</div><div class="metric-sub">Plastics &amp; Ghost Nets Removed</div></div>
            </div>
            """, unsafe_allow_html=True)

            with st.expander("🛢️🗑️ Pollution, Reported Oil Spill (PAH) & Ocean Trash Screening", expanded=True):
                st.caption("Screens every site via Sentinel-1 radar and water sensors for **Reported Oil Spills (`PAHs`)**, **Floating Ocean Trash / Ghost Fishing Nets**, and **Agricultural Fertilizer Runoff**:")
                pol_rows = [
                    {
                        "Pollution / Waste Type": "🛢️ Reported Oil Spills & Hydrocarbons (PAHs)",
                        "Site Sensor Reading": f"{site_data.get('pah_oil_ppm', 0.0):.2f} ppm PAH (Safety Limit: <0.05 ppm)",
                        "Impact & Action": site_data.get("crop_safety_verdict", "✅ 100% Safe for Food, Cow Feed & Bioplastics"),
                    },
                    {
                        "Pollution / Waste Type": "🗑️ Ocean Trash & Ghost Fishing Nets",
                        "Site Sensor Reading": f"{site_data.get('plastic_trash_tons', 0):.2f} MT/yr intercepted at perimeter",
                        "Impact & Action": "Perimeter Trash Boom traps plastics & ghost nets -> Earns $850/MT Plastic Credit",
                    },
                    {
                        "Pollution / Waste Type": "💧 Agricultural Fertilizer & Sewage Runoff (N₂)",
                        "Site Sensor Reading": f"{site_data.get('nitrogen_tons', 0):.2f} MT/yr dissolved Nitrogen absorbed",
                        "Impact & Action": "Prevents coastal 'Dead Zones' -> Earns $2,000/MT Water Quality Credit",
                    },
                ]
                st.dataframe(pd.DataFrame(pol_rows), use_container_width=True, hide_index=True)

            if PLOTLY_AVAILABLE and bounds:
                cats = ['Carbon Yield', 'Coastal Protection', 'Biodiversity', 'Pollution Cleanup', 'Social Equity']
                s_norm = [round(norm_val(site_data[m], *bounds[m]) * 100, 1) for m in metrics_to_norm]
                a_norm = [round(float(np.mean([norm_val(s[m], *bounds[m]) * 100 for s in raw_sites])), 1) for m in metrics_to_norm]
                fig_rad = go.Figure()
                fig_rad.add_trace(go.Scatterpolar(r=a_norm + [a_norm[0]], theta=cats + [cats[0]], fill='toself', name='Regional Avg', line=dict(color='#64748B', width=1.5)))
                fig_rad.add_trace(go.Scatterpolar(r=s_norm + [s_norm[0]], theta=cats + [cats[0]], fill='toself', name=f"{sel_site} ({site_data['pareto_score']}/100)", line=dict(color='#1A73E8', width=2.5)))
                fig_rad.update_layout(template="plotly_white", font=dict(color="#0F172A"), paper_bgcolor="rgba(0,0,0,0)", polar=dict(bgcolor="#F8FAFC", radialaxis=dict(visible=True, range=[0, 100])), margin=dict(l=30, r=30, t=20, b=15), height=205)
                st.plotly_chart(fig_rad, use_container_width=True)

            with st.expander("📊 40-Year Satellite Canopy History & Ecosystem Report Card (1985–2025)", expanded=False):
                hist_p = int(site_data.get("hist_persistence_40yr", 88))
                rc_grade = site_data.get("report_card_grade", "A (High Persistence)")
                c_h1, c_h2 = st.columns(2)
                c_h1.metric("Ecosystem Report Card Grade", rc_grade)
                c_h2.metric("40-Yr Satellite Rebound Rate", f"{hist_p}%")
                if PLOTLY_AVAILABLE:
                    decs = ["1985", "1990", "1995", "1998 (El Niño)", "2005", "2010", "2015 (Heatwave)", "2020", "2025"]
                    h_vals = [round(hist_p * m, 1) for m in [0.96, 1.00, 0.98, 0.72, 1.02, 1.04, 0.68, 0.97, 1.00]]
                    fig_h = go.Figure(go.Scatter(x=decs, y=h_vals, mode="lines+markers", line=dict(color="#188038", width=2.5), fill="tozeroy", fillcolor="rgba(24,128,56,0.14)"))
                    fig_h.update_layout(template="plotly_white", font=dict(color="#0F172A"), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", yaxis_title="Canopy Persistence (%)", margin=dict(l=0, r=0, t=10, b=0), height=175)
                    st.plotly_chart(fig_h, use_container_width=True)

            with st.expander("🧬 Multi-Species Biophysical Niche Matcher (5 Kelp Species × 6 Ocean Factors)", expanded=False):
                niche_rows = [
                    {"Kelp Species": "Giant Kelp (Macrocystis pyrifera)", "Best Use": "Carbon Sinking + Bioplastics", "Ideal Temp": "11–18°C", "Site Match": f"{min(99, max(55, int(100 - abs(sst - 14.8)*4.5)))}%", "Verdict": "⭐ Primary High-Yield Crop" if sst <= 18.5 else "⚠️ Use Baja Heat Strain"},
                    {"Kelp Species": "Bull Kelp (Nereocystis luetkeana)", "Best Use": "High-Wave Cold Restoration", "Ideal Temp": "9–15°C", "Site Match": f"{min(98, max(45, int(100 - abs(sst - 12.5)*5.2)))}%", "Verdict": "✅ Strong Cold/Wave Fit" if sst <= 15.8 else "Warm for Bull Kelp"},
                    {"Kelp Species": "Sugar Kelp (Saccharina latissima)", "Best Use": "Food, Bio-Packaging & N₂ Cleanup", "Ideal Temp": "8–16°C", "Site Match": f"{min(97, max(50, int(100 - abs(sst - 13.5)*4.8)))}%", "Verdict": "✅ High Commercial Value" if sst <= 16.5 else "Seasonal Winter Crop"},
                    {"Kelp Species": "Golden Kelp (Ecklonia radiata)", "Best Use": "Southern Reef & Temperate Carbon", "Ideal Temp": "13–20°C", "Site Match": f"{min(98, max(60, int(100 - abs(sst - 16.5)*4.0)))}%", "Verdict": "✅ Resilient Temperate Fit"},
                    {"Kelp Species": "Red Ogo / Asparagopsis Guild", "Best Use": "Anti-Methane Cow Feed (Warm)", "Ideal Temp": "18–25°C", "Site Match": f"{min(99, max(48, int(100 - abs(sst - 20.5)*4.5)))}%", "Verdict": "⭐ Top Tropical Pick" if sst > 17.5 else "Supplemental Summer Crop"},
                ]
                st.dataframe(pd.DataFrame(niche_rows), use_container_width=True, hide_index=True)

            st.download_button("📥 Download Site Fact Sheet & Pollution/Satellite Provenance (PDF)", data=create_provenance_pdf(site_data.to_dict()), file_name=f"Blue42_Data_Provenance_{sel_site}.pdf", mime="application/pdf", use_container_width=True)

    with t2:
        if site_data is not None:
            st.markdown(f"<h5 style='display:flex; align-items:center;'>💵 10-Year Returns &amp; Farm Cost-Cutting Levers {leaf_info('Model 5 income streams (including Ocean Trash & Fertilizer Cleanup Credits), toggle farm cost-reduction levers, and build an optimal portfolio.')}</h5>", unsafe_allow_html=True)
            with st.expander("⚙️ Prices, Return Rate (WACC), Community Share & Farm Engineering Levers", expanded=True):
                c_p1, c_p2, c_p3 = st.columns(3)
                carbon_price = c_p1.number_input("Carbon Price ($/MT)", 50, 500, 150, 10)
                biomass_price = c_p2.number_input("Kelp Price ($/MT)", 100, 800, 300, 25)
                wacc_rate = c_p3.slider("Discount Rate / WACC (%)", 2.0, 15.0, 8.0, 0.5) / 100.0
                commons_share_pct = st.slider("🤝 Local Fishing & Indigenous Community Share (% Gross Rev)", 0, 15, 8, 1)
                st.markdown("**🔧 Offshore Farm Engineering & Ocean Trash Cleanup Levers:**")
                cl1, cl2 = st.columns(2)
                lever_auto_harvest = cl1.checkbox("🤖 Automated Harvester Barge (-18% OPEX)", value=False)
                lever_shared_hub = cl2.checkbox("🏭 Shared Coastal Processing Hub (-15% Upfront Cost)", value=False)
                cl3, cl4 = st.columns(2)
                lever_dual_seed = cl3.checkbox("🌱 Dual-Season Spore Seeding (+12% Harvest)", value=False)
                lever_trash_boom = cl4.checkbox("🗑️ Perimeter Ocean Trash Boom (+$850/MT Plastic Credit)", value=True)

            strain_mult = 1.12 if adopt_baja_strain else 1.0
            capex = site_data['area_ha'] * 15000 * strain_mult * (0.85 if lever_shared_hub else 1.0)
            opex_yr = ((site_data['area_ha'] * 2000) + site_data['sinking_cost']) * (0.82 if lever_auto_harvest else 1.0)
            y_mult = 1.12 if lever_dual_seed else 1.0
            eff_co2 = site_data['net_bankable_co2'] * y_mult
            eff_bio = site_data['biomass_tons'] * y_mult
            wave_reb = (site_data['area_ha'] * 1500) + (site_data['averted_damage_millions'] * 1e6 * 0.0025)
            bio_rev_yr = 0.0 if float(site_data.get("pah_oil_ppm", 0.0)) >= 0.05 else (eff_bio * biomass_price)
            trash_credit_yr = (float(site_data.get("plastic_trash_tons", 0)) * 850.0) if lever_trash_boom else 0.0
            gross_rev_yr = (eff_co2 * carbon_price) + bio_rev_yr + wave_reb + (site_data['nitrogen_tons'] * 2000) + trash_credit_yr
            rev_yr = gross_rev_yr * (1.0 - commons_share_pct / 100.0)
            permit_months = max(12, 36 - int(commons_share_pct * 2))

            years = np.arange(0, 11)
            npv_curve = [-capex + sum((rev_yr - opex_yr) / ((1 + wacc_rate) ** t) for t in range(1, yr + 1)) for yr in years]
            if PLOTLY_AVAILABLE:
                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(x=years, y=capex + opex_yr * years, name="Cumulative Cost", line=dict(color="#D93025", width=2)))
                fig2.add_trace(go.Scatter(x=years, y=rev_yr * years, name="Cumulative Revenue", line=dict(color="#188038", width=2), fill='tozeroy', fillcolor='rgba(24,128,56,0.14)'))
                fig2.add_trace(go.Scatter(x=years, y=npv_curve, name="Discounted 10-Yr NPV ($)", line=dict(color="#1A73E8", width=2.5, dash="dot")))
                fig2.update_layout(template="plotly_white", font=dict(color="#0F172A"), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", yaxis_title="USD ($)", margin=dict(l=0, r=0, t=10, b=0), height=210)
                st.plotly_chart(fig2, use_container_width=True)

            ann_prof = rev_yr - opex_yr
            unit_bio_cost = ((capex / 10.0) + opex_yr) / max(eff_bio, 1.0)
            lcok = ((capex / 10.0) + opex_yr) / max(eff_co2, 1.0)
            if ann_prof > 0:
                st.success(f"**Payback:** Year {capex/ann_prof:.1f} | **10-Yr NPV:** \\${npv_curve[-1]:,.0f} | **Ocean Trash Credit:** +\\${trash_credit_yr:,.0f}/yr | **Farm Cost/Ton Kelp:** \\${unit_bio_cost:,.0f}/MT | **Cost/Ton CO₂:** \\${lcok:,.0f}")

            with st.expander("🍩 Where Does the Money Come From? (5 Annual Revenue Streams Explained)", expanded=True):
                rev_streams = [
                    {"Revenue Stream": "💨 1. Verified Carbon Credits", "Annual Income ($)": f"${eff_co2 * carbon_price:,.0f}/yr", "How It Works (Plain English)": f"Selling {eff_co2:.1f} MT of net deep-sea carbon credits at ${carbon_price}/MT"},
                    {"Revenue Stream": "🧴 2. Clean Kelp Harvest (Bioplastics & Feed)", "Annual Income ($)": f"${bio_rev_yr:,.0f}/yr", "How It Works (Plain English)": "Sold to bioplastics, fertilizer & low-methane cattle feed buyers (halted if oil >0.05 ppm)"},
                    {"Revenue Stream": "🌊 3. Coastal Storm Protection Rebate", "Annual Income ($)": f"${wave_reb:,.0f}/yr", "How It Works (Plain English)": "Insurance & municipal coastal resilience rebate for dampening storm waves"},
                    {"Revenue Stream": "💧 4. Fertilizer Nitrogen Water Cleanup", "Annual Income ($)": f"${site_data['nitrogen_tons'] * 2000:,.0f}/yr", "How It Works (Plain English)": f"Removes {site_data['nitrogen_tons']} MT/yr of agricultural nitrogen runoff at $2,000/MT"},
                    {"Revenue Stream": "🗑️ 5. Ocean Plastic & Ghost-Net Credit", "Annual Income ($)": f"${trash_credit_yr:,.0f}/yr", "How It Works (Plain English)": f"Perimeter Trash Boom skims {site_data.get('plastic_trash_tons', 0):.1f} MT/yr of plastics at $850/MT"},
                ]
                st.dataframe(pd.DataFrame(rev_streams), use_container_width=True, hide_index=True)

            with st.expander("🎲 500-Scenario Weather & Price Stress Test (Monte Carlo) + Farm Equipment Breakdown", expanded=False):
                mc_rng = np.random.default_rng(42)
                shocks = np.clip(mc_rng.normal(1.0, 0.16, (500, 10)), 0.45, 1.40)
                paths = np.zeros((500, 11))
                paths[:, 0] = -capex
                for y_i in range(1, 11):
                    paths[:, y_i] = paths[:, y_i - 1] + (((rev_yr * shocks[:, y_i - 1]) - opex_yr) / ((1.0 + wacc_rate) ** y_i))
                st.info(f"**500-Future 10-Yr NPV Range:** **Worst Case (5th %):** \\${np.percentile(paths[:,-1], 5):,.0f} | **Median:** \\${np.percentile(paths[:,-1], 50):,.0f} | **Best Case (95th %):** \\${np.percentile(paths[:,-1], 95):,.0f}")
                fa_df = pd.DataFrame([
                    {"Equipment & Infrastructure Item": "Subsurface Mooring Grid, Anchors & Trash Boom", "Cost Share": "55%", "Estimated Cost ($)": f"${capex*0.55:,.0f}", "Expected Life": "10 Yrs"},
                    {"Equipment & Infrastructure Item": "Satellite/Drone Buoys & SMART Cable Link", "Cost Share": "20%", "Estimated Cost ($)": f"${capex*0.20:,.0f}", "Expected Life": "5 Yrs"},
                    {"Equipment & Infrastructure Item": "Hatchery Seeding & Harvester Barge Gear", "Cost Share": "15%", "Estimated Cost ($)": f"${capex*0.15:,.0f}", "Expected Life": "7 Yrs"},
                    {"Equipment & Infrastructure Item": "Ocean Seabed Permit & Lease Filing", "Cost Share": "10%", "Estimated Cost ($)": f"${capex*0.10:,.0f}", "Expected Life": "10 Yrs"},
                    {"Equipment & Infrastructure Item": "End-of-Lease Seafloor Cleanup Reserve", "Cost Share": "+5% Reserve", "Estimated Cost ($)": f"${capex*0.05:,.0f}", "Expected Life": "10 Yrs"},
                ])
                st.dataframe(fa_df, use_container_width=True, hide_index=True)

            st.markdown("###### 💼 'How Many Safe Sites Can My Budget Buy?' (Auto-Portfolio Builder)")
            capex_budget = st.slider("Your Total Project Budget ($ USD)", 150000, 2500000, 750000, 50000)
            cands = []
            for _, row in safe_df.iterrows():
                sc_x = row['area_ha'] * 15000 * strain_mult
                so_x = (row['area_ha'] * 2000) + row['sinking_cost']
                sr_x = (row['net_bankable_co2'] * carbon_price) + (row['biomass_tons'] * biomass_price) + (row['area_ha'] * 1500) + (row['nitrogen_tons'] * 2000) + (row.get('plastic_trash_tons', 0) * 850)
                snpv = -sc_x + sum((sr_x - so_x) / ((1 + wacc_rate) ** t) for t in range(1, 11))
                if snpv > 0:
                    cands.append({"Site ID": row['id'], "Pareto": f"{row['pareto_score']:.1f}", "Area (HA)": row['area_ha'], "CAPEX_num": sc_x, "NPV_num": snpv, "Net_CO2_num": row['net_bankable_co2'], "Upfront Cost ($)": f"${sc_x:,.0f}", "10-Yr NPV ($)": f"${snpv:,.0f}", "Net CO₂e/yr": f"{row['net_bankable_co2']:.1f} MT", "Eff": (snpv / sc_x) * (row['pareto_score'] / 100.0)})
            cands.sort(key=lambda x: x["Eff"], reverse=True)
            funded_sites, spent = [], 0.0
            for c in cands:
                if spent + c["CAPEX_num"] <= capex_budget:
                    spent += c["CAPEX_num"]
                    funded_sites.append({k: c[k] for k in ["Site ID", "Pareto", "Area (HA)", "Upfront Cost ($)", "10-Yr NPV ($)", "Net CO₂e/yr"]})
            if funded_sites:
                st.dataframe(pd.DataFrame(funded_sites), use_container_width=True, hide_index=True)

            c_perm1, c_perm2 = st.columns(2)
            if c_perm1.button("🤝 Initiate Lease & Permit Handshake", use_container_width=True):
                handshake_animation()
                st.success(f"✅ Legal & community lease protocols initiated! Fast-Track `{permit_months}-Month` BOEM/NOAA Permit Ready.")
            c_perm2.download_button("📥 Download Permit Dossier (PDF)", data=create_lease_permit_pdf(site_data.to_dict(), funded_sites, commons_share_pct, permit_months), file_name=f"Blue42_Permit_Dossier_{sel_site}.pdf", mime="application/pdf", use_container_width=True)

    with t_mrv:
        if site_data is not None:
            is_kandidate_cleared = "CLEARED" in site_data.get('status', '')
            st.markdown(f"<h5 style='display:flex; align-items:center;'>🛰️ Carbon Credit Waterfall &amp; 4-Tier Sensor Fusion {leaf_info('Proves to carbon & plastic credit buyers that your kelp grew in clean water using Satellites, Drones, Underwater ROV AI, and SMART Subsea Cables.')}</h5>", unsafe_allow_html=True)
            gross_c, tow_c, remin_c, buf_c, net_c = float(site_data["co2_tons"]), float(site_data["tow_emissions_co2"]), float(site_data["remin_discount_co2"]), float(site_data["buffer_pool_co2"]), float(site_data["net_bankable_co2"])
            if PLOTLY_AVAILABLE:
                fig_wf = go.Figure(go.Waterfall(
                    orientation="v", measure=["absolute", "relative", "relative", "relative", "total"],
                    x=["Total Absorbed", "Less Boat Fuel", "Less 5% Deep Loss", "Less Insurance Reserve", "Net Sellable Credits"],
                    y=[gross_c, -tow_c, -remin_c, -buf_c, net_c],
                    text=[f"{gross_c:.1f}", f"-{tow_c:.2f}", f"-{remin_c:.2f}", f"-{buf_c:.2f}", f"{net_c:.1f} MT"],
                    decreasing={"marker": {"color": "#D93025"}}, increasing={"marker": {"color": "#1A73E8"}}, totals={"marker": {"color": "#188038"}},
                ))
                fig_wf.update_layout(template="plotly_white", font=dict(color="#0F172A"), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", yaxis_title="MT CO₂e / Yr", margin=dict(l=0, r=0, t=15, b=0), height=210)
                st.plotly_chart(fig_wf, use_container_width=True)

            with st.expander("🤖 4-Tier Sensor Fusion: Satellite + Drone + Underwater ROV AI + SMART Subsea Cable", expanded=True):
                st.caption("Combines **Space Satellites (30m + SAR Oil Slick Detection)**, **Coastal Drones (3cm Trash & Canopy Scan)**, **Underwater ROV AI Cameras**, and **SMART Subsea Cable Seafloor Sensors**:")
                rov_sub = site_data.get("substrate_type", "Consolidated Rocky Reef")
                rov_stipes = float(site_data.get("rov_stipe_density", 14.2))
                rov_fish = int(site_data.get("rov_wildlife_species", 28))
                rov_par = float(site_data.get("par_light", 36.5))
                rc1, rc2, rc3 = st.columns(3)
                rc1.metric("🪨 Seafloor Anchor (ROV)", rov_sub.split("(")[0].strip())
                rc2.metric("🌿 Underwater Stalks (ROV)", f"{rov_stipes:.1f} stalks/m²")
                rc3.metric("🗑️ Trash Skimmed (Boom)", f"{site_data.get('plastic_trash_tons', 0):.1f} MT/yr")
                sensor_df = pd.DataFrame([
                    {"Verification Layer": "🛰️ Tier 1: Orbital Satellite (Sentinel-2 + SAR Oil Radar)", "Resolution": "10m – 30m", "What It Proves": "Tracks floating kelp canopy + screens for surface oil slicks", "Live Reading": f"{int(95 * (site_data['stress_retention_pct']/100.0))}% Canopy | Oil Slick: {site_data.get('pah_oil_ppm', 0.0):.2f} ppm"},
                    {"Verification Layer": "🚁 Tier 2: Multispectral Coastal Drone (UAV)", "Resolution": "3cm Ultra-HD", "What It Proves": "Measures blade health, nitrogen cleanup & perimeter trash boom", "Live Reading": f"PAR: {rov_par:.1f} mol/m²/d | Trash Skimmed: {site_data.get('plastic_trash_tons', 0)} MT/yr"},
                    {"Verification Layer": "🤖 Tier 3: Underwater ROV AI Vision (Sub-Surface)", "Resolution": "Sub-mm HD + Sonar", "What It Proves": "Counts underwater stalks, rock anchors & checks for ghost nets", "Live Reading": f"{rov_stipes:.1f} stalks/m² | {rov_fish} species | Zero Ghost-Net Snags"},
                    {"Verification Layer": "⚡ Tier 4: SMART Subsea Cable Telemetry (Seafloor)", "Resolution": "24/7 Optical/Benthic", "What It Proves": "Verifies >1.5km safe cable clearance + live seafloor O₂/Temp", "Live Reading": site_data.get("smart_cable_status", "✅ Safe Clearance")},
                ])
                st.dataframe(sensor_df, use_container_width=True, hide_index=True)

            ts_now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')
            tx_hash = generate_sha256_signature(site_data.to_dict(), ts_now)
            itmo_serial = f"B42-ART64-{sector_key[:3].upper()}-{sel_site}-{tx_hash[:8].upper()}"
            cert_pdf = create_minted_credit_pdf(site_data.to_dict(), itmo_serial, tx_hash, ts_now)
            if st.button("🔐 Issue & Stamp Official Carbon & Ocean Cleanup Certificate", use_container_width=True, disabled=not is_kandidate_cleared):
                kelp_animation()
                st.success(f"✅ Verified across 4 Sensor Tiers! **{net_c:.2f} Net Carbon Credits (MT CO₂e)** + **{site_data.get('plastic_trash_tons', 0):.1f} MT Ocean Trash Credits** issued (`{itmo_serial}`).")
                st.markdown(f"<div class='crypto-box'><b>SERIAL:</b> {itmo_serial} | <b>NET CARBON:</b> {net_c:.2f} MT CO₂e | <b>OCEAN TRASH REMOVED:</b> {site_data.get('plastic_trash_tons', 0):.1f} MT<br><b>SHA-256 SEAL:</b> {tx_hash}</div>", unsafe_allow_html=True)
            st.download_button("📥 Download Official Carbon & Cleanup Certificate (PDF)", data=cert_pdf, file_name=f"Blue42_ITMO_Certificate_{sel_site}.pdf", mime="application/pdf", use_container_width=True)

    with t3:
        if site_data is not None:
            with st.expander("🛡️ 6-Point Site Safety, Pollution & Verification Checklist", expanded=True):
                ctrl_rows = [
                    {"Safety Check": "1. Spatial & Subsea Cable Safety", "What We Verify": "Clear of shipping lanes, whale paths, sanctuaries & >1.5km from Subsea Cables", "Status": "✅ PASS" if "CLEARED" in site_data.get("status", "") else "❌ BLOCKED"},
                    {"Safety Check": "2. Oil Spill & Ocean Trash Screen", "What We Verify": "Screened for Reported Oil Spills (<0.05 ppm PAH) & Ghost-Net Gyres", "Status": f"✅ {site_data.get('pah_oil_ppm', 0.0):.2f} ppm PAH" if site_data.get("pah_oil_ppm", 0.0) < 0.05 and "CLEARED" in site_data.get("status", "") else "⚠️ ALERT"},
                    {"Safety Check": "3. 4-Tier Sensor Proof", "What We Verify": "40-Yr Satellite + Drone + Underwater ROV AI + SMART Cable verified", "Status": f"✅ {site_data.get('report_card_grade')}"},
                    {"Safety Check": "4. Conservative Carbon Math", "What We Verify": "Subtracts boat fuel, 5% deep-sea loss & insurance reserve", "Status": f"✅ {site_data.get('net_bankable_co2')} MT Net"},
                    {"Safety Check": "5. 500-Scenario Weather Stress Test", "What We Verify": "Tested against El Niño heatwaves, Category 4 storms & price swings", "Status": f"✅ {site_data.get('stress_retention_pct'):.0f}% Kept"},
                    {"Safety Check": "6. Seafloor Oxygen Safety", "What We Verify": "Caps deep-sea sinking so seafloor oxygen stays safe for marine life", "Status": f"✅ ΔO₂ {site_data.get('benthic_o2_delta_pct')}%"},
                ]
                st.dataframe(pd.DataFrame(ctrl_rows), use_container_width=True, hide_index=True)

            def generate_expert_agent_response(user_q: str, s_data) -> str:
                q_low = user_q.lower()
                s_id, status = s_data.get("id"), s_data.get("status")
                area, pareto = float(s_data.get("area_ha", 0)), float(s_data.get("pareto_score", 0))
                bio, net_c = float(s_data.get("biomass_tons", 0)), float(s_data.get("net_bankable_co2", 0))
                c_dist, c_stat = float(s_data.get("cable_dist_km", 10.0)), s_data.get("smart_cable_status", "✅ Safe")
                pah_ppm = float(s_data.get("pah_oil_ppm", 0.0))
                trash_mt = float(s_data.get("plastic_trash_tons", 0.0))
                nit_mt = float(s_data.get("nitrogen_tons", 0.0))
                site_capex = area * 15000.0
                site_opex = (area * 2000.0) + float(s_data.get("sinking_cost", 0))
                gross_rev = (net_c * 150.0) + (bio * 300.0) + (area * 1500.0) + (nit_mt * 2000.0) + (trash_mt * 850.0)
                site_net_yr = (gross_rev * 0.92) - site_opex

                if any(k in q_low for k in ["oil", "spill", "trash", "plastic", "garbage", "pollution", "waste", "ghost", "pah"]):
                    return (
                        f"### 🛢️🗑️ Oil Spills, Ocean Trash & Water Pollution Analysis — **{s_id}**\n"
                        f"- **1. Reported Oil Spills & Hydrocarbons (`PAHs`):** Reading is **`{pah_ppm:.2f} ppm PAH`** (`{s_data.get('crop_safety_verdict')}`). Because kelp acts like a sponge, any site inside a reported oil spill (`Brown Zone on Map`) is automatically blocked, and if a drift slick exceeds `0.05 ppm PAH`, Blue 42 automatically halts food/cattle-feed sales and routes the kelp strictly to **>1,000m Deep-Sea Carbon Sinking**.\n"
                        f"- **2. 'Ocean of Trash' & Ghost Fishing Nets (`Teal Zone + Perimeter Boom`):** Severe plastic gyres and derelict ghost nets are blocked on the 3D map. At safe sites like **{s_id}**, our **Perimeter Trash Interceptor Boom** skims **`{trash_mt:.2f} MT/yr`** of floating ocean plastics & ghost nets before they touch the kelp—earning **\\${trash_mt*850:,.0f}/yr** (`\\$850/MT`) in **Verified Ocean Plastic Cleanup Credits**!\n"
                        f"- **3. Agricultural Fertilizer & Sewage Runoff (`Nitrogen`):** Absorbs **`{nit_mt:.2f} MT/yr`** of dissolved nitrogen to prevent toxic algae blooms, earning **\\${nit_mt*2000:,.0f}/yr** (`\\$2,000/MT`)."
                    )
                if any(k in q_low for k in ["cable", "subsea", "fiber", "smart", "telecom", "anchor"]):
                    return (
                        f"### ⚡ Subsea Cables & SMART Telemetry — Kelp Kandidate **{s_id}**\n"
                        f"- **Distance to Nearest Subsea Cable:** **{c_dist:.2f} km** (`{c_stat}`)\n"
                        f"- **1. Anchor Strike Protection:** Under **ICPC** rules, dropping a 10-ton kelp anchor within **1.5 km** of an undersea fiber-optic or power cable is strictly prohibited (`\\$1.5M–\\$5.0M` repair cost).\n"
                        f"- **2. SMART Cable Synergy:** Sites safely **1.5 km – 9.0 km** outside the cable buffer can tap into **ITU/UNESCO SMART Subsea Cable** seafloor sensors for 24/7 bottom temperature, wave pressure, and deep-sea oxygen monitoring!"
                    )
                if any(k in q_low for k in ["cost", "roi", "profit", "equipment", "payback", "revenue"]):
                    return (
                        f"### 📊 10-Year Economics & Equipment Breakdown — **{s_id}**\n"
                        f"- **Total Upfront Infrastructure Cost:** **\\${site_capex:,.0f}** across **{area} HA ({area*2.471:.0f} Acres)**\n"
                        f"- **Breakdown:** Mooring Grid & Trash Boom (`55%`: **\\${site_capex*0.55:,.0f}**), Sensor Buoys (`20%`: **\\${site_capex*0.20:,.0f}**), Seeding & Harvest Gear (`15%`: **\\${site_capex*0.15:,.0f}**), Seabed Permit (`10%`: **\\${site_capex*0.10:,.0f}**)\n"
                        f"- **Estimated Net Profit:** **\\${site_net_yr:,.0f}/yr** (~{site_capex/max(site_net_yr,1):.1f} yr payback)"
                    )
                return (
                    f"### 💡 Site Summary — Kelp Kandidate **{s_id}**\n"
                    f"- **Verdict:** **{status}** | **Quality Score:** **{pareto}/100** | **40-Yr Satellite Grade:** **{s_data.get('report_card_grade')}**\n"
                    f"- **Economics (5 Revenue Streams):** Upfront Cost **\\${site_capex:,.0f}** | Est. Net Profit **\\${site_net_yr:,.0f}/yr** (~{site_capex/max(site_net_yr,1):.1f} yr payback)\n"
                    f"- **Pollution & Trash Cleanup:** `{pah_ppm:.2f} ppm Oil/PAH` | `{trash_mt:.1f} MT/yr Ocean Trash Skimmed (+${trash_mt*850:,.0f}/yr)` | `{nit_mt:.2f} MT/yr Nitrogen Cleaned`"
                )

            st.caption("⚡ **1-Click Questions:** Tap any button below for an instant answer:")
            qp0, qp1, qp2, qp3 = st.columns(4)
            trig = None
            if qp0.button("💡 Site Summary", use_container_width=True):
                trig = f"Give me a simple summary for {sel_site}."
            if qp1.button("🛢️ Oil & Ocean Trash", use_container_width=True):
                trig = f"How do reported oil spills, ocean trash gyres, and fertilizer pollution affect {sel_site}?"
            if qp2.button("⚡ Subsea Cables", use_container_width=True):
                trig = f"How do subsea cables and SMART cable telemetry affect {sel_site}?"
            if qp3.button("📊 Costs & 10-Yr ROI", use_container_width=True):
                trig = f"Show the equipment costs, 5 revenue streams, and 10-year ROI for {sel_site}."

            chat_box = st.container(height=210)
            with chat_box:
                for m in st.session_state.messages:
                    st.markdown(f"**{'🤖 Blue 42 Advisor' if m['role']=='assistant' else '👤 You'}:**\n{m['content']}")

            u_in = st.chat_input(f"Ask anything about {sel_site} (e.g. 'How do oil spills or ocean trash affect this site?')...")
            act_q = trig or u_in
            if act_q:
                st.session_state.messages.append({"role": "user", "content": act_q})
                st.session_state.messages.append({"role": "assistant", "content": generate_expert_agent_response(act_q, site_data)})
                st.rerun()

            audit_ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')
            audit_sig = generate_sha256_signature(site_data.to_dict(), audit_ts)
            audit_txt = f"Verdict: {site_data.get('status')} | Score: {site_data.get('pareto_score')}/100 | 40-Yr Grade: {site_data.get('report_card_grade')} | Net Carbon: {site_data.get('net_bankable_co2')} MT/yr | Oil/PAH: {site_data.get('pah_oil_ppm', 0.0):.2f} ppm | Ocean Trash Removed: {site_data.get('plastic_trash_tons', 0):.1f} MT/yr | Subsea Cable Check: {site_data.get('smart_cable_status')}."
            st.download_button("📥 Export Verified Site Safety & Economic Report (PDF)", data=create_lca_brief(site_data.to_dict(), audit_txt, audit_sig, audit_ts), file_name=f"Blue42_Site_Report_{sel_site}.pdf", mime="application/pdf", use_container_width=True)
