import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import numpy as np

st.set_page_config(page_title="AI Trading Dashboard", layout="wide", initial_sidebar_state="expanded")

REFRESH_SECONDS = 30

# ============================================
# FETCH LIVE PRICES FROM YFINANCE (with error handling)
# ============================================
@st.cache_data(ttl=REFRESH_SECONDS)
def fetch_live_prices(symbols):
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

# ============================================
# DATA LOADER WITH TYPE SAFETY
# ============================================
@st.cache_data(ttl=REFRESH_SECONDS)
def load_data():
    try:
        df = pd.read_csv("dashboard_data.csv")
        
        # Ensure numeric columns are actually numeric
        numeric_cols = ['entry_price', 'stop_loss', 'target_price', 'rsi', 'support', 'resistance']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Fetch live prices
        symbols = df['stock'].unique().tolist()
        live_prices = fetch_live_prices(symbols)
        df['current_price'] = df['stock'].map(live_prices).fillna(df.get('current_price', df['entry_price']))
        
        # Recalculate P&L
        df['pnl_rs'] = (df['current_price'] - df['entry_price']).round(2)
        df['pnl_pct'] = ((df['current_price'] - df['entry_price']) / df['entry_price'] * 100).round(2)
        
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

df = load_data()

# ============================================
# HEADER
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
        open_trades = len(df[df['status'].str.upper() == 'HOLD']) if 'status' in df.columns else 0
        st.metric("🔓 Open Positions", open_trades)
    
    with col2:
        total_pnl = df['pnl_rs'].sum() if 'pnl_rs' in df.columns else 0
        st.metric("💰 Total P&L (₹)", f"₹{total_pnl:,.0f}")
    
    with col3:
        total_pnl_pct = (df['pnl_rs'].sum() / (df['entry_price'] * abs(df.get('quantity', 1))).sum() * 100) if (df['entry_price'] * abs(df.get('quantity', 1))).sum() > 0 else 0
        st.metric("📈 Total Return", f"{total_pnl_pct:.2f}%")
    
    with col4:
        avg_conf = pd.to_numeric(df.get('confidence', [0]), errors='coerce').mean()
        st.metric("🧠 Avg Confidence", f"{avg_conf:.2f}")
else:
    st.info("No trading data available")

st.divider()

# ============================================
# HOLDINGS & BUY RECOMMENDATIONS
# ============================================
st.subheader("📈 Current Recommendations")

if not df.empty:
    # Separate by status (safe handling)
    if 'status' in df.columns:
        df['status'] = df['status'].str.upper()
        buy_recs = df[df['status'] == 'BUY'].copy()
        holdings = df[df['status'] == 'HOLD'].copy()
    else:
        buy_recs = pd.DataFrame()
        holdings = df.copy()
    
    if not buy_recs.empty:
        st.markdown("### 🎯 BUY Recommendations (New Signals)")
        display_cols = ['stock', 'current_price', 'entry_price', 'target_price', 'stop_loss', 'confidence']
        available_cols = [c for c in display_cols if c in buy_recs.columns]
        st.dataframe(buy_recs[available_cols], use_container_width=True)
    
    if not holdings.empty:
        st.markdown("### 📊 Current Holdings")
        display_cols = ['stock', 'entry_price', 'current_price', 'pnl_rs', 'pnl_pct', 'stop_loss', 'target_price']
        available_cols = [c for c in display_cols if c in holdings.columns]
        
        def style_pnl(val):
            try:
                if float(val) < 0:
                    return 'color: red; font-weight: bold;'
                elif float(val) > 0:
                    return 'color: green; font-weight: bold;'
            except:
                pass
            return ''
        
        styled_df = holdings[available_cols].style.applymap(style_pnl, subset=['pnl_rs', 'pnl_pct'] if 'pnl_rs' in available_cols else [])
        st.dataframe(styled_df, use_container_width=True)
else:
    st.warning("No recommendations available")

st.divider()

# ============================================
# DETAILED SIGNAL ANALYSIS
# ============================================
st.subheader("🧠 Signal Details & Technical Analysis")

if not df.empty and len(df) > 0:
    selected_stock = st.selectbox("Select a stock for detailed analysis", df['stock'].unique())
    row = df[df['stock'] == selected_stock].iloc[0]
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 📌 Trade Details")
        st.write(f"**Stock:** {row.get('stock', 'N/A')}")
        st.write(f"**Status:** {row.get('status', 'N/A')}")
        try:
            conf = float(row.get('confidence', 0))
            st.write(f"**Confidence:** {conf:.2f}")
        except:
            st.write(f"**Confidence:** {row.get('confidence', 'N/A')}")
    
    with col2:
        st.markdown("### 💹 Price Levels")
        try:
            st.write(f"**Entry:** ₹{float(row.get('entry_price', 0)):,.2f}")
            st.write(f"**Current:** ₹{float(row.get('current_price', 0)):,.2f}")
            st.write(f"**SL:** ₹{float(row.get('stop_loss', 0)):,.2f}")
            st.write(f"**Target:** ₹{float(row.get('target_price', 0)):,.2f}")
            if 'pnl_rs' in df.columns:
                st.write(f"**P&L:** ₹{float(row.get('pnl_rs', 0)):,.0f} ({float(row.get('pnl_pct', 0)):+.2f}%)")
        except:
            st.write("Error displaying prices")
    
    with col3:
        st.markdown("### 📊 Technical Metrics")
        try:
            rsi = float(row.get('rsi', 0))
            st.write(f"**RSI:** {rsi:.2f}")
        except:
            st.write(f"**RSI:** {row.get('rsi', 'N/A')}")
        
        st.write(f"**EMA Signal:** {row.get('ema_signal', 'N/A')}")
        st.write(f"**Volume Signal:** {row.get('volume_signal', 'N/A')}")
        try:
            st.write(f"**Support:** ₹{float(row.get('support', 0)):,.2f}")
            st.write(f"**Resistance:** ₹{float(row.get('resistance', 0)):,.2f}")
        except:
            pass
    
    st.markdown("---")
    st.markdown("### 📝 Why This Stock?")
    st.info(row.get('reason', 'No reasoning provided'))
else:
    st.warning("No stock data available")

st.divider()

# ============================================
# RISK ALERTS
# ============================================
st.subheader("⚠️ Risk Management")

if not df.empty:
    try:
        near_sl = df[
            (df['current_price'] <= df['stop_loss'] * 1.02) &
            (df['status'].str.upper() == 'HOLD')
        ]
        
        if len(near_sl) > 0:
            st.warning("🔴 ALERT: Positions Near Stop Loss")
            for _, row in near_sl.iterrows():
                st.write(f"**{row['stock']}** - Current: ₹{float(row['current_price']):.2f} vs SL: ₹{float(row['stop_loss']):.2f}")
        else:
            st.success("✅ All positions are safe from stop-loss")
    except:
        st.info("Risk check unavailable")

st.divider()
st.caption(f"Last update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')} | Dashboard READ-ONLY | Data auto-refreshes every {REFRESH_SECONDS}s")
