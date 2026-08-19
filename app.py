# app.py
import streamlit as st

st.set_page_config(page_title="Sports Betting Simulator", page_icon="📈", layout="wide")

# ==========================================
# 1. MAIN PAGE HEADER
# ==========================================
head_col1, head_col2 = st.columns([5, 1])

with head_col1:
    st.title("📈 Sports Betting Simulator")
    
with head_col2:
    st.markdown("<div style='padding-top: 15px;'></div>", unsafe_allow_html=True) 
    selected_sport = st.selectbox(
        "Select Sport", 
        ["NFL", "NHL", "NBA", "MLB"],
        label_visibility="collapsed"
    )

st.divider()

# ==========================================
# 2. SPORT ROUTING
# ==========================================
if selected_sport == "NFL":
    from sports.nfl.app_nfl import render_nfl
    render_nfl()

elif selected_sport == "NHL":
    from sports.nhl.app_nhl import render_nhl
    render_nhl()

elif selected_sport == "NBA":
    st.subheader("🏀 NBA Player Prop Simulator")
    st.warning("NBA engine is currently in development.")

elif selected_sport == "MLB":
    st.subheader("⚾ MLB Player Prop Simulator")
    st.warning("MLB engine is currently in development.")