import streamlit as st
import pydeck as pdk
import pandas as pd
import numpy as np
import math
import random

# ---------------------------------------------------------
# 1. PAGE SETUP & ENTERPRISE UX THEME
# ---------------------------------------------------------
st.set_page_config(layout="wide", page_title="Blue 42 Strategic Command", page_icon="🌐", initial_sidebar_state="expanded")

# Professional, eye-friendly color palettes
night_vision = st.sidebar.toggle("🌙 Executive Dark Mode", value=True)

if night_vision:
    bg_color = "#0f172a"          # Slate 900
    card_bg = "#1e293b"           # Slate 800
    text_color = "#f8fafc"        # Slate 50
    accent_blue = "#38bdf8"       # Light Blue
    accent_red = "#fb7185"        # Soft Rose/Red
    accent_green = "#34d399"      # Soft Emerald
    map_style = "dark"            # Guaranteed free PyDeck style
else:
    bg_color = "#f8fafc"
    card_bg = "#ffffff"
    text_color = "#0f172a"
    accent_blue = "#0284c7"
    accent_red = "#e11d48"
    accent_green = "#059669"
    map_style = "light"           # Guaranteed free PyDeck style

css = f"""
<style>
    /* Clean Enterprise Typography and Spacing */
    .stApp {{ background-color: {bg_color}; color: {text_color}; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }}
    
    /* Elegant Metric Cards */
    .metric-card {{ 
        background-color: {card_bg}; 
        padding: 24px; 
        border-radius: 8px; 
        border-top: 4px solid {accent_blue}; 
        margin-bottom: 16px; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); 
    }}
    .protection-card {{ border-top-color: {accent_red}; }}
    .mitigation-card {{ border-top-color: {accent_green}; }}
    
    h2, h3, h4 {{ color: {text_color}; font-weight: 600; margin-top: 0; letter-spacing: -0.01em; }}
    h4 {{ font-size: 0.85rem; text-transform: uppercase; color: #64748b; margin-bottom: 12px; }}
    
    .kpi-value {{ font-size: 2.2rem; font-weight: 700; margin: 0; line-height: 1.1; }}
    .kpi-subtext {{ font-size: 0.85rem; color: #64748b; margin-top: 6px; display: block; }}
    
    /* Sidebar Styling */
    div[data-testid="stSidebar"] {{ background-color: {card_bg}; border-right: 1px solid rgba(100,116,139,0.2); }}
</style>
"""
st.markdown(css, unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. SIDEBAR: STRATEGIC NAVIGATION
# ---------------------------------------------------------
st.sidebar.markdown(f"""
<div style="margin-bottom: 30px; text-align: center;">
    <div style="font-size: 40px; color: {accent_blue}; line-height: 1;">🌊</div>
    <div style="font-weight: 700; font-size: 1.3rem; letter-spacing: 1.5px; margin-top: 10px;">BLUE 42 COMMAND</div>
    <div style="color: #64748b; font-size: 0.75rem; font-weight: 500; letter-spacing: 1px; text-transform: uppercase;">Maritime Intelligence</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("### 🌍 REGIONAL DEPLOYMENT")
sector_mode = st.sidebar.selectbox("Operational Theater:", ["US West Coast (Channel Islands)", "Pacific Operations (Hawaiian Islands)"], label_visibility="collapsed")
st.sidebar.markdown("---")

st.sidebar.markdown("### 📊 TACTICAL OVERLAYS")
show_iuu = st.sidebar.checkbox("🛡️ Marine Protected Areas", value=True)
show_weather = st.sidebar.checkbox("⛈️ Extreme Weather Hazards", value=True)
show_depth = st.sidebar.checkbox("🌱 Blue Carbon Sites", value=True)
st.sidebar.markdown("---")

# ---------------------------------------------------------
# 3. EXECUTIVE STORYBOARD & KPIs
# ---------------------------------------------------------
st.markdown(f"<h2 style='color: {text_color}; text-align: center; margin-bottom: 8px;'>Global Maritime Command Center</h2>", unsafe_allow_html=True)
st.markdown(f"<p style='color: #64748b; text-align: center; font-size: 1.1rem; margin-bottom: 30px;'>Synthesizing planetary telemetry into predictive intelligence and actionable workflows.</p>", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"<div class='metric-card protection-card'><h4>🛡️ ACTIVE THREATS</h4><p class='kpi-value' style='color:{accent_red};'>1 CRITICAL</p><span class='kpi-subtext'>Target masking identity near MPA</span></div>", unsafe_allow_html=True)
with col2:
    st.markdown(f"<div class='metric-card'><h4>🌪️ RESILIENCE</h4><p class='kpi-value' style='color:{accent_blue};'>5 REROUTED</p><span class='kpi-subtext'>Avoiding extreme wave heights</span></div>", unsafe_allow_html=True)
with col3:
    st.markdown(f"<div class='metric-card mitigation-card'><h4>🌱 BLUE CARBON</h4><p class='kpi-value' style='color:{accent_green};'>14.2 HA</p><span class='kpi-subtext'>Optimal restoration sites verified</span></div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 4. ROBUST GEOSPATIAL DATA STRUCTURES
# ---------------------------------------------------------
# We use strictly formatted lists to guarantee PyDeck never crashes
polygon_data = []
scatter_data = []
path_data = []

if sector_mode == "US West Coast (Channel Islands)":
    view_state = pdk.ViewState(latitude=33.9, longitude=-119.5, zoom=7.5, pitch=45, bearing=-10)
    base_lat, base_lon = 33.8, -119.5
    
    if show_iuu:
        polygon_data.append({
            "polygon": [[[-120.2, 33.8], [-119.2, 33.8], [-119.2, 34.2], [-120.2, 34.2]]],
            "name": "Channel Islands Marine Sanctuary", "primary": "Status: Fully Protected", "secondary": "Jurisdiction: Federal",
            "analytics": "Zero-take zone. Continuous AI surveillance active to detect illicit 'dark fleet' incursions.", "source": "UNEP-WCMC",
            "fill_color": [16, 185, 129, 30], "line_color": [16, 185, 129, 200]
        })
    if show_weather:
        polygon_data.append({
            "polygon": [[[-119.5, 33.6], [-119.1, 33.6], [-119.1, 34.0], [-119.5, 34.0]]],
            "name": "Severe Gale Warning", "primary": "Intensity: H_s > 6.1m (20ft)", "secondary": "Wind: Sustained 45 knots",
            "analytics": "Extreme hydrodynamic drag detected. Routing through this zone risks cargo loss and increases fuel consumption by 12%.", "source": "WeatherNext 3",
            "fill_color": [225, 29, 72, 30], "line_color": [225, 29, 72, 180]
        })
        path_data.append({
            "path": [[[-119.8, 33.5], [-119.6, 33.4], [-119.0, 33.4], [-118.8, 33.8]]],
            "name": "AI Optimized Logistics Route", "primary": "Status: Active Reroute", "secondary": "Fuel Averted: 54 MT",
            "analytics": "Predictive vector safely circumvents the Gale Warning polygon, preserving operational continuity.", "source": "AlphaEarth",
            "color": [14, 165, 233, 255]
        })
    if show_depth:
        scatter_data.append({
            "lat": 34.02, "lon": -119.55, "name": "Verified Carbon Sink K-1", "primary": "Area: 5.1 HA", "secondary": "Viability Index: 98%",
            "analytics": "Depth 14m, SST 16.5°C. Site meets all thermal survivability thresholds against decadal heatwaves.", "source": "DeepMind SDM",
            "color": [16, 185, 129, 220], "radius": 3500
        })

else: # HAWAII
    view_state = pdk.ViewState(latitude=21.4, longitude=-157.9, zoom=7.5, pitch=45, bearing=-10)
    base_lat, base_lon = 21.2, -158.0
    
    if show_iuu:
        polygon_data.append({
            "polygon": [[[-158.3, 21.4], [-157.8, 21.4], [-157.8, 21.7], [-158.3, 21.7]]],
            "name": "Kaena Point MPA Expansion", "primary": "Status: Fully Protected", "secondary": "Jurisdiction: State/Federal",
            "analytics": "Critical habitat preservation area. High-value target for illicit commercial harvesting.", "source": "UNEP-WCMC",
            "fill_color": [16, 185, 129, 30], "line_color": [16, 185, 129, 200]
        })
    if show_weather:
        polygon_data.append({
            "polygon": [[[-158.2, 21.0], [-157.5, 21.0], [-157.5, 21.4], [-158.2, 21.4]]],
            "name": "Tropical Squall Hazard", "primary": "Intensity: H_s > 4.5m", "secondary": "Wind: Gusts to 35 knots",
            "analytics": "Localized squall creating supply chain delays for Honolulu port approaches.", "source": "WeatherNext 3",
            "fill_color": [225, 29, 72, 30], "line_color": [225, 29, 72, 180]
        })
    if show_depth:
        scatter_data.append({
            "lat": 21.45, "lon": -157.8, "name": "Verified Reef Restoration Zone", "primary": "Area: 6.5 HA", "secondary": "Viability Index: 96%",
            "analytics": "Depth 8m, SST 24.5°C. Optimal ESG rehabilitation zone in Kaneohe Bay.", "source": "DeepMind SDM",
            "color": [16, 185, 129, 220], "radius": 3500
        })

# --- DYNAMIC VESSEL FLEET ---
for i in range(15):
    sog = random.uniform(10.0, 22.0)
    cog = random.uniform(0, 360)
    lat, lon = base_lat + random.uniform(-1.5, 1.5), base_lon + random.uniform(-2.0, 2.0)
    
    scatter_data.append({
        "lat": lat, "lon": lon, "name": f"COMMERCIAL VESSEL (MMSI: 36{random.randint(10000, 99999)})", 
        "primary": f"Speed: {sog:.1f} kts", "secondary": f"Heading: {cog:.1f}°", 
        "analytics": "Vessel kinetics operate within nominal parameters. Compliant track.", "source": "Verified AIS",
        "color": [100, 116, 139, 180], "radius": 1200 # Subtle grey/blue for nominal ships to reduce clutter
    })
    
    # Calculate tactical ARPA heading vector lines safely
    vec_len = max(sog * 0.003, 0.01)
    path_data.append({
        "path": [[[lon, lat], [lon + vec_len * math.sin(math.radians(cog)), lat + vec_len * math.cos(math.radians(cog))]]],
        "name": "Vessel Heading Vector", "primary": f"Speed: {sog:.1f} kts", "secondary": f"Heading: {cog:.1f}°",
        "analytics": "Kinematic trajectory calculation.", "source": "AIS",
        "color": [100, 116, 139, 180]
    })

# The Critical Dark Target
dt_lat, dt_lon = base_lat + 0.15, base_lon - 0.65
scatter_data.append({
    "lat": dt_lat, "lon": dt_lon, "name": "UNVERIFIED DARK TARGET", "primary": "Speed: 2.5 kts (Loitering)", "secondary": "Status: CRITICAL ANOMALY",
    "analytics": "Vessel disabled transponder 15nm from MPA. Kinematics strongly suggest illicit fishing deployment. Intercept recommended.", "source": "AIS / DeepMind Anomaly Detection",
    "color": [225, 29, 72, 255], "radius": 2500
})
path_data.append({
    "path": [[[dt_lon, dt_lat], [dt_lon + 0.01, dt_lat + 0.005]]],
    "name": "Target Heading Vector", "primary": "Speed: 2.5 kts", "secondary": "Heading: 80°",
    "analytics": "Anomalous kinematic trajectory.", "source": "AIS",
    "color": [225, 29, 72, 255]
})

# ---------------------------------------------------------
# 5. ASSEMBLE PYDECK MAP LAYERS SAFELY
# ---------------------------------------------------------
map_layers = []

if polygon_data:
    map_layers.append(pdk.Layer("PolygonLayer", data=pd.DataFrame(polygon_data), get_polygon="polygon", get_fill_color="fill_color", get_line_color="line_color", line_width_min_pixels=2, pickable=True))
if path_data:
    map_layers.append(pdk.Layer("PathLayer", data=pd.DataFrame(path_data), get_path="path", get_color="color", width_min_pixels=3, pickable=True))
if scatter_data:
    map_layers.append(pdk.Layer("ScatterplotLayer", data=pd.DataFrame(scatter_data), get_position="[lon, lat]", get_fill_color="color", get_radius="radius", pickable=True))

# Ultra-Professional Information Tooltip
tooltip_html = f"""
<div style='background: {card_bg}; border: 1px solid {accent_blue}; padding: 16px; border-radius: 6px; color: {text_color}; font-family: Inter, sans-serif; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); max-width: 300px;'>
    <div style='font-size: 1.05rem; font-weight: 600; color: {accent_blue}; margin-bottom: 6px;'>{{name}}</div>
    <div style='font-size: 0.85rem; color: #64748b; margin-bottom: 2px;'>{{primary}}</div>
    <div style='font-size: 0.85rem; color: #64748b; margin-bottom: 12px;'>{{secondary}}</div>
    <div style='border-top: 1px solid rgba(100, 116, 139, 0.2); padding-top: 10px;'>
        <span style='color: {accent_green}; font-weight: 600; font-size: 0.8rem;'>AI ANALYTICS:</span><br/>
        <span style='font-size: 0.85rem; line-height: 1.5; color: {text_color};'>{{analytics}}</span>
    </div>
    <div style='margin-top: 10px; font-size: 0.75rem; color: #64748b; font-style: italic;'>Source: {{source}}</div>
</div>
"""
custom_tooltip = {"html": tooltip_html, "style": {"backgroundColor": "transparent", "padding": "0"}}

st.markdown("#### 🗺️ TACTICAL BATTLESPACE OVERVIEW", unsafe_allow_html=True)
r = pdk.Deck(layers=map_layers, initial_view_state=view_state, map_style=map_style, tooltip=custom_tooltip)
st.pydeck_chart(r, use_container_width=True)

# ---------------------------------------------------------
# 6. DEEP DIVE ANALYTICS SECTION
# ---------------------------------------------------------
st.write("---")
col_a, col_b = st.columns([1, 1])

with col_a:
    st.markdown(f"<h3 style='color: {accent_red};'>🛡️ Threat Interdiction Analytics</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color: #64748b; font-size: 0.9rem;'>When a vessel disables its AIS transponder near a Marine Protected Area (MPA), it correlates strongly with Illegal, Unreported, and Unregulated (IUU) fishing.</p>", unsafe_allow_html=True)
    st.markdown("#### The Mathematical Trigger")
    st.code("IF (Distance_to_MPA < 15nm) \nAND (Signal_Loss > 60m) \nAND (Speed < 4kts):\n   TRIGGER = HIGH_THREAT", language="python")
    
    if st.button("🛰️ INITIATE SAR TASKING", use_container_width=True):
        st.session_state.sar_tasked = True
    if st.session_state.sar_tasked:
        st.success("SAR CONFIRMATION: 45m metallic hull detected. Intercept authorized.")

with col_b:
    st.markdown(f"<h3 style='color: {accent_blue};'>🌪️ Supply Chain Resilience Analytics</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color: #64748b; font-size: 0.9rem;'>By avoiding severe weather polygons, fleets save millions of dollars and drastically cut Scope 3 emissions.</p>", unsafe_allow_html=True)
    st.markdown("#### Hydrodynamic Drag")
    st.latex(r"R_T = \frac{1}{2} \rho v^2 S C_T")
    st.markdown(f"<span style='color: #64748b; font-size: 0.85rem;'>Altering the route to avoid $H_s \ge 6.1$m waves drops the drag coefficient ($C_T$) by ~42%.</span>", unsafe_allow_html=True)
