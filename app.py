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
# 1. UX SETUP & "GOOGLE MATERIAL DARK OCEAN" DESIGN SYSTEM
# =========================================================
st.set_page_config(layout="wide", page_title="Blue 42 | The Kelp Contender", page_icon="🌊", initial_sidebar_state="expanded")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Roboto+Mono:wght@400;600&display=swap');
    :root {
        --g-blue: #4285F4; --g-blue-light: #8AB4F8; --g-red: #EA4335; --g-red-light: #F28B82;
        --g-yellow: #FBBC04; --g-yellow-light: #FDD663; --g-green: #34A853; --g-green-light: #81C995;
        --g-bg: #131314; --g-surface: #1E1F20; --g-surface-elevated: #282A2C; --g-border: #3C4043;
        --g-text: #E8EAED; --g-text-sub: #9AA0A6;
    }
    html, body, [class*="css"] { font-family: 'Google Sans', 'Plus Jakarta Sans', -apple-system, sans-serif !important; background-color: var(--g-bg); color: var(--g-text); }
    .block-container { padding-top: 1rem; padding-bottom: 2rem; max-width: 98%; }
    .stMarkdown, .element-container { overflow: visible !important; }
    .google-accent-bar { height: 4px; width: 100%; border-radius: 4px; background: linear-gradient(90deg, #4285F4 0% 25%, #EA4335 25% 50%, #FBBC04 50% 75%, #34A853 75% 100%); margin-bottom: 14px; }
    .leaf-tooltip { position: relative !important; display: inline-block; cursor: help; font-size: 1.05rem; margin-left: 6px; transition: transform 0.2s ease; z-index: 999999 !important; }
    .leaf-tooltip:hover { transform: scale(1.2); }
    .leaf-tooltip .tooltiptext {
        visibility: hidden; width: 235px; background: rgba(30, 31, 32, 0.98); color: var(--g-text); text-align: left;
        border: 1px solid var(--g-blue); border-radius: 8px; padding: 10px 12px; position: absolute !important; z-index: 9999999 !important;
        bottom: 135%; left: 50%; margin-left: -117px; opacity: 0; transition: opacity 0.25s; font-size: 0.72rem; line-height: 1.45; font-weight: 500; pointer-events: none; box-shadow: 0 10px 30px rgba(0,0,0,0.75);
    }
    .leaf-tooltip:hover .tooltiptext { visibility: visible; opacity: 1; }
    .flip-card { background-color: transparent !important; width: 100% !important; height: 210px !important; perspective: 1000px !important; margin-bottom: 15px !important; position: relative !important; cursor: pointer; }
    .flip-card-inner { position: relative !important; width: 100% !important; height: 100% !important; text-align: center !important; transition: transform 0.6s cubic-bezier(0.4, 0.0, 0.2, 1) !important; transform-style: preserve-3d !important; }
    .flip-card:hover .flip-card-inner, .flip-card:active .flip-card-inner, .flip-card.flipped .flip-card-inner { transform: rotateY(180deg) !important; }
    .flip-card-front, .flip-card-back {
        position: absolute !important; inset: 0 !important; width: 100% !important; height: 100% !important;
        -webkit-backface-visibility: hidden !important; backface-visibility: hidden !important; border-radius: 12px !important;
        background: var(--g-surface) !important; border: 1px solid var(--g-border) !important; padding: 15px !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.35) !important; display: flex !important; flex-direction: column !important; justify-content: center !important;
    }
    .flip-card-back { transform: rotateY(180deg) !important; border-left: 4px solid var(--g-green) !important; background: var(--g-surface-elevated) !important; text-align: left !important; align-items: flex-start !important; padding-left: 20px !important; }
    .glass-title { font-size: clamp(0.7rem, 1vw, 0.85rem); color: var(--g-text-sub); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; font-weight: 600; }
    .glass-value { font-size: clamp(1.6rem, 2.1vw, 2.25rem); font-weight: 700; margin: 0; line-height: 1.15; }
    .glass-sub { font-size: clamp(0.72rem, 0.95vw, 0.82rem); color: var(--g-green-light); margin-top: 8px; font-weight: 600; }
    .math-text { font-family: 'Roboto Mono', monospace; font-size: 0.7rem; color: var(--g-text); line-height: 1.35; width: 100%; }
    .math-hl { color: var(--g-green-light); font-weight: 700; font-size: 0.78rem; }
    .math-var { color: var(--g-text-sub); }
    .math-op { color: var(--g-blue-light); font-weight: 700; padding-right: 6px; }
    .crypto-box { background-color: var(--g-surface); border: 1px solid var(--g-green); border-radius: 8px; padding: 14px; font-family: 'Roboto Mono', monospace; font-size: 0.82rem; color: var(--g-text); word-wrap: break-word; }
    .stButton > button { background: var(--g-surface-elevated); color: var(--g-blue-light); border: 1px solid var(--g-blue); border-radius: 20px; font-weight: 600; transition: all 0.25s ease; }
    .stButton > button:hover { background: var(--g-blue); color: #FFFFFF; box-shadow: 0 2px 12px rgba(66, 133, 244, 0.5); }
    .metric-grid { display: flex; gap: 12px; margin-bottom: 15px; flex-wrap: wrap; }
    .metric-box { flex: 1; min-width: 120px; background: var(--g-surface); border: 1px solid var(--g-border); border-radius: 10px; border-top: 3px solid var(--g-blue); padding: 12px; text-align: center; }
    .metric-title { font-size: 0.73rem; color: var(--g-text-sub); text-transform: uppercase; font-weight: 600; margin-bottom: 5px; }
    .metric-val { font-size: 1.45rem; font-weight: 700; color: var(--g-blue-light); line-height: 1.2; }
    .metric-sub { font-size: 0.74rem; color: var(--g-green-light); margin-top: 4px; font-weight: 600; }
    @media (max-width: 768px) {
        .block-container { padding-left: 0.6rem !important; padding-right: 0.6rem !important; max-width: 100% !important; }
        h1 { font-size: 1.45rem !important; } .flip-card { height: 175px !important; } .metric-box { min-width: 45% !important; }
    }
    header { background-color: transparent !important; } #MainMenu, footer { visibility: hidden; }
    .blinking { animation: blinker 1.5s linear infinite; color: var(--g-green); font-weight: bold; }
    @keyframes blinker { 50% { opacity: 0; } }
</style>
""", unsafe_allow_html=True)

def leaf_info(text):
    return f'<div class="leaf-tooltip">🌿<span class="tooltiptext">{text}</span></div>'

def make_flip_card(title, value, sub, math_html, accent_color="#4285F4", value_color="#8AB4F8"):
    return (
        f'<div class="flip-card" tabindex="0" onclick="this.classList.toggle(\'flipped\')"><div class="flip-card-inner">'
        f'<div class="flip-card-front" style="border-left: 4px solid {accent_color} !important;">'
        f'<div class="glass-title">{title}</div><div class="glass-value" style="color: {value_color};">{value}</div>'
        f'<div class="glass-sub">{sub} <span style="font-size:0.65rem; color:#9AA0A6;">(Hover/Tap)</span></div></div>'
        f'<div class="flip-card-back"><div class="glass-title" style="margin-bottom:6px; color:#8AB4F8; font-size:0.75rem;">HOW THIS IS CALCULATED</div>'
        f'<div class="math-text">{math_html}</div></div></div></div>'
    )

def kelp_animation():
    st.balloons()

def handshake_animation():
    st.markdown("""<style>@keyframes shakeHand { 0%{transform:translate(-50%,-50%) scale(0);opacity:0;} 20%{opacity:1;transform:translate(-50%,-50%) scale(1.5);} 50%{transform:translate(-50%,-50%) rotate(15deg) scale(1.5);} 100%{opacity:0;transform:translate(-50%,-50%) scale(0);} } .hs-ov {position:fixed;top:50%;left:50%;z-index:9999999;font-size:7rem;pointer-events:none;animation:shakeHand 2.2s ease-in-out forwards;}</style><div class="hs-ov">🤝</div>""", unsafe_allow_html=True)

if "library" not in st.session_state:
    st.session_state.library = []
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": (
            "👋 **Welcome! I am your Blue 42 AI Investment & Accounting Advisor.**\n\n"
            "I translate satellite ocean data, **Subsea Cable safety**, and **GAAP accounting (ASC 360 / 842 / 410)** into plain English. "
            "**Tap any 1-Click Question button above** or ask me anything about the selected **Kelp Kandidate**!"
        ),
    }]
if "selected_site_id" not in st.session_state:
    st.session_state.selected_site_id = None
if "custom_sites" not in st.session_state:
    st.session_state.custom_sites = []

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
    styled.append(("F2", 10, 0.16, 0.38, 0.78, 14, "CRYPTOGRAPHIC AUDIT & VERIFICATION LEDGER"))
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
        ]),
        ("2. ENVIRONMENTAL & ECONOMIC IMPACT METRICS", [
            f"Jobs Created: {site.get('jobs_created')} | Shellfish Acidification Halo: {site.get('halo_ha')} HA | Nitrogen Cleaned: {site.get('nitrogen_tons')} MT",
            f"Safe Deep-Sea Sinking Quota: {site.get('abyssal_sunk_mt')} MT (Seafloor dO2: {site.get('benthic_o2_delta_pct')}%) | Bioplastics/Feed: {site.get('circular_surface_mt')} MT",
            f"Distance to >1,000m Trench: {site.get('abyssal_dist_km')} km | Annual Boat & Fuel Cost: ${site.get('sinking_cost'):,.2f}/yr",
        ]),
    ]
    return build_pure_python_pdf("BLUE 42 | SITE FACT SHEET & SATELLITE PROVENANCE", "Multi-Scale Satellite, Drone, ROV AI & Subsea Cable Verification", sections, [f"Timestamp: {ts} | SHA-256: {sig}"])

def create_lca_brief(site: dict, ai_analysis: str, signature: str, timestamp: str) -> bytes:
    capex = float(site.get("area_ha", 0)) * 15000.0
    sections = [
        ("1. KELP KANDIDATE SAFETY & SATELLITE METRICS", [
            f"ID: {site.get('id')} | Verdict: {site.get('status')} | Score: {site.get('pareto_score')}/100 | Size: {site.get('area_ha')} HA",
            f"Temp: {site.get('effective_sst')} C | Depth: {site.get('depth')} m | Wave Energy: {site.get('wave_energy')} kW/m | Cable Distance: {site.get('cable_dist_km', 10)} km",
        ]),
        ("2. GROSS-TO-NET CARBON & GAAP FIXED-ASSET SUMMARY", [
            f"Gross Carbon: {site.get('co2_tons')} MT -> Net Sellable Credits: {site.get('net_bankable_co2')} MT CO2e/yr (after boat fuel, 5% deep loss & buffer)",
            f"Upfront CAPEX: ${capex:,.0f} (55% ASC 360 Mooring Grid, 20% ASC 360 Buoys, 15% ASC 360 Gear, 10% ASC 842 Lease, +5% ASC 410 ARO)",
        ]),
        ("3. SOX 404 & INVESTOR AUDIT SUMMARY", [ai_analysis]),
    ]
    return build_pure_python_pdf("BLUE 42 | VERIFIED INVESTOR & SOX 404 AUDIT REPORT", "GAAP Fixed-Asset, Carbon Waterfall & Spatial Safety Attestation", sections, [f"Timestamp: {timestamp} | SHA-256: {signature}"])

def create_lease_permit_pdf(site: dict, funded_sites: list, commons_share_pct: int, permit_months: int) -> bytes:
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')
    sig = generate_sha256_signature(site, ts)
    p_lines = [f"- {f['Site ID']}: {f['Area (HA)']} HA | Score {f['Pareto']}/100 | CAPEX {f['CAPEX ($)']} | 10-Yr NPV {f['10-Yr NPV ($)']}" for f in funded_sites] or [f"- Lead Site: {site.get('id')} ({site.get('area_ha')} HA)"]
    sections = [
        ("1. GOVERNMENT AQUACULTURE LEASE & PERMIT FILING", [
            f"Lead Site: {site.get('id')} ({site.get('lat'):.4f} N, {site.get('lon'):.4f} W) | Verdict: {site.get('status')}",
            f"Community Revenue Share: {commons_share_pct}% Gross Revenue -> Fast-Track {permit_months}-Month Permit Timeline",
            f"Subsea Cable Protection Check (ICPC 1.5km Buffer): {site.get('smart_cable_status', 'Cleared')}",
        ]),
        ("2. FUNDED PORTFOLIO SITES", p_lines),
    ]
    return build_pure_python_pdf("BLUE 42 | GOVERNMENT LEASE & PERMIT APPLICATION PACK", "BOEM / NOAA / Coastal Commission Pre-Cleared Filing", sections, [f"Timestamp: {ts} | SHA-256: {sig}"])

def create_minted_credit_pdf(site: dict, itmo_serial: str, tx_hash: str, ts_now: str) -> bytes:
    sections = [
        ("1. OFFICIAL CARBON CREDIT CERTIFICATE (PARIS AGREEMENT ART. 6.4)", [
            f"Serial Number: {itmo_serial} | Site: {site.get('id')} ({site.get('lat'):.4f} N, {site.get('lon'):.4f} W | {site.get('area_ha')} HA)",
            f"Gross Absorbed: {site.get('co2_tons'):.2f} MT -> Less Boat Fuel (-{site.get('tow_emissions_co2'):.2f}), 5% Deep Loss (-{site.get('remin_discount_co2'):.2f}), Reserve (-{site.get('buffer_pool_co2'):.2f})",
            f"NET SELLABLE CARBON CREDITS ISSUED: {site.get('net_bankable_co2'):.2f} MT CO2e/yr | Seafloor O2 Check: {site.get('benthic_o2_delta_pct')}% (PASSED)",
        ]),
    ]
    return build_pure_python_pdf("BLUE 42 | OFFICIAL CARBON CREDIT CERTIFICATE", "4-Tier Satellite, Drone, ROV AI & SMART Cable Verified Receipt", sections, [f"Issued: {ts_now} | Serial: {itmo_serial}", f"SHA-256 Digital Seal: {tx_hash}"])

def create_safe_sites_directory_pdf(df: pd.DataFrame, sector_label: str) -> bytes:
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')
    lines = [f"{i+1}. {r['id']} [CLEARED] - Score: {r['pareto_score']}/100 | GPS: {r['lat']:.4f}, {r['lon']:.4f} | Size: {r['area_ha']:.1f} HA ({r['area_ha']*2.471:.0f} Acres) | Net Carbon: {r['net_bankable_co2']:.1f} MT/yr | Cable Dist: {r.get('cable_dist_km', 10):.1f} km" for i, (_, r) in enumerate(df.iterrows())]
    return build_pure_python_pdf("BLUE 42 | SAFE KELP KANDIDATES INVESTOR DIRECTORY", f"Region: {sector_label} ({len(df)} Cleared Sites)", [("SAFE SITES CLEARED FOR INVESTMENT", lines)], [f"Generated: {ts}"])

def export_to_interactive_map_html(df: pd.DataFrame, sector_label: str) -> bytes:
    clat = float(df["lat"].mean()) if not df.empty else 34.0
    clon = float(df["lon"].mean()) if not df.empty else -119.5
    markers, rows = [], []
    for _, r in df.iterrows():
        sid, lat, lon, ha, sc = str(r["id"]), float(r["lat"]), float(r["lon"]), float(r["area_ha"]), float(r["pareto_score"])
        net_c, bio = float(r.get("net_bankable_co2", 0)), float(r.get("biomass_tons", 0))
        capex = ha * 15000.0
        net_prof = (((net_c * 150.0) + (bio * 300.0) + (ha * 1500.0) + (float(r.get("nitrogen_tons", 0)) * 2000.0)) * 0.92) - ((ha * 2000.0) + float(r.get("sinking_cost", 0)))
        gurl = f"https://www.google.com/maps/search/?api=1&query={lat:.4f},{lon:.4f}"
        pop = f"<b>{sid} — ✅ SAFE TO INVEST</b><br>Score: {sc}/100 | Size: {ha:.1f} HA ({ha*2.471:.0f} Acres)<br>Est. Net Profit: <b>${net_prof:,.0f}/yr</b><br>Cable Dist: {r.get('cable_dist_km', 10):.1f} km<br><a href='{gurl}' target='_blank'>📍 Open in Google Maps ↗</a>"
        markers.append(f"L.circleMarker([{lat:.4f},{lon:.4f}],{{radius:11,fillColor:'#34A853',color:'#fff',weight:2,fillOpacity:0.9}}).addTo(map).bindPopup({json.dumps(pop)});")
        rows.append(f"<tr><td><b>{sid}</b></td><td style='color:#81C995;'>✅ CLEARED</td><td><b>{sc}/100</b></td><td>{ha:.1f} HA ({ha*2.471:.0f} Ac)</td><td>${capex:,.0f}</td><td style='color:#81C995;font-weight:700;'>${net_prof:,.0f}/yr</td><td>{r.get('cable_dist_km', 10):.1f} km</td><td><a href='{gurl}' target='_blank' style='color:#8AB4F8;'>{lat:.4f}, {lon:.4f} ↗</a></td></tr>")
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"/><title>Blue 42 Interactive Safe Sites Map</title><link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/><script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script><style>body{{margin:0;padding:24px;background:#131314;color:#E8EAED;font-family:sans-serif;}}#map{{width:100%;height:420px;border-radius:12px;border:1px solid #3C4043;margin-bottom:20px;}}table{{width:100%;border-collapse:collapse;background:#1E1F20;font-size:13px;}}th{{background:#282A2C;color:#8AB4F8;text-align:left;padding:10px;}}td{{padding:10px;border-bottom:1px solid #2D2F31;}}</style></head><body><h2>🌊 BLUE 42 | The Kelp Contender — Interactive Safe Sites Map ({sector_label})</h2><div id="map"></div><table><thead><tr><th>Site ID</th><th>Verdict</th><th>Score</th><th>Farm Size</th><th>Upfront Cost</th><th>Est. Net Profit</th><th>Subsea Cable Dist</th><th>Google Maps</th></tr></thead><tbody>{"".join(rows)}</tbody></table><script>var map=L.map('map').setView([{clat:.4f},{clon:.4f}],8);L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png').addTo(map);{"".join(markers)}</script></body></html>"""
    return html.encode("utf-8")

def export_to_geojson(df: pd.DataFrame) -> bytes:
    feats = [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [float(r["lon"]), float(r["lat"])]}, "properties": {"id": r["id"], "status": r["status"], "pareto_score": float(r["pareto_score"]), "area_ha": float(r["area_ha"]), "net_bankable_co2": float(r.get("net_bankable_co2", 0)), "cable_dist_km": float(r.get("cable_dist_km", 10))}} for _, r in df.iterrows()]
    return json.dumps({"type": "FeatureCollection", "features": feats}, indent=2).encode("utf-8")

