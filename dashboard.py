import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import numpy as np

# ============================================
# CONFIGURATION
# ============================================
st.set_page_config(
    page_title="AI Trading Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

REFRESH_SECONDS = 30

# ============================================
# FETCH LIVE PRICES FROM YFINANCE
# ============================================
@st.cache_data(ttl=REFRESH_SECONDS)
def fetch_live_prices(symbols):
    """
    Fetch real-time prices from yfinance for given symbols.
    Converts NSE symbols (e.g., 'TCS.NS') to live prices.
    """
    try:
        prices = {}
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                data = ticker.history(period='1d')
                if not data.empty:
                    prices[symbol] = data['Close'].iloc[-1]
                else:
                    prices[symbol] = None
            except:
                prices[symbol] = None
        return prices
    except Exception as e:
        st.error(f"Error fetching prices: {e}")
        return {}

# ============================================
# DATA LOADER WITH REAL-TIME PRICES
# ============================================
@st.cache_data(ttl=REFRESH_SECONDS)
def load_data():
    try:
        df = pd.read_csv("dashboard_data.csv")
        
        # Fetch live prices for all stocks
        symbols = df['stock'].unique().tolist()
        live_prices = fetch_live_prices(symbols)
        
        # Update current prices with live data
        df['current_price_live'] = df['stock'].map(live_prices)
        df['current_price'] = df['current_price_live'].fillna(df['current_price'])
        
        # Recalculate P&L based on live prices
        df['pnl_rs'] = (df['current_price'] - df['entry_price']) * df['quantity']
        df['pnl_pct'] = ((df['current_price'] - df['entry_price']) / df['entry_price'] * 100).round(2)
        
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

df = load_data()

# ============================================
# HEADER WITH LIVE STATUS
# ============================================
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.title("📊 AI Trading System Dashboard")
with col2:
    st.caption(f"🔄 Auto-refresh: {REFRESH_SECONDS}s")
with col3:
    st.caption(f"⏱ {datetime.now().strftime('%H:%M:%S IST')}")

st.divider()

# ============================================
# KEY METRICS
# ============================================
if not df.empty:
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        open_trades = len(df[df['status'] == 'HOLD'])
        st.metric("🔓 Open Positions", open_trades)
    
    with col2:
        total_pnl = df['pnl_rs'].sum()
        color = "green" if total_pnl > 0 else "red"
        st.metric("💰 Total P&L (₹)", f"₹{total_pnl:,.0f}")
    
    with col3:
        total_pnl_pct = (df['pnl_rs'].sum() / (df['entry_price'] * df['quantity']).sum() * 100) if (df['entry_price'] * df['quantity']).sum() > 0 else 0
        st.metric("📈 Total Return", f"{total_pnl_pct:.2f}%")
    
    with col4:
        avg_conf = df['confidence'].mean()
        st.metric("🧠 Avg Confidence", f"{avg_conf:.2f}")
else:
    st.info("No trading data available. Please load dashboard_data.csv")

st.divider()

# ============================================
# RECOMMENDATIONS TABLE
# ============================================
st.subheader("📈 Current Recommendations")

if not df.empty:
    # Separate BUY recommendations from Holdings
    buy_recs = df[df['status'] == 'BUY'].copy()
    holdings = df[df['status'] == 'HOLD'].copy()
    
    # Display BUY Recommendations
    if not buy_recs.empty:
        st.markdown("### 🎯 BUY Recommendations (New Signals)")
        display_buy = buy_recs[['stock', 'current_price', 'entry_price', 'target_price', 'stop_loss', 'confidence', 'rsi', 'ema_signal']].copy()
        st.dataframe(display_buy, use_container_width=True)
    
    # Display Holdings
    if not holdings.empty:
        st.markdown("### 📊 Current Holdings")
        display_hold = holdings[['stock', 'entry_price', 'current_price', 'pnl_rs', 'pnl_pct', 'stop_loss', 'target_price', 'holding_days']].copy()
        
        # Style the dataframe
        def style_pnl(val):
            try:
                if float(val) < 0:
                    return 'color: red; font-weight: bold;'
                elif float(val) > 0:
                    return 'color: green; font-weight: bold;'
            except:
                pass
            return ''
        
        styled_df = display_hold.style.applymap(style_pnl, subset=['pnl_rs', 'pnl_pct'])
        st.dataframe(styled_df, use_container_width=True)
else:
    st.warning("No recommendations available")

st.divider()

# ============================================
# DETAILED SIGNAL EXPLANATION
# ============================================
st.subheader("🧠 Signal Details & Technical Analysis")

if not df.empty:
    # Stock selector
    selected_stock = st.selectbox("Select a stock for detailed analysis", df['stock'].unique())
    row = df[df['stock'] == selected_stock].iloc[0]
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 📌 Trade Details")
        st.write(f"**Stock:** {row['stock']}")
        st.write(f"**Status:** {row['status']}")
        st.write(f"**Signal Confidence:** {row['confidence']:.2f}")
        st.write(f"**Holding Days:** {int(row['holding_days']) if pd.notna(row['holding_days']) else 0}")
    
    with col2:
        st.markdown("### 💹 Price Levels")
        st.write(f"**Entry Price:** ₹{row['entry_price']:,.2f}")
        st.write(f"**Current Price:** ₹{row['current_price']:,.2f}")
        st.write(f"**Stop Loss:** ₹{row['stop_loss']:,.2f}")
        st.write(f"**Target Price:** ₹{row['target_price']:,.2f}")
        st.write(f"**P&L:** ₹{row['pnl_rs']:,.0f} ({row['pnl_pct']:+.2f}%)")
    
    with col3:
        st.markdown("### 📊 Technical Metrics")
        st.write(f"**RSI:** {row['rsi']:.2f}")
        st.write(f"**EMA Signal:** {row['ema_signal']}")
        st.write(f"**Volume Signal:** {row['volume_signal']}")
        st.write(f"**Support Level:** ₹{row['support']:,.2f}")
        st.write(f"**Resistance Level:** ₹{row['resistance']:,.2f}")
    
    st.markdown("---")
    st.markdown("### 📝 Why This Stock?")
    st.info(row['reason'])
else:
    st.warning("No stock data available")

st.divider()

# ============================================
# RISK ALERTS
# ============================================
st.subheader("⚠️ Risk Management")

if not df.empty:
    # Positions near stop loss
    near_sl = df[
        (df['current_price'] <= df['stop_loss'] * 1.02) &
        (df['status'] == 'HOLD')
    ]
    
    if len(near_sl) > 0:
        st.warning("🔴 ALERT: Positions Near Stop Loss")
        for _, row in near_sl.iterrows():
            st.write(f"**{row['stock']}** - Current: ₹{row['current_price']:.2f} vs SL: ₹{row['stop_loss']:.2f}")
    else:
        st.success("✅ All positions are safe from stop-loss")
    
    # Positions at profit target
    at_target = df[
        (df['current_price'] >= df['target_price'] * 0.98) &
        (df['status'] == 'HOLD')
    ]
    
    if len(at_target) > 0:
        st.success("🟢 Positions Near Profit Target")
        for _, row in at_target.iterrows():
            st.write(f"**{row['stock']}** - Current: ₹{row['current_price']:.2f} vs Target: ₹{row['target_price']:.2f}")
    
    # Portfolio risk summary
    total_risk = (df['pnl_rs'] < 0).sum()
    st.info(f"📊 Portfolio Summary: {total_risk} position(s) in loss")

st.divider()

# ============================================
# FOOTER
# ============================================
st.caption(
    f"Last update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')} | "
    f"Dashboard is READ-ONLY (Safe Mode) | "
    f"Data refreshes every {REFRESH_SECONDS} seconds"
)
