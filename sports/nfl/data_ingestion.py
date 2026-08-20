# sports/nfl/data_ingestion.py

import numpy as np
import pandas as pd
import streamlit as st
from sports.nfl.config import NFL_TEAM_COLORS

try:
    import nflreadpy as nfl
    HAS_NFLREADPY = True
except ImportError:
    HAS_NFLREADPY = False

@st.cache_data(ttl=3600, show_spinner="Loading NFL data...")
def load_nfl_data():
    if not HAS_NFLREADPY:
        return pd.DataFrame()
    dfs = []
    for season in [2024, 2025, 2026]:
        try:
            season_df = nfl.load_player_stats([season]).to_pandas()
            if not season_df.empty:
                dfs.append(season_df)
        except Exception:
            continue

    if not dfs:
        return pd.DataFrame()
    df = pd.concat(dfs, ignore_index=True)
    if "player_display_name" in df.columns: df["player_name"] = df["player_display_name"]
    if "target_share" in df.columns and "tgt_sh" not in df.columns: df["tgt_sh"] = df["target_share"]
    if "team" in df.columns and "recent_team" not in df.columns: df["recent_team"] = df["team"]
    if "position" not in df.columns and "player_position" in df.columns: df["position"] = df["player_position"]
    if "rushing_attempts" in df.columns and "carries" not in df.columns: df["carries"] = df["rushing_attempts"]
    if "passing_interceptions" in df.columns and "interceptions" not in df.columns: df["interceptions"] = df["passing_interceptions"]
    if "passing_sacks" in df.columns and "sacks" not in df.columns: df["sacks"] = df["passing_sacks"]
    elif "sacks_suffered" in df.columns and "sacks" not in df.columns: df["sacks"] = df["sacks_suffered"]
    elif "sack" in df.columns and "sacks" not in df.columns: df["sacks"] = df["sack"]

    if "position" in df.columns: df["position"] = df["position"].astype(str).str.upper()

    numeric_cols = [
        "attempts", "completions", "passing_yards", "passing_tds", "interceptions",
        "sacks", "carries", "rushing_yards", "rushing_tds", "targets",
        "receptions", "receiving_yards", "receiving_tds",
        "air_yards", "receiving_air_yards", "passing_air_yards",
        "passing_epa", "rushing_epa", "receiving_epa", "routes"
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df

@st.cache_data(ttl=3600, show_spinner="Loading schedules...")
def load_schedule_data():
    if not HAS_NFLREADPY:
        return pd.DataFrame()
    try:
        return nfl.load_schedules([2024, 2025, 2026]).to_pandas()
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=1800, show_spinner="Loading injury reports...")
def load_injury_data():
    """Loads official NFL injury report and IR designations."""
    if not HAS_NFLREADPY:
        return pd.DataFrame()
    try:
        injuries = nfl.load_injuries([2025, 2026]).to_pandas()
        if "full_name" in injuries.columns and "player_name" not in injuries.columns:
            injuries["player_name"] = injuries["full_name"]
        return injuries
    except Exception:
        return pd.DataFrame()

def get_team_injury_report(team_abbr: str, injury_df: pd.DataFrame, weekly_df: pd.DataFrame, current_week=None):
    """
    Identifies all players on a team who are on the injury report.
    Returns every position without filtering out low-volume players.
    """
    if injury_df is None or injury_df.empty:
        return []

    clean_team = str(team_abbr).upper().strip()
    team_injuries = injury_df[injury_df["team"] == clean_team].copy()
    
    if team_injuries.empty:
        return []

    if current_week and "week" in team_injuries.columns:
        week_injuries = team_injuries[team_injuries["week"] == current_week]
        if not week_injuries.empty:
            team_injuries = week_injuries

    report_col = "report_status" if "report_status" in team_injuries.columns else ("status" if "status" in team_injuries.columns else None)
    
    players_list = []
    seen = set()

    for _, row in team_injuries.iterrows():
        p_name = row.get("player_name", None)
        if not p_name or pd.isna(p_name) or p_name in seen:
            continue
        
        status_str = str(row.get(report_col, "")).upper().strip() if report_col else ""
        practice_str = str(row.get("practice_status", "")).upper().strip() if "practice_status" in row else ""

        is_out = status_str in ["OUT", "DOUBTFUL", "IR", "INJURED RESERVE", "PUP", "SUSPENDED"] or "DID NOT PARTICIPATE" in practice_str or "DNP" in practice_str
        is_questionable = status_str in ["QUESTIONABLE", "PROBABLE"] or ("LIMITED" in practice_str and not is_out)

        if is_out or is_questionable:
            seen.add(p_name)
            pos = str(row.get("position", "UNK")).upper()
            
            # Fetch historical volume for the UI impact display
            if not weekly_df.empty:
                p_stats = weekly_df[(weekly_df["recent_team"] == clean_team) & (weekly_df["player_name"] == p_name)]
                tot_att = p_stats["attempts"].sum() if not p_stats.empty else 0
                tot_carries = p_stats["carries"].sum() if not p_stats.empty else 0
                tot_targets = p_stats["targets"].sum() if not p_stats.empty else 0
            else:
                tot_att = tot_carries = tot_targets = 0
                
            players_list.append({
                "player_name": p_name,
                "position": pos,
                "status": "Out / IR" if is_out else "Questionable",
                "is_out": is_out,
                "attempts": tot_att,
                "carries": tot_carries,
                "targets": tot_targets
            })

    return players_list