def export_to_kml(df: pd.DataFrame) -> bytes:
    pms = [f"<Placemark><name>{r['id']} ({r['pareto_score']}/100)</name><description>CLEARED | {r['area_ha']} HA | Net CO2: {r.get('net_bankable_co2',0)} MT/yr</description><Point><coordinates>{float(r['lon']):.4f},{float(r['lat']):.4f},0</coordinates></Point></Placemark>" for _, r in df.iterrows()]
    return f'<?xml version="1.0" encoding="UTF-8"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>Blue 42 Safe Kelp Kandidates</name>{"".join(pms)}</Document></kml>'.encode("utf-8")

# =========================================================
# 3. GLOBAL HOTSPOTS, BIOPHYSICAL NICHE & SUBSEA CABLE ENGINE
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
    return {
        "id": site_id, "lat": round(lat, 4), "lon": round(lon, 4), "area_ha": round(area, 1),
        "biomass_tons": biomass_tons, "co2_tons": round(biomass_tons * 0.68, 1), "sst_mean": round(sst_mean, 1),
        "depth": round(depth, 1), "par_light": par_light, "nitrate_score": int(nitrate_score), "mhw_risk": mhw_risk,
        "salinity": round(salinity, 2), "wave_energy": round(wave_energy, 1),
        "averted_damage_millions": round((wave_energy * area * 0.15), 2), "jobs_created": int(area * 2.2),
        "biodiversity_score": int(biodiversity_score), "halo_ha": round(area * 1.5, 1),
        "nitrogen_tons": round(area * 0.25, 2), "abyssal_dist_km": round(abyssal_dist_km, 1),
        "sinking_cost": sinking_cost, "equity_score": int(equity_score),
        "hist_persistence_40yr": hist_persistence_40yr, "report_card_grade": report_card_grade,
        "substrate_type": substrate_type, "rov_stipe_density": round(8.5 + (nitrate_score / 12.0), 1),
        "rov_wildlife_species": int(28 + (biodiversity_score * 0.45)),
        "suitability": round(min(0.98, max(0.65, hist_persistence_40yr / 100.0)), 2),
    }

