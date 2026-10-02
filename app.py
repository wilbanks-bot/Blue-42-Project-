# ---------------------------------------------------------
# 6. MAIN DASHBOARD: THE EXECUTIVE STORYBOARD
# ---------------------------------------------------------
st.markdown(f"<h2 style='color: {text_color};'>Global Maritime Command Center</h2>", unsafe_allow_html=True)
st.markdown("<p class='hud-text' style='margin-bottom: 25px;'>Synthesizing planetary telemetry into predictive intelligence and actionable ESG workflows.</p>", unsafe_allow_html=True)

# Clean, elegant KPI row with Interactive Expanders
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"<div class='metric-card protection-card'><h4>🛡️ ACTIVE THREATS</h4><p class='kpi-value' style='color:{accent_red};'>1 VOI</p><span class='kpi-subtext'>Target masking identity near MPA</span></div>", unsafe_allow_html=True)
    with st.expander("📊 View Analytics & Recommendations"):
        st.markdown("""
        **📡 Data Analytics:**  
        Kinematic anomaly detected. Vessel MMSI 413000000 dropped AIS transmission 15nm from the MPA boundary. Speed reduced from 12 kts to 2.5 kts (loitering profile).
        
        **🧠 GenAI Recommendation:**  
        Deploy autonomous surface vehicle (ASV) or nearest Coast Guard cutter for visual identification. Initiate satellite Synthetic Aperture Radar (SAR) tasking to verify physical presence.
        """)

with col2:
    st.markdown(f"<div class='metric-card military-card'><h4>⚓ MILITARY ZONES</h4><p class='kpi-value' style='color:{accent_purple};'>SECURE</p><span class='kpi-subtext'>No incursions in weapons ranges</span></div>", unsafe_allow_html=True)
    with st.expander("📊 View Analytics & Recommendations"):
        st.markdown("""
        **📡 Data Analytics:**  
        Geospatial perimeter of active testing range remains clear of civilian AIS tracks. No kinetic intersection anomalies detected in the last 24 hours.
        
        **🧠 GenAI Recommendation:**  
        Maintain current geofence monitoring. Routine baseline established. No immediate action required.
        """)

with col3:
    st.markdown(f"<div class='metric-card'><h4>🌪️ RESILIENCE</h4><p class='kpi-value' style='color:{accent_blue};'>5 REROUTED</p><span class='kpi-subtext'>Avoiding extreme wave heights</span></div>", unsafe_allow_html=True)
    with st.expander("📊 View Analytics & Recommendations"):
        st.markdown("""
        **📡 Data Analytics:**  
        5 commercial vessels successfully diverted from severe gale polygon ($H_s \ge 6.1$m). Hydrodynamic drag coefficient reduced by 42% on average across the fleet.
        
        **🧠 GenAI Recommendation:**  
        Log 54 MT of Scope 3 Fuel Savings in the financial ledger. Alert port authorities of revised Estimated Time of Arrival (ETA) to manage Just-In-Time (JIT) anchorage and prevent port congestion.
        """)

with col4:
    st.markdown(f"<div class='metric-card mitigation-card'><h4>🌱 BLUE CARBON</h4><p class='kpi-value' style='color:{accent_green};'>14.2 HA</p><span class='kpi-subtext'>Optimal restoration sites verified</span></div>", unsafe_allow_html=True)
    with st.expander("📊 View Analytics & Recommendations"):
        st.markdown("""
        **📡 Data Analytics:**  
        Bathymetric depth (-5m to -30m) and Sea Surface Temperature (< 18°C) criteria met. 92% survival probability for *Macrocystis pyrifera* (Giant Kelp) against decadal heatwave trends.
        
        **🧠 GenAI Recommendation:**  
        Proceed with spatial asset minting. Package coordinates and telemetry data for Verra/Gold Standard registry validation to instantly unlock $187,500 in ESG capital financing.
        """)
