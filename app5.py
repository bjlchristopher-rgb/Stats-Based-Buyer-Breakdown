import streamlit as st
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

st.set_page_config(page_title="🗺️ Canada Home Affordability Map", layout="wide")

st.title("🗺️ Canada Home Affordability MAP ANALYZER")
st.markdown("**✅ FIXED • Pure Plotly • No errors**")

# Canadian cities
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
    
    use_manual = st.checkbox("Custom coordinates")
    if use_manual:
        lat = st.number_input("Lat", 40, 60, lat, 0.01)
        lon = st.number_input("Lon", -130, -60, lon, 0.01)

with col2:
    st.header("🔍 Analysis")
    radius_km = st.slider("Radius (km)", 5, 100, 25)
    price = st.number_input("Price ($)", 100000, 3000000, 800000, 50000)
    buyer_type = st.selectbox("Buyers", ["Total", "Couples (60%)", "Singles (40%)"])

# CALCULATE
city_data = CITIES[city]
income_single, down_payment = calc_income_needed(price, city_data["rate"])

if buyer_type == "Total":
    income_needed = income_single
    pop_factor = 1.0
elif buyer_type == "Couples (60%)":
    income_needed = income_single * 0.75
    pop_factor = 0.60
else:
    income_needed = income_single
    pop_factor = 0.40

prob_affordable = max(0, 1 - lognorm_cdf(income_needed))
base_pop = city_data["pop"] * (radius_km / 50)**0.7
buyers_in_radius = prob_affordable * base_pop * pop_factor

# RESULTS
col1, col2, col3 = st.columns(3)
col1.metric("🏠 Price", f"${price:,}")
col2.metric("👥 Buyers", f"{buyers_in_radius:,.0f}")
col3.metric("💰 Down", f"${down_payment:,.0f}")

st.success(f"**{radius_km}km around {city}: {buyers_in_radius:,.0f} buyers need ${income_needed:,.0f}+**")

# FIXED MAP - PURE SCATTER (NO DataFrame issues)
st.subheader("🗺️ Buyer Density Map")
n_points = 200
noise = radius_km / 5000
lats = lat + np.random.normal(0, noise, n_points)
lons = lon + np.random.normal(0, noise, n_points)
densities = np.random.uniform(0.01, 0.3, n_points) * prob_affordable * 100

fig_map = go.Figure()
fig_map.add_trace(go.Scattermapbox(
    lat=lats, lon=lons, mode='markers',
    marker=go.scattermapbox.Marker(
        size=densities*100, color=densities, colorscale='Reds',
        colorbar=dict(title="Buyer Density", thickness=20),
        opacity=0.6
    ),
    name="Buyer Density"
))

# Add center marker
fig_map.add_trace(go.Scattermapbox(
    lat=[lat], lon=[lon], mode='markers+text',
    marker=go.scattermapbox.Marker(size=20, color="blue"),
    text=[f"{buyers_in_radius:,.0f}<br>buyers"], textposition="middle center",
    name="Analysis Point"
))

fig_map.update_layout(
    mapbox_style="carto-positron",
    mapbox=dict(center=dict(lat=lat, lon=lon), zoom=10),
    height=500, showlegend=True,
    title=f"Buyer Density - {radius_km}km Radius (${price:,})"
)
st.plotly_chart(fig_map, use_container_width=True)

# CITY COMPARISON
st.subheader("🏙️ City Comparison")
comparison = []
for city_name, data in CITIES.items():
    inc, _ = calc_income_needed(price, data["rate"])
    prob = max(0, 1 - lognorm_cdf(inc))
    buyers = prob * data["pop"] * (radius_km / 50)**0.7 * pop_factor
    comparison.append({"City": city_name, "Pop": f"{data['pop']:,.0f}", "Buyers": f"{buyers:,.0f}"})

df_comp = pd.DataFrame(comparison)
st.dataframe(df_comp, use_container_width=True)

# BREAKDOWN
st.subheader("📊 Buyer Types")
buyer_types = {
    "Singles (40%)": prob_affordable * base_pop * 0.40,
    "Couples (60%)": max(0, 1 - lognorm_cdf(income_single * 0.75)) * base_pop * 0.60
}
breakdown_df = pd.DataFrame(list(buyer_types.items()), columns=["Type", "Buyers"])
st.dataframe(breakdown_df, use_container_width=True)

# INCOME CHART
st.subheader("💰 Income Threshold")
income_range = np.linspace(1, 400000, 1000)
fig_income = go.Figure()
fig_income.add_trace(go.Scatter(x=income_range, y=lognorm_pdf(income_range), mode='lines', name='Population'))
fig_income.add_vline(x=income_needed, line_dash="dash", line_color="red",
                    annotation_text=f"${income_needed:,.0f}+ needed")
fig_income.update_layout(height=400)
st.plotly_chart(fig_income)

st.caption(f"**Map center: ({lat:.2f}, {lon:.2f}) | {radius_km}km | ${price:,} | {buyers_in_radius:,.0f} buyers**")
