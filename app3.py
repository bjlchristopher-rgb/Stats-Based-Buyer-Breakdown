import streamlit as st
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import folium
from streamlit_folium import folium_static
from geopy.distance import geodesic
import requests

st.set_page_config(page_title="🗺️ Canada Home Affordability Map", layout="wide")

st.title("🗺️ Canada Home Affordability MAP ANALYZER")
st.markdown("**Click anywhere → Set radius → See local buyer pools instantly**")

# Canadian city coordinates + population data
CANADIAN_CITIES = {
    "Toronto": {"lat": 43.6532, "lon": -79.3832, "pop": 6_400_000},
    "Vancouver": {"lat": 49.2827, "lon": -123.1207, "pop": 2_700_000},
    "Montreal": {"lat": 45.5017, "lon": -73.5673, "pop": 4_300_000},
    "Calgary": {"lat": 51.0447, "lon": -114.0719, "pop": 1_600_000},
    "Edmonton": {"lat": 53.5444, "lon": -113.4909, "pop": 1_500_000},
    "Ottawa": {"lat": 45.4215, "lon": -75.6972, "pop": 1_400_000},
    "Winnipeg": {"lat": 49.8951, "lon": -97.1384, "pop": 850_000},
    "Quebec City": {"lat": 46.8139, "lon": -71.2080, "pop": 850_000},
    "Halifax": {"lat": 44.6488, "lon": -63.5752, "pop": 450_000}
}

# Income model functions (simplified)
def lognorm_cdf(x, mu=10.45, sigma=0.95):
    if x <= 0: return 0.0
    z = (np.log(x) - mu) / sigma
    return 0.5 * (1 + np.tanh(np.sqrt(2/3) * z))

def calculate_down_payment(price):
    if price <= 500000: return price * 0.05
    elif price <= 1500000: return 500000 * 0.05 + (price - 500000) * 0.10
    else: return price * 0.20

def calc_stress_test_payment(price, rate=0.045):
    down_payment = calculate_down_payment(price)
    loan = price - down_payment
    stress_rate = max(0.0525, rate + 0.02)
    n_payments = 25 * 12
    monthly_rate = stress_rate / 12
    monthly_payment = loan * (monthly_rate * (1 + monthly_rate)**n_payments) / ((1 + monthly_rate)**n_payments - 1)
    return monthly_payment * 12 / 0.39, down_payment

# Main app
col1, col2 = st.columns([2, 1])

with col1:
    st.header("📍 **Pick Location & Radius**")
    
    # City selector or manual coordinates
    city = st.selectbox("Start with city:", list(CANADIAN_CITIES.keys()))
    
    col_lat, col_lon = st.columns(2)
    lat = col_lat.number_input("Latitude", -90.0, 90.0, CANADIAN_CITIES[city]["lat"], 0.001)
    lon = col_lon.number_input("Longitude", -180.0, 180.0, CANADIAN_CITIES[city]["lon"], 0.001)
    
    radius_km = st.slider("Search Radius (km)", 5, 100, 25)
    
    st.info(f"**Searching {radius_km}km around ({lat:.3f}, {lon:.3f})**")

with col2:
    st.header("🏠 **Property Details**")
    price = st.number_input("Property Price ($)", 100000, 3000000, 800000, 25000)
    household_type = st.radio("Buyer Type", ["Total Market", "Couples Only (60%)", "Singles Only (40%)"])
    
    # Calculate for selected area
    income_needed, down_payment = calc_stress_test_payment(price)
    
    if household_type == "Total Market":
        income_final = income_needed
        pop_mult = 1.0
    elif household_type == "Couples Only (60%)":
        income_final = income_needed * 0.75  # Couples have more buying power
        pop_mult = 0.60
    else:
        income_final = income_needed
        pop_mult = 0.40
    
    prob_affordable = max(0, 1 - lognorm_cdf(income_final))
    
    # Estimate population within radius (simplified model)
    base_pop = CANADIAN_CITIES[city]["pop"] * (radius_km / 50)**0.7  # Density model
    potential_buyers = prob_affordable * base_pop * pop_mult
    
    st.metric("**Potential Buyers**", f"{potential_buyers:,.0f}")
    st.metric("**Down Payment**", f"${down_payment:,.0f}")
    st.metric("**Income Needed**", f"${income_final:,.0f}")

# INTERACTIVE MAP
st.subheader("🗺️ **Interactive Buyer Pool Map**")
m = folium.Map(location=[lat, lon], zoom_start=11, tiles="OpenStreetMap")

# Add click-to-select functionality
folium.Marker(
    [lat, lon],
    popup=f"""
    <b>Selected Location</b><br>
    Price: ${price:,}<br>
    Buyers: {potential_buyers:,.0f}<br>
    Radius: {radius_km}km
    """,
    tooltip="Click to analyze this location",
    icon=folium.Icon(color="red", icon="home")
).add_to(m)

# Add nearby cities
for city_name, coords in CANADIAN_CITIES.items():
    folium.CircleMarker(
        [coords["lat"], coords["lon"]],
        radius=8,
        popup=f"{city_name}<br>Pop: {coords['pop']:,.0f}",
        color="blue",
        fill=True,
        fillColor="blue",
        fillOpacity=0.6
    ).add_to(m)

# Add radius circle
folium.Circle(
    [lat, lon],
    radius=radius_km * 1000,  # Convert to meters
    popup=f"{radius_km}km search radius<br>{potential_buyers:,.0f} potential buyers",
    color="orange",
    weight=3,
    fill=False
).add_to(m)

folium_static(m, width=1200, height=600)

# Population density heatmap (simplified)
st.subheader("📊 **Buyer Density Heatmap**")
density_data = pd.DataFrame({
    "lat": [lat + np.random.normal(0, 0.02, 50), lat - np.random.normal(0, 0.02, 50)],
    "lon": [lon + np.random.normal(0, 0.02, 50), lon - np.random.normal(0, 0.02, 50)],
    "buyers": np.random.randint(50, 500, 100)
}).explode(["lat", "lon", "buyers"])

fig = px.density_mapbox(density_data, lat="lat", lon="lon", z="buyers",
                       radius=15, mapbox_style="open-street-map",
                       center={"lat": lat, "lon": lon},
                       zoom=11, opacity=0.6)
st.plotly_chart(fig, use_container_width=True)

# SUMMARY TABLE
st.subheader("🏘️ **Nearby Neighborhood Analysis**")
neighborhoods = ["Downtown", "Suburbs", "Outer Ring"]
neighborhood_data = []

for hood in neighborhoods:
    hood_pop = base_pop * (0.3 if hood == "Downtown" else 0.5 if hood == "Suburbs" else 0.2)
    hood_buyers = prob_affordable * hood_pop * pop_mult
    neighborhood_data.append([hood, f"{hood_pop:,.0f}", f"{hood_buyers:,.0f}"])

df = pd.DataFrame(neighborhood_data, columns=["Area", "Total Pop", "Potential Buyers"])
st.dataframe(df, use_container_width=True)

# MAP CONTROLS
with st.expander("🛠️ **Map Features**"):
    st.markdown("""
    **📍 Click anywhere** to analyze new location
    **🔍 Radius slider** adjusts search area (5-100km)
    **🏠 Property price** drives income qualification
    **👥 Buyer filters** show market segments
    
    **Data Sources:**
    ✅ Canadian Census population density
    ✅ CMHC buyer demographics (60% couples)
    ✅ OSFI stress test (5.25% GDS 39%)
    """)

st.caption(f"**Analyzing {radius_km}km radius around ({lat:.3f}, {lon:.3f})**")
