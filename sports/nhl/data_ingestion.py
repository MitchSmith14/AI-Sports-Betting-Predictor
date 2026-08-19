# sports/nhl/data_ingestion.py

import pandas as pd
import streamlit as st
from sports.nhl.config import NHL_TEAM_COLORS, NHL_TEAM_NAMES

@st.cache_data(ttl=3600, show_spinner="Loading NHL data...")
def load_nhl_data():
    """
    Placeholder for NHL Data Ingestion. 
    In production, integrate `nhl-api-py` or scrape the NHL Stats API.
    Returns a dataframe formatted for the simulation engine.
    """
    # Expected schema for the NHL engine:
    columns = [
        "player_name", "position", "recent_team", "opponent_team", "season", "date",
        "time_on_ice_mins", "shots_on_goal", "goals", "assists", "points", "team_shots", "team_goals"
    ]
    df = pd.DataFrame(columns=columns)
    
    # Ensure numeric columns are cast correctly
    numeric_cols = ["time_on_ice_mins", "shots_on_goal", "goals", "assists", "points", "team_shots", "team_goals"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        
    return df

def get_nhl_team_colors(team_abbr: str) -> dict:
    abbr = str(team_abbr).upper().strip() if pd.notna(team_abbr) else "NHL"
    return NHL_TEAM_COLORS.get(abbr, {"primary": "#1E293B", "secondary": "#475569"})

def get_nhl_team_logo(team_abbr: str) -> str:
    # Uses standard NHL CDN routing
    clean = str(team_abbr).upper().strip()
    return f"https://assets.nhle.com/logos/nhl/svg/{clean}_light.svg"