@st.cache_data
def load_teams_data():
    if HAS_NFLREADPY:
        try:
            return nfl.load_teams().to_pandas()
        except Exception:
            pass
    return None

def get_upcoming_matchup(team_abbr, schedules_data):
    if schedules_data is None or schedules_data.empty:
        return None
    schedules_copy = schedules_data.copy()
    schedules_copy['gameday_dt'] = pd.to_datetime(schedules_copy['gameday'], errors='coerce')
    team_games = schedules_copy[(schedules_copy['home_team'] == team_abbr) | (schedules_copy['away_team'] == team_abbr)].copy()
    if team_games.empty:
        return None
    
    if 'home_score' in team_games.columns:
        future_games = team_games[team_games['home_score'].isna()].sort_values('gameday_dt')
    else:
        future_games = team_games[team_games['gameday_dt'] >= pd.Timestamp.now()].sort_values('gameday_dt')
        
    next_game = future_games.iloc[0] if not future_games.empty else team_games.sort_values('gameday_dt').iloc[-1]
    is_home = (next_game['home_team'] == team_abbr)
    home_team_id = team_abbr if is_home else next_game['home_team']
    
    raw_spread = next_game.get('spread_line', np.nan)
    app_spread = (-raw_spread if is_home else raw_spread) if not pd.isna(raw_spread) else (-3.5 if is_home else 3.5)
    total_line = next_game.get('total_line', 47.5) if not pd.isna(next_game.get('total_line', np.nan)) else 47.5
    roof = str(next_game.get('roof', 'Unknown')).title()

    return {
        'opponent': next_game['away_team'] if is_home else next_game['home_team'],
        'home_team': home_team_id,
        'is_home': is_home,
        'spread': float(round(app_spread * 2) / 2),
        'total': float(round(total_line * 2) / 2),
        'gameday': next_game['gameday'],
        'roof': "Dome" if roof.lower() in ['dome', 'closed'] else "Outdoor",
        'week': next_game.get('week', 1),
        'season': next_game.get('season', 2026)
    }

def get_team_colors(team_abbr: str, teams_metadata) -> dict:
    abbr = str(team_abbr).upper().strip() if pd.notna(team_abbr) else "NFL"
    if teams_metadata is not None and not teams_metadata.empty:
        match = teams_metadata[teams_metadata["team_abbr"] == abbr]
        if not match.empty:
            p_col, s_col = match.iloc[0].get("team_color", None), match.iloc[0].get("team_color2", None)
            if pd.notna(p_col) and str(p_col).startswith("#"):
                return {"primary": p_col, "secondary": s_col if (pd.notna(s_col) and str(s_col).startswith("#")) else "#1E1E1E"}
    return NFL_TEAM_COLORS.get(abbr, {"primary": "#1E293B", "secondary": "#475569"})

def get_team_logo_url(team_abbr: str, teams_metadata) -> str:
    if team_abbr and teams_metadata is not None and not teams_metadata.empty:
        match = teams_metadata[teams_metadata["team_abbr"] == team_abbr]
        if not match.empty and "team_logo_espn" in match.columns:
            logo_url = match.iloc[0]["team_logo_espn"]
            if pd.notna(logo_url) and str(logo_url).startswith("http"):
                return logo_url
    clean = str(team_abbr).lower().strip() if pd.notna(team_abbr) else "nfl"
    mapping = {"wsh": "was", "la": "lar", "bal": "bal", "kc": "kc", "ne": "ne", "gb": "gb", "sf": "sf", "no": "no", "tb": "tb", "lv": "lv", "ari": "ari"}
    return f"https://a.espncdn.com/i/teamlogos/nfl/500/{mapping.get(clean, clean)}.png"

def get_player_headshot_url(player_row) -> str:
    if "headshot_url" in player_row and pd.notna(player_row["headshot_url"]):
        url = str(player_row["headshot_url"]).strip()
        if url.startswith("http"):
            return url
    return "https://a.espncdn.com/i/headshots/nfl/players/full/0.png"