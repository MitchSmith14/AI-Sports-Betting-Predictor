# sports/nhl/app_nhl.py

import streamlit as st
import pandas as pd
from sports.nhl.data_ingestion import load_nhl_data, get_nhl_team_colors, get_nhl_team_logo
from sports.nhl.engine import calculate_nhl_baselines, run_nhl_simulation
from sports.nhl.config import NHL_TEAM_NAMES
from shared.api_services import fetch_live_game_odds, fetch_player_props
from shared.ui_components import render_team_card, render_prop_row

def render_nhl():
    weekly_df = load_nhl_data()
    
    # ---------------------------------------------------------
    # DEMO MODE: If no live data is found, load dummy superstars
    # ---------------------------------------------------------
    if weekly_df.empty:
        st.info("ℹ️ No live NHL data feed detected. Running in Demo Mode.")
        dummy_data = {
            "player_name": ["Connor McDavid", "Auston Matthews", "Nathan MacKinnon"],
            "position": ["C", "C", "C"],
            "recent_team": ["EDM", "TOR", "COL"],
            "date": ["2026-10-15"] * 3,
            "time_on_ice_mins": [22.5, 21.0, 22.0],
            "shots_on_goal": [4, 5, 4],
            "goals": [1, 1, 1],
            "assists": [2, 0, 1],
            "points": [3, 1, 2],
            "team_shots": [35, 33, 34],
            "team_goals": [4, 3, 4]
        }
        weekly_df = pd.DataFrame(dummy_data)

    # Sidebar Navigation
    st.sidebar.header("🎯 Matchup Selection")
    
    player_list = sorted(weekly_df["player_name"].dropna().unique())
    selected_player = st.sidebar.selectbox("Select Player:", player_list)

    player_row = weekly_df[weekly_df["player_name"] == selected_player].iloc[-1]
    player_team_abbr = player_row.get("recent_team", "EDM")
    player_pos_detected = player_row.get("position", "F")
    
    p_colors = get_nhl_team_colors(player_team_abbr)
    player_team_logo = get_nhl_team_logo(player_team_abbr)
    
    # Fallback Headshot for NHL Demo
    player_headshot = "https://a.espncdn.com/i/headshots/nhl/players/full/3041697.png" if selected_player == "Connor McDavid" else None

    # Opponent Selection
    default_opp = "FLA" if player_team_abbr == "EDM" else "BOS"
    team_list = sorted(list(NHL_TEAM_NAMES.keys()))
    selected_opponent = st.sidebar.selectbox("Opposing Defense:", team_list, index=team_list.index(default_opp) if default_opp in team_list else 0)
    
    d_colors = get_nhl_team_colors(selected_opponent)
    def_team_logo = get_nhl_team_logo(selected_opponent)

    # Default Puck Line & Totals
    default_spread = -1.5
    default_total = 6.5

    # State init
    if 'nhl_current_player' not in st.session_state or st.session_state['nhl_current_player'] != selected_player:
        st.session_state['nhl_current_player'] = selected_player
        st.session_state['nhl_spread_input'] = float(default_spread)
        st.session_state['nhl_total_input'] = float(default_total)
        st.session_state['sog_input'] = 3.5; st.session_state['sog_odds_input'] = -130
        st.session_state['goal_input'] = 0.5; st.session_state['goal_odds_input'] = 120
        st.session_state['point_input'] = 1.5; st.session_state['point_odds_input'] = -110
        st.session_state['assist_input'] = 0.5; st.session_state['assist_odds_input'] = -120

    with st.sidebar.expander("⚙️ Game Environment Setup", expanded=False):
        st.session_state['nhl_spread_input'] = st.number_input("Spread (-Fav / +Dog)", value=st.session_state['nhl_spread_input'], step=0.5, key="nhl_spread")
        st.session_state['nhl_total_input'] = st.number_input("Over/Under Total Goals", value=st.session_state['nhl_total_input'], step=0.5, key="nhl_total")
        simulations = st.slider("Monte Carlo Sims", 1000, 50000, 10000, step=1000, key="nhl_sims")

    with st.sidebar.expander("📡 Live Odds API Integration", expanded=False):
        st.caption("Pull consensus lines from The Odds API")
        api_key = st.text_input("The Odds API Key", type="password", key="nhl_api_key")
        if st.button("Fetch Live Lines", key="nhl_fetch"):
            if not api_key:
                st.error("Please enter a valid API Key.")
            else:
                with st.spinner("Fetching live Vegas odds..."):
                    full_team_name = NHL_TEAM_NAMES.get(player_team_abbr, player_team_abbr)
                    game_odds = fetch_live_game_odds(api_key, "NHL", full_team_name)
                    if game_odds:
                        if game_odds['spread'] is not None: st.session_state['nhl_spread_input'] = float(game_odds['spread'])
                        if game_odds['total'] is not None: st.session_state['nhl_total_input'] = float(game_odds['total'])
                        
                        props = fetch_player_props(api_key, "NHL", game_odds['event_id'], selected_player)
                        if props:
                            if 'player_shots_on_goal' in props and props['player_shots_on_goal'].get('point'): st.session_state['sog_input'] = float(props['player_shots_on_goal']['point'])
                            if 'player_goals' in props and props['player_goals'].get('point'): st.session_state['goal_input'] = float(props['player_goals']['point'])
                            if 'player_points' in props and props['player_points'].get('point'): st.session_state['point_input'] = float(props['player_points']['point'])
                            if 'player_assists' in props and props['player_assists'].get('point'): st.session_state['assist_input'] = float(props['player_assists']['point'])
                        st.success("✅ NHL Lines updated!")
                    else:
                        st.warning("No live odds found for this game.")

    # Scoreboard
    col_p_card, col_d_card = st.columns(2)
    with col_p_card:
        render_team_card(
            title="PLAYER PROJECTION", name=selected_player, team_abbr=player_team_abbr,
            primary_color=p_colors["primary"], secondary_color=p_colors["secondary"],
            logo_url=player_team_logo, headshot_url=player_headshot, subtitle=f"Pos: {player_pos_detected}"
        )
    with col_d_card:
        render_team_card(
            title="OPPOSING DEFENSE", name=f"{selected_opponent} Defense", team_abbr=selected_opponent,
            primary_color=d_colors["primary"], secondary_color=d_colors["secondary"],
            logo_url=def_team_logo, subtitle=f"Puck Line: {st.session_state['nhl_spread_input']} | Total: {st.session_state['nhl_total_input']}"
        )

    st.divider()

    # Simulation engine
    matchup = calculate_nhl_baselines(selected_player, selected_opponent, st.session_state['nhl_spread_input'], st.session_state['nhl_total_input'], weekly_df)
    df_sims = run_nhl_simulation(simulations, matchup)

    # Prop Tabs (Grouped into pairs for the render_prop_row function)
    tab1, tab2 = st.tabs(["🎯 Shots & Goals", "📊 Points & Assists"])
    
    with tab1:
        st.markdown("##### Configuration")
        c1, c2, c3, c4 = st.columns(4)
        render_prop_row(
            df_sims, 
            "shots", "Shots on Goal", 
            c1.number_input("SOG Line", value=st.session_state['sog_input'], step=0.5, key="sog_l"),
            c2.number_input("SOG Odds", value=st.session_state['sog_odds_input'], step=5, key="sog_o"),
            "goals", "Goals",
            c3.number_input("Goal Line", value=st.session_state['goal_input'], step=0.5, key="goal_l"),
            c4.number_input("Goal Odds", value=st.session_state['goal_odds_input'], step=5, key="goal_o"),
            context_metrics={"Proj Team Shots": df_sims["team_shots"].mean(), "Player Shot Share": matchup["shot_share"]}
        )

    with tab2:
        st.markdown("##### Configuration")
        c1, c2, c3, c4 = st.columns(4)
        render_prop_row(
            df_sims, 
            "points", "Points", 
            c1.number_input("Points Line", value=st.session_state['point_input'], step=0.5, key="pt_l"),
            c2.number_input("Points Odds", value=st.session_state['point_odds_input'], step=5, key="pt_o"),
            "assists", "Assists",
            c3.number_input("Assist Line", value=st.session_state['assist_input'], step=0.5, key="ast_l"),
            c4.number_input("Assist Odds", value=st.session_state['assist_odds_input'], step=5, key="ast_o"),
            context_metrics={"Proj Team Goals": df_sims["team_goals"].mean(), "Player Assist Share": matchup["assist_share"]}
        )