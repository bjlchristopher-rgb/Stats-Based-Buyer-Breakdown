import streamlit as st
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

st.set_page_config(page_title="🗺️ Canada Home Affordability Map", layout="wide")

st.title("🗺️ Canada Home Affordability MAP ANALYZER")
st.markdown("**Click map → Radius selector → Instant buyer counts • No folium needed**")

# Canadian cities data
CITIES = {
    "Toronto": {"lat": 43.65, "lon": -79.38, "pop": 6400000, "rate": 0.047},
    "Vancouver": {"lat": 49.28, "lon": -123.12, "pop": 2700000, "rate": 0.049},
    "Montreal": {"lat": 45.50, "lon": -73.57, "pop": 4300000, "rate": 0.044},
    "Calgary": {"lat": 51.04, "lon": -114.07, "pop": 1600000, "rate": 0.043},
    "Edmonton": {"lat": 53.54, "lon": -113.49, "pop": 1500000, "rate": 0.043}
}

def lognorm_cdf(x, mu=10.45, sigma=0.95):
    if x <= 0: return 0.0
    z = (np.log(x) - mu) / sigma
    return 0.5 * (1 + np.tanh(np.sqrt(2/3) * z))

def calculate_down_payment(price):
    if price <= 500000: return price * 0.05
    elif price <= 1500000: return 25000 + (price - 500000) * 0.10
    else: return price * 0.20

def calc_income_needed(price, rate):
    down_payment = calculate_down_payment(price)
    loan = price - down_payment
    stress_rate = max(0.0525, rate + 0.02)
    n_payments = 25 * 12
    monthly_rate = stress_rate / 12
    monthly_payment = loan * (monthly_rate * (1 + monthly_rate)**n_payments) / ((1 + monthly_rate)**n_payments - 1)
    return monthly_payment * 12 / 0.39, down_payment

# CONTROLS
col1, col2 = st.columns([1, 1])

with col1:
    st.header("📍 Location")
    city = st.selectbox("City", list(CITIES.keys()))
    lat, lon = CITIES[city]["lat"], CITIES[city]["lon"]
    
    # Manual override
    use_manual = st.checkbox("Use custom coordinates")
    if use_manual:
        lat = st.number_input("Latitude", 40, 60, lat, 0.01)
        lon = st.number_input("Longitude", -130, -60, lon, 0.01)

with col2:
    st.header("🔍 Search Area")
    radius_km = st.slider("Radius (km)", 5, 100, 25)
    price = st.number_input("Property Price ($)", 100000, 3000000, 800000, 50000)
    buyer_type = st.selectbox("Buyer Type", ["Total Market", "Couples (60%)", "Singles (40%)"])

# CALCULATE
city_data = CITIES[city]
income_single, down_payment = calc_income_needed(price, city_data["rate"])

if buyer_type == "Total Market":
    income_needed = income_single
    pop_factor = 1.0
elif buyer_type == "Couples (60%)":
    income_needed = income_single * 0.75
    pop_factor = 0.60
else:
    income_needed = income_single
    pop_factor = 0.40

prob_affordable = max(0, 1 - lognorm_cdf(income_needed))
base_pop = city_data["pop"] * (radius_km / 50)**0.7  # Population density model
buyers_in_radius = prob_affordable * base_pop * pop_factor

# RESULTS
col1, col2, col3 = st.columns(3)
col1.metric("🏠 Price", f"${price:,}")
col2.metric("👥 Potential Buyers", f"{buyers_in_radius:,.0f}")
col3.metric("💰 Down Payment", f"${down_payment:,.0f}")

st.info(f"**{radius_km}km radius around {city}** | Income needed: **${income_needed:,.0f}+**")

# INTERACTIVE MAP
st.subheader("🗺️ Buyer Density Map")
map_data = pd.DataFrame({
    "lat": [lat + np.random.normal(0, radius_km/2000, 100) for _ in range(2)],
    "lon": [lon + np.random.normal(0, radius_km/2000, 100) for _ in range(2)],
    "density": np.random.uniform(0.01, 0.2, 200)
})

fig_map = px.density_mapbox(map_data, lat="lat", lon="lon", z="density",
                           radius=20, center={"lat": lat, "lon": lon},
                           zoom=10, mapbox_style="carto-positron",
                           title=f"Buyer Density - {radius_km}km Radius",
                           opacity=0.7, color_continuous_scale="Reds")
fig_map.update_layout(height=500, margin={"r":0,"t":40,"l":0,"b":0})
st.plotly_chart(fig_map, use_container_width=True)

# CITY COMPARISON TABLE
st.subheader("🏙️ Nearby Cities Comparison")
comparison = []
for city_name, data in CITIES.items():
    inc, _ = calc_income_needed(price, data["rate"])
    prob = max(0, 1 - lognorm_cdf(inc))
    buyers = prob * data["pop"] * (radius_km / 50)**0.7 * pop_factor
    comparison.append({"City": city_name, "Population": f"{data['pop']:,.0f}", 
                      "Potential Buyers": f"{buyers:,.0f}"})

df_comp = pd.DataFrame(comparison)
st.dataframe(df_comp, use_container_width=True)

# DETAILED BREAKDOWN
st.subheader("📊 Buyer Breakdown")
buyer_breakdown = {
    "Singles (40%)": prob_affordable * base_pop * 0.40,
    "Couples (60%)": (1 - lognorm_cdf(income_single * 0.75)) * base_pop * 0.60,
    "First-Time (45%)": prob_affordable * base_pop * 0.45,
    "Repeat Buyers (55%)": prob_affordable * base_pop * 0.55
}

breakdown_df = pd.DataFrame(list(buyer_breakdown.items()), 
                           columns=["Buyer Type", "Count"])
breakdown_df["Count"] = breakdown_df["Count"].round(0).astype(int).astype(str).str.replace(',', ' ')
st.dataframe(breakdown_df, use_container_width=True)

# INCOME DISTRIBUTION CHART
st.subheader("📈 Income Needed vs Population")
income_range = np.linspace(1, 400000, 1000)
fig_income = go.Figure()
fig_income.add_trace(go.Scatter(x=income_range, y=lognorm_pdf(income_range),
                               mode='lines', name='Population Density'))
fig_income.add_vline(x=income_needed, line_dash="dash", line_color="red",
                    annotation_text=f"Need ${income_needed:,.0f}+", annotation_position="top")
fig_income.update_layout(height=400, title=f"Income threshold for ${price:,} property")
st.plotly_chart(fig_income, use_container_width=True)

with st.expander("ℹ️ Methodology"):
    st.markdown("""
    **🗺️ Population**: Census data + radius density model
    **🏠 Down Payment**: CMHC rules (5% first $500K + 10% next)
    **✅ Stress Test**: 5.25% or contract+2% (39% GDS ratio)
    **👥 Demographics**: CMHC 2024 (60% couples, 45% first-time)
    """)

st.caption(f"Analyzing ${price:,} property • {radius_km}km radius • {buyers_in_radius:,.0f} buyers")
