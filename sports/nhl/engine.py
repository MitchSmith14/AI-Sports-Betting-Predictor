# sports/nhl/engine.py

import numpy as np
import pandas as pd
import streamlit as st

def get_ema(series, span=5, default=0.0):
    if series is None or len(series) == 0 or series.dropna().empty: return default
    val = series.dropna().ewm(span=span, min_periods=1).mean().iloc[-1]
    return default if pd.isna(val) else float(val)

@st.cache_data
def calculate_nhl_baselines(player_name, opp_team, spread_val, total_val, weekly_df):
    """Calculates Expected Rates for Shots, Goals, and Assists."""
    if weekly_df.empty:
        # Fallback baselines if data is empty
        return {
            "player_team": "BOS", "player_pos": "C", "implied_team_goals": 3.2,
            "team_shots_mean": 31.5, "team_shots_std": 4.5,
            "shot_share": 0.10, "shooting_pct": 0.12, "assist_share": 0.15
        }

    player_games = weekly_df[weekly_df["player_name"] == player_name].sort_values("date")
    recent = player_games.tail(15).copy()
    
    player_team = recent["recent_team"].iloc[-1] if not recent.empty else "BOS"
    player_pos = recent["position"].iloc[-1] if not recent.empty else "F"

    # Vegas Implied Goal Math
    # In hockey, the spread is usually -1.5 (Puck Line). 
    # Example: Total 6.5, Spread -1.5 -> Implied Team Total ~ 4.0
    implied_team_goals = (total_val - spread_val) / 2.0

    # Player Context Metrics
    recent["shot_share"] = np.where(recent["team_shots"] > 0, recent["shots_on_goal"] / recent["team_shots"], 0.0)
    recent["shooting_pct"] = np.where(recent["shots_on_goal"] > 0, recent["goals"] / recent["shots_on_goal"], 0.0)
    recent["assist_share"] = np.where(recent["team_goals"] > 0, recent["assists"] / recent["team_goals"], 0.0)

    team_shots_mean = recent["team_shots"].mean() if not recent.empty else 31.0
    team_shots_std = recent["team_shots"].std() if not recent.empty and len(recent) > 1 else 4.5

    return {
        "player_team": player_team, 
        "player_pos": player_pos,
        "implied_team_goals": max(1.0, implied_team_goals),
        "team_shots_mean": max(20.0, team_shots_mean),
        "team_shots_std": team_shots_std,
        "shot_share": min(1.0, max(0.0, get_ema(recent["shot_share"], span=5, default=0.08))),
        "shooting_pct": min(1.0, max(0.0, get_ema(recent["shooting_pct"], span=5, default=0.10))),
        "assist_share": min(1.0, max(0.0, get_ema(recent["assist_share"], span=5, default=0.12)))
    }

@st.cache_data
def run_nhl_simulation(num_sims, m):
    """
    Monte Carlo Engine using Poisson and Binomial Event Generators.
    """
    np.random.seed(42)
    
    # 1. Simulate Team Volume
    team_shots = np.random.normal(m["team_shots_mean"], m["team_shots_std"], num_sims)
    team_shots = np.maximum(15, team_shots).astype(int)
    
    # Poisson distribution for exact team goals based on Vegas Lines
    team_goals = np.random.poisson(m["implied_team_goals"], num_sims)

    # 2. Player Shot Generation
    player_shots = np.random.binomial(team_shots, m["shot_share"])
    
    # 3. Player Goal Generation (Did their shots go in?)
    player_goals = np.random.binomial(player_shots, m["shooting_pct"])
    
    # Prevent player from scoring more goals than the team total
    player_goals = np.minimum(player_goals, team_goals)

    # 4. Player Assist Generation
    # A player can only assist on goals they did NOT score themselves.
    available_team_goals = team_goals - player_goals
    player_assists = np.random.binomial(available_team_goals, m["assist_share"])

    # 5. Points = Goals + Assists
    player_points = player_goals + player_assists

    return pd.DataFrame({
        "team_shots": team_shots,
        "team_goals": team_goals,
        "shots": player_shots,
        "goals": player_goals,
        "assists": player_assists,
        "points": player_points
    })