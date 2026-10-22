<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="color-scheme" content="light only">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=Space+Grotesk:wght@700&display=swap" rel="stylesheet">
<style>
  body {
    margin: 0;
    padding: 4px;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background: transparent;
    color: #0F172A;
  }
  .accent-bar {
    height: 6px;
    width: 100%;
    background: linear-gradient(90deg, #4285F4 0%, #4285F4 25%, #EA4335 25%, #EA4335 50%, #FBBC05 50%, #FBBC05 75%, #34A853 75%, #34A853 100%);
    border-radius: 12px 12px 0 0;
  }
  .hero-card {
    background: linear-gradient(135deg, #FFFFFF 0%, #F0F7FF 55%, #ECFDF5 100%);
    border: 1.5px solid #BFDBFE;
    border-top: none;
    border-radius: 0 0 14px 14px;
    padding: 20px 24px;
    box-shadow: 0 6px 18px rgba(15, 23, 42, 0.06);
  }
  .badge-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 10px;
  }
  .pill {
    font-size: 11.5px;
    font-weight: 800;
    padding: 4px 10px;
    border-radius: 999px;
    letter-spacing: 0.3px;
    text-transform: uppercase;
  }
  .pill-blue { background: #DBEAFE; color: #1E40AF; border: 1px solid #93C5FD; }
  .pill-green { background: #DCFCE7; color: #166534; border: 1px solid #86EFAC; }
  .pill-amber { background: #FEF3C7; color: #92400E; border: 1px solid #FCD34D; }
  h1 {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 26px;
    margin: 0 0 8px 0;
    color: #0F172A;
  }
  .subtitle {
    font-size: 14.5px;
    line-height: 1.55;
    color: #334155;
    margin-bottom: 16px;
  }
  .kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(195px, 1fr));
    gap: 10px;
  }
  .kpi-box {
    background: #FFFFFF;
    border: 1.5px solid #CBD5E1;
    border-radius: 10px;
    padding: 10px 14px;
  }
  .kpi-label {
    font-size: 11px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    color: #475569;
  }
  .kpi-val {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 20px;
    font-weight: 800;
    margin: 3px 0;
  }
  .kpi-sub {
    font-size: 11.5px;
    font-weight: 600;
    color: #334155;
  }
</style>
</head>
<body>
  <div class="accent-bar"></div>
  <div class="hero-card">
    <div class="badge-row">
      <span class="pill pill-blue">🏅 2026 Google Sustainability Grand Challenge</span>
      <span class="pill pill-green">🌲 Mode 1: Stationary Kelp Restoration</span>
      <span class="pill pill-amber">🚨 Mode 2: Pelagic Sargassum Interception</span>
    </div>
    <h1>🌊 BLUE 42: The Kelp Contender — Planetary Ocean Capital &amp; MRV OS</h1>
    <div class="subtitle">
      An end-to-end decision-support, multi-sensor verification (Sentinel-2/3 NDKI/FAI + Sentinel-1 SAR + NASA PACE + ROV + ITU SMART Subsea Cables), and institutional finance engine scaling <b>Stationary Kelp Restoration</b> and <b>Pelagic Sargassum Interception &amp; Methane Avoidance</b> across <b>8 global ocean basins (96 candidate vectors)</b>.
    </div>
    <div class="kpi-grid">
      <div class="kpi-box" style="border-left: 5px solid #188038;">
        <div class="kpi-label">🟢 M — Carbon &amp; Methane Mitigation</div>
        <div class="kpi-val" style="color: #188038;">10,175 MT CO₂e/yr</div>
        <div class="kpi-sub">+58,539 MT CO₂e/yr Avoided CH₄ (GWP-20)</div>
      </div>
      <div class="kpi-box" style="border-left: 5px solid #1A73E8;">
        <div class="kpi-label">🔵 A — Coastal Surge &amp; Reef Adaptation</div>
        <div class="kpi-val" style="color: #1A73E8;">$179.9M / yr</div>
        <div class="kpi-sub">Storm Wave &amp; Beach Stranding Avoided</div>
      </div>
      <div class="kpi-box" style="border-left: 5px solid #7C3AED;">
        <div class="kpi-label">🟣 P — 30x30 Marine Protection Halo</div>
        <div class="kpi-val" style="color: #6B21A8;">14,087 Hectares</div>
        <div class="kpi-sub">IUCN Red List, eDNA (H') &amp; Ω_arag Verified</div>
      </div>
      <div class="kpi-box" style="border-left: 5px solid #D97706;">
        <div class="kpi-label">🏦 Institutional CDR Economics</div>
        <div class="kpi-val" style="color: #B45309;">$24–$68 / MT</div>
        <div class="kpi-sub">Co-Product Subsidized • -2.8% Blended WACC</div>
      </div>
    </div>
  </div>
</body>
</html>
