# sports/nfl/engine.py

import numpy as np
import pandas as pd
import streamlit as st

def get_ema(series, span=4, default=0.0):
    if series is None or len(series) == 0 or series.dropna().empty:
        return default
    val = series.dropna().ewm(span=span, min_periods=1).mean().iloc[-1]
    return default if pd.isna(val) else float(val)

@st.cache_data
def calculate_defense_summary(weekly_data, target_team, pos_filter=None):
    available_seasons = sorted(weekly_data["season"].unique(), reverse=True)
    def_season = available_seasons[0] if available_seasons else 2025
    season_df = weekly_data[weekly_data["season"] == def_season].copy()
    if len(season_df) == 0 and len(available_seasons) > 1:
        def_season = available_seasons[1]
        season_df = weekly_data[weekly_data["season"] == def_season].copy()

    team_weekly = season_df.groupby(["opponent_team", "week"]).agg({
        "carries": "sum", "rushing_yards": "sum", "rushing_tds": "sum",
        "attempts": "sum", "completions": "sum", "passing_yards": "sum",
        "passing_tds": "sum", "sacks": "sum",
        "rushing_epa": "sum", "passing_epa": "sum"
    }).reset_index()

    if len(team_weekly) == 0:
        return {"season": def_season, "has_data": False}

    team_season_def = team_weekly.groupby("opponent_team").agg({
        "carries": "mean", "rushing_yards": "mean", "rushing_tds": "mean",
        "attempts": "mean", "completions": "mean", "passing_yards": "mean",
        "passing_tds": "mean", "sacks": "mean"
    }).reset_index()

    totals = season_df.groupby("opponent_team").agg({
        "carries": "sum", "rushing_yards": "sum", "attempts": "sum",
        "completions": "sum", "passing_yards": "sum",
        "rushing_epa": "sum", "passing_epa": "sum"
    }).reset_index()

    team_season_def["ypc"] = np.where(totals["carries"] > 0, totals["rushing_yards"] / totals["carries"], 0.0)
    team_season_def["comp_pct"] = np.where(totals["attempts"] > 0, (totals["completions"] / totals["attempts"]) * 100, 0.0)
    team_season_def["ypa"] = np.where(totals["attempts"] > 0, totals["passing_yards"] / totals["attempts"], 0.0)
    
    # EPA Calculations
    team_season_def["rush_epa_per_att"] = np.where(totals["carries"] > 0, totals["rushing_epa"] / totals["carries"], 0.0)
    team_season_def["pass_epa_per_att"] = np.where(totals["attempts"] > 0, totals["passing_epa"] / totals["attempts"], 0.0)

    # Ranks (Defense: Lower EPA allowed is better)
    team_season_def["rush_yds_rank"] = team_season_def["rushing_yards"].rank(ascending=True, method="min").astype(int)
    team_season_def["rush_att_rank"] = team_season_def["carries"].rank(ascending=True, method="min").astype(int)
    team_season_def["ypc_rank"] = team_season_def["ypc"].rank(ascending=True, method="min").astype(int)
    team_season_def["pass_yds_rank"] = team_season_def["passing_yards"].rank(ascending=True, method="min").astype(int)
    team_season_def["pass_att_rank"] = team_season_def["attempts"].rank(ascending=True, method="min").astype(int)
    team_season_def["comp_pct_rank"] = team_season_def["comp_pct"].rank(ascending=True, method="min").astype(int)
    team_season_def["ypa_rank"] = team_season_def["ypa"].rank(ascending=True, method="min").astype(int)
    team_season_def["sacks_rank"] = team_season_def["sacks"].rank(ascending=False, method="min").astype(int)
    team_season_def["rush_epa_rank"] = team_season_def["rush_epa_per_att"].rank(ascending=True, method="min").astype(int)
    team_season_def["pass_epa_rank"] = team_season_def["pass_epa_per_att"].rank(ascending=True, method="min").astype(int)

    target_row = team_season_def[team_season_def["opponent_team"] == target_team]
    if len(target_row) == 0:
        return {"season": def_season, "has_data": False}

    row = target_row.iloc[0]
    result_dict = {
        "season": def_season, "has_data": True, "is_2025_fallback": (def_season == 2025),
        "rush_yds_pg": row["rushing_yards"], "rush_yds_rank": int(row["rush_yds_rank"]),
        "rush_att_pg": row["carries"], "rush_att_rank": int(row["rush_att_rank"]),
        "ypc": row["ypc"], "ypc_rank": int(row["ypc_rank"]),
        "rush_tds_pg": row["rushing_tds"],
        "pass_yds_pg": row["passing_yards"], "pass_yds_rank": int(row["pass_yds_rank"]),
        "pass_att_pg": row["attempts"], "pass_att_rank": int(row["pass_att_rank"]),
        "comp_pct": row["comp_pct"], "comp_pct_rank": int(row["comp_pct_rank"]),
        "ypa": row["ypa"], "ypa_rank": int(row["ypa_rank"]),
        "sacks_pg": row["sacks"], "sacks_rank": int(row["sacks_rank"]),
        "rush_epa_per_att": row["rush_epa_per_att"], "rush_epa_rank": int(row["rush_epa_rank"]),
        "pass_epa_per_att": row["pass_epa_per_att"], "pass_epa_rank": int(row["pass_epa_rank"]),
        "total_teams": len(team_season_def)
    }

    if pos_filter and pos_filter in ["RB", "WR", "TE"]:
        pos_df = season_df[season_df["position"] == pos_filter]
        pos_weekly = pos_df.groupby(["opponent_team", "week"]).agg({
            "receiving_yards": "sum", "rushing_yards": "sum"
        }).reset_index()
        
        if not pos_weekly.empty:
            pos_season = pos_weekly.groupby("opponent_team").mean(numeric_only=True).reset_index()
            pos_season["dvp_rec_rank"] = pos_season["receiving_yards"].rank(ascending=True, method="min").astype(int)
            pos_season["dvp_rush_rank"] = pos_season["rushing_yards"].rank(ascending=True, method="min").astype(int)
            
            dvp_row = pos_season[pos_season["opponent_team"] == target_team]
            if not dvp_row.empty:
                result_dict["dvp_rec_yds"] = dvp_row.iloc[0]["receiving_yards"]
                result_dict["dvp_rec_rank"] = int(dvp_row.iloc[0]["dvp_rec_rank"])
                result_dict["dvp_rush_yds"] = dvp_row.iloc[0]["rushing_yards"]
                result_dict["dvp_rush_rank"] = int(dvp_row.iloc[0]["dvp_rush_rank"])
                result_dict["dvp_pos"] = pos_filter

    return result_dict