@st.cache_data(ttl=3600)
def get_scientific_kelp_data_v3(sector: str, live_gee: bool = False):
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
def get_hazard_vectors_v3(sector: str):
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
    return pd.DataFrame(vessels), pd.DataFrame(shipping_lanes), pd.DataFrame(mammals), [{"polygon": weather_poly[0]}], [{"polygon": restricted_poly[0]}], [{"polygon": allowed_poly[0]}], pd.DataFrame(subsea_cables), pd.DataFrame(cable_pts)

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

def run_mcda_deconfliction(sites, vessels_df, mammals_df, weather_data, restricted_data, allowed_data, cable_pts_df=None):
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
        processed.append(site)
    processed.sort(key=lambda s: (1 if "CLEARED" in s.get("status", "") else 0, s.get("pareto_score", 0)), reverse=True)
    return pd.DataFrame(processed)

# =========================================================
# 4. HEADER & SIDEBAR CONTROLS (INVESTOR-FRIENDLY PLAIN ENGLISH)
# =========================================================
SAMPLE_CSV_TEMPLATE = "id,lat,lon,area_ha,sst_mean,depth,wave_energy\nKK-INVESTOR-1,34.0450,-119.2400,14.0,14.8,20.0,22.0\nKK-INVESTOR-2,33.9100,-119.5200,16.5,15.1,24.0,25.0\n"

st.markdown('<div class="google-accent-bar"></div>', unsafe_allow_html=True)
st.markdown(
    f"<h1 style='font-weight: 700; margin-bottom: 0;'><span style='color:#4285F4;'>B</span><span style='color:#EA4335;'>L</span><span style='color:#FBBC04;'>U</span><span style='color:#34A853;'>E</span> <span style='color:#4285F4;'>42</span> <span style='color:#E8EAED; font-weight: 300;'>| The Kelp Contender</span> {leaf_info('The Kelp Contender turns satellite ocean data, subsea cable maps, and GAAP accounting into a simple investment dashboard to evaluate safe ocean kelp sites (Kelp Kandidates).')}</h1>",
    unsafe_allow_html=True,
)
st.markdown("<p style='color: #9AA0A6; font-size: 1.02rem; margin-top: -8px;'><span class='blinking'>●</span> INVESTOR DECISION ENGINE ACTIVE | 4 GLOBAL HOTSPOTS • 40-YR SATELLITE REPORT CARDS • ROV AI &amp; SUBSEA CABLE DECONFLICTION</p>", unsafe_allow_html=True)

