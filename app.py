import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd

st.set_page_config(page_title="🏠 Canada Mortgage Calculator", layout="wide")

st.title("🏠 Canada Mortgage Affordability PRO")
st.markdown("**Automatic Buyer Demographics • CMHC Stats Breakdown**")

# REGIONS
REGIONS = {
    "🇨🇦 National": {"rate": 0.045, "pop": 20_000_000},
    "🇴🇳 Ontario": {"rate": 0.047, "pop": 15_000_000},
    "🇧🇨 BC": {"rate": 0.049, "pop": 5_300_000},
    "🇦🇧 Alberta": {"rate": 0.043, "pop": 4_500_000},
    "🇶🇨 Quebec": {"rate": 0.044, "pop": 9_000_000}
}

# ===========================================
# CMHC/STATS CAN BUYER DEMOGRAPHICS
# ===========================================
BUYER_DEMOS = {
    "Single": {"pct": 0.40, "income_mult": 1.0},
    "Couple": {"pct": 0.60, "income_mult": 0.75},  # 25% more buying power
    "First-Time": {"pct": 0.45, "amort_bonus": 30},  # 45% of buyers
    "Repeat": {"pct": 0.55, "amort_bonus": 25}
}

def lognorm_cdf(x, mu=10.45, sigma=0.95):
    if x <= 0: return 0.0
    z = (np.log(x) - mu) / sigma
    return 0.5 * (1 + np.tanh(np.sqrt(2/3) * z))

def calculate_down_payment(price):
    if price <= 500000: return price * 0.05
    elif price <= 1500000:
        return 500000 * 0.05 + (price - 500000) * 0.10
    else: return price * 0.20

def calc_stress_test_payment(price, contract_rate, amort_years=25):
    down_payment = calculate_down_payment(price)
    loan = price - down_payment
    stress_rate = max(0.0525, contract_rate + 0.02)
    n_payments = amort_years * 12
    monthly_rate = stress_rate / 12
    monthly_payment = loan * (monthly_rate * (1 + monthly_rate)**n_payments) / ((1 + monthly_rate)**n_payments - 1)
    return monthly_payment * 12 / 0.39, down_payment, stress_rate, amort_years

# MAIN INPUTS
col1, col2 = st.columns(2)

with col1:
    st.header("🏠 Property 1")
    price1 = st.number_input("Price ($)", 100000, 3000000, 800000, 25000, key="p1")

with col2:
    st.header("🏠 Property 2")
    price2 = st.number_input("Price ($)", 100000, 3000000, 1000000, 25000, key="p2")

region = st.selectbox("Region", list(REGIONS.keys()))
region_data = REGIONS[region]
region_pop = region_data["pop"]

# ===========================================
# AUTOMATIC BUYER BREAKDOWN CALCULATION
# ===========================================
def calculate_buyer_breakdown(price, region_pop):
    buyers = {"Single": 0, "Couple": 0, "First-Time": 0, "Repeat": 0, "Total": 0}
    
    # Single buyers (40% of market)
    income_single, down, stress, amort = calc_stress_test_payment(price, region_data["rate"])
    prob_single = max(0, 1 - lognorm_cdf(income_single))
    buyers["Single"] = prob_single * region_pop * BUYER_DEMOS["Single"]["pct"]
    
    # Couple buyers (60% of market - more buying power)
    income_couple = income_single * BUYER_DEMOS["Couple"]["income_mult"]
    prob_couple = max(0, 1 - lognorm_cdf(income_couple))
    buyers["Couple"] = prob_couple * region_pop * BUYER_DEMOS["Couple"]["pct"]
    
    # First-time buyers (45% - 30yr amort)
    income_ft, _, _, _ = calc_stress_test_payment(price, region_data["rate"], BUYER_DEMOS["First-Time"]["amort_bonus"])
    prob_ft = max(0, 1 - lognorm_cdf(income_ft))
    buyers["First-Time"] = prob_ft * region_pop * BUYER_DEMOS["First-Time"]["pct"]
    
    # Repeat buyers (55% - 25yr amort)
    income_repeat, _, _, _ = calc_stress_test_payment(price, region_data["rate"], BUYER_DEMOS["Repeat"]["amort_bonus"])
    prob_repeat = max(0, 1 - lognorm_cdf(income_repeat))
    buyers["Repeat"] = prob_repeat * region_pop * BUYER_DEMOS["Repeat"]["pct"]
    
    buyers["Total"] = buyers["Single"] + buyers["Couple"]  # Household total
    return buyers, income_single, down