@st.cache_data
def calculate_offense_summary(weekly_data, target_team):
    available_seasons = sorted(weekly_data["season"].unique(), reverse=True)
    off_season = available_seasons[0] if available_seasons else 2025
    season_df = weekly_data[weekly_data["season"] == off_season].copy()
    if len(season_df) == 0 and len(available_seasons) > 1:
        off_season = available_seasons[1]
        season_df = weekly_data[weekly_data["season"] == off_season].copy()

    team_weekly = season_df.groupby(["recent_team", "week"]).agg({
        "carries": "sum", "rushing_yards": "sum", "rushing_tds": "sum",
        "attempts": "sum", "completions": "sum", "passing_yards": "sum",
        "passing_tds": "sum", "sacks": "sum",
        "rushing_epa": "sum", "passing_epa": "sum"
    }).reset_index()

    if len(team_weekly) == 0:
        return {"season": off_season, "has_data": False}

    team_season_off = team_weekly.groupby("recent_team").agg({
        "carries": "mean", "rushing_yards": "mean", "rushing_tds": "mean",
        "attempts": "mean", "completions": "mean", "passing_yards": "mean",
        "passing_tds": "mean", "sacks": "mean"
    }).reset_index()

    totals = season_df.groupby("recent_team").agg({
        "carries": "sum", "rushing_yards": "sum", "attempts": "sum",
        "completions": "sum", "passing_yards": "sum",
        "rushing_epa": "sum", "passing_epa": "sum"
    }).reset_index()

    team_season_off["ypc"] = np.where(totals["carries"] > 0, totals["rushing_yards"] / totals["carries"], 0.0)
    team_season_off["comp_pct"] = np.where(totals["attempts"] > 0, (totals["completions"] / totals["attempts"]) * 100, 0.0)
    team_season_off["ypa"] = np.where(totals["attempts"] > 0, totals["passing_yards"] / totals["attempts"], 0.0)
    
    # EPA Calculations
    team_season_off["rush_epa_per_att"] = np.where(totals["carries"] > 0, totals["rushing_epa"] / totals["carries"], 0.0)
    team_season_off["pass_epa_per_att"] = np.where(totals["attempts"] > 0, totals["passing_epa"] / totals["attempts"], 0.0)

    # Ranks (Offense: Higher EPA generated is better)
    team_season_off["rush_yds_rank"] = team_season_off["rushing_yards"].rank(ascending=False, method="min").astype(int)
    team_season_off["rush_att_rank"] = team_season_off["carries"].rank(ascending=False, method="min").astype(int)
    team_season_off["ypc_rank"] = team_season_off["ypc"].rank(ascending=False, method="min").astype(int)
    team_season_off["pass_yds_rank"] = team_season_off["passing_yards"].rank(ascending=False, method="min").astype(int)
    team_season_off["pass_att_rank"] = team_season_off["attempts"].rank(ascending=False, method="min").astype(int)
    team_season_off["comp_pct_rank"] = team_season_off["comp_pct"].rank(ascending=False, method="min").astype(int)
    team_season_off["ypa_rank"] = team_season_off["ypa"].rank(ascending=False, method="min").astype(int)
    team_season_off["sacks_rank"] = team_season_off["sacks"].rank(ascending=True, method="min").astype(int)
    team_season_off["rush_epa_rank"] = team_season_off["rush_epa_per_att"].rank(ascending=False, method="min").astype(int)
    team_season_off["pass_epa_rank"] = team_season_off["pass_epa_per_att"].rank(ascending=False, method="min").astype(int)

    target_row = team_season_off[team_season_off["recent_team"] == target_team]
    if len(target_row) == 0:
        return {"season": off_season, "has_data": False}

    row = target_row.iloc[0]
    return {
        "season": off_season, "has_data": True, "is_2025_fallback": (off_season == 2025),
        "rush_yds_pg": row["rushing_yards"], "rush_yds_rank": int(row["rush_yds_rank"]),
        "rush_att_pg": row["carries"], "rush_att_rank": int(row["rush_att_rank"]),
        "ypc": row["ypc"], "ypc_rank": int(row["ypc_rank"]),
        "rush_tds_pg": row["rushing_tds"],
        "pass_yds_pg": row["passing_yards"], "pass_yds_rank": int(row["pass_yds_rank"]),
        "pass_att_pg": row["attempts"], "pass_att_rank": int(row["pass_att_rank"]),
        "comp_pct": row["comp_pct"], "comp_pct_rank": int(row["comp_pct_rank"]),
        "ypa": row["ypa"], "ypa_rank": int(row["ypa_rank"]),
        "sacks_pg": row["sacks"], "sacks_rank": int(row["sacks_rank"]),
        "rush_epa_per_att": row["rush_epa_per_att"], "rush_epa_rank": int(row["rush_epa_rank"]),
        "pass_epa_per_att": row["pass_epa_per_att"], "pass_epa_rank": int(row["pass_epa_rank"]),
        "total_teams": len(team_season_off)
    }

@st.cache_data
def calculate_matchup_baselines(player_name, opp_team, spread_val, total_val, weather_dict, weekly_df):
    player_games = weekly_df[weekly_df["player_name"] == player_name].sort_values(["season", "week"])
    recent_player_games = player_games.tail(12).copy()
    
    player_team = recent_player_games["recent_team"].iloc[-1] if len(recent_player_games) > 0 else "SF"
    player_pos = recent_player_games["position"].iloc[-1] if ("position" in recent_player_games.columns and len(recent_player_games) > 0) else "RB"

    team_weekly_off = weekly_df.groupby(["recent_team", "season", "week"]).agg({
        "attempts": "sum", "carries": "sum", "sacks": "sum", "rushing_yards": "sum",
        "rushing_tds": "sum", "passing_tds": "sum", "rushing_epa": "sum", "passing_epa": "sum"
    }).reset_index()

    implied_team_total = (total_val - spread_val) / 2.0
    pace_multiplier = 1.0 + ((total_val - 44.0) * 0.008)
    efficiency_multiplier = 1.0 + ((implied_team_total - 22.0) * 0.012)

    wind_mph = weather_dict.get("wind_mph", 0.0)
    precip_mm = weather_dict.get("precip_mm", 0.0)
    wind_pass_penalty = 1.0
    wind_rush_boost = 1.0
    precip_catch_penalty = 1.0
    
    if wind_mph > 15.0:
        wind_pass_penalty = max(0.6, 1.0 - ((wind_mph - 15.0) * 0.015))
        wind_rush_boost = min(1.2, 1.0 + ((wind_mph - 15.0) * 0.01))
    if precip_mm > 5.0:
        precip_catch_penalty = 0.95

    # League & Opponent EPA Benchmarks
    team_def_stats = weekly_df.groupby(["opponent_team", "season", "week"]).agg({
        "rushing_yards": "sum", "receiving_yards": "sum", "attempts": "sum",
        "completions": "sum", "passing_tds": "sum", "interceptions": "sum",
        "carries": "sum", "rushing_tds": "sum", "sacks": "sum",
        "rushing_epa": "sum", "passing_epa": "sum"
    }).reset_index()

    # Calculate defensive rate stats FIRST before calculating league/opp averages!
    team_def_stats["comp_rate_allowed"] = np.where(team_def_stats["attempts"] > 0, team_def_stats["completions"] / team_def_stats["attempts"], 0.65)
    team_def_stats["pass_td_rate_allowed"] = np.where(team_def_stats["attempts"] > 0, team_def_stats["passing_tds"] / team_def_stats["attempts"], 0.04)
    team_def_stats["int_rate_forced"] = np.where(team_def_stats["attempts"] > 0, team_def_stats["interceptions"] / team_def_stats["attempts"], 0.02)
    team_def_stats["rush_td_rate_allowed"] = np.where(team_def_stats["carries"] > 0, team_def_stats["rushing_tds"] / team_def_stats["carries"], 0.03)

    # NOW create the snapshot averages
    league_def = team_def_stats.mean(numeric_only=True)
    opp_def_df = team_def_stats[team_def_stats["opponent_team"] == opp_team]
    opp_def = opp_def_df.mean(numeric_only=True) if not opp_def_df.empty else league_def

    league_rush_epa_att = team_def_stats["rushing_epa"].sum() / max(1, team_def_stats["carries"].sum())
    league_pass_epa_att = team_def_stats["passing_epa"].sum() / max(1, team_def_stats["attempts"].sum())

    opp_rush_epa_allowed = opp_def_df["rushing_epa"].sum() / max(1, opp_def_df["carries"].sum()) if not opp_def_df.empty else league_rush_epa_att
    opp_pass_epa_allowed = opp_def_df["passing_epa"].sum() / max(1, opp_def_df["attempts"].sum()) if not opp_def_df.empty else league_pass_epa_att

    # Calculate defensive EPA weakness (Positive delta = defense gives up high EPA)
    rush_epa_delta = opp_rush_epa_allowed - league_rush_epa_att
    pass_epa_delta = opp_pass_epa_allowed - league_pass_epa_att

    league_avg_rush_att = team_weekly_off["carries"].mean() if not team_weekly_off.empty else 27.0
    league_avg_pass_att = team_weekly_off["attempts"].mean() if not team_weekly_off.empty else 34.0
    league_avg_sacks = team_weekly_off["sacks"].mean() if not team_weekly_off.empty else 2.5
    league_ypc = team_weekly_off["rushing_yards"].sum() / max(1, team_weekly_off["carries"].sum()) if not team_weekly_off.empty else 4.3

    off_rush_series = team_weekly_off[team_weekly_off["recent_team"] == player_team]["carries"]
    off_pass_series = team_weekly_off[team_weekly_off["recent_team"] == player_team]["attempts"]
    off_sacks_series = team_weekly_off[team_weekly_off["recent_team"] == player_team]["sacks"]

    team_avg_rush_att = get_ema(off_rush_series, span=6, default=27.5)
    team_avg_pass_att = get_ema(off_pass_series, span=6, default=34.0)
    team_sacks_allowed = get_ema(off_sacks_series, span=4, default=league_avg_sacks)
    
    off_team_data = team_weekly_off[team_weekly_off["recent_team"] == player_team]
    off_ypc = off_team_data["rushing_yards"].sum() / max(1, off_team_data["carries"].sum()) if not off_team_data.empty else league_ypc

    team_std_rush_att = float(off_rush_series.std()) if len(off_rush_series) > 1 and not pd.isna(off_rush_series.std()) else 4.8
    team_std_pass_att = float(off_pass_series.std()) if len(off_pass_series) > 1 and not pd.isna(off_pass_series.std()) else 5.2

    def_rush_att = opp_def["carries"]
    def_pass_att = opp_def["attempts"]
    def_rush_factor = (def_rush_att / league_avg_rush_att) if league_avg_rush_att > 0 else 1.0
    def_pass_factor = (def_pass_att / league_avg_pass_att) if league_avg_pass_att > 0 else 1.0

    opp_sacks_forced = opp_def["sacks"]
    opp_ypc_allowed = opp_def_df["rushing_yards"].sum() / max(1, opp_def_df["carries"].sum()) if not opp_def_df.empty else league_ypc

    pass_trench_factor = min(2.0, max(0.5, (opp_sacks_forced / max(1, league_avg_sacks)) * (team_sacks_allowed / max(1, league_avg_sacks))))
    run_trench_factor = min(1.5, max(0.6, (opp_ypc_allowed / max(1, league_ypc)) * (off_ypc / max(1, league_ypc))))

    pos_df = weekly_df[weekly_df["position"] == player_pos]
    pos_def_weekly = pos_df.groupby(["opponent_team", "season", "week"]).agg({
        "targets": "sum", "receptions": "sum", "receiving_yards": "sum", "receiving_tds": "sum",
        "carries": "sum", "rushing_yards": "sum", "rushing_tds": "sum"
    }).reset_index()

    league_pos_def = pos_def_weekly.mean(numeric_only=True)
    opp_pos_df = pos_def_weekly[pos_def_weekly["opponent_team"] == opp_team]
    opp_pos_def = opp_pos_df.mean(numeric_only=True) if not opp_pos_df.empty else league_pos_def

    def_pass_yd_factor = (opp_def["receiving_yards"] / league_def["receiving_yards"]) if league_def["receiving_yards"] > 0 else 1.0
    def_comp_factor = (opp_def["comp_rate_allowed"] / league_def["comp_rate_allowed"]) if league_def["comp_rate_allowed"] > 0 else 1.0
    def_pass_td_factor = (opp_def["pass_td_rate_allowed"] / league_def["pass_td_rate_allowed"]) if league_def["pass_td_rate_allowed"] > 0 else 1.0
    def_int_factor = (opp_def["int_rate_forced"] / league_def["int_rate_forced"]) if league_def["int_rate_forced"] > 0 else 1.0
    def_rush_td_factor = (opp_def["rush_td_rate_allowed"] / league_def["rush_td_rate_allowed"]) if league_def["rush_td_rate_allowed"] > 0 else 1.0

    if player_pos in ["WR", "TE", "RB"]:
        dvp_rec_yd_factor = (opp_pos_def["receiving_yards"] / league_pos_def["receiving_yards"]) if league_pos_def["receiving_yards"] > 0 else 1.0
        dvp_rec_td_factor = (opp_pos_def["receiving_tds"] / league_pos_def["receiving_tds"]) if league_pos_def["receiving_tds"] > 0 else 1.0
        dvp_rush_yd_factor = (opp_pos_def["rushing_yards"] / league_pos_def["rushing_yards"]) if league_pos_def["rushing_yards"] > 0 else 1.0
        dvp_rush_td_factor = (opp_pos_def["rushing_tds"] / league_pos_def["rushing_tds"]) if league_pos_def["rushing_tds"] > 0 else 1.0
    else:
        dvp_rec_yd_factor = def_pass_yd_factor
        dvp_rec_td_factor = def_pass_td_factor
        dvp_rush_yd_factor = 1.0
        dvp_rush_td_factor = def_rush_td_factor

    proj_team_rush = max(12.0, (team_avg_rush_att * def_rush_factor + (-spread_val * 0.45)) * pace_multiplier * wind_rush_boost)
    proj_team_pass = max(15.0, (team_avg_pass_att * def_pass_factor + (spread_val * 0.55)) * pace_multiplier * wind_pass_penalty)

    merged = recent_player_games.merge(team_weekly_off, on=["recent_team", "season", "week"], suffixes=("", "_team"))
    if merged.empty:
        merged = recent_player_games.copy()
        merged["carries_team"] = team_avg_rush_att
        merged["attempts_team"] = team_avg_pass_att
        merged["rushing_tds_team"] = 1.0
        merged["passing_tds_team"] = 1.5

    merged["rush_share"] = np.where(merged["carries_team"] > 0, merged["carries"] / merged["carries_team"], 0.0)
    merged["rec_share"] = np.where(merged["attempts_team"] > 0, merged["targets"] / merged["attempts_team"], 0.0)
    merged["pass_share"] = np.where(merged["attempts_team"] > 0, merged["attempts"] / merged["attempts_team"], 0.0)
    
    merged["rush_td_share"] = np.where(merged["rushing_tds_team"] > 0, merged["rushing_tds"] / merged["rushing_tds_team"], 0.0)
    merged["rec_td_share"] = np.where(merged["passing_tds_team"] > 0, merged["receiving_tds"] / merged["passing_tds_team"], 0.0)
    
    merged["ypc"] = np.where(merged["carries"] > 0, merged["rushing_yards"] / merged["carries"], 0.0)
    merged["ypt"] = np.where(merged["receptions"] > 0, merged["receiving_yards"] / merged["receptions"], 0.0)
    merged["ypa"] = np.where(merged["attempts"] > 0, merged["passing_yards"] / merged["attempts"], 0.0)
    merged["catch_rate"] = np.where(merged["targets"] > 0, merged["receptions"] / merged["targets"], 0.0)
    merged["comp_rate"] = np.where(merged["attempts"] > 0, merged["completions"] / merged["attempts"], 0.0)
    merged["int_rate"] = np.where(merged["attempts"] > 0, merged["interceptions"] / merged["attempts"], 0.0)

    # -------------------------------------------------------------
    # OFFENSIVE PLAYER EPA CALCULATION
    # -------------------------------------------------------------
    merged["rush_epa_per_att"] = np.where(merged["carries"] > 0, merged["rushing_epa"] / merged["carries"], 0.0)
    merged["rec_epa_per_tgt"] = np.where(merged["targets"] > 0, merged["receiving_epa"] / merged["targets"], 0.0)
    merged["pass_epa_per_att"] = np.where(merged["attempts"] > 0, merged["passing_epa"] / merged["attempts"], 0.0)
    
    player_rush_epa = get_ema(merged[merged["carries"] > 0]["rush_epa_per_att"], span=4, default=0.0)
    player_rec_epa = get_ema(merged[merged["targets"] > 0]["rec_epa_per_tgt"], span=4, default=0.0)
    player_pass_epa = get_ema(merged[merged["attempts"] > 0]["pass_epa_per_att"], span=4, default=0.0)

    # The EPA Efficiency Multiplier integrates True Talent + Matchup Weakness
    epa_rush_mult = max(0.7, min(1.3, 1.0 + (rush_epa_delta * 0.4) + (player_rush_epa * 0.15)))
    epa_pass_mult = max(0.7, min(1.3, 1.0 + (pass_epa_delta * 0.4) + (player_pass_epa * 0.15)))
    epa_rec_mult = max(0.7, min(1.3, 1.0 + (pass_epa_delta * 0.4) + (player_rec_epa * 0.15)))

    # -------------------------------------------------------------
    # aDOT CALCULATION
    # -------------------------------------------------------------
    air_yards_col = "receiving_air_yards" if "receiving_air_yards" in merged.columns else ("air_yards" if "air_yards" in merged.columns else None)
    if air_yards_col:
        merged["adot"] = np.where(merged["targets"] > 0, merged[air_yards_col] / merged["targets"], np.nan)
        player_adot = get_ema(merged[merged["targets"] > 0]["adot"], span=4, default=(10.5 if player_pos == "WR" else (7.0 if player_pos == "TE" else 3.5)))
    else:
        raw_ypt_est = merged["receiving_yards"].sum() / max(1.0, merged["targets"].sum())
        player_adot = max(2.5, min(16.0, raw_ypt_est * 1.15))

    adot_variance_mult = min(1.65, max(0.65, 1.0 + ((player_adot - 8.5) * 0.055)))

    opp_rush_share = get_ema(merged["rush_share"], span=4, default=(0.5 if player_pos == "RB" else 0.0))
    opp_rec_share = get_ema(merged["rec_share"], span=4, default=(0.12 if player_pos == "RB" else 0.22))
    opp_pass_share = get_ema(merged["pass_share"], span=4, default=(1.0 if player_pos == "QB" else 0.0))
    
    rz_rush_share = get_ema(merged["rush_td_share"], span=4, default=(0.4 if player_pos == "RB" else 0.0))
    rz_target_share = get_ema(merged["rec_td_share"], span=4, default=(0.15 if player_pos in ["WR", "TE"] else 0.05))
    
    raw_catch_rate = get_ema(merged[merged["targets"] > 0]["catch_rate"], span=4, default=0.65)
    raw_comp_rate = get_ema(merged[merged["attempts"] > 0]["comp_rate"], span=4, default=0.65)
    raw_ypc = get_ema(merged[merged["carries"] > 0]["ypc"], span=4, default=4.3)
    raw_ypt = get_ema(merged[merged["receptions"] > 0]["ypt"], span=4, default=8.0)
    raw_ypa = get_ema(merged[merged["attempts"] > 0]["ypa"], span=4, default=7.0)
    
    ypc_base = max(3.0, raw_ypc)
    ypt_base = max(5.0, raw_ypt)
    ypa_base = max(4.0, raw_ypa)
    
    int_rate_base = (get_ema(merged[merged["attempts"] > 0]["int_rate"], span=4, default=0.02) * 0.75) + 0.005

    ypc_std = (merged["rushing_yards"].std() / max(1.0, merged["carries"].mean())) if len(merged) > 1 else 2.8
    ypt_std = (merged["receiving_yards"].std() / max(1.0, merged["receptions"].mean())) if len(merged) > 1 else 3.5
    ypa_std = (merged["passing_yards"].std() / max(1.0, merged["attempts"].mean())) if len(merged) > 1 else 2.5

    scaled_rec_eff_std = float(np.nan_to_num(ypt_std, nan=3.5)) * adot_variance_mult

    # Multipliers applied natively to Log-Normal mean expectations
    adj_catch_rate = raw_catch_rate * def_comp_factor * (1 - ((pass_trench_factor - 1) * 0.05)) * precip_catch_penalty * wind_pass_penalty
    adj_comp_rate = raw_comp_rate * def_comp_factor * (1 - ((pass_trench_factor - 1) * 0.05)) * precip_catch_penalty * wind_pass_penalty
    
    adj_pass_eff_mean = ypa_base * def_pass_yd_factor * efficiency_multiplier * epa_pass_mult * (1 - ((pass_trench_factor - 1) * 0.05)) * wind_pass_penalty
    adj_rec_eff_mean = ypt_base * dvp_rec_yd_factor * efficiency_multiplier * epa_rec_mult * wind_pass_penalty
    adj_rush_eff_mean = ypc_base * run_trench_factor * epa_rush_mult * (dvp_rush_yd_factor if player_pos == "RB" else 1.0) * efficiency_multiplier

    adj_int_rate = ((int_rate_base * def_int_factor) / efficiency_multiplier) * (1 + ((pass_trench_factor - 1) * 0.15))
    if wind_mph > 15.0:
        adj_int_rate *= 1.25 

    return {
        "player_team": player_team, "player_pos": player_pos, "implied_team_total": implied_team_total,
        "proj_team_rush": proj_team_rush, "team_rush_std": team_std_rush_att,
        "proj_team_pass": proj_team_pass, "team_pass_std": team_std_pass_att,
        "opp_rush_share": min(1.0, max(0.0, opp_rush_share)),
        "opp_rec_share": min(1.0, max(0.0, opp_rec_share)),
        "opp_pass_share": min(1.0, max(0.0, opp_pass_share)),
        "rz_rush_share": min(1.0, max(0.0, rz_rush_share)),
        "rz_target_share": min(1.0, max(0.0, rz_target_share)),
        "catch_rate": min(1.0, max(0.2, adj_catch_rate)),
        "comp_rate": min(1.0, max(0.2, adj_comp_rate)),
        "player_adot": round(float(player_adot), 1),
        "player_epa": round(float(player_pass_epa if player_pos == "QB" else (player_rush_epa if player_pos == "RB" else player_rec_epa)), 3),
        "rush_eff_mean": adj_rush_eff_mean,
        "rush_eff_std": float(np.nan_to_num(ypc_std, nan=2.8)),
        "rec_eff_mean": adj_rec_eff_mean,
        "rec_eff_std": scaled_rec_eff_std,
        "pass_eff_mean": adj_pass_eff_mean,
        "pass_eff_std": float(np.nan_to_num(ypa_std, nan=2.5)),
        "def_rush_td_factor": dvp_rush_td_factor,
        "def_pass_td_factor": dvp_rec_td_factor,
        "int_rate": min(1.0, max(0.0, adj_int_rate))
    }

@st.cache_data
def run_simulation(num_sims, m):
    np.random.seed(42)
    
    team_rush = np.maximum(10, np.random.normal(m["proj_team_rush"], m["team_rush_std"], num_sims).astype(int))
    team_pass = np.maximum(15, np.random.normal(m["proj_team_pass"], m["team_pass_std"], num_sims).astype(int))

    carries = np.random.binomial(n=team_rush, p=m["opp_rush_share"])
    targets = np.random.binomial(n=team_pass, p=m["opp_rec_share"])
    receptions = np.random.binomial(n=targets, p=m["catch_rate"])
    pass_attempts = np.random.binomial(n=team_pass, p=m["opp_pass_share"])
    completions = np.random.binomial(n=pass_attempts, p=m["comp_rate"])

    expected_rz_trips = np.maximum(1.0, m["implied_team_total"] / 5.5)
    team_rz_trips = np.random.poisson(expected_rz_trips, num_sims)
    
    run_pass_ratio = np.maximum(0.01, m["proj_team_rush"] / (m["proj_team_rush"] + m["proj_team_pass"]))
    team_rz_rush_plays = np.random.binomial(n=team_rz_trips, p=run_pass_ratio)
    team_rz_pass_plays = team_rz_trips - team_rz_rush_plays

    player_rz_carries = np.minimum(carries, np.random.binomial(n=team_rz_rush_plays, p=m["rz_rush_share"]))
    player_rz_targets = np.minimum(targets, np.random.binomial(n=team_rz_pass_plays, p=m["rz_target_share"]))
    qb_rz_pass_attempts = np.minimum(pass_attempts, np.random.binomial(n=team_rz_pass_plays, p=m["opp_pass_share"]))

    player_open_carries = carries - player_rz_carries
    player_open_targets = targets - player_rz_targets
    qb_open_pass_attempts = pass_attempts - qb_rz_pass_attempts

    rz_rush_conv = min(1.0, 0.40 * m["def_rush_td_factor"])
    open_rush_conv = min(1.0, 0.01 * m["def_rush_td_factor"])
    rz_pass_conv = min(1.0, 0.35 * m["def_pass_td_factor"])
    open_pass_conv = min(1.0, 0.015 * m["def_pass_td_factor"])

    rush_tds = np.random.binomial(player_rz_carries, p=rz_rush_conv) + np.random.binomial(player_open_carries, p=open_rush_conv)
    rec_tds = np.random.binomial(player_rz_targets, p=rz_pass_conv) + np.random.binomial(player_open_targets, p=open_pass_conv)
    pass_tds = np.random.binomial(qb_rz_pass_attempts, p=rz_pass_conv) + np.random.binomial(qb_open_pass_attempts, p=open_pass_conv)
    ints = np.random.binomial(n=pass_attempts, p=m["int_rate"])

    def lognormal_yards(opportunities, eff_mean, eff_std):
        expected_yards = opportunities * eff_mean
        std_yards = np.sqrt(opportunities) * eff_std
        shift = 15.0 
        shifted_mean = np.maximum(1.0, expected_yards + shift)
        std_yards = np.maximum(0.1, std_yards)
        sigma_sq = np.log(1 + (std_yards / shifted_mean)**2)
        mu = np.log(shifted_mean) - (sigma_sq / 2)
        raw_yards = np.random.lognormal(mu, np.sqrt(sigma_sq)) - shift
        return np.where(opportunities == 0, 0.0, raw_yards)

    rush_yards = lognormal_yards(carries, m["rush_eff_mean"], m["rush_eff_std"])
    rec_yards = lognormal_yards(receptions, m["rec_eff_mean"], m["rec_eff_std"])
    pass_yards = lognormal_yards(pass_attempts, m["pass_eff_mean"], m["pass_eff_std"])

    return pd.DataFrame({
        "team_rush": team_rush, "carries": carries, "rush_yards": rush_yards, "rush_tds": rush_tds,
        "team_pass": team_pass, "targets": targets, "receptions": receptions, "rec_yards": rec_yards, "rec_tds": rec_tds,
        "pass_attempts": pass_attempts, "completions": completions, "pass_yards": pass_yards, "pass_tds": pass_tds, "interceptions": ints
    })