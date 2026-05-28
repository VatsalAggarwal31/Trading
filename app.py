import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

from data_engine import fetch_and_prepare_data
from capital_manager import get_pool_summary
from state_manager import load_state, save_state

def update_env_variable(key, value):
    env_path = ".env"
    lines = []
    updated = False
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            
    new_lines = []
    for line in lines:
        clean_line = line.strip()
        if clean_line.startswith(f"{key}=") or clean_line.startswith(f"export {key}="):
            new_lines.append(f'{key}="{value}"\n')
            updated = True
        else:
            new_lines.append(line)
            
    if not updated:
        new_lines.append(f'{key}="{value}"\n')
        
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)


# ── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="Apex Multi-Stock Control Room",
    page_icon="📈",
    layout="wide"
)

STARTING_CAPITAL = 1000.0

# ── Load states ───────────────────────────────────────────────
pool   = get_pool_summary()
state  = load_state()
tickers = state.get('tickers', ["TATASTEEL.NS", "RELIANCE.NS", "INFY.NS", "ITC.NS", "TCS.NS"])

# Calculate portfolio exposure
total_equity = pool['capital']
invested_capital = 0.0
for tick, pos in state.get('positions', {}).items():
    if pos.get('holding_position', False):
        invested_capital += pos.get('entry_price', 0.0) * pos.get('current_shares', 0)
        
free_cash = max(0.0, round(total_equity - invested_capital, 2))

# ── Clean Modern UI/UX Styling ────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@300;400;500;600;700;800&display=swap');
    
    /* Main body styles */
    .stApp {
        background-color: #0b0f19;
        color: #f1f5f9;
        font-family: 'Inter', sans-serif;
    }
    
    /* Headers styling */
    h1, h2, h3, h4 {
        font-family: 'Outfit', sans-serif;
        font-weight: 700;
        letter-spacing: -0.02em;
    }
    
    h1 {
        background: linear-gradient(135deg, #6366f1 0%, #0ea5e9 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.1rem !important;
    }
    
    /* Sleek card container */
    .glass-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
        margin-bottom: 1rem;
    }
    
    /* Metrics Custom Styles */
    div[data-testid="stMetricValue"] {
        font-family: 'Outfit', sans-serif;
        font-weight: 700;
        font-size: 1.8rem !important;
        color: #f8fafc !important;
    }
    
    div[data-testid="stMetricLabel"] {
        font-family: 'Inter', sans-serif;
        text-transform: capitalize;
        font-weight: 500;
        letter-spacing: 0;
        font-size: 0.85rem !important;
        color: #94a3b8 !important;
    }
    
    div[data-testid="metric-container"] {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 12px;
        box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1);
        padding: 1.2rem 1rem !important;
        transition: all 0.2s ease-in-out;
    }
    
    div[data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        border: 1px solid #374151;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
    }
    
    /* Elegant Status Badges */
    .status-badge {
        display: inline-block;
        padding: 0.4rem 1rem;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.8rem;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        font-family: 'Outfit', sans-serif;
        text-align: center;
        width: 100%;
        margin-bottom: 1rem;
    }
    .status-holding {
        background: rgba(16, 185, 129, 0.1);
        border: 1px solid #10b981;
        color: #10b981;
    }
    .status-cash {
        background: rgba(99, 102, 241, 0.1);
        border: 1px solid #6366f1;
        color: #6366f1;
    }
    
    /* Custom Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #0f172a !important;
        border-right: 1px solid #1e293b !important;
    }
    
    /* Sidebar Headers */
    .sidebar-header {
        font-family: 'Outfit', sans-serif;
        color: #f8fafc;
        font-weight: 600;
        font-size: 1rem;
        margin-bottom: 0.8rem;
    }
    
    /* Interactive custom CSS scrollbars */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    ::-webkit-scrollbar-track {
        background: #0b0f19;
    }
    ::-webkit-scrollbar-thumb {
        background: #1f2937;
        border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #4b5563;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────
st.markdown("<h1>📈 APEX PORTFOLIO CONTROL ROOM</h1>", unsafe_allow_html=True)
st.caption(f"Portfolio Mode · Clean Minimalist Design · Telemetry Synced: {datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime('%H:%M:%S')}")

# ── Sidebar Control Panel ─────────────────────────────────────
with st.sidebar:
    st.markdown("<div class='sidebar-header'>⚡ Core Actuators</div>", unsafe_allow_html=True)
    
    # 1. Dynamic Mode Toggle
    is_live = not state.get('dry_run', True)
    mode_toggle = st.toggle("⚡ LIVE ORDER EXECUTION", value=is_live, 
                            help="Toggle between simulation (Dry Run) and real API orders on Dhan.")
    
    if mode_toggle != is_live:
        state['dry_run'] = not mode_toggle
        save_state(state)
        st.success(f"Actuator Mode: {'⚡ LIVE' if mode_toggle else '⚙ DRY RUN (Simulated)'}")
        st.rerun()
        
    st.markdown("<hr style='border-color: #1f2937;'/>", unsafe_allow_html=True)
    
    # 2. Ticker Pool Configurator
    st.markdown("<div class='sidebar-header'>⚙️ Scan Tickers</div>", unsafe_allow_html=True)
    with st.expander("⚙️ Manage Scanner Tickers"):
        st.write("Current Scan Pool:")
        for tick in tickers:
            col_t1, col_t2 = st.columns([4, 1])
            col_t1.caption(f"**{tick}**")
            if col_t2.button("❌", key=f"del_{tick}"):
                if len(tickers) > 1:
                    tickers.remove(tick)
                    state['tickers'] = tickers
                    save_state(state)
                    st.success(f"Removed {tick}!")
                    st.rerun()
                else:
                    st.error("Cannot delete the last ticker!")
                    
        new_ticker = st.text_input("Add Ticker (e.g. INFY.NS)", value="", help="Use Yahoo Finance symbols (.NS for NSE)").strip().upper()
        if st.button("➕ Add Ticker to Pool", use_container_width=True):
            if new_ticker:
                if new_ticker not in tickers:
                    tickers.append(new_ticker)
                    state['tickers'] = tickers
                    save_state(state)
                    st.success(f"Added {new_ticker} to scanner pool!")
                    st.rerun()
                else:
                    st.warning("Ticker already in pool.")

    st.markdown("<hr style='border-color: #1f2937;'/>", unsafe_allow_html=True)

    # 3. Secure Token Refresher
    st.markdown("<div class='sidebar-header'>🔑 API Security Key</div>", unsafe_allow_html=True)
    with st.expander("🔑 Secure Token Refresher"):
        load_dotenv()
        curr_token = os.getenv("DHAN_ACCESS_TOKEN", "")
        masked = f"{curr_token[:6]}...{curr_token[-6:]}" if len(curr_token) > 12 else "Not Configured"
        st.caption(f"Active Token: `{masked}`")
        new_token = st.text_area("Paste New Access Token", height=90, help="Generate from your DhanHQ API console daily.")
        if st.button("🔄 Apply Daily Token", use_container_width=True):
            if new_token.strip():
                update_env_variable("DHAN_ACCESS_TOKEN", new_token.strip())
                st.success("Access Token updated! Loop is armed.")
                st.rerun()
            else:
                st.error("Token field cannot be empty.")

    # 4. Capital Management
    st.markdown("<div class='sidebar-header'>💰 Liquidity Pool</div>", unsafe_allow_html=True)
    with st.expander("🛠️ Capital Pool Adjuster"):
        add_amount = st.number_input("Inject Capital (₹)", min_value=10.0, max_value=50000.0, value=500.0, step=100.0)
        if st.button("➕ Inject Funds", use_container_width=True):
            from capital_manager import _load_pool, _save_pool
            pool_data = _load_pool()
            pool_data['capital'] = round(pool_data['capital'] + add_amount, 2)
            if pool_data['capital'] > pool_data['peak_capital']:
                pool_data['peak_capital'] = pool_data['capital']
            _save_pool(pool_data)
            st.success(f"Injected ₹{add_amount:.2f} into pool.")
            st.rerun()
            
        st.markdown("<br/>", unsafe_allow_html=True)
        if st.button("🚨 Factory Reset Capital (₹1,000)", type="primary", use_container_width=True):
            from capital_manager import _load_pool, _save_pool
            pool_data = _load_pool()
            pool_data['capital'] = STARTING_CAPITAL
            pool_data['peak_capital'] = STARTING_CAPITAL
            pool_data['total_trades'] = 0
            pool_data['winning_trades'] = 0
            pool_data['history'] = []
            _save_pool(pool_data)
            
            # Reset active position state as well
            from state_manager import _default_state
            st_data = _default_state()
            save_state(st_data)
            st.warning("Capital and Position states fully reset to factory default!")
            st.rerun()

    # 5. Emergency Square Off
    active_holdings = [t for t, p in state.get('positions', {}).items() if p.get('holding_position', False)]
    if active_holdings:
        st.markdown("<hr style='border-color: #1f2937;'/>", unsafe_allow_html=True)
        st.markdown("<div class='sidebar-header'>🚨 Emergency Actuator</div>", unsafe_allow_html=True)
        target_close = st.selectbox("Select Asset to Liquidate", options=active_holdings)
        if st.button("💥 FORCE CLOSE POSITION", type="primary", use_container_width=True):
            from auto_trader import execute_sell
            try:
                df_c = fetch_and_prepare_data(target_close)
                cp = df_c['Close'].iloc[-1]
            except Exception:
                cp = state['positions'][target_close]['entry_price']
            execute_sell(state, target_close, cp, reason="MANUAL_EMERGENCY_SELL")
            st.warning(f"Emergency square-off executed for {target_close} successfully!")
            st.rerun()

    # 6. Live Logs Preview
    st.markdown("<hr style='border-color: #1f2937;'/>", unsafe_allow_html=True)
    if os.path.exists("bot.log"):
        st.markdown("<div class='sidebar-header'>📋 Engine Telemetry (10 Lines)</div>", unsafe_allow_html=True)
        with open("bot.log", "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        for line in lines[-10:]:
            st.text(line.strip())

# ── Row 1: Capital Pool & High Performance Metrics ────────────
col_p1, col_p2, col_p3, col_p4, col_p5 = st.columns(5)

# Capital Metrics
col_p1.metric("Account Equity", f"₹{total_equity:.2f}", f"₹{pool['total_pnl']:+.2f} ({pool['total_pnl_pct']:+.1f}%)")
col_p2.metric("Available Free Cash", f"₹{free_cash:.2f}")
col_p3.metric("Invested Capital", f"₹{invested_capital:.2f}")
col_p4.metric("Win Rate", f"{pool['win_rate']}%", f"{pool['winning_trades']} / {pool['total_trades']} Trades")
col_p5.metric("Engine Mode", "LIVE TRADING" if mode_toggle else "SIMULATION", 
              delta="Live Actuators Active" if mode_toggle else "Dry Run Protection", 
              delta_color="normal" if mode_toggle else "off")

st.markdown("<br/>", unsafe_allow_html=True)

# ── Row 2: Live Charts & Position Monitor ─────────────────────
col_chart, col_status = st.columns([7, 3])

# Set a selectbox to pick which stock to look at in the Technical Terminal
with col_chart:
    st.markdown("<h3 style='margin-bottom:0.5rem;'>📊 Dynamic Technical Terminal</h3>", unsafe_allow_html=True)
    selected_ticker = st.selectbox("Select Active Asset to Analyze", options=tickers, index=0)
    
    try:
        df = fetch_and_prepare_data(ticker=selected_ticker)
        current_price = df['Close'].iloc[-1]
        
        # Prepare the beautiful clean theme plot
        fig = go.Figure()
        
        # Candlestick
        fig.add_trace(go.Candlestick(
            x=df.index[-60:],
            open=df['Open'].iloc[-60:],
            high=df['High'].iloc[-60:],
            low=df['Low'].iloc[-60:],
            close=df['Close'].iloc[-60:],
            name='Candles',
            increasing_line_color='#10b981', decreasing_line_color='#ef4444',
            increasing_fillcolor='rgba(16, 185, 129, 0.1)', decreasing_fillcolor='rgba(239, 68, 68, 0.1)'
        ))

        # Overlay EMA-20
        fig.add_trace(go.Scatter(
            x=df.index[-60:], y=df['EMA_20'].iloc[-60:],
            mode='lines', line=dict(color='#6366f1', width=1.5),
            name='EMA-20'
        ))

        # If holding, overlay entry, sl, and tp levels
        pos_details = state.get('positions', {}).get(selected_ticker, {})
        if pos_details.get('holding_position', False):
            fig.add_hline(y=pos_details['entry_price'], line_color='#94a3b8', line_dash="dash",
                          annotation_text=f"Entry: ₹{pos_details['entry_price']:.2f}", annotation_position="right",
                          annotation_font=dict(color="#94a3b8"))
            fig.add_hline(y=pos_details['active_stop_loss'], line_color='#ef4444', line_dash="dash",
                          annotation_text=f"SL: ₹{pos_details['active_stop_loss']:.2f}", annotation_position="right",
                          annotation_font=dict(color="#ef4444"))
            fig.add_hline(y=pos_details['active_take_profit'], line_color='#10b981', line_dash="dash",
                          annotation_text=f"TP: ₹{pos_details['active_take_profit']:.2f}", annotation_position="right",
                          annotation_font=dict(color="#10b981"))

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0b0f19",
            plot_bgcolor="#111827",
            height=430,
            xaxis_rangeslider_visible=False,
            margin=dict(l=0, r=0, t=10, b=0),
            legend=dict(orientation="h", y=1.08, x=0.01),
            xaxis=dict(gridcolor='#1e293b', linecolor='#334155'),
            yaxis=dict(gridcolor='#1e293b', linecolor='#334155')
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Failed to render chart for {selected_ticker}: {e}")
        current_price = None

with col_status:
    st.markdown("<h3 style='margin-bottom:0.5rem;'>🤖 Actuator Telemetry</h3>", unsafe_allow_html=True)
    
    with st.container(border=True):
        pos_details = state.get('positions', {}).get(selected_ticker, {})
        if pos_details.get('holding_position', False):
            pnl_now = 0
            if current_price:
                pnl_now = (current_price - pos_details['entry_price']) * pos_details['current_shares']
            
            st.markdown("<div class='status-badge status-holding'>🟢 ACTIVE POSITION</div>", unsafe_allow_html=True)
            
            s1, s2 = st.columns(2)
            s1.metric("Stock Owned", f"{pos_details['current_shares']} Shares")
            s2.metric("Unrealized Profit", f"₹{pnl_now:+.2f}", 
                      delta=f"{((current_price - pos_details['entry_price'])/pos_details['entry_price']*100):+.2f}%")
            
            t1, t2 = st.columns(2)
            t1.metric("Entry Price", f"₹{pos_details['entry_price']:.2f}")
            t2.metric("Stop Loss", f"₹{pos_details['active_stop_loss']:.2f}")
            
            st.metric("Take Profit Target", f"₹{pos_details['active_take_profit']:.2f}")
        else:
            st.markdown("<div class='status-badge status-cash'>⚪ CASH — AGENT SCANNING</div>", unsafe_allow_html=True)
            st.info(f"System has no active exposure in {selected_ticker}. Scanning technical indicators and AI signals for entry coordinates.")

        st.markdown("<hr style='border-color: #1e293b; margin: 0.5rem 0;'/>", unsafe_allow_html=True)
        
        d1, d2 = st.columns(2)
        d1.metric("Today's Net Return", f"₹{state.get('daily_pnl', 0.0):+.2f}")
        d2.metric("Trades Executed Today", state.get('trade_count_today', 0))
        
        if current_price:
            st.metric("Selected Spot Price", f"₹{current_price:.2f}")

    # Add quick Manual signal test in telemetry column for ease
    if st.button("🔮 Run Quick Brain Inference on selected asset", use_container_width=True):
        with st.spinner(f"Scanning {selected_ticker}..."):
            try:
                df_test = fetch_and_prepare_data(selected_ticker)
                cp = df_test['Close'].iloc[-1]
                from ai_model import get_live_prediction
                forecast = get_live_prediction(df_test, selected_ticker)
                margin = (forecast - cp) / cp
                st.markdown(f"""
                <div style="background: #111827; border: 1px solid #1f2937; border-radius: 8px; padding: 0.8rem; margin-top: 0.5rem;">
                    <h5 style="color: #6366f1; margin: 0 0 5px 0; font-family: 'Outfit'; font-size: 0.85rem;">Inference Status: {selected_ticker}</h5>
                    <p style="font-size:0.75rem; margin: 3px 0; color: #94a3b8;"><b>Spot:</b> ₹{cp:.2f}  |  <b>Forecast:</b> ₹{forecast:.2f}</p>
                    <p style="font-size:0.75rem; margin: 3px 0; color: #94a3b8;"><b>Edge:</b> <span style="color: {'#10b981' if margin >= 0 else '#ef4444'}; font-weight: 600;">{margin*100:+.2f}%</span></p>
                </div>
                """, unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Inference error: {e}")

st.markdown("<br/>", unsafe_allow_html=True)

# ── Portfolio Exposure Grid ───────────────────────────────────
st.subheader("💼 Cybernetic Portfolio Active Exposure Grid")

exposure_data = []
for tick in tickers:
    pos = state.get('positions', {}).get(tick, {})
    is_holding = pos.get('holding_position', False)
    
    status_str = "🟢 HOLDING" if is_holding else "⚪ CASH"
    shares_str = str(pos.get('current_shares', 0)) if is_holding else "-"
    entry_str = f"₹{pos.get('entry_price', 0.0):.2f}" if is_holding else "-"
    sl_str = f"₹{pos.get('active_stop_loss', 0.0):.2f}" if is_holding else "-"
    tp_str = f"₹{pos.get('active_take_profit', 0.0):.2f}" if is_holding else "-"
    
    live_price = "-"
    unrealized_pnl = "-"
    pnl_pct = ""
    
    if is_holding:
        try:
            import yfinance as yf
            ticker_df = yf.download(tick, period="1d", interval="1m", progress=False)
            if not ticker_df.empty:
                if isinstance(ticker_df.columns, pd.MultiIndex):
                    ticker_df.columns = ticker_df.columns.get_level_values(0)
                cur_p = float(ticker_df['Close'].iloc[-1])
                live_price = f"₹{cur_p:.2f}"
                pnl = (cur_p - pos['entry_price']) * pos['current_shares']
                unrealized_pnl = f"₹{pnl:+.2f}"
                pnl_pct = f" ({((cur_p - pos['entry_price'])/pos['entry_price']*100):+.2f}%)"
        except Exception:
            pass
            
    exposure_data.append({
        "Asset Ticker": tick,
        "Status": status_str,
        "Shares": shares_str,
        "Entry Price": entry_str,
        "Current Price": live_price,
        "Unrealized PnL": unrealized_pnl + pnl_pct,
        "Stop Loss": sl_str,
        "Take Profit": tp_str
    })
    
st.dataframe(pd.DataFrame(exposure_data), use_container_width=True, hide_index=True)

st.markdown("<br/>", unsafe_allow_html=True)

# ── Row 3: Equity growth curve ────────────────────────────────
st.subheader("📈 Capital Pool Compounding Trajectory (Equity Curve)")

history = pool.get('history', [])
if len(history) >= 2:
    hist_df = pd.DataFrame(history)
    hist_df['date'] = pd.to_datetime(hist_df['date'])

    fig_eq = go.Figure()
    fig_eq.add_trace(go.Scatter(
        x=hist_df['date'], y=hist_df['capital_after'],
        mode='lines+markers', fill='tozeroy',
        line=dict(color='#10b981', width=2),
        fillcolor='rgba(16, 185, 129, 0.05)',
        marker=dict(size=6, color='#6366f1', line=dict(color='#ffffff', width=1)),
        name='Pool Net Asset Value'
    ))
    fig_eq.add_hline(y=STARTING_CAPITAL, line_color='rgba(255, 255, 255, 0.2)', line_dash='dot',
                     annotation_text=f"Principal ₹{STARTING_CAPITAL:.0f}", annotation_position="left")

    fig_eq.update_layout(
        template="plotly_dark", 
        paper_bgcolor="#0b0f19",
        plot_bgcolor="#111827",
        height=260,
        margin=dict(l=0, r=0, t=10, b=0),
        yaxis_title="Pool Value (₹)",
        xaxis=dict(gridcolor='#1e293b', linecolor='#334155'),
        yaxis=dict(gridcolor='#1e293b', linecolor='#334155')
    )
    st.plotly_chart(fig_eq, use_container_width=True)
else:
    st.info("Visual Compounding Curve will render automatically once the bot completes at least 2 trades.")

st.markdown("<br/>", unsafe_allow_html=True)

# ── Row 4: Trade Ledger & Individual Trade PnL ───────────────
col_ledger, col_pnl_chart = st.columns([3, 2])

with col_ledger:
    st.subheader("📒 Engine Transaction Ledger")
    if os.path.exists("trade_history.csv"):
        try:
            trades_df = pd.read_csv("trade_history.csv")
            trades_df['PnL'] = pd.to_numeric(trades_df['PnL'], errors='coerce').fillna(0)

            # High-fidelity styling function for PnL cells
            def style_pnl(val):
                if val > 0:
                    return 'color: #10b981; font-weight: 600; background-color: rgba(16, 185, 129, 0.05)'
                elif val < 0:
                    return 'color: #ef4444; font-weight: 600; background-color: rgba(239, 68, 68, 0.05)'
                return ''

            styled = trades_df.tail(20).sort_index(ascending=False).style.map(
                style_pnl, subset=['PnL']
            )
            st.dataframe(styled, use_container_width=True, hide_index=True)
        except Exception as e:
            st.warning(f"Could not parse transaction ledger: {e}")
    else:
        st.info("No recorded trades detected. The database ledger will populate upon first transaction order.")

with col_pnl_chart:
    st.subheader("📊 Individual Trade Net Returns")
    if history:
        pnl_df = pd.DataFrame(history)
        pnl_df['date'] = pd.to_datetime(pnl_df['date'])
        pnl_df['color'] = pnl_df['pnl'].apply(lambda x: '#10b981' if x >= 0 else '#ef4444')

        fig_pnl = go.Figure(go.Bar(
            x=pnl_df['date'].dt.strftime('%m/%d %H:%M'),
            y=pnl_df['pnl'],
            marker_color=pnl_df['color']
        ))
        
        fig_pnl.update_layout(
            template="plotly_dark", 
            paper_bgcolor="#0b0f19",
            plot_bgcolor="#111827",
            height=260,
            margin=dict(l=0, r=0, t=10, b=0),
            yaxis_title="Profit / Loss (₹)", 
            showlegend=False,
            xaxis=dict(gridcolor='#1e293b', linecolor='#334155'),
            yaxis=dict(gridcolor='#1e293b', linecolor='#334155')
        )
        st.plotly_chart(fig_pnl, use_container_width=True)
    else:
        st.info("Visual performance bar-chart will appear here once the first trade is completed.")

# ── Footer ────────────────────────────────────────────────────
st.markdown("<hr style='border-color: #1e293b;'/>", unsafe_allow_html=True)
st.caption(
    "Apex Portfolio Compounding System — Designed for Premium High-Frequency Operations. "
    "To toggle actuators on-the-fly, use the toggles in the side cockpit. "
    "Dashboard is state-synced automatically in real-time."
)
