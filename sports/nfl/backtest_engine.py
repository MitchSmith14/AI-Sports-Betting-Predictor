# sports/nfl/backtest_engine.py

import pandas as pd
import numpy as np
import datetime
import streamlit as st
from tqdm import tqdm
from sports.nfl.engine import calculate_matchup_baselines, run_simulation

def filter_historical_data(weekly_df, target_season, target_week):
    """
    Prevents data leakage (Lookahead Bias).
    Returns only the game logs that occurred BEFORE the target season/week.
    """
    return weekly_df[
        (weekly_df["season"] < target_season) | 
        ((weekly_df["season"] == target_season) & (weekly_df["week"] < target_week))
    ].copy()

def run_historical_backtest(weekly_df, schedules_df, target_season, start_week=1, end_week=18, num_sims=5000):
    """
    Runs a walk-forward simulation across historical NFL weeks to evaluate model accuracy.
    """
    results_log = []
    
    # Filter schedule to the requested window
    season_schedule = schedules_df[
        (schedules_df["season"] == target_season) & 
        (schedules_df["week"] >= start_week) & 
        (schedules_df["week"] <= end_week)
    ]

    # Initialize a progress bar for Streamlit UI
    progress_text = "Running Walk-Forward Backtest..."
    backtest_bar = st.progress(0, text=progress_text)
    total_games = len(season_schedule)

    for idx, game in enumerate(season_schedule.itertuples()):
        current_week = game.week
        home_team = game.home_team
        away_team = game.away_team
        
        # Use actual closing lines from historical Vegas data
        closing_spread = game.spread_line if not pd.isna(game.spread_line) else 0.0
        closing_total = game.total_line if not pd.isna(game.total_line) else 45.0
        roof_type = str(game.roof).title() if pd.notna(game.roof) else "Outdoor"
        
        # Basic weather assumption for past games (could integrate historical weather API later)
        weather_dict = {"wind_mph": 5.0, "precip_mm": 0.0, "condition": "Dome" if roof_type in ["Dome", "Closed"] else "Outdoor"}
        
        # 1. Blindfold the data (Walk-Forward)
        historical_slice = filter_historical_data(weekly_df, target_season, current_week)
        
        # Get actual box score outcomes for this exact week to grade the model
        actuals_df = weekly_df[
            (weekly_df["season"] == target_season) & 
            (weekly_df["week"] == current_week) &
            (weekly_df["recent_team"].isin([home_team, away_team]))
        ]

        # 2. Find primary starters to test (QBs, Top 2 RBs, Top 2 WRs, Top TE)
        for team, opp_team, is_home in [(home_team, away_team, True), (away_team, home_team, False)]:
            team_actuals = actuals_df[actuals_df["recent_team"] == team]
            if team_actuals.empty:
                continue
                
            # Loop over players who actually recorded stats in this historical game
            for _, player_actual in team_actuals.iterrows():
                player_name = player_actual["player_name"]
                pos = str(player_actual["position"]).upper()
                
                # Filter out low-volume players to speed up the backtest
                if pos not in ["QB", "RB", "WR", "TE"]: continue
                if pos == "QB" and player_actual["attempts"] < 10: continue
                if pos in ["RB", "WR", "TE"] and player_actual["targets"] < 3 and player_actual["carries"] < 3: continue

                # App Spread is negative for favorites. 
                # If home_team is favored, spread_line is negative.
                app_spread = -closing_spread if is_home else closing_spread

                try:
                    # Generate Baselines without future knowledge
                    matchup = calculate_matchup_baselines(
                        player_name=player_name,
                        opp_team=opp_team,
                        spread_val=app_spread,
                        total_val=closing_total,
                        weather_dict=weather_dict,
                        weekly_df=historical_slice,
                        inactive_players=[], # Assuming 0 inactives for pure baseline backtest
                        coverage_scheme="Neutral"
                    )
                    
                    # Run Simulation
                    sims = run_simulation(num_sims, matchup)
                    
                    # Compare Projections vs Actuals
                    # 1. Passing Yards (QBs)
                    if pos == "QB":
                        sim_mean_pass = sims["pass_yards"].mean()
                        actual_pass = player_actual["passing_yards"]
                        prob_over_200 = (sims["pass_yards"] >= 200.5).mean()
                        prob_over_250 = (sims["pass_yards"] >= 250.5).mean()
                        
                        results_log.append({
                            "season": target_season, "week": current_week,
                            "player": player_name, "position": pos, "team": team,
                            "stat_type": "pass_yards",
                            "sim_mean": sim_mean_pass, "actual": actual_pass,
                            "error": actual_pass - sim_mean_pass,
                            "prob_over_200": prob_over_200, "actual_over_200": 1 if actual_pass >= 200 else 0,
                            "prob_over_250": prob_over_250, "actual_over_250": 1 if actual_pass >= 250 else 0
                        })

                    # 2. Rushing Yards (RBs)
                    if pos in ["RB", "QB"]:
                        sim_mean_rush = sims["rush_yards"].mean()
                        actual_rush = player_actual["rushing_yards"]
                        prob_over_40 = (sims["rush_yards"] >= 40.5).mean()
                        
                        results_log.append({
                            "season": target_season, "week": current_week,
                            "player": player_name, "position": pos, "team": team,
                            "stat_type": "rush_yards",
                            "sim_mean": sim_mean_rush, "actual": actual_rush,
                            "error": actual_rush - sim_mean_rush,
                            "prob_over_40": prob_over_40, "actual_over_40": 1 if actual_rush >= 40 else 0,
                            "prob_over_250": None, "actual_over_250": None # Padding for dataframe consistency
                        })
                        
                    # 3. Receiving Yards (WRs/TEs/RBs)
                    if pos in ["WR", "TE", "RB"]:
                        sim_mean_rec = sims["rec_yards"].mean()
                        actual_rec = player_actual["receiving_yards"]
                        prob_over_40 = (sims["rec_yards"] >= 40.5).mean()
                        
                        results_log.append({
                            "season": target_season, "week": current_week,
                            "player": player_name, "position": pos, "team": team,
                            "stat_type": "rec_yards",
                            "sim_mean": sim_mean_rec, "actual": actual_rec,
                            "error": actual_rec - sim_mean_rec,
                            "prob_over_40": prob_over_40, "actual_over_40": 1 if actual_rec >= 40 else 0,
                            "prob_over_250": None, "actual_over_250": None
                        })

                except Exception as e:
                    # Skip players with insufficient historical data to form a baseline
                    continue
        
        # Update progress bar
        backtest_bar.progress((idx + 1) / total_games, text=f"Backtesting Week {current_week} ({team} vs {opp_team})...")

    backtest_bar.empty()
    return pd.DataFrame(results_log)