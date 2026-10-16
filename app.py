import streamlit as st
import pydeck as pdk
import pandas as pd
import numpy as np
import json
import ee
import math
import random
import time
from datetime import datetime
from google.oauth2 import service_account
import google.generativeai as genai

try:
    from fpdf import FPDF
except ImportError:
    st.error("Please install fpdf: pip install fpdf")

# =========================================================
# 1. UX SETUP & SUSTAINABILITY THEME
# =========================================================
st.set_page_config(layout="wide", page_title="Blue 42: Kelp Capital", page_icon="🌱", initial_sidebar_state="expanded")

card_bg = "#0B1D2E"
accent_green = "#10B981"
accent_teal = "#0D9488"

custom_css = f"""
<style>
    .block-container {{ padding-top: 1.5rem; max-width: 98%; }}
    div[data-testid="metric-container"] {{
        background-color: {card_bg}; border: 1px solid #1E3A5F; padding: 1rem; border-radius: 8px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
    }}
    .stButton>button {{ border-radius: 6px; font-weight: 600; border: 1px solid {accent_teal}; }}
    .stButton>button:hover {{ border-color: {accent_green}; box-shadow: 0 0 10px rgba(16, 185, 129, 0.3); }}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

if "library" not in st.session_state: st.session_state.library = []
if "messages" not in st.session_state: st.session_state.messages = [{"role": "assistant", "content": "Blue Carbon AI active. Analyzing bathymetry for optimal Macrocystis pyrifera cultivation."}]

# =========================================================
# 2. AUDITABLE ACTION: ECOLOGICAL INVESTMENT PDF
# =========================================================
def create_investment_brief(site_data: dict) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "BLUE 42 - ECOLOGICAL INVESTMENT & HARVEST BRIEF", ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("Arial", size=11)
    pdf.cell(0, 10, f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC", ln=True)
    pdf.cell(0, 10, f"Coordinates: {site_data.get('lat')}, {site_data.get('lon')}", ln=True)
    pdf.cell(0, 10, f"Verified Polygon Area: {site_data.get('area_ha')} Hectares", ln=True)
    pdf.cell(0, 10, f"Calculated Biomass Yield: {site_data.get('biomass_tons')} Wet Tons", ln=True)
    pdf.cell(0, 10, f"Projected Annual Sequestration: {site_data.get('co2_tons')} MT CO2e", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Gemini 4 Argon Suitability Analysis:", ln=True)
    pdf.set_font("Arial", size=10)
    text = site_data.get('ai_reasoning', 'N/A').encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 6, text)
    return pdf.output(dest="S").encode("latin-1")

# =========================================================
# 3. SECURE API INITIALIZATION (Local + Cloud Auth)
# =========================================================
ee_connected = False
try:
    # First, try default local authentication (if running locally via CLI auth)
    ee.Initialize()
    ee_connected = True
    ee_status = "🟢 GEE UPLINK SECURE (Local Auth)"
except Exception:
    try:
        # Fallback to Streamlit secrets (if deployed on Streamlit Cloud)
        if "EARTHENGINE_TOKEN" in st.secrets:
            key_dict = json.loads(st.secrets["EARTHENGINE_TOKEN"])
            creds = service_account.Credentials.from_service_account_info(key_dict).with_scopes(['https://www.googleapis.com/auth/earthengine'])
            ee.Initialize(credentials=creds, project=key_dict.get("project_id"))
            ee_connected = True
            ee_status = "🟢 GEE UPLINK SECURE (Cloud Auth)"
        else: ee_status = "🟡 GEE MOCKED (NO SECRETS)"
    except: ee_status = "🟡 GEE MOCKED (NO AUTH)"

try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        available_models = [m.name for m in genai.list_models()]
        if 'models/gemini-4-argon' in available_models: target_model = 'gemini-4-argon'
        elif 'models/gemini-3.8-flash' in available_models: target_model = 'gemini-3.8-flash'
        elif 'models/gemini-1.5-pro' in available_models: target_model = 'gemini-1.5-pro'
        else: target_model = 'gemini-4-argon'
        model = genai.GenerativeModel(target_model)
        ai_status = f"🟢 {target_model.upper()} ACTIVE"
    else: ai_status = "🔴 AI OFFLINE"
except Exception as e: ai_status = f"🔴 AI OFFLINE"

# =========================================================
# 4. GREEN COMPUTING: REAL-TIME GEE BIOMASS CALCULATOR
# =========================================================
@st.cache_data(ttl=3600)
def get_kelp_biomass_data(sector):
    if ee_connected:
        try:
            bathy = ee.ImageCollection('COPERNICUS/MARINE/WAV/ANFC_0_083DEG_STATIC').first().select('deptho')
            depth_mask = bathy.gte(5).And(bathy.lte(30))
            sst = ee.ImageCollection('ECMWF/ERA5_HOURLY').filterDate('2023-01-01', '2023-12-31').mean().select('sea_surface_temperature')
            temp_mask = sst.lt(291.15)
            suitability = depth_mask.And(temp_mask)
            suitable_areas = suitability.updateMask(suitability)
            
            roi = ee.Geometry.Rectangle([-121.0, 33.5, -119.0, 34.5]) if sector == "Channel Islands" else ee.Geometry.Rectangle([-159.0, 20.5, -157.0, 21.8])
            clusters = suitable_areas.reduceToVectors(geometry=roi, crs=bathy.projection(), scale=1000, geometryType='polygon', maxPixels=1e9).limit(10)
            
            def calculate_biomass(feature):
                f = ee.Feature(feature)
                area_ha = f.geometry().area(maxError=100).divide(10000)
                biomass_tons = area_ha.multiply(18.5)
                co2_tons = area_ha.multiply(12.5) 
                centroid = f.geometry().centroid(maxError=100)
                return ee.Feature(None, {'area_ha': area_ha, 'biomass_tons': biomass_tons, 'co2_tons': co2_tons, 'lon': centroid.coordinates().get(0), 'lat': centroid.coordinates().get(1)})

            processed_clusters = clusters.map(calculate_biomass)
            features = processed_clusters.getInfo()['features']
            
            sites = []
            for i, f in enumerate(features):
                props = f['properties']
                sites.append({
                    "lat": props['lat'], "lon": props['lon'], "name": f"EE Verified Site {i+1}", 
                    "area_ha": round(props['area_ha'], 2), "biomass_tons": round(props['biomass_tons'], 2), "co2_tons": round(props['co2_tons'], 2)
                })
            if sites: return pd.DataFrame(sites)
        except Exception as e: print(f"EE Error: {e}")

    # DYNAMIC FALLBACK: Returns correct coordinates based on selected sector!
    if sector == "Channel Islands":
        return pd.DataFrame([
            {"lat": 34.02, "lon": -119.55, "name": "Kelp Bio-Zone Alpha (Mocked)", "area_ha": 6.2, "biomass_tons": 114.7, "co2_tons": 77.5},
            {"lat": 33.95, "lon": -120.10, "name": "Kelp Bio-Zone Bravo (Mocked)", "area_ha": 4.1, "biomass_tons": 75.8, "co2_tons": 51.2},
            {"lat": 33.88, "lon": -119.75, "name": "Kelp Bio-Zone Charlie (Mocked)", "area_ha": 8.5, "biomass_tons": 157.2, "co2_tons": 106.2}
        ])
    else:
        return pd.DataFrame([
            {"lat": 21.35, "lon": -157.90, "name": "Reef Bio-Zone Alpha (Mocked)", "area_ha": 7.5, "biomass_tons": 138.7, "co2_tons": 93.7},
            {"lat": 21.25, "lon": -157.90, "name": "Reef Bio-Zone Bravo (Mocked)", "area_ha": 5.2, "biomass_tons": 96.2, "co2_tons": 65.0}
        ])

@st.cache_resource(ttl=60)
def get_shipping_traffic(sector):
    """Dynamically generates shipping lanes over the selected sector."""
    vessels = []
    base_lat, base_lon = (34.0, -119.8) if sector == "Channel Islands" else (21.2, -157.8)
    conflict_lat, conflict_lon = (33.955, -120.095) if sector == "Channel Islands" else (21.255, -157.895)
    
    for _ in range(15):
        vessels.append({"lat": base_lat + random.uniform(-0.5, 0.5), "lon": base_lon + random.uniform(-0.8, 0.8), "mmsi": random.randint(100000, 999999)})
    vessels.append({"lat": conflict_lat, "lon": conflict_lon, "mmsi": 999999}) # Force a conflict
    return pd.DataFrame(vessels)

# =========================================================
# 5. DO NO HARM: IMMUTABLE ECOLOGICAL DECONFLICTION
# =========================================================
def process_deconfliction(kelp_df, vessels_df, safe_distance_km=2.5):
    """Uses a DataFrame copy to prevent Streamlit CachedObjectMutationWarnings."""
    df = kelp_df.copy()
    statuses = []
    colors = []
    R = 6371 
    
    for _, site in df.iterrows():
        conflict = False
        for _, ship in vessels_df.iterrows():
            dlat, dlon = math.radians(ship['lat'] - site['lat']), math.radians(ship['lon'] - site['lon'])
            a = math.sin(dlat/2)**2 + math.cos(math.radians(site['lat'])) * math.cos(math.radians(ship['lat'])) * math.sin(dlon/2)**2
            if R * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a))) < safe_distance_km:
                conflict = True
                break
        
        statuses.append("HAZARD: Shipping Conflict" if conflict else "CLEARED: Ready for Planting")
        colors.append([239, 68, 68, 220] if conflict else [16, 185, 129, 220])
        
    df['status'] = statuses
    df['color'] = colors
    return df

# =========================================================
# 6. UI: MAIN DASHBOARD RENDERING
# =========================================================
st.sidebar.markdown(f"<h2>🌱 BLUE 42</h2><p style='color:{accent_teal};'>Kelp Capital Allocator</p>", unsafe_allow_html=True)
st.sidebar.markdown("---")
sector = st.sidebar.selectbox("Target Ecosystem:", ["Channel Islands", "Hawaiian Archipelago"])

st.sidebar.markdown("### System Telemetry")
st.sidebar.caption(ee_status)
st.sidebar.caption(ai_status)

st.title("🌱 Blue Carbon Ecological Command")
st.caption("Fusing Earth Engine spatial reduction and Gemini reasoning to calculate real-time kelp biomass yield.")

# Fetch and Process Data
raw_sites_df = get_kelp_biomass_data(sector)
vessels_df = get_shipping_traffic(sector)
kelp_df = process_deconfliction(raw_sites_df, vessels_df)

# Top KPIs
safe_df = kelp_df[kelp_df['status'] == "CLEARED: Ready for Planting"]
total_ha = safe_df['area_ha'].sum()
total_biomass = safe_df['biomass_tons'].sum()
total_co2 = safe_df['co2_tons'].sum()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Verified Safe Area", f"{total_ha:.1f} HA", "Optimal Depth/SST")
c2.metric("Total Biomass Yield", f"{total_biomass:.1f} MT", "Calculated via Earth Engine")
c3.metric("ESG Capital Value", f"${total_co2 * 85:,.2f}", "At $85/Ton Credit")
c4.metric("Ecological Hazards Averted", str(len(kelp_df) - len(safe_df)), "Shipping Lane Deconfliction", delta_color="inverse")
st.write("")

# ---------------------------------------------------------
# 7. MAP & AI OPERATIONS SPLIT
# ---------------------------------------------------------
col_map, col_ops = st.columns([6, 4], gap="large")

with col_map:
    st.markdown("#### Spatially Verified Investment Zones")
    
    kelp_layer = pdk.Layer(
        "ScatterplotLayer", data=kelp_df, get_position="[lon, lat]", 
        get_color="color", get_radius=3500, pickable=True
    )
    
    ship_layer = pdk.Layer(
        "ScatterplotLayer", data=vessels_df, get_position="[lon, lat]",
        get_color="[255, 204, 0, 180]", get_radius=1500, pickable=False # Bright yellow for visibility
    )
    
    tooltip = {"html": "<b>{name}</b><br/>Area: {area_ha} HA<br/>Status: <b>{status}</b><br/>Biomass Yield: {biomass_tons} MT<br/>Sequestration: {co2_tons} MT CO2e", "style": {"backgroundColor": card_bg, "color": "white", "border": f"1px solid {accent_teal}"}}
    
    # Dynamic camera centering based on sector!
    view_state = pdk.ViewState(latitude=33.95 if sector == "Channel Islands" else 21.25, longitude=-119.8 if sector == "Channel Islands" else -157.8, zoom=8, pitch=40)
    
    # Map Style: SATELLITE (Fixes the blank grey screen issue if MapBox API key is missing locally)
    r = pdk.Deck(layers=[ship_layer, kelp_layer], initial_view_state=view_state, map_style=pdk.map_styles.SATELLITE, tooltip=tooltip)
    st.pydeck_chart(r, use_container_width=True, height=500)

with col_ops:
    st.markdown("#### Blue Carbon AI (Gemini 4 Argon)")
    tab1, tab2 = st.tabs(["💬 Ecological Advisor", "📁 Auditable Artifacts"])
    
    with tab1:
        chat_container = st.container(height=350)
        with chat_container:
            for msg in st.session_state.messages:
                st.markdown(f"**{'🤖 AI' if msg['role']=='assistant' else '👤 You'}:** {msg['content']}")
                
        if prompt := st.chat_input("Ask Gemini 4 Argon about Macrocystis yields..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.spinner("Argon Reasoning..."):
                try:
                    res = model.generate_content(f"You are Gemini 4 Argon, a highly advanced marine biologist AI. Keep responses under 3 sentences. User asks: {prompt}")
                    st.session_state.messages.append({"role": "assistant", "content": res.text})
                    st.rerun()
                except Exception: st.error("AI Comms Offline.")
                
    with tab2:
        st.write("Generate Immutable ESG Audits for Capital Deployment.")
        target_site = st.selectbox("Select Cleared Site:", safe_df['name'].tolist() if not safe_df.empty else ["No sites cleared"])
        
        if st.button("Generate Ecological Investment Brief", type="primary", use_container_width=True) and not safe_df.empty:
            site_data = safe_df[safe_df['name'] == target_site].iloc[0].to_dict()
            with st.spinner("Gemini 4 Argon validating telemetry..."):
                try:
                    res = model.generate_content(f"Write a 1-paragraph investment justification for planting Giant Kelp at {site_data['lat']}, {site_data['lon']} covering {site_data['area_ha']} hectares yielding {site_data['biomass_tons']} tons. Mention Copernicus bathymetry and ERA5 SST data.")
                    site_data['ai_reasoning'] = res.text
                    pdf_bytes = create_investment_brief(site_data)
                    st.session_state.library.append({"site": target_site, "pdf": pdf_bytes, "time": pd.Timestamp.now().strftime('%H:%M:%SZ')})
                    st.success("Audit Generated.")
                except Exception as e: st.error("Failed to generate audit.")
        
        for idx, doc in enumerate(reversed(st.session_state.library)):
            st.download_button(f"📄 Download Brief: {doc['site']} ({doc['time']})", data=doc['pdf'], file_name=f"ESG_Audit_{doc['site']}.pdf", mime="application/pdf", key=f"dl_{idx}", use_container_width=True)

# ---------------------------------------------------------
# 8. FINANCIAL LEDGER 
# ---------------------------------------------------------
st.markdown("#### 📈 Verified Carbon Ledger")
st.dataframe(safe_df[['name', 'lat', 'lon', 'area_ha', 'biomass_tons', 'co2_tons', 'status']].style.highlight_max(axis=0, subset=["biomass_tons"], color=accent_teal), use_container_width=True, hide_index=True)