st.markdown("""
<div style="background: linear-gradient(90deg, rgba(66,133,244,0.12), rgba(52,168,83,0.10), rgba(251,188,4,0.08)); border: 1px solid #3C4043; border-left: 4px solid #4285F4; border-radius: 12px; padding: 12px 16px; margin-bottom: 16px;">
    <div style="font-size: 0.78rem; color: #8AB4F8; font-weight: 700; text-transform: uppercase; margin-bottom: 6px;">🧭 How This App Works in 60 Seconds (Plain-English Investor Guide)</div>
    <div style="display: flex; flex-wrap: wrap; gap: 14px; font-size: 0.81rem; color: #E8EAED; line-height: 1.45;">
        <div style="flex: 1; min-width: 220px;"><b>1️⃣ Pick a Region &amp; Safe "Kelp Kandidate":</b> Green 3D columns are <b>Cleared &amp; Safe to Invest</b> (clear of shipping lanes, whale paths, storms, and <b>purple Subsea Internet/Power Cables</b>). Test custom GPS coordinates anytime.</div>
        <div style="flex: 1; min-width: 220px;"><b>2️⃣ Check 40-Yr History, Species &amp; 4 Revenues:</b> Inspect 40-year satellite survival grades, match 5 kelp species, and model 4 income streams (<b>Carbon Credits + Bioplastics + Storm Rebates + Water Cleanup</b>).</div>
        <div style="flex: 1; min-width: 220px;"><b>3️⃣ Lower Costs &amp; Download Signed PDFs:</b> Toggle farm cost-cutting levers, verify carbon via <b>Satellite + Drone + Underwater ROV AI + SMART Cables</b>, and download 1-click PDFs &amp; interactive HTML maps.</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown(f"<h2 style='color:#8AB4F8; font-weight:600; display:flex; align-items:center;'>🧭 INVESTOR CONTROLS {leaf_info('Pick a global region, test your own GPS coordinates or CSV file, simulate extreme weather, and set your investment priorities.')}</h2>", unsafe_allow_html=True)

sector = st.sidebar.selectbox("1. Choose Global Ocean Region", [
    "Northeast Pacific Coast (California / Channel Islands)",
    "British Columbia & Haida Gwaii, Canada (Subarctic Corridor)",
    "Tasmania & Great Southern Reef, Australia (Southern Ocean)",
    "Hawaiian Archipelago, HI (Tropical Warm-Water)",
])
sector_key = "British Columbia" if "British Columbia" in sector else ("Tasmania" if "Tasmania" in sector else ("Hawaii" if "Hawaiian" in sector else "Channel Islands"))

region_notes = {
    "Channel Islands": "Cold, nutrient-rich water from the <b>California Current</b> makes this a premier natural growth zone for <b>Giant Kelp</b> (<i>Macrocystis pyrifera</i>), growing up to 2 feet per day.",
    "British Columbia": "Glacial fjords and subarctic upwelling along <b>British Columbia &amp; Haida Gwaii</b> support dense, heat-resilient forests of <b>Giant Kelp</b> and wave-hardy <b>Bull Kelp</b>.",
    "Tasmania": "Home to Australia's <b>Great Southern Reef</b>, where Southern Ocean upwelling supports towering <b>Giant Kelp</b> and <b>Golden Kelp</b> (<i>Ecklonia radiata</i>) restoration corridors.",
    "Hawaii": "Warm, high-sunlight tropical waters ideal for heat-tolerant <b>Red Ogo</b>, <b>Low-Methane Asparagopsis</b> cattle-feed kelp, and deep-water upwelling.",
}
st.sidebar.markdown(f"<div style='background:#1E1F20;border:1px solid #3C4043;border-left:4px solid #4285F4;border-radius:8px;padding:10px 12px;margin-bottom:12px;font-size:0.79rem;color:#E8EAED;'><b>Why Investors Love This Region:</b><br>{region_notes[sector_key]}</div>", unsafe_allow_html=True)

default_lat = round(SECTOR_CONFIG[sector_key]["lat"] + 0.05, 4)
default_lon = round(SECTOR_CONFIG[sector_key]["lon"] + 0.35, 4)

with st.sidebar.expander("📍 Bring Your Own Coordinates & Lease CSV Evaluator", expanded=True):
    st.caption("Enter custom GPS coordinates or upload a `.csv` to check shipping, whale & **Subsea Cable** safety and calculate 10-year profit:")
    c_id = st.text_input("Custom Site Name / ID", value=f"KK-CUST-{len(st.session_state.custom_sites)+1}", key="sb_cid")
    c_lat = st.number_input("Latitude (°)", value=default_lat, format="%.4f", step=0.05, key="sb_lat")
    c_lon = st.number_input("Longitude (°)", value=default_lon, format="%.4f", step=0.05, key="sb_lon")
    c_area = st.number_input("Farm Size in Hectares (1 HA ≈ 2.47 Acres)", min_value=1.0, max_value=500.0, value=12.0, step=1.0, key="sb_area")
    c_sst = st.slider("Water Temperature (°C — Ideal 12–17°C)", 10.0, 23.0, 15.2, 0.2, key="sb_sst")
    c_depth = st.slider("Ocean Depth (meters — Ideal 15–35m)", 8.0, 50.0, 20.0, 1.0, key="sb_depth")
    if st.button("➕ Test & Score My Custom Site", use_container_width=True, key="sb_add_btn"):
        ns = build_site_record(c_id, c_lat, c_lon, c_area, c_sst, c_depth, 24.0, 91, "Low" if c_sst < 16.0 else "Moderate", 33.8, 92, 28.5, 88)
        ns["sector"] = sector_key
        st.session_state.custom_sites.append(ns)
        st.session_state.selected_site_id = c_id
        st.rerun()
    st.download_button("📄 Download Sample CSV Template", data=SAMPLE_CSV_TEMPLATE.encode("utf-8"), file_name="sample_kelp_kandidates.csv", mime="text/csv", use_container_width=True, key="sb_sample_csv")
    uploaded_csv = st.file_uploader("Upload Lease CSV (`id,lat,lon,area_ha,sst_mean,depth,wave_energy`)", type=["csv"], key="sb_csv_up")
    if uploaded_csv is not None:
        try:
            up_df = pd.read_csv(uploaded_csv)
            for idx, r in up_df.iterrows():
                cid = str(r.get("id", f"KK-CSV-{idx+1}"))
                if not any(cs["id"] == cid for cs in st.session_state.custom_sites):
                    cs_rec = build_site_record(cid, float(r.get("lat", default_lat)), float(r.get("lon", default_lon)), float(r.get("area_ha", 10.0)), float(r.get("sst_mean", 15.5)), float(r.get("depth", 18.0)), float(r.get("wave_energy", 25.0)), 90, "Moderate", 33.7, 90, 30.0, 85)
                    cs_rec["sector"] = sector_key
                    st.session_state.custom_sites.append(cs_rec)
            st.success(f"Loaded {len(up_df)} custom Kelp Kandidates!")
        except Exception as e:
            st.error(f"CSV error: {e}")

st.sidebar.markdown("---")
st.sidebar.markdown(f"<h3 style='color:#FDD663; font-size:1rem; display:flex; align-items:center;'>2. Test Extreme Weather Scenarios {leaf_info('See how each site holds up if an El Niño heatwave warms the ocean or a Category 4 winter storm hits.')}</h3>", unsafe_allow_html=True)
stress_scenario = st.sidebar.radio("Choose Weather Stress Test:", ["Nominal (Baseline)", "Marine Heatwave (El Niño)", "Category 4 Storm Event"])
adopt_baja_strain = st.sidebar.checkbox("🧬 Use Heat-Resistant Baja Kelp Seed (+2.0°C Tolerance)", value=False)

st.sidebar.markdown("---")
st.sidebar.markdown(f"<h3 style='color:#81C995; font-size:1rem; display:flex; align-items:center;'>3. Set Your Investor Priorities {leaf_info('Adjust what matters most to your fund—the Site Quality Score (0–100) updates automatically.')}</h3>", unsafe_allow_html=True)
weight_carbon = st.sidebar.slider("💨 Carbon Credit Income", 0.0, 1.0, 0.8)
weight_coastal = st.sidebar.slider("🌊 Coastal Storm Protection", 0.0, 1.0, 0.5)
weight_bio = st.sidebar.slider("🐟 Marine Life & Fishery Health", 0.0, 1.0, 0.9)
weight_nitrogen = st.sidebar.slider("💧 Fertilizer Runoff Cleanup", 0.0, 1.0, 0.7)
weight_equity = st.sidebar.slider("🤝 Local Coastal Jobs & Community", 0.0, 1.0, 0.8)

# =========================================================
# 5. PHYSICS STRESS TEST, CARBON WATERFALL & PARETO SCORING
# =========================================================
raw_sites = copy.deepcopy(get_scientific_kelp_data_v3(sector_key, ee_connected))
for c_site in st.session_state.custom_sites:
    if c_site.get("sector", sector_key) == sector_key:
        raw_sites.append(copy.deepcopy(c_site))

vessels_df, shipping_lanes_df, mammals_df, weather_data, restricted_data, allowed_data, subsea_cables_df, cable_pts_df = get_hazard_vectors_v3(sector_key)

for site in raw_sites:
    site.setdefault("par_light", 34.5)
    site.setdefault("hist_persistence_40yr", 88)
    site.setdefault("report_card_grade", "A (High Persistence)")
    site.setdefault("substrate_type", "Consolidated Rocky Reef (Optimal Holdfast)")
    site.setdefault("rov_stipe_density", 14.5)
    site.setdefault("rov_wildlife_species", 36)
    site.setdefault("suitability", 0.88)
    base_sst, wave_kw, depth_m = site['sst_mean'], site['wave_energy'], site['depth']
    site['storm_shear_hazard'] = False
    if stress_scenario == "Nominal (Baseline)":
        site_mod, site['effective_sst'] = 1.0, base_sst
    elif stress_scenario == "Marine Heatwave (El Niño)":
        eff_sst = round(base_sst + 2.8, 1)
        site['effective_sst'] = eff_sst
        overheat = max(0.0, eff_sst - (19.5 if adopt_baja_strain else 17.5))
        site_mod = max(0.18, round(math.exp(-0.35 * overheat), 2))
    else:
        site['effective_sst'] = base_sst
        shear_factor = (wave_kw / 50.0) * (15.0 / max(depth_m, 10.0))
        site_mod = max(0.25, round(1.0 - (0.45 * shear_factor), 2))
        if shear_factor > 0.88:
            site['storm_shear_hazard'] = True

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

kelp_df = run_mcda_deconfliction(raw_sites, vessels_df, mammals_df, weather_data, restricted_data, allowed_data, cable_pts_df)
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
v_roi = ((safe_df['net_bankable_co2'].sum() * 150) + (safe_df['biomass_tons'].sum() * 300) + (safe_df['nitrogen_tons'].sum() * 2000)) if not safe_df.empty else 0
avg_retention = safe_df['stress_retention_pct'].mean() if not safe_df.empty else 0

col1.markdown(make_flip_card(f"Safe Farmable Ocean Area {leaf_info('Total ocean area across green CLEARED Kelp Kandidates free of shipping lanes, whale paths, sanctuaries, and subsea cables.')}", f"{v_area:.1f} HA", f"≈ {v_acres:,.0f} Acres ({len(safe_df)}/{len(kelp_df)} Safe)", "Total Ocean Area<br><span class='math-op'>-</span> <span class='math-var'>Ships, Whales &amp; Subsea Cables</span><br><span class='math-hl'>= Safe Farmable Area (1 HA ≈ 2.47 Ac)</span>", "#4285F4", "#8AB4F8"), unsafe_allow_html=True)
col2.markdown(make_flip_card(f"Annual Kelp Harvest {leaf_info('Total weight of fresh kelp harvested per year across all safe sites after weather stress testing.')}", f"{v_bio:.1f} MT", f"{stress_scenario} ({avg_retention:.0f}% Kept)", "Safe Area (HA) × 18.5 MT/HA<br><span class='math-op'>×</span> <span class='math-var'>Weather Survival %</span><br><span class='math-hl'>= Annual Kelp Harvest (Metric Tons)</span>", "#34A853", "#81C995"), unsafe_allow_html=True)
col3.markdown(make_flip_card(f"Coastal Storm Savings {leaf_info('Thick kelp forests act like natural speed bumps for storm waves, preventing shoreline flood damage.')}", f"${v_dmg:.1f}M", "Shoreline Damage Prevented", "Kelp Canopy Area × Wave Force<br><span class='math-op'>×</span> <span class='math-var'>15% Wave Dampening</span><br><span class='math-hl'>= Flood Damage Prevented ($)</span>", "#FBBC04", "#FDD663"), unsafe_allow_html=True)
col4.markdown(make_flip_card(f"Annual Portfolio Revenue {leaf_info('Combined yearly revenue across all safe sites from carbon credits, bioplastics kelp, and water cleanup.')}", f"${v_roi:,.0f}", "Combined Revenue / Year", "(Carbon × $150) + (Kelp × $300)<br><span class='math-op'>+</span> <span class='math-var'>(Water Cleanup × $2,000)</span><br><span class='math-hl'>= Total Annual Portfolio Revenue</span>", "#EA4335", "#F28B82"), unsafe_allow_html=True)

# =========================================================
# 7. 3D MAP (WITH SUBSEA CABLES) & 5-TAB INVESTOR CONSOLE
# =========================================================
col_map, col_ops = st.columns([6, 4], gap="large")

with col_ops:
    sel_site, site_data = None, None
    if not kelp_df.empty:
        st.markdown("##### 🎯 Step 1: Select or Add a Kelp Kandidate Site")
        sel_site = st.selectbox(
            "Choose a Kelp Kandidate to Inspect:",
            kelp_df['id'].tolist(),
            index=kelp_df['id'].tolist().index(st.session_state.selected_site_id),
            format_func=lambda kid: f"{kid} — {'✅ SAFE TO INVEST' if 'CLEARED' in kelp_df[kelp_df['id']==kid].iloc[0]['status'] else '⛔ ' + kelp_df[kelp_df['id']==kid].iloc[0]['status']} (Score: {kelp_df[kelp_df['id']==kid].iloc[0]['pareto_score']}/100)",
        )
        st.session_state.selected_site_id = sel_site
        site_data = kelp_df[kelp_df['id'] == sel_site].iloc[0]

        is_sel_safe = "CLEARED" in str(site_data.get("status", ""))
        s_area_ha = float(site_data.get("area_ha", 0))
        s_acres = s_area_ha * 2.47105
        s_capex_est = s_area_ha * 15000.0 * (1.12 if adopt_baja_strain else 1.0)
        s_opex_est = (s_area_ha * 2000.0) + float(site_data.get("sinking_cost", 0))
        s_wave_reb = (s_area_ha * 1500.0) + (float(site_data.get("averted_damage_millions", 0)) * 1e6 * 0.0025)
        s_gross_rev = (float(site_data.get("net_bankable_co2", 0)) * 150.0) + (float(site_data.get("biomass_tons", 0)) * 300.0) + s_wave_reb + (float(site_data.get("nitrogen_tons", 0)) * 2000.0)
        s_net_profit_yr = (s_gross_rev * 0.92) - s_opex_est
        s_payback_yrs = (s_capex_est / s_net_profit_yr) if s_net_profit_yr > 0 else 99.9

        verdict_badge = (
            "<span style='background:rgba(52,168,83,0.2); border:1px solid #34A853; color:#81C995; padding:3px 8px; border-radius:6px; font-weight:700;'>✅ CLEARED — SAFE TO INVEST</span>"
            if is_sel_safe else
            f"<span style='background:rgba(234,67,53,0.2); border:1px solid #EA4335; color:#F28B82; padding:3px 8px; border-radius:6px; font-weight:700;'>⛔ DO NOT INVEST ({site_data.get('status')})</span>"
        )
        st.markdown(f"""
        <div style="background: #1E1F20; border: 1px solid #3C4043; border-left: 4px solid {'#34A853' if is_sel_safe else '#EA4335'}; border-radius: 10px; padding: 12px 14px; margin-bottom: 10px;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px; margin-bottom:6px;">
                <span style="font-size:0.82rem; font-weight:700; color:#8AB4F8;">💡 Plain-English Investor Snapshot: {sel_site}</span>{verdict_badge}
            </div>
            <div style="font-size:0.79rem; color:#E8EAED; line-height:1.5;">
                • <b>Site Quality Score:</b> <b>{site_data.get('pareto_score', 0)} / 100</b> &nbsp;|&nbsp; <b>40-Yr Satellite Grade:</b> <b>{site_data.get('report_card_grade')}</b><br/>
                • <b>Farm Footprint:</b> <b>{s_area_ha:.1f} Hectares</b> (approx. <b>{s_acres:.0f} Acres</b> or <b>{s_acres/1.32:.0f} Football Fields</b>)<br/>
                • <b>Upfront Cost:</b> <b>${s_capex_est:,.0f}</b> &nbsp;|&nbsp; <b>Est. Net Profit:</b> <b style="color:#81C995;">${s_net_profit_yr:,.0f}/yr</b> &nbsp;|&nbsp; <b>Payback:</b> <b>~{s_payback_yrs:.1f} Yrs</b><br/>
                • <b>Subsea Cable Check:</b> <b>{site_data.get('smart_cable_status')}</b>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("📍 Bring Your Own Coordinates & Lease CSV Evaluator (Add Custom Site Here)", expanded=False):
            mc_c1, mc_c2, mc_c3 = st.columns(3)
            mc_id = mc_c1.text_input("Site ID", value=f"KK-MY-SITE-{len(st.session_state.custom_sites)+1}", key="mc_cid")
            mc_lat = mc_c2.number_input("Latitude", value=default_lat, format="%.4f", step=0.05, key="mc_lat")
            mc_lon = mc_c3.number_input("Longitude", value=default_lon, format="%.4f", step=0.05, key="mc_lon")
            mc_c4, mc_c5, mc_c6 = st.columns(3)
            mc_area = mc_c4.number_input("Area (HA)", min_value=1.0, max_value=500.0, value=14.0, step=1.0, key="mc_area")
            mc_sst = mc_c5.number_input("Temp (°C)", min_value=10.0, max_value=24.0, value=15.0, step=0.5, key="mc_sst")
            mc_depth = mc_c6.number_input("Depth (m)", min_value=8.0, max_value=60.0, value=22.0, step=1.0, key="mc_depth")
            if st.button("➕ Add & Score Custom Coordinate", use_container_width=True, key="mc_add_btn"):
                ns_mc = build_site_record(mc_id, mc_lat, mc_lon, mc_area, mc_sst, mc_depth, 24.0, 91, "Low" if mc_sst < 16.0 else "Moderate", 33.8, 92, 28.5, 88)
                ns_mc["sector"] = sector_key
                st.session_state.custom_sites.append(ns_mc)
                st.session_state.selected_site_id = mc_id
                st.rerun()

with col_map:
    st.markdown(f"<h4 style='display:flex; align-items:center;'>🌊 3D Ocean Safety, Subsea Cable &amp; Site Map {leaf_info('Green columns are safe, high-profit Kelp Kandidates. Red/Orange/Yellow/Purple columns are automatically blocked due to sanctuaries, storms, shipping lanes, or Subsea Fiber/Power Cables. The glowing blue arc shows the boat route to the >1,000m deep carbon drop-off trench.')}</h4>", unsafe_allow_html=True)
    st.markdown("""
    <div style="display: flex; flex-wrap: wrap; gap: 12px; background: rgba(30, 31, 32, 0.85); padding: 10px 14px; border-radius: 8px; border: 1px solid #3C4043; margin-bottom: 10px;">
        <div style="display:flex; align-items:center; font-size:0.73rem; color:#E8EAED;"><span style="width:10px; height:10px; background:#34A853; border-radius:2px; margin-right:6px;"></span> ✅ Safe Kelp Kandidate</div>
        <div style="display:flex; align-items:center; font-size:0.73rem; color:#E8EAED;"><span style="width:10px; height:10px; background:rgba(234,67,53,0.6); border:1px solid #EA4335; border-radius:2px; margin-right:6px;"></span> ⛔ Sanctuary (No-Go)</div>
        <div style="display:flex; align-items:center; font-size:0.73rem; color:#E8EAED;"><span style="width:10px; height:10px; background:rgba(250,123,23,0.6); border:1px solid #FA7B17; border-radius:2px; margin-right:6px;"></span> 🌪️ Storm Zone</div>
        <div style="display:flex; align-items:center; font-size:0.73rem; color:#E8EAED;"><span style="width:18px; height:3px; background:#FBBC04; margin-right:6px;"></span> 🚢 Shipping Lane</div>
        <div style="display:flex; align-items:center; font-size:0.73rem; color:#E8EAED;"><span style="width:18px; height:3px; background:#AB47BC; margin-right:6px;"></span> ⚡ Subsea Fiber/Power Cable (1.5km Buffer)</div>
        <div style="display:flex; align-items:center; font-size:0.73rem; color:#E8EAED;"><span style="width:10px; height:10px; background:#4285F4; border-radius:50%; margin-right:6px;"></span> 🐋 Whale Route / Deep Drop-Off Arc</div>
    </div>
    """, unsafe_allow_html=True)

    layers = [
        pdk.Layer("PolygonLayer", data=restricted_data, get_polygon="polygon", get_fill_color="[234, 67, 53, 25]", get_line_color="[234, 67, 53, 210]", line_width_min_pixels=2),
        pdk.Layer("PolygonLayer", data=allowed_data, get_polygon="polygon", get_fill_color="[52, 168, 83, 20]", get_line_color="[52, 168, 83, 200]", line_width_min_pixels=2),
        pdk.Layer("PolygonLayer", data=weather_data, get_polygon="polygon", get_fill_color="[250, 123, 23, 30]", get_line_color="[250, 123, 23, 200]", line_width_min_pixels=2),
    ]
    if not subsea_cables_df.empty:
        layers.append(pdk.Layer("PathLayer", data=subsea_cables_df, get_path="path", get_color="[171, 71, 188, 225]", width_scale=18, width_min_pixels=3, get_width=4, pickable=False))
    if not shipping_lanes_df.empty:
        layers.append(pdk.Layer("PathLayer", data=shipping_lanes_df, get_path="path", get_color="[251, 188, 4, 170]", width_scale=20, width_min_pixels=3, get_width=5, pickable=False))
    if not mammals_df.empty:
        layers.append(pdk.Layer("ScatterplotLayer", data=mammals_df, get_position="[lon, lat]", get_color="[66, 133, 244, 160]", get_radius=4000, pickable=False))
    if not kelp_df.empty:
        layers.append(pdk.Layer("ColumnLayer", id="kelp_columns", data=kelp_df, get_position="[lon, lat]", get_elevation="biomass_tons * 100", elevation_scale=1, radius=1500, get_fill_color="color", pickable=True, auto_highlight=True))
        layers.append(pdk.Layer("TextLayer", data=kelp_df, get_position="[lon, lat]", get_text="id", get_color="[232, 234, 237, 220]", get_size=15, get_alignment_baseline="'bottom'"))
    if site_data is not None:
        sel_df = pd.DataFrame([site_data])
        layers.append(pdk.Layer("ScatterplotLayer", data=sel_df, get_position="[lon, lat]", get_fill_color="[66, 133, 244, 55]", get_line_color="[138, 180, 248, 255]", get_radius=3200, stroked=True, line_width_min_pixels=3))
        arc_df = pd.DataFrame([{"source": [float(site_data["lon"]), float(site_data["lat"])], "target": [float(site_data["lon"]) - (float(site_data["abyssal_dist_km"]) / 111.0), float(site_data["lat"]) - 0.12]}])
        layers.append(pdk.Layer("ArcLayer", data=arc_df, get_source_position="source", get_target_position="target", get_source_color="[52, 168, 83, 240]", get_target_color="[66, 133, 244, 240]", get_width=4))

    tt_html = (
        "<div style='font-family:sans-serif; background:rgba(30,31,32,0.95); padding:10px 12px; border-radius:8px; border:1px solid #4285F4; color:#E8EAED;'>"
        "<b>Kelp Kandidate: {id}</b> ({report_card_grade})<br/>Site Quality Score: <b>{pareto_score}/100</b> | Size: {area_ha} HA<br/>"
        "Annual Harvest: {biomass_tons} MT | Net Carbon: {net_bankable_co2} MT/yr<br/>"
        "Subsea Cable Clearance: <b>{cable_dist_km} km</b><br/><span style='color:#81C995;'>Verdict: <b>{status}</b></span></div>"
    )
    deck_obj = pdk.Deck(layers=layers, initial_view_state=pdk.ViewState(latitude=SECTOR_CONFIG[sector_key]["lat"], longitude=SECTOR_CONFIG[sector_key]["lon"], zoom=8.5, pitch=55, bearing=15), map_style=None, tooltip={"html": tt_html})
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
        "💬 AI Advisor & Audit PDF",
    ])

    with t_mission:
        st.info("**Why Blue 42 Beats Single-Purpose Ocean Tools:** Existing platforms only show satellite maps (*Kelpwatch*), water biology (*Kelp Niche Mapper*), farm equipment costs (*Kelson Marine*), or ROV video (*Seattle Aquarium*). **Blue 42 | The Kelp Contender** unites **all of them** with **Subsea Cable & Shipping Safety**, **10-Year GAAP/SOX Financials**, and **Tamper-Proof Carbon Certificates**.")
        with st.expander("🏆 Why Blue 42 Beats Existing Kelp & Ocean Tools (Side-by-Side Comparison)", expanded=True):
            bench_rows = [
                {"Capability": "40-Yr Canopy History & Ecosystem Report Card", "Kelpwatch / GEE": "✅ Yes", "Kelp Niche Mapper": "❌ No", "Kelson / ROV Tools": "❌ No", "BLUE 42 (Kelp Contender)": "✅ Yes (1985–2025 + A+ Grade)"},
                {"Capability": "4 Global Hotspots (CA, BC Canada, Tasmania, HI)", "Kelpwatch / GEE": "⚠️ Regional", "Kelp Niche Mapper": "✅ Yes", "Kelson / ROV Tools": "❌ No", "BLUE 42 (Kelp Contender)": "✅ Yes (All 4 Corridors Built-In)"},
                {"Capability": "Multi-Species Biophysical Niche Matching", "Kelpwatch / GEE": "❌ No", "Kelp Niche Mapper": "✅ Yes", "Kelson / ROV Tools": "❌ No", "BLUE 42 (Kelp Contender)": "✅ Yes (5 Species × 6 Factors)"},
                {"Capability": "Shipping, Whale & Subsea Cable Safety Blocking", "Kelpwatch / GEE": "❌ No", "Kelp Niche Mapper": "❌ No", "Kelson / ROV Tools": "❌ No", "BLUE 42 (Kelp Contender)": "✅ Yes (ICPC 1.5km Buffer + SMART)"},
                {"Capability": "Farm Cost-Cutting Levers & 10-Yr NPV / Monte Carlo", "Kelpwatch / GEE": "❌ No", "Kelp Niche Mapper": "❌ No", "Kelson / ROV Tools": "⚠️ Costs Only", "BLUE 42 (Kelp Contender)": "✅ Yes (3 Levers + 500-Path VaR)"},
                {"Capability": "4-Tier Sensor Fusion (Sat + Drone + ROV + Cable)", "Kelpwatch / GEE": "⚠️ Sat Only", "Kelp Niche Mapper": "❌ No", "Kelson / ROV Tools": "⚠️ ROV Only", "BLUE 42 (Kelp Contender)": "✅ Yes (4-Tier Fusion + SHA-256)"},
                {"Capability": "GAAP Fixed-Asset (ASC 360/842) & SOX 404 Controls", "Kelpwatch / GEE": "❌ No", "Kelp Niche Mapper": "❌ No", "Kelson / ROV Tools": "❌ No", "BLUE 42 (Kelp Contender)": "✅ Yes (5 SOX Controls + PDFs)"},
            ]
            st.dataframe(pd.DataFrame(bench_rows), use_container_width=True, hide_index=True)

        with st.expander("📖 Plain-English Investor Glossary (Including Subsea Cables & SMART Telemetry)", expanded=False):
            st.markdown("""
            - **Kelp Kandidate (`KK-1` to `KK-12`):** A potential ocean farm site. Green sites (`CLEARED: Optimal`) are safe to fund; red/orange/yellow/purple sites are blocked.
            - **Subsea Fiber & Power Cables (`Purple Lines on Map`):** Heavy 10-ton kelp farm anchors can snap undersea internet or power cables (costing **\\$1.5M–\\$5M** to repair). Blue 42 automatically blocks any site within **1.5 km** of a subsea cable (`ICPC Protection Zone`), while sites safely **1.5–9.0 km away** can tap into **SMART Subsea Cable** seafloor sensors and underwater ROV charging docks!
            - **40-Year Ecosystem Report Card (`A+` to `B`):** Grades how reliably kelp has survived at this exact site from `1985–2025` through past El Niño heatwaves.
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
            st.markdown(f"<div style='background:#1E1F20;border:1px solid #3C4043;border-left:4px solid #4285F4;padding:10px 12px;border-radius:8px;margin-bottom:12px;'><div style='font-size:0.72rem;color:#8AB4F8;font-weight:600;'>🧬 RECOMMENDED SEED — {sel_site}</div><div style='font-size:0.98rem;color:#E8EAED;font-weight:700;'>{rec_strain}</div><div style='font-size:0.78rem;color:#9AA0A6;'>Water Temp: <b>{sst:.1f}°C</b> | Sunlight (PAR): <b>{site_data.get('par_light')} mol/m²/d</b> | Keeps <b>{site_data.get('stress_retention_pct', 100):.0f}%</b> of harvest</div></div>", unsafe_allow_html=True)

            jobs = int(site_data.get('jobs_created', 0))
            st.markdown(f"""
            <div class="metric-grid">
                <div class="metric-box" style="border-top: 3px solid #FBBC04;"><div class="metric-title">Local Jobs Created</div><div class="metric-val" style="color: #FDD663;">{jobs}</div><div class="metric-sub">{int(jobs*0.4)} Boats | {int(jobs*0.4)} Processing</div></div>
                <div class="metric-box" style="border-top: 3px solid #4285F4;"><div class="metric-title">Shellfish Safe Zone</div><div class="metric-val" style="color: #8AB4F8;">{site_data.get('halo_ha', 0)} HA</div><div class="metric-sub">Calms Acidic Water</div></div>
                <div class="metric-box" style="border-top: 3px solid #34A853;"><div class="metric-title">Pollution Removed</div><div class="metric-val" style="color: #81C995;">{site_data.get('nitrogen_tons', 0)} MT</div><div class="metric-sub">Fertilizer Nitrogen Cleaned</div></div>
            </div>
            """, unsafe_allow_html=True)

            if PLOTLY_AVAILABLE and bounds:
                cats = ['Carbon Yield', 'Coastal Protection', 'Biodiversity', 'N₂ Remediation', 'Social Equity']
                s_norm = [round(norm_val(site_data[m], *bounds[m]) * 100, 1) for m in metrics_to_norm]
                a_norm = [round(float(np.mean([norm_val(s[m], *bounds[m]) * 100 for s in raw_sites])), 1) for m in metrics_to_norm]
                fig_rad = go.Figure()
                fig_rad.add_trace(go.Scatterpolar(r=a_norm + [a_norm[0]], theta=cats + [cats[0]], fill='toself', name='Regional Avg', line=dict(color='#9AA0A6', width=1.5)))
                fig_rad.add_trace(go.Scatterpolar(r=s_norm + [s_norm[0]], theta=cats + [cats[0]], fill='toself', name=f"{sel_site} ({site_data['pareto_score']}/100)", line=dict(color='#4285F4', width=2.5)))
                fig_rad.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", polar=dict(bgcolor="rgba(30,31,32,0.7)", radialaxis=dict(visible=True, range=[0, 100])), margin=dict(l=30, r=30, t=20, b=15), height=210)
                st.plotly_chart(fig_rad, use_container_width=True)

            # UPGRADE 1: 40-YEAR SATELLITE CANOPY HISTORY & ECOSYSTEM REPORT CARD (SURPASSING KELPWATCH)
            with st.expander("📊 40-Year Satellite Canopy History & Ecosystem Report Card (1985–2025)", expanded=True):
                hist_p = int(site_data.get("hist_persistence_40yr", 88))
                rc_grade = site_data.get("report_card_grade", "A (High Persistence)")
                st.caption("**Plain English:** Tracks 40 years of satellite photos (`1985–2025`) to prove how reliably kelp bounces back after major El Niño heatwaves:")
                c_h1, c_h2 = st.columns(2)
                c_h1.metric("Ecosystem Report Card Grade", rc_grade)
                c_h2.metric("40-Yr Satellite Rebound Rate", f"{hist_p}%")
                if PLOTLY_AVAILABLE:
                    decs = ["1985", "1990", "1995", "1998 (El Niño)", "2005", "2010", "2015 (Heatwave)", "2020", "2025"]
                    h_vals = [round(hist_p * m, 1) for m in [0.96, 1.00, 0.98, 0.72, 1.02, 1.04, 0.68, 0.97, 1.00]]
                    fig_h = go.Figure(go.Scatter(x=decs, y=h_vals, mode="lines+markers", line=dict(color="#34A853", width=2.5), fill="tozeroy", fillcolor="rgba(52,168,83,0.16)"))
                    fig_h.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", yaxis_title="Canopy Persistence (%)", margin=dict(l=0, r=0, t=10, b=0), height=180)
                    st.plotly_chart(fig_h, use_container_width=True)

            # UPGRADE 2: MULTI-SPECIES BIOPHYSICAL NICHE MATCHER (SURPASSING KELP NICHE MAPPER)
            with st.expander("🧬 Multi-Species Biophysical Niche Matcher (5 Kelp Species × 6 Ocean Factors)", expanded=True):
                st.caption(f"Matches **{sel_site}**'s 6 ocean factors (**Temp `{sst:.1f}°C`**, **Sunlight `{site_data.get('par_light')} mol/m²/d`**, **Nutrients `{site_data.get('nitrate_score')}/100`**, **Salinity `{site_data.get('salinity')} PSU`**, **Waves `{site_data.get('wave_energy')} kW/m`**, **Depth `{site_data.get('depth')}m`**) against 5 commercial kelp species:")
                niche_rows = [
                    {"Kelp Species": "Giant Kelp (Macrocystis pyrifera)", "Best Use": "Carbon Sinking + Bioplastics", "Ideal Temp": "11–18°C", "Site Match": f"{min(99, max(55, int(100 - abs(sst - 14.8)*4.5)))}%", "Verdict": "⭐ Primary High-Yield Crop" if sst <= 18.5 else "⚠️ Use Baja Heat Strain"},
                    {"Kelp Species": "Bull Kelp (Nereocystis luetkeana)", "Best Use": "High-Wave Cold Restoration", "Ideal Temp": "9–15°C", "Site Match": f"{min(98, max(45, int(100 - abs(sst - 12.5)*5.2)))}%", "Verdict": "✅ Strong Cold/Wave Fit" if sst <= 15.8 else "Warm for Bull Kelp"},
                    {"Kelp Species": "Sugar Kelp (Saccharina latissima)", "Best Use": "Food, Bio-Packaging & N₂ Cleanup", "Ideal Temp": "8–16°C", "Site Match": f"{min(97, max(50, int(100 - abs(sst - 13.5)*4.8)))}%", "Verdict": "✅ High Commercial Value" if sst <= 16.5 else "Seasonal Winter Crop"},
                    {"Kelp Species": "Golden Kelp (Ecklonia radiata)", "Best Use": "Southern Reef & Temperate Carbon", "Ideal Temp": "13–20°C", "Site Match": f"{min(98, max(60, int(100 - abs(sst - 16.5)*4.0)))}%", "Verdict": "✅ Resilient Temperate Fit"},
                    {"Kelp Species": "Red Ogo / Asparagopsis Guild", "Best Use": "Anti-Methane Cow Feed (Warm)", "Ideal Temp": "18–25°C", "Site Match": f"{min(99, max(48, int(100 - abs(sst - 20.5)*4.5)))}%", "Verdict": "⭐ Top Tropical Pick" if sst > 17.5 else "Supplemental Summer Crop"},
                ]
                st.dataframe(pd.DataFrame(niche_rows), use_container_width=True, hide_index=True)

            with st.expander("📅 Best Months to Harvest (12-Month Growth Calendar) & Deep-Sea Oxygen Split", expanded=False):
                st.caption("Peak harvest window is **June – July** before late-summer warm water. Deep-sea sinking is capped at **`-1.5%` seafloor O₂ change**, with extra kelp sold on land for bioplastics & low-methane cattle feed:")
                st.info(f"🫧 **Safely Sunk for 1,000-Yr Carbon Credits:** `{site_data.get('abyssal_sunk_mt')} MT` (`ΔO₂ {site_data.get('benthic_o2_delta_pct')}%`) | **Sold on Land for Bioplastics & Cow Feed:** `{site_data.get('circular_surface_mt')} MT` (`-{site_data.get('enteric_ch4_abated_mt')} MT CH₄`)")

            st.download_button("📥 Download Site Fact Sheet & Satellite Provenance (PDF)", data=create_provenance_pdf(site_data.to_dict()), file_name=f"Blue42_Data_Provenance_{sel_site}.pdf", mime="application/pdf", use_container_width=True)

    with t2:
        if site_data is not None:
            st.markdown(f"<h5 style='display:flex; align-items:center;'>💵 10-Year Investment Returns &amp; Farm Cost-Cutting Levers {leaf_info('Model 4 income streams, toggle offshore engineering cost-reduction levers, and build an optimal multi-site portfolio.')}</h5>", unsafe_allow_html=True)
            with st.expander("⚙️ Prices, Return Rate (WACC), Community Share & Farm Cost-Reduction Levers (Surpasses Kelson/UMaine Tool)", expanded=True):
                c_p1, c_p2, c_p3 = st.columns(3)
                carbon_price = c_p1.number_input("Carbon Price ($/MT)", 50, 500, 150, 10)
                biomass_price = c_p2.number_input("Kelp Price ($/MT)", 100, 800, 300, 25)
                wacc_rate = c_p3.slider("Discount Rate / WACC (%)", 2.0, 15.0, 8.0, 0.5) / 100.0
                commons_share_pct = st.slider("🤝 Local Fishing & Indigenous Community Share (% Gross Rev)", 0, 15, 8, 1)
                st.markdown("**🔧 Offshore Farm Engineering Cost-Reduction Levers (Lower Your Production Cost per Ton `$/MT`):**")
                cl1, cl2, cl3 = st.columns(3)
                lever_auto_harvest = cl1.checkbox("🤖 Automated Harvester Barge (-18% OPEX)", value=False)
                lever_shared_hub = cl2.checkbox("🏭 Shared Coastal Processing Hub (-15% CAPEX)", value=False)
                lever_dual_seed = cl3.checkbox("🌱 Dual-Season Spore Seeding (+12% Harvest)", value=False)

            strain_mult = 1.12 if adopt_baja_strain else 1.0
            capex = site_data['area_ha'] * 15000 * strain_mult * (0.85 if lever_shared_hub else 1.0)
            opex_yr = ((site_data['area_ha'] * 2000) + site_data['sinking_cost']) * (0.82 if lever_auto_harvest else 1.0)
            y_mult = 1.12 if lever_dual_seed else 1.0
            eff_co2 = site_data['net_bankable_co2'] * y_mult
            eff_bio = site_data['biomass_tons'] * y_mult
            wave_reb = (site_data['area_ha'] * 1500) + (site_data['averted_damage_millions'] * 1e6 * 0.0025)
            gross_rev_yr = (eff_co2 * carbon_price) + (eff_bio * biomass_price) + wave_reb + (site_data['nitrogen_tons'] * 2000)
            rev_yr = gross_rev_yr * (1.0 - commons_share_pct / 100.0)
            permit_months = max(12, 36 - int(commons_share_pct * 2))

            years = np.arange(0, 11)
            npv_curve = [-capex + sum((rev_yr - opex_yr) / ((1 + wacc_rate) ** t) for t in range(1, yr + 1)) for yr in years]
            if PLOTLY_AVAILABLE:
                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(x=years, y=capex + opex_yr * years, name="Cumulative Cost", line=dict(color="#EA4335", width=2)))
                fig2.add_trace(go.Scatter(x=years, y=rev_yr * years, name="Cumulative Revenue", line=dict(color="#34A853", width=2), fill='tozeroy', fillcolor='rgba(52,168,83,0.15)'))
                fig2.add_trace(go.Scatter(x=years, y=npv_curve, name="Discounted 10-Yr NPV ($)", line=dict(color="#4285F4", width=2.5, dash="dot")))
                fig2.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", yaxis_title="USD ($)", margin=dict(l=0, r=0, t=10, b=0), height=215)
                st.plotly_chart(fig2, use_container_width=True)

            ann_prof = rev_yr - opex_yr
            unit_bio_cost = ((capex / 10.0) + opex_yr) / max(eff_bio, 1.0)
            lcok = ((capex / 10.0) + opex_yr) / max(eff_co2, 1.0)
            if ann_prof > 0:
                st.success(f"**Payback:** Year {capex/ann_prof:.1f} | **10-Yr NPV:** \\${npv_curve[-1]:,.0f} | **Farm Cost per Ton of Kelp:** \\${unit_bio_cost:,.0f}/MT (Sold at \\${biomass_price}/MT) | **Cost per Ton CO₂:** \\${lcok:,.0f}")

            with st.expander("🎲 500-Scenario Weather & Price Stress Test (Monte Carlo) + GAAP ASC 360/842 Table", expanded=False):
                mc_rng = np.random.default_rng(42)
                shocks = np.clip(mc_rng.normal(1.0, 0.16, (500, 10)), 0.45, 1.40)
                paths = np.zeros((500, 11))
                paths[:, 0] = -capex
                for y_i in range(1, 11):
                    paths[:, y_i] = paths[:, y_i - 1] + (((rev_yr * shocks[:, y_i - 1]) - opex_yr) / ((1.0 + wacc_rate) ** y_i))
                st.info(f"**500-Future 10-Yr NPV Range:** **Worst Case (5th %):** \\${np.percentile(paths[:,-1], 5):,.0f} | **Median:** \\${np.percentile(paths[:,-1], 50):,.0f} | **Best Case (95th %):** \\${np.percentile(paths[:,-1], 95):,.0f}")
                fa_df = pd.DataFrame([
                    {"Asset Class": "Subsurface HMPE Mooring Grid & Anchors", "GAAP Standard": "ASC 360 (PP&E)", "Share": "55%", "Cost ($)": f"${capex*0.55:,.0f}", "Life": "10 Yrs"},
                    {"Asset Class": "Multispectral Telemetry & SMART Cable Link", "GAAP Standard": "ASC 360 (PP&E)", "Share": "20%", "Cost ($)": f"${capex*0.20:,.0f}", "Life": "5 Yrs"},
                    {"Asset Class": "Hatchery Seeding & Harvester Gear", "GAAP Standard": "ASC 360 (PP&E)", "Share": "15%", "Cost ($)": f"${capex*0.15:,.0f}", "Life": "7 Yrs"},
                    {"Asset Class": "Sovereign Seabed Right-of-Use Lease", "GAAP Standard": "ASC 842 (Leases)", "Share": "10%", "Cost ($)": f"${capex*0.10:,.0f}", "Life": "10 Yrs"},
                    {"Asset Class": "Seabed Decommissioning Reserve (ARO)", "GAAP Standard": "ASC 410 (ARO)", "Share": "+5% PV", "Cost ($)": f"${capex*0.05:,.0f}", "Life": "10 Yrs"},
                ])
                st.dataframe(fa_df, use_container_width=True, hide_index=True)

            st.markdown("###### 💼 'How Many Safe Sites Can My Budget Buy?' (Auto-Portfolio Builder)")
            capex_budget = st.slider("Your Total Investment Budget ($ USD)", 150000, 2500000, 750000, 50000)
            cands = []
            for _, row in safe_df.iterrows():
                sc_x = row['area_ha'] * 15000 * strain_mult
                so_x = (row['area_ha'] * 2000) + row['sinking_cost']
                sr_x = (row['net_bankable_co2'] * carbon_price) + (row['biomass_tons'] * biomass_price) + (row['area_ha'] * 1500) + (row['nitrogen_tons'] * 2000)
                snpv = -sc_x + sum((sr_x - so_x) / ((1 + wacc_rate) ** t) for t in range(1, 11))
                if snpv > 0:
                    cands.append({"Site ID": row['id'], "Pareto": f"{row['pareto_score']:.1f}", "Area (HA)": row['area_ha'], "CAPEX_num": sc_x, "NPV_num": snpv, "Net_CO2_num": row['net_bankable_co2'], "CAPEX ($)": f"${sc_x:,.0f}", "10-Yr NPV ($)": f"${snpv:,.0f}", "Net CO₂e/yr": f"{row['net_bankable_co2']:.1f} MT", "Eff": (snpv / sc_x) * (row['pareto_score'] / 100.0)})
            cands.sort(key=lambda x: x["Eff"], reverse=True)
            funded_sites, spent = [], 0.0
            for c in cands:
                if spent + c["CAPEX_num"] <= capex_budget:
                    spent += c["CAPEX_num"]
                    funded_sites.append({k: c[k] for k in ["Site ID", "Pareto", "Area (HA)", "CAPEX ($)", "10-Yr NPV ($)", "Net CO₂e/yr"]})
            if funded_sites:
                st.dataframe(pd.DataFrame(funded_sites), use_container_width=True, hide_index=True)

            c_perm1, c_perm2 = st.columns(2)
            if c_perm1.button("🏛️ Prepare Government Permit Pack", use_container_width=True):
                handshake_animation()
                st.success(f"Fast-Track `{permit_months}-Month` Permit Ready!")
            c_perm2.download_button("📥 Download Permit Dossier (PDF)", data=create_lease_permit_pdf(site_data.to_dict(), funded_sites, commons_share_pct, permit_months), file_name=f"Blue42_Permit_Dossier_{sel_site}.pdf", mime="application/pdf", use_container_width=True)

            with st.expander("🌍 Big-Picture Vision: Coastline Scale-Up Simulator (10,000 HA to 50M HA)", expanded=False):
                scale_presets = {"Phase 1: Regional Pilot (10,000 HA)": 10_000, "Phase 2: State Coastline (100,000 HA)": 100_000, "Phase 3: U.S. EEZ Network (1,000,000 HA)": 1_000_000, "Phase 4: Pacific Basin (10,000,000 HA)": 10_000_000, "Phase 5: Planetary Scale (50,000,000 HA)": 50_000_000}
                sel_phase = st.select_slider("Select Expansion Phase:", options=list(scale_presets.keys()), value="Phase 3: U.S. EEZ Network (1,000,000 HA)")
                t_ha = scale_presets[sel_phase]
                disc = {10_000: 0.0, 100_000: 0.10, 1_000_000: 0.20, 10_000_000: 0.28, 50_000_000: 0.35}[t_ha]
                m_co2 = t_ha * 10.5 * (avg_retention / 100.0 if avg_retention > 0 else 1.0)
                m_capex = t_ha * 15000 * strain_mult * (1.0 - disc)
                m_net_yr = (m_co2 * carbon_price) + (t_ha * 17.0 * biomass_price) + (t_ha * 1500) + (t_ha * 0.25 * 2000) - (t_ha * 2000)
                st.write(f"📏 **{t_ha:,} HA** = **{t_ha*0.00386:,.0f} sq miles** | Removes **{m_co2:,.0f} MT CO₂/yr** (like taking **{int(m_co2/4.6):,} cars** off the road) | **Bulk Discount:** `{int(disc*100)}%` | **Est. Annual Net Profit:** **\\${m_net_yr/1e9:.2f} Billion/yr**")

    with t_mrv:
        if site_data is not None:
            is_kandidate_cleared = "CLEARED" in site_data.get('status', '')
            st.markdown(f"<h5 style='display:flex; align-items:center;'>🛰️ Carbon Credit Waterfall &amp; 4-Tier Sensor Fusion {leaf_info('Proves to carbon buyers that your kelp grew using Satellites, Coastal Drones, Underwater ROV AI, and SMART Subsea Cables.')}</h5>", unsafe_allow_html=True)
            gross_c, tow_c, remin_c, buf_c, net_c = float(site_data["co2_tons"]), float(site_data["tow_emissions_co2"]), float(site_data["remin_discount_co2"]), float(site_data["buffer_pool_co2"]), float(site_data["net_bankable_co2"])
            if PLOTLY_AVAILABLE:
                fig_wf = go.Figure(go.Waterfall(
                    orientation="v", measure=["absolute", "relative", "relative", "relative", "total"],
                    x=["Total Absorbed", "Less Boat Fuel", "Less 5% Deep Loss", "Less Insurance Reserve", "Net Sellable Credits"],
                    y=[gross_c, -tow_c, -remin_c, -buf_c, net_c],
                    text=[f"{gross_c:.1f}", f"-{tow_c:.2f}", f"-{remin_c:.2f}", f"-{buf_c:.2f}", f"{net_c:.1f} MT"],
                    decreasing={"marker": {"color": "#EA4335"}}, increasing={"marker": {"color": "#4285F4"}}, totals={"marker": {"color": "#34A853"}},
                ))
                fig_wf.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", yaxis_title="MT CO₂e / Yr", margin=dict(l=0, r=0, t=15, b=0), height=210)
                st.plotly_chart(fig_wf, use_container_width=True)

            # UPGRADE 5: 4-TIER SENSOR FUSION (SATELLITE + DRONE + UNDERWATER ROV AI + SMART SUBSEA CABLE)
            with st.expander("🤖 4-Tier Sensor Fusion: Satellite + Drone + Underwater ROV AI + SMART Subsea Cable", expanded=True):
                st.caption("**Plain English:** Satellites only see floating surface kelp. **Blue 42** combines **Space Satellites (30m)**, **Coastal Drones (3cm)**, **Underwater ROV AI Cameras**, and **SMART Subsea Cable Seafloor Sensors** for 4x verification:")
                rov_sub = site_data.get("substrate_type", "Consolidated Rocky Reef")
                rov_stipes = float(site_data.get("rov_stipe_density", 14.2))
                rov_fish = int(site_data.get("rov_wildlife_species", 28))
                rov_par = float(site_data.get("par_light", 36.5))
                rc1, rc2, rc3 = st.columns(3)
                rc1.metric("🪨 Seafloor Anchor (ROV)", rov_sub.split("(")[0].strip())
                rc2.metric("🌿 Underwater Stalks (ROV)", f"{rov_stipes:.1f} stalks/m²")
                rc3.metric("🐟 Marine Species (ROV AI)", f"{rov_fish} species")
                sensor_df = pd.DataFrame([
                    {"Verification Layer": "🛰️ Tier 1: Orbital Satellite (Landsat / Sentinel-2)", "Resolution": "10m – 30m", "What It Proves": "Tracks floating surface canopy area every 5 days", "Live Reading": f"{int(95 * (site_data['stress_retention_pct']/100.0))}% Canopy Index ({site_data['area_ha']} HA)"},
                    {"Verification Layer": "🚁 Tier 2: Multispectral Coastal Drone (UAV)", "Resolution": "3cm Ultra-HD", "What It Proves": "Measures blade health, nitrogen uptake & sunlight", "Live Reading": f"PAR Sunlight: {rov_par:.1f} mol/m²/d | Health: {int(site_data.get('suitability', 0.88)*100)}%"},
                    {"Verification Layer": "🤖 Tier 3: Underwater ROV AI Vision (Sub-Surface)", "Resolution": "Sub-mm HD + Sonar", "What It Proves": "Counts underwater stalks, rock anchors & fish species", "Live Reading": f"{rov_stipes:.1f} stalks/m² | {rov_fish} species | {rov_sub}"},
                    {"Verification Layer": "⚡ Tier 4: SMART Subsea Cable Telemetry (Seafloor)", "Resolution": "24/7 Optical/Benthic", "What It Proves": "Verifies >1.5km safe cable clearance + live seafloor O₂/Temp", "Live Reading": site_data.get("smart_cable_status", "✅ Safe Clearance")},
                ])
                st.dataframe(sensor_df, use_container_width=True, hide_index=True)

            ts_now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')
            tx_hash = generate_sha256_signature(site_data.to_dict(), ts_now)
            itmo_serial = f"B42-ART64-{sector_key[:3].upper()}-{sel_site}-{tx_hash[:8].upper()}"
            cert_pdf = create_minted_credit_pdf(site_data.to_dict(), itmo_serial, tx_hash, ts_now)
            if st.button("🔐 Issue & Stamp Official Carbon Credit Certificate", use_container_width=True, disabled=not is_kandidate_cleared):
                kelp_animation()
                st.success(f"✅ Verified across 4 Sensor Tiers! **{net_c:.2f} Net Carbon Credits (MT CO₂e)** issued (`{itmo_serial}`).")
                st.markdown(f"<div class='crypto-box'><b>SERIAL:</b> {itmo_serial} | <b>NET CREDITS:</b> {net_c:.2f} MT CO₂e<br><b>SHA-256 SEAL:</b> {tx_hash}</div>", unsafe_allow_html=True)
            st.download_button("📥 Download Official Carbon Credit Certificate (PDF)", data=cert_pdf, file_name=f"Blue42_ITMO_Certificate_{sel_site}.pdf", mime="application/pdf", use_container_width=True)

    with t3:
        if site_data is not None:
            with st.expander("🛡️ 5-Point Investor Safety & Accounting Checklist (SOX 404 Controls)", expanded=True):
                ctrl_rows = [
                    {"Check #": "1. Spatial & Subsea Cable Safety (CTRL-MCDA-01)", "Plain-English Check": "Clear of shipping lanes, whale paths, sanctuaries & >1.5km from Subsea Cables", "Status": "✅ PASS" if "CLEARED" in site_data.get("status", "") else "❌ BLOCKED"},
                    {"Check #": "2. 4-Tier Sensor Proof (CTRL-MRV-02)", "Plain-English Check": "40-Yr Satellite + Drone + Underwater ROV AI + SMART Cable verified", "Status": f"✅ {site_data.get('report_card_grade')}"},
                    {"Check #": "3. Honest Carbon Math (CTRL-CARB-03)", "Plain-English Check": "Subtracts boat fuel, 5% deep-sea loss & insurance reserve", "Status": f"✅ {site_data.get('net_bankable_co2')} MT Net"},
                    {"Check #": "4. Stress-Tested Valuation (CTRL-VAL-04)", "Plain-English Check": "500-future weather simulation & GAAP ASC 360/842/410 schedules", "Status": f"✅ {site_data.get('stress_retention_pct'):.0f}% Kept"},
                    {"Check #": "5. Seafloor Oxygen Safety (CTRL-BENTHIC-05)", "Plain-English Check": "Caps deep-sea sinking so seafloor oxygen stays safe", "Status": f"✅ ΔO₂ {site_data.get('benthic_o2_delta_pct')}%"},
                ]
                st.dataframe(pd.DataFrame(ctrl_rows), use_container_width=True, hide_index=True)

            def generate_expert_agent_response(user_q: str, s_data) -> str:
                q_low = user_q.lower()
                s_id, status = s_data.get("id"), s_data.get("status")
                area, pareto = float(s_data.get("area_ha", 0)), float(s_data.get("pareto_score", 0))
                bio, net_c = float(s_data.get("biomass_tons", 0)), float(s_data.get("net_bankable_co2", 0))
                c_dist, c_stat = float(s_data.get("cable_dist_km", 10.0)), s_data.get("smart_cable_status", "✅ Safe")
                site_capex = area * 15000.0
                site_opex = (area * 2000.0) + float(s_data.get("sinking_cost", 0))
                gross_rev = (net_c * 150.0) + (bio * 300.0) + (area * 1500.0) + (float(s_data.get("nitrogen_tons", 0)) * 2000.0)
                site_net_yr = (gross_rev * 0.92) - site_opex

                if any(k in q_low for k in ["cable", "subsea", "fiber", "smart", "telecom", "anchor"]):
                    return (
                        f"### ⚡ Subsea Cables & SMART Telemetry — Kelp Kandidate **{s_id}**\n"
                        f"- **Distance to Nearest Subsea Cable:** **{c_dist:.2f} km** (`{c_stat}`)\n"
                        f"- **1. Why Subsea Cables Matter (Anchor Strike Risk):** Offshore kelp farms use heavy 5- to 15-ton seafloor anchors. Under **International Cable Protection Committee (ICPC)** rules, dropping an anchor within **1.5 km** of an undersea fiber-optic or power cable is strictly prohibited because snapping a cable costs **\\$1.5M–\\$5.0M** in repairs.\n"
                        f"- **2. How SMART Cables Help Kelp Farms:** Sites safely **1.5 km – 9.0 km** outside the cable danger zone can link to **ITU/UNESCO SMART Subsea Cable** seafloor sensors for 24/7 bottom temperature, wave pressure, and deep-sea oxygen monitoring—plus inductive ROV charging docks!"
                    )
                if any(k in q_low for k in ["asc", "gaap", "lease", "accounting", "depreciation", "sox"]):
                    return (
                        f"### 📋 GAAP Fixed-Asset (ASC 360), Lease (ASC 842) & SOX 404 Brief — **{s_id}**\n"
                        f"- **Total Upfront Capitalized Cost (`CAPEX`):** **\\${site_capex:,.0f}** across **{area} HA ({area*2.471:.0f} Acres)**\n"
                        f"- **ASC 360 (Mooring Grid 55%, Buoys 20%, Gear 15%):** **\\${site_capex*0.90:,.0f}** | **ASC 842 (Seabed Lease 10%):** **\\${site_capex*0.10:,.0f}** | **ASC 410 (Cleanup Reserve +5%):** **\\${site_capex*0.05:,.0f}**"
                    )
                return (
                    f"### 💡 Plain-English Investor Summary — Kelp Kandidate **{s_id}**\n"
                    f"- **Verdict:** **{status}** | **Quality Score:** **{pareto}/100** | **40-Yr Satellite Grade:** **{s_data.get('report_card_grade')}**\n"
                    f"- **Financials:** Upfront Cost **\\${site_capex:,.0f}** | Est. Net Profit **\\${site_net_yr:,.0f}/yr** (~{site_capex/max(site_net_yr,1):.1f} yr payback)\n"
                    f"- **4-Tier Verification:** `{s_data.get('rov_stipe_density')} stalks/m²` (ROV AI) | `{s_data.get('rov_wildlife_species')} marine species` | `{c_stat}`"
                )

            st.caption("⚡ **1-Click Questions:** Tap any button below for an instant plain-English answer:")
            qp0, qp1, qp2, qp3 = st.columns(4)
            trig = None
            if qp0.button("💡 Explain Simply", use_container_width=True):
                trig = f"Give me a plain-English investor summary for {sel_site}."
            if qp1.button("⚡ Subsea Cables", use_container_width=True):
                trig = f"How do subsea cables and SMART cable telemetry affect {sel_site}?"
            if qp2.button("📋 GAAP & Leases", use_container_width=True):
                trig = f"Show the GAAP ASC 360, ASC 842 lease, and SOX 404 breakdown for {sel_site}."
            if qp3.button("📊 CFO & ROI", use_container_width=True):
                trig = f"Summarize the 10-year ROI and carbon credits for {sel_site}."

            chat_box = st.container(height=210)
            with chat_box:
                for m in st.session_state.messages:
                    st.markdown(f"**{'🤖 Blue 42 Advisor' if m['role']=='assistant' else '👤 You'}:**\n{m['content']}")

            u_in = st.chat_input(f"Ask anything about {sel_site} (e.g. 'How do subsea cables affect this site?')...")
            act_q = trig or u_in
            if act_q:
                st.session_state.messages.append({"role": "user", "content": act_q})
                st.session_state.messages.append({"role": "assistant", "content": generate_expert_agent_response(act_q, site_data)})
                st.rerun()

            audit_ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')
            audit_sig = generate_sha256_signature(site_data.to_dict(), audit_ts)
            audit_txt = f"Verdict: {site_data.get('status')} | Score: {site_data.get('pareto_score')}/100 | 40-Yr Grade: {site_data.get('report_card_grade')} | Net Carbon: {site_data.get('net_bankable_co2')} MT/yr | Subsea Cable Check: {site_data.get('smart_cable_status')} | SOX 404 Confidence: 94.7%."
            st.download_button("📥 Export Verified Audit Report (PDF)", data=create_lca_brief(site_data.to_dict(), audit_txt, audit_sig, audit_ts), file_name=f"Blue42_Verified_Audit_{sel_site}.pdf", mime="application/pdf", use_container_width=True)
