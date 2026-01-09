import streamlit as st
import pandas as pd
from datetime import datetime

# ---------------- CONFIG ----------------
st.set_page_config(
    page_title="AI Trading Dashboard",
    layout="wide"
)

REFRESH_SECONDS = 30

# ---------------- DATA LOADER ----------------
@st.cache_data(ttl=REFRESH_SECONDS)
def load_data():
    try:
        df = pd.read_csv("dashboard_data.csv")
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

df = load_data()

# ---------------- HEADER ----------------
st.title("📊 AI Trading System Dashboard")
st.caption(f"⏱ Auto-refresh every {REFRESH_SECONDS} seconds")

# ---------------- METRICS ----------------
if not df.empty:
    total_pnl = df["pnl_rs"].sum()
    avg_conf = df["confidence"].mean()
    open_trades = len(df[df["status"] != "EXIT"])

    col1, col2, col3 = st.columns(3)
    col1.metric("Open Positions", open_trades)
    col2.metric("Total P&L (₹)", round(total_pnl, 2))
    col3.metric("Avg Confidence", round(avg_conf, 2))

st.divider()

# ---------------- MAIN TABLE ----------------
st.subheader("📈 Current Recommendations")

def color_pnl(val):
    try:
        val = float(val)
        if val < 0:
            return "color:red;"
        elif val > 0:
            return "color:green;"
    except:
        return ""
    return ""

styled_df = df.style.applymap(
    color_pnl,
    subset=["pnl_rs", "pnl_pct"]
)

st.dataframe(styled_df, use_container_width=True)

# ---------------- SIGNAL EXPLANATION ----------------
st.divider()
st.subheader("🧠 Signal Explanation")

if not df.empty:
    selected_stock = st.selectbox("Select Stock", df["stock"].unique())
    row = df[df["stock"] == selected_stock].iloc[0]

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📌 Trade Details")
        st.write("**Stock:**", row["stock"])
        st.write("**Status:**", row["status"])
        st.write("**Confidence:**", row["confidence"])
        st.write("**Holding Days:**", row["holding_days"])
    with col2:
        st.markdown("### 📊 Price Levels")
        st.write("**Entry Price:** ₹", row["entry_price"])
        st.write("**Current Price:** ₹", row["current_price"])
        st.write("**Stop Loss:** ₹", row["stop_loss"])
        st.write("**Target Price:** ₹", row["target_price"])

    st.markdown("### 🧠 Why this stock?")
    st.info(row["reason"])

# ---------------- RISK WARNINGS ----------------
st.divider()
st.subheader("⚠️ Risk Alerts")

if not df.empty:
    near_sl = df[
        (df["current_price"] <= df["stop_loss"] * 1.02) &
        (df["status"] == "HOLD")
    ]
    if len(near_sl) > 0:
        for _, r in near_sl.iterrows():
            st.warning(
                f"{r['stock']} is near STOP LOSS (₹{r['current_price']} vs SL ₹{r['stop_loss']})"
            )
    else:
        st.success("No positions near stop-loss.")

# ---------------- FOOTER ----------------
st.caption(
    f"Last update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Dashboard is READ-ONLY (Safe Mode)"
)