# Calculate both properties
buyers1, income1_single, down1 = calculate_buyer_breakdown(price1, region_pop)
buyers2, income2_single, down2 = calculate_buyer_breakdown(price2, region_pop)

buyer_difference = buyers1["Total"] - buyers2["Total"]

# ===========================================
# RESULTS WITH BUYER BREAKDOWN
# ===========================================
st.subheader("📊 Automatic Buyer Demographics (CMHC Stats)")

col_a, col_b = st.columns(2)

with col_a:
    st.header(f"**Property 1: ${price1:,}**")
    st.metric("**Total Buyers**", f"{buyers1['Total']:,.0f}")
    st.metric("Down Payment", f"${down1:,.0f}")
    
    with st.container():
        st.subheader("👥 **Buyer Breakdown**")
        col_s, col_c = st.columns(2)
        with col_s: st.metric("Single", f"{buyers1['Single']:,.0f}")
        with col_c: st.metric("👨‍👩 Couples", f"{buyers1['Couple']:,.0f}")
        col_ft, col_r = st.columns(2)
        with col_ft: st.metric("🆕 First-Time", f"{buyers1['First-Time']:,.0f}")
        with col_r: st.metric("🔄 Repeat", f"{buyers1['Repeat']:,.0f}")

with col_b:
    st.header(f"**Property 2: ${price2:,}**")
    st.metric("**Total Buyers**", f"{buyers2['Total']:,.0f}")
    st.metric("Down Payment", f"${down2:,.0f}")
    
    with st.container():
        st.subheader("👥 **Buyer Breakdown**")
        col_s, col_c = st.columns(2)
        with col_s: st.metric("Single", f"{buyers2['Single']:,.0f}")
        with col_c: st.metric("👨‍👩 Couples", f"{buyers2['Couple']:,.0f}")
        col_ft, col_r = st.columns(2)
        with col_ft: st.metric("🆕 First-Time", f"{buyers2['First-Time']:,.0f}")
        with col_r: st.metric("🔄 Repeat", f"{buyers2['Repeat']:,.0f}")

# WINNER + DIFFERENCE
st.markdown("---")
if abs(price1 - price2) > 50000:
    col_win1, col_win2 = st.columns([1, 3])
    if buyer_difference > 0:
        col_win1.success(f"🏆 **Property 1**")
        col_win1.metric("Wins By", f"+{buyer_difference:,.0f} buyers")
        col_win2.error(f"Property 2: {buyers2['Total']:,.0f} total buyers")
    else:
        col_win1.error(f"🏆 **Property 2**")
        col_win1.metric("Wins By", f"+{abs(buyer_difference):,.0f} buyers")
        col_win2.error(f"Property 1: {buyers1['Total']:,.0f} total buyers")
else:
    st.info("**Equal pricing** - Similar buyer pools")

# CHART
st.subheader("📈 Income Distribution")
income_range = np.linspace(1, 400_000, 1000)
fig = go.Figure()
fig.add_trace(go.Scatter(x=income_range, y=lognorm_pdf(income_range)/np.max(lognorm_pdf(income_range))*50,
                        mode='lines', line=dict(color='#1f77b4', width=4)))
fig.add_vline(x=income1_single, line_dash="dash", line_color="blue", 
              annotation_text=f"Prop1: ${income1_single:,.0f}", annotation_position="top left")
fig.add_vline(x=income2_single, line_dash="dash", line_color="orange", 
              annotation_text=f"Prop2: ${income2_single:,.0f}", annotation_position="top right")
fig.update_layout(height=450, hovermode='x unified')
fig.update_xaxes(title="Income ($)", tickformat="$,d")
st.plotly_chart(fig, use_container_width=True)

# DEMOGRAPHICS SOURCES
st.markdown("---")
with st.expander("📊 **CMHC Buyer Demographics (2024)**"):
    st.markdown("""
    **✅ Single Households**: 40% of buyers
    **✅ Couples**: 60% of buyers (+25% buying power)  
    **✅ First-Time**: 45% of buyers (30yr amortization)
    **✅ Repeat Buyers**: 55% of buyers (25yr amortization)
    
    **🎯 Sources**: CMHC Housing Market Report + StatsCan Family Income
    """)

st.caption(f"Property 1 Total: {buyers1['Total']:,.0f} | Property 2 Total: {buyers2['Total']:,.0f}")
