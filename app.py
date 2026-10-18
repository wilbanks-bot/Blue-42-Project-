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
    out.extend(f"xref
