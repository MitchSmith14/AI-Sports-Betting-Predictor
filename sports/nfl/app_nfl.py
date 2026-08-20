# sports/nfl/app_nfl.py

import streamlit as st
import pandas as pd
import numpy as np
from sports.nfl.data_ingestion import (
    load_nfl_data, load_schedule_data, load_teams_data, load_injury_data, load_roster_data,
    get_upcoming_matchup, get_team_injury_report, get_team_colors, get_team_logo_url, get_player_headshot_url
)
from sports.nfl.config import NFL_STADIUM_COORDS, TEAM_ABBR_TO_NAME
from sports.nfl.engine import (
    calculate_defense_summary, calculate_offense_summary,
    calculate_matchup_baselines, run_simulation
)
from sports.nfl.backtest_engine import run_historical_backtest
from sports.nfl.calibration import (
    calculate_brier_score, calculate_log_loss, 
    compute_reliability_curve, simulate_flat_betting_roi
)
from shared.api_services import fetch_weather, fetch_live_game_odds, fetch_player_props
from shared.ui_components import render_team_card, render_prop_row

def render_last_10_games(player_name, weekly_data, schedules_data):
    df_player = weekly_data[weekly_data["player_name"] == player_name].copy()
    if df_player.empty: return
    
    if schedules_data is not None and not schedules_data.empty:
        sched_subset = schedules_data[["season", "week", "gameday"]].drop_duplicates()
        df_player = df_player.merge(sched_subset, on=["season", "week"], how="left")
        date_col = ["gameday"]
    else:
        date_col = ["season", "week"]

    df_player = df_player.drop_duplicates(subset=["season", "week"]).sort_values(by=["season", "week"], ascending=False).head(10)
    player_pos = df_player["position"].iloc[0] if "position" in df_player.columns and not df_player["position"].isna().all() else "RB"
    base_cols = date_col + ["recent_team", "opponent_team"]
    
    if player_pos == "QB":
        stat_cols = ["completions", "attempts", "passing_yards", "passing_tds", "interceptions", "sacks", "carries", "rushing_yards", "rushing_tds", "fantasy_points_ppr"]
    elif player_pos == "RB":
        stat_cols = ["carries", "rushing_yards", "rushing_tds", "targets", "receptions", "receiving_yards", "receiving_tds", "fantasy_points_ppr"]
    else:
        stat_cols = ["targets", "receptions", "receiving_yards", "receiving_tds", "tgt_sh", "fantasy_points_ppr"]
    
    display_cols = [col for col in base_cols + stat_cols if col in df_player.columns]
    formatted_df = df_player[display_cols].rename(columns={
        "gameday": "Date", "season": "Season", "week": "Week", "recent_team": "Team", "opponent_team": "Opp", 
        "carries": "Carries", "rushing_yards": "Rush Yds", "rushing_tds": "Rush TD", 
        "completions": "Comp", "attempts": "Att", "passing_yards": "Pass Yds", "passing_tds": "Pass TD", "interceptions": "INT", "sacks": "Sacks",
        "targets": "Targets", "receptions": "Rec", "receiving_yards": "Rec Yds", "receiving_tds": "Rec TD", "tgt_sh": "Tgt Share", "fantasy_points_ppr": "PPR Pts"
    })
    st.dataframe(formatted_df, use_container_width=True, hide_index=True)


def render_backtester(weekly_df, schedules_df):
    st.header("📈 Historical Backtesting & Calibration")
    st.markdown("Run walk-forward Monte Carlo simulations on historical slates to compute true Brier Scores, Log-Loss, and simulated betting ROI.")
    
    with st.expander("⚙️ Backtest Configuration", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            target_season = st.selectbox("Season", [2024, 2025], index=1)
        with c2:
            weeks = st.slider("Week Range", 1, 18, (1, 4))
        with c3:
            num_sims = st.selectbox("Simulations per Matchup", [1000, 2500, 5000, 10000], index=1)
            
        if st.button("🚀 Run Walk-Forward Backtest", type="primary"):
            df_results = run_historical_backtest(weekly_df, schedules_df, target_season, weeks[0], weeks[1], num_sims)
            st.session_state['bt_results'] = df_results
            
    if 'bt_results' in st.session_state and not st.session_state['bt_results'].empty:
        df_results = st.session_state['bt_results']
        
        st.divider()
        st.subheader("📊 Calibration Diagnostics")
        
        prop_col1, prop_col2 = st.columns([2, 1])
        with prop_col1:
            prop_filter = st.selectbox("Select Prop Market to Analyze", [
                "Passing Yards > 200", "Passing Yards > 250",
                "Rushing Yards > 40", "Receiving Yards > 40"
            ])
        with prop_col2:
            min_edge = st.slider("Minimum Value Edge (for ROI)", 0.01, 0.15, 0.05, 0.01, help="Only bet when the model's win probability exceeds the implied market odds by this margin.")
        
        # Map selection to actual dataframe columns
        if prop_filter == "Passing Yards > 200":
            p_col, a_col, s_type = "prob_over_200", "actual_over_200", "pass_yards"
        elif prop_filter == "Passing Yards > 250":
            p_col, a_col, s_type = "prob_over_250", "actual_over_250", "pass_yards"
        elif prop_filter == "Rushing Yards > 40":
            p_col, a_col, s_type = "prob_over_40", "actual_over_40", "rush_yards"
        else:
            p_col, a_col, s_type = "prob_over_40", "actual_over_40", "rec_yards"
            
        filtered_df = df_results[df_results["stat_type"] == s_type].dropna(subset=[p_col, a_col])
        
        if filtered_df.empty:
            st.warning("No valid data for this prop market in the selected range.")
            return
            
        brier = calculate_brier_score(filtered_df, p_col, a_col)
        logloss = calculate_log_loss(filtered_df, p_col, a_col)
        roi_data = simulate_flat_betting_roi(filtered_df, p_col, a_col, min_edge=min_edge)
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Brier Score", f"{brier:.4f}", help="Lower is better. 0.0 is perfect, 0.25 is random.")
        m2.metric("Log-Loss", f"{logloss:.4f}", help="Lower is better. Penalizes overconfidence.")
        m3.metric("Simulated ROI", f"{roi_data['roi_pct']}%", f"{roi_data['net_units']} Units")
        m4.metric("Total Bets Triggered", roi_data['total_bets'])
        
        st.divider()
        col_chart, col_data = st.columns([3, 2])
        
        with col_chart:
            st.markdown("**Reliability Curve (Calibration)**")
            rel_df = compute_reliability_curve(filtered_df, p_col, a_col, n_bins=10)
            if not rel_df.empty:
                # Plot Actual Hit Rate vs Perfect Calibration (Ideal)
                plot_df = pd.DataFrame({
                    "Predicted Probability": rel_df["mean_predicted"],
                    "Actual Hit Rate": rel_df["actual_win_rate"],
                    "Ideal (Perfect Calibration)": rel_df["mean_predicted"]
                }).set_index("Predicted Probability")
                
                st.line_chart(plot_df)
                st.caption("A perfectly calibrated model will follow a straight 45-degree line.")
        
        with col_data:
            st.markdown("**Bin Summary**")
            st.dataframe(rel_df[["bin_range", "mean_predicted", "actual_win_rate", "sample_size"]].style.format({
                "mean_predicted": "{:.1%}",
                "actual_win_rate": "{:.1%}"
            }), hide_index=True)
            
        st.subheader("Raw Simulation Logs")
        st.dataframe(filtered_df[["season", "week", "player", "team", "sim_mean", "actual", p_col, a_col]])


def render_matchup_simulator(weekly_df, schedules_df, teams_metadata, injuries_df, rosters_df):
    # Failsafe Initialization
    if 'inactive_selections' not in st.session_state:
        st.session_state['inactive_selections'] = []

    st.sidebar.header("🎯 Matchup Selection")
    selected_pos = st.sidebar.radio("Position Filter", ["ALL", "QB", "RB", "WR", "TE"], horizontal=True)

    active_players = weekly_df[weekly_df["position"] == selected_pos] if selected_pos != "ALL" else weekly_df[(weekly_df["targets"] > 0) | (weekly_df["carries"] > 0) | (weekly_df["attempts"] > 0)]
    player_list = sorted(active_players["player_name"].dropna().unique())
    if not player_list:
        st.warning("No active players found for this filter.")
        return

    selected_player = st.sidebar.selectbox("Select Player:", player_list, index=player_list.index("Christian McCaffrey") if "Christian McCaffrey" in player_list else 0)

    player_row = weekly_df[weekly_df["player_name"] == selected_player].sort_values(["season", "week"]).iloc[-1]
    player_team_abbr, player_pos_detected = player_row.get("recent_team", "SF"), player_row.get("position", "RB")
    player_team_logo = get_team_logo_url(player_team_abbr, teams_metadata)
    player_headshot = get_player_headshot_url(player_row)

    matchup_info = get_upcoming_matchup(player_team_abbr, schedules_df)
    default_opp = matchup_info['opponent'] if matchup_info else "GB"
    default_spread = matchup_info['spread'] if matchup_info else (-3.5 if player_pos_detected in ["RB", "QB"] else 3.5)
    default_total = matchup_info['total'] if matchup_info else 47.5
    current_matchup_week = matchup_info.get("week") if matchup_info else None

    team_list = sorted(weekly_df["recent_team"].dropna().unique())
    selected_opponent = st.sidebar.selectbox("Opposing Defense:", team_list, index=team_list.index(default_opp) if default_opp in team_list else 0)
    def_team_logo = get_team_logo_url(selected_opponent, teams_metadata)

    raw_off_injuries = get_team_injury_report(player_team_abbr, injuries_df, weekly_df, current_matchup_week)
    def_injuries = get_team_injury_report(selected_opponent, injuries_df, weekly_df, current_matchup_week)

    auto_confirmed_inactives = [p["player_name"] for p in raw_off_injuries if p["is_out"] and p["player_name"] != selected_player]

    if 'current_player' not in st.session_state or st.session_state['current_player'] != selected_player:
        st.session_state['current_player'] = selected_player
        st.session_state['spread_input'] = float(default_spread)
        st.session_state['total_input'] = float(default_total)
        st.session_state['pass_yds_input'] = 250.5; st.session_state['pass_yds_odds_input'] = -110
        st.session_state['pass_tds_input'] = 1.5; st.session_state['pass_td_odds_input'] = -110
        st.session_state['pass_comp_input'] = 21.5; st.session_state['pass_comp_odds_input'] = -110
        st.session_state['pass_int_input'] = 0.5; st.session_state['pass_int_odds_input'] = 110
        st.session_state['rush_yds_input'] = 55.5 if player_pos_detected == "RB" else 15.5; st.session_state['rush_odds_input'] = -110
        st.session_state['rush_tds_input'] = 0.5; st.session_state['rush_td_odds_input'] = 120 if player_pos_detected == "RB" else 350
        st.session_state['rec_yds_input'] = float(22.5 if player_pos_detected == "RB" else 68.5); st.session_state['rec_odds_input'] = -110
        st.session_state['rec_tds_input'] = 0.5; st.session_state['rec_td_odds_input'] = 250 if player_pos_detected == "RB" else 130
        st.session_state['inactive_selections'] = auto_confirmed_inactives

    with st.sidebar.expander("⚙️ Game Environment Setup", expanded=False):
        st.session_state['spread_input'] = st.number_input("Spread (-Fav / +Dog)", value=st.session_state['spread_input'], step=0.5)
        st.session_state['total_input'] = st.number_input("Over/Under Total", value=st.session_state['total_input'], step=0.5)
        coverage_scheme = st.selectbox("Opponent Coverage Scheme", ["Neutral", "Heavy Man", "Heavy Zone", "2-High Shell"])
        simulations = st.slider("Monte Carlo Sims", 1000, 50000, 10000, step=1000)

    with st.sidebar.expander("🚑 Active Inactives & Vacated Volume", expanded=True):
        st.caption("Players listed below are treated as OUT. Their volume & QB impact are calculated dynamically:")
        
        if not rosters_df.empty:
            roster_col = "team" if "team" in rosters_df.columns else ("club" if "club" in rosters_df.columns else None)
            roster = sorted(rosters_df[rosters_df[roster_col] == player_team_abbr]["player_name"].dropna().unique()) if roster_col else sorted(weekly_df[weekly_df["recent_team"] == player_team_abbr]["player_name"].dropna().unique())
        else:
            roster = sorted(weekly_df[weekly_df["recent_team"] == player_team_abbr]["player_name"].dropna().unique())
            
        if selected_player in roster: roster.remove(selected_player)
        
        active_inactives = [p for p in st.session_state.get('inactive_selections', auto_confirmed_inactives) if p in roster]
        
        selected_inactives = st.multiselect(
            "Out / Inactive Teammates:", 
            roster, 
            default=active_inactives,
            key="inactive_selections_widget"
        )
        st.session_state['inactive_selections'] = selected_inactives

    with st.sidebar.expander("🌤️ Weather Override", expanded=False):
        override_weather = st.checkbox("Manually override weather forecast")
        if override_weather:
            wind_input = st.slider("Wind Speed (mph)", 0.0, 40.0, 5.0, step=1.0)
            precip_input = st.slider("Precipitation (mm)", 0.0, 20.0, 0.0, step=1.0)
            current_weather = {"wind_mph": wind_input, "precip_mm": precip_input, "condition": "Manual Override"}
        else:
            if matchup_info and matchup_info['home_team'] in NFL_STADIUM_COORDS:
                coords = NFL_STADIUM_COORDS[matchup_info['home_team']]
                current_weather = fetch_weather(coords['lat'], coords['lon'], matchup_info['gameday'], matchup_info['roof'])
            else:
                current_weather = {"wind_mph": 5.0, "precip_mm": 0.0, "condition": "Default"}

    with st.sidebar.expander("📡 Live Odds API Integration", expanded=False):
        st.caption("Pull consensus lines from The Odds API")
        api_key = st.text_input("The Odds API Key", type="password")
        if st.button("Fetch Live Lines"):
            if not api_key:
                st.error("Please enter a valid API Key.")
            else:
                with st.spinner("Fetching live Vegas odds..."):
                    full_team_name = TEAM_ABBR_TO_NAME.get(player_team_abbr, player_team_abbr)
                    game_odds = fetch_live_game_odds(api_key, "NFL", full_team_name)
                    if game_odds:
                        if game_odds['spread'] is not None: st.session_state['spread_input'] = float(game_odds['spread'])
                        if game_odds['total'] is not None: st.session_state['total_input'] = float(game_odds['total'])
                        props = fetch_player_props(api_key, "NFL", game_odds['event_id'], selected_player)
                        if props:
                            if 'player_pass_yds' in props and props['player_pass_yds'].get('point'): st.session_state['pass_yds_input'] = float(props['player_pass_yds']['point'])
                            if 'player_pass_tds' in props and props['player_pass_tds'].get('point'): st.session_state['pass_tds_input'] = float(props['player_pass_tds']['point'])
                            if 'player_pass_completions' in props and props['player_pass_completions'].get('point'): st.session_state['pass_comp_input'] = float(props['player_pass_completions']['point'])
                            if 'player_pass_interceptions' in props and props['player_pass_interceptions'].get('point'): st.session_state['pass_int_input'] = float(props['player_pass_interceptions']['point'])
                            if 'player_rush_yds' in props and props['player_rush_yds'].get('point'): st.session_state['rush_yds_input'] = float(props['player_rush_yds']['point'])
                            if 'player_reception_yds' in props and props['player_reception_yds'].get('point'): st.session_state['rec_yds_input'] = float(props['player_reception_yds']['point'])
                        st.success("✅ Lines updated!")
                    else:
                        st.warning("No live odds found.")

    # Scoreboard
    p_colors = get_team_colors(player_team_abbr, teams_metadata)
    d_colors = get_team_colors(selected_opponent, teams_metadata)

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
            logo_url=def_team_logo, subtitle=f"Spread: {st.session_state['spread_input']} | Total: {st.session_state['total_input']}"
        )

    # Simulation calculations
    matchup = calculate_matchup_baselines(selected_player, selected_opponent, st.session_state['spread_input'], st.session_state['total_input'], current_weather, weekly_df, selected_inactives, coverage_scheme)
    def_stats = calculate_defense_summary(weekly_df, selected_opponent, player_pos_detected)
    off_stats = calculate_offense_summary(weekly_df, matchup["player_team"])
    df_sims = run_simulation(simulations, matchup)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Matchup", f"{player_team_abbr} {'vs' if matchup_info and matchup_info['is_home'] else '@'} {selected_opponent}")
    qb_badge = f"{matchup['projected_qb']} ⚠️ (Backup)" if matchup["is_backup_qb"] else f"{matchup['projected_qb']}"
    c2.metric("Projected QB", qb_badge)
    c3.metric("Game Environment", f"Spread: {st.session_state['spread_input']} | Total: {st.session_state['total_input']}")
    c4.metric("Weather", "🏟️ Dome (Indoors)" if current_weather['condition'] == "Dome" else f"💨 {current_weather['wind_mph']} mph | 🌧️ {current_weather['precip_mm']} mm", help=current_weather['condition'])
    st.divider()

    # Merge manual inactives into offensive injury report
    displayed_off_injuries = []
    seen_off_players = set()

    for p in raw_off_injuries:
        p_copy = p.copy()
        if p_copy["player_name"] in selected_inactives:
            p_copy["is_out"] = True
            p_copy["status"] = "OUT / Inactive (Vacated in Sim)"
        displayed_off_injuries.append(p_copy)
        seen_off_players.add(p_copy["player_name"])

    for name in selected_inactives:
        if name not in seen_off_players:
            p_stats = weekly_df[(weekly_df["recent_team"] == player_team_abbr) & (weekly_df["player_name"] == name)]
            pos = p_stats["position"].iloc[-1] if not p_stats.empty and "position" in p_stats.columns else "SKILL"
            displayed_off_injuries.append({
                "player_name": name,
                "position": pos,
                "status": "OUT / Inactive (Manual Override)",
                "is_out": True
            })

    # Injury Banner
    with st.expander("🚑 Matchup Injury & Status Report", expanded=(len(displayed_off_injuries) > 0 or len(def_injuries) > 0)):
        inj_col1, inj_col2 = st.columns(2)
        with inj_col1:
            st.markdown(f"**{player_team_abbr} Full Injury Report:**")
            if displayed_off_injuries:
                for p in displayed_off_injuries:
                    icon = "❌" if p["is_out"] else "⚠️"
                    st.markdown(f"* {icon} **{p['player_name']}** ({p['position']}) — {p['status']}")
            else:
                st.caption("✅ No players on the injury report.")

        with inj_col2:
            st.markdown(f"**{selected_opponent} Full Injury Report:**")
            if def_injuries:
                for p in def_injuries:
                    icon = "❌" if p["is_out"] else "⚠️"
                    status_note = "**OUT / IR**" if p["is_out"] else "**QUESTIONABLE**"
                    st.markdown(f"* {icon} **{p['player_name']}** ({p['position']}) — {status_note}")
            else:
                st.caption("✅ No players on the injury report.")

    # Trench profiles
    with st.expander("📊 View Matchup Trench Profiles", expanded=False):
        if off_stats.get("has_data", False):
            st.markdown(f"<div style='display: flex; align-items: center; margin-bottom: 10px;'><img src='{player_team_logo}' width='40' style='margin-right: 12px;'><h4 style='margin: 0; padding: 0;'>{matchup['player_team']} Offensive Profile ({off_stats['season']} Season)</h4></div>", unsafe_allow_html=True)
            ocol1, ocol2, ocol3, ocol4, ocol5, ocol6 = st.columns(6)
            if player_pos_detected == "RB":
                ocol1.metric("Rush Yds/G", f"{off_stats['rush_yds_pg']:.1f}", delta=f"Rank #{off_stats['rush_yds_rank']}/{off_stats['total_teams']}", delta_color="off")
                ocol2.metric("Rush Att/G", f"{off_stats['rush_att_pg']:.1f}", delta=f"Rank #{off_stats['rush_att_rank']}/{off_stats['total_teams']}", delta_color="off")
                ocol3.metric("YPC", f"{off_stats['ypc']:.2f}", delta=f"Rank #{off_stats['ypc_rank']}/{off_stats['total_teams']}", delta_color="off")
                ocol4.metric("Pass Yds/G", f"{off_stats['pass_yds_pg']:.1f}", delta=f"Rank #{off_stats['pass_yds_rank']}/{off_stats['total_teams']}", delta_color="off")
                ocol5.metric("Sacks Allowed/G", f"{off_stats['sacks_pg']:.1f}", delta=f"Rank #{off_stats['sacks_rank']}/{off_stats['total_teams']}", delta_color="off")
                ocol6.metric("Rush EPA/Play", f"{off_stats['rush_epa_per_att']:.3f}", delta=f"Rank #{off_stats['rush_epa_rank']}/{off_stats['total_teams']}", delta_color="off")
            else:
                ocol1.metric("Pass Yds/G", f"{off_stats['pass_yds_pg']:.1f}", delta=f"Rank #{off_stats['pass_yds_rank']}/{off_stats['total_teams']}", delta_color="off")
                ocol2.metric("Pass Att/G", f"{off_stats['pass_att_pg']:.1f}", delta=f"Rank #{off_stats['pass_att_rank']}/{off_stats['total_teams']}", delta_color="off")
                ocol3.metric("Comp %", f"{off_stats['comp_pct']:.1f}%", delta=f"Rank #{off_stats['comp_pct_rank']}/{off_stats['total_teams']}", delta_color="off")
                ocol4.metric("Yards / Att", f"{off_stats['ypa']:.1f}", delta=f"Rank #{off_stats['ypa_rank']}/{off_stats['total_teams']}", delta_color="off")
                ocol5.metric("Sacks Allowed/G", f"{off_stats['sacks_pg']:.1f}", delta=f"Rank #{off_stats['sacks_rank']}/{off_stats['total_teams']}", delta_color="off")
                ocol6.metric("Pass EPA/Play", f"{off_stats['pass_epa_per_att']:.3f}", delta=f"Rank #{off_stats['pass_epa_rank']}/{off_stats['total_teams']}", delta_color="off")
        st.markdown("---")
        if def_stats.get("has_data", False):
            st.markdown(f"<div style='display: flex; align-items: center; margin-bottom: 10px;'><img src='{def_team_logo}' width='40' style='margin-right: 12px;'><h4 style='margin: 0; padding: 0;'>{selected_opponent} Defensive Profile ({def_stats['season']} Season)</h4></div>", unsafe_allow_html=True)
            dcol1, dcol2, dcol3, dcol4, dcol5, dcol6 = st.columns(6)
            if player_pos_detected == "RB":
                dcol1.metric("Rush Yds Allowed/G", f"{def_stats['rush_yds_pg']:.1f}", delta=f"Rank #{def_stats['rush_yds_rank']}/{def_stats['total_teams']}", delta_color="off")
                dcol2.metric("Rush Att Allowed/G", f"{def_stats['rush_att_pg']:.1f}", delta=f"Rank #{def_stats['rush_att_rank']}/{def_stats['total_teams']}", delta_color="off")
                dcol3.metric("YPC Allowed", f"{def_stats['ypc']:.2f}", delta=f"Rank #{def_stats['ypc_rank']}/{def_stats['total_teams']}", delta_color="off")
                dcol4.metric("Pass Yds Allowed/G", f"{def_stats['pass_yds_pg']:.1f}", delta=f"Rank #{def_stats['pass_yds_rank']}/{def_stats['total_teams']}", delta_color="off")
                dcol5.metric("Sacks Forced/G", f"{def_stats['sacks_pg']:.1f}", delta=f"Rank #{def_stats['sacks_rank']}/{def_stats['total_teams']}", delta_color="off")
                dcol6.metric("Rush EPA Allowed", f"{def_stats['rush_epa_per_att']:.3f}", delta=f"Rank #{def_stats['rush_epa_rank']}/{def_stats['total_teams']}", delta_color="off")
            else:
                dcol1.metric("Pass Yds Allowed/G", f"{def_stats['pass_yds_pg']:.1f}", delta=f"Rank #{def_stats['pass_yds_rank']}/{def_stats['total_teams']}", delta_color="off")
                dcol2.metric("Pass Att Allowed/G", f"{def_stats['pass_att_pg']:.1f}", delta=f"Rank #{def_stats['pass_att_rank']}/{def_stats['total_teams']}", delta_color="off")
                dcol3.metric("Comp % Allowed", f"{def_stats['comp_pct']:.1f}%", delta=f"Rank #{def_stats['comp_pct_rank']}/{def_stats['total_teams']}", delta_color="off")
                dcol4.metric("Yards / Att Allowed", f"{def_stats['ypa']:.1f}", delta=f"Rank #{def_stats['ypa_rank']}/{def_stats['total_teams']}", delta_color="off")
                dcol5.metric("Sacks Forced/G", f"{def_stats['sacks_pg']:.1f}", delta=f"Rank #{def_stats['sacks_rank']}/{def_stats['total_teams']}", delta_color="off")
                dcol6.metric("Pass EPA Allowed", f"{def_stats['pass_epa_per_att']:.3f}", delta=f"Rank #{def_stats['pass_epa_rank']}/{def_stats['total_teams']}", delta_color="off")
            if "dvp_pos" in def_stats:
                st.markdown(f"**Vs. {def_stats['dvp_pos']}s specifically (Defense vs. Position):**")
                dvp_c1, dvp_c2 = st.columns([1, 1])
                if def_stats['dvp_pos'] == "RB":
                    dvp_c1.metric(f"Rush Yds Allowed to {def_stats['dvp_pos']}", f"{def_stats['dvp_rush_yds']:.1f}", delta=f"Rank #{def_stats['dvp_rush_rank']}/{def_stats['total_teams']}", delta_color="off")
                dvp_c2.metric(f"Rec Yds Allowed to {def_stats['dvp_pos']}", f"{def_stats['dvp_rec_yds']:.1f}", delta=f"Rank #{def_stats['dvp_rec_rank']}/{def_stats['total_teams']}", delta_color="off")

    # Prop Tabs
    if player_pos_detected == "QB":
        tab1, tab2, tab3 = st.tabs(["🎯 Passing", "📉 Completions & INTs", "👟 Rushing"])
        with tab1:
            st.markdown("##### Configuration")
            c1, c2, c3, c4 = st.columns(4)
            render_prop_row(
                df_sims, "pass_yards", "Passing Yards",
                c1.number_input("Passing Yds Line", value=st.session_state['pass_yds_input'], step=0.5, key="py"),
                c2.number_input("Passing Yds Odds", value=st.session_state['pass_yds_odds_input'], step=5, key="pyo"),
                "pass_tds", "Passing TDs",
                c3.number_input("Passing TDs Line", value=st.session_state['pass_tds_input'], step=0.5, key="pt"),
                c4.number_input("Passing TD Odds", value=st.session_state['pass_td_odds_input'], step=5, key="pto"),
                context_metrics={"Team Pass Att": df_sims["team_pass"].mean(), "Player Pass Att": df_sims["pass_attempts"].mean(), "Player EPA/Att": matchup["player_epa"], "Opp Scheme": coverage_scheme}
            )
        with tab2:
            st.markdown("##### Configuration")
            c1, c2, c3, c4 = st.columns(4)
            render_prop_row(
                df_sims, "completions", "Completions",
                c1.number_input("Completions Line", value=st.session_state['pass_comp_input'], step=0.5, key="pc"),
                c2.number_input("Completions Odds", value=st.session_state['pass_comp_odds_input'], step=5, key="pco"),
                "interceptions", "Interceptions",
                c3.number_input("Interceptions Line", value=st.session_state['pass_int_input'], step=0.5, key="pi"),
                c4.number_input("Interceptions Odds", value=st.session_state['pass_int_odds_input'], step=5, key="pio"),
                context_metrics={"Team Pass Att": df_sims["team_pass"].mean(), "Player Pass Att": df_sims["pass_attempts"].mean(), "Player EPA/Att": matchup["player_epa"], "Opp Scheme": coverage_scheme}
            )
        with tab3:
            st.markdown("##### Configuration")
            c1, c2, c3, c4 = st.columns(4)
            render_prop_row(
                df_sims, "rush_yards", "Rushing Yards",
                c1.number_input("Rushing Yds Line", value=st.session_state['rush_yds_input'], step=0.5, key="ryq"),
                c2.number_input("Rushing Yds Odds", value=st.session_state['rush_odds_input'], step=5, key="ryoq"),
                "rush_tds", "Rushing TDs",
                c3.number_input("Rushing TDs Line", value=st.session_state['rush_tds_input'], step=0.5, key="rtq"),
                c4.number_input("Rushing TD Odds", value=st.session_state['rush_td_odds_input'], step=5, key="rtoq"),
                context_metrics={"Team Rush Att": df_sims["team_rush"].mean(), "Player Carries": df_sims["carries"].mean(), "Player EPA/Rush": matchup["player_epa"], "Vacated Rush Share": f"{matchup['vacated_rush_share']:.1%}"}
            )
    elif player_pos_detected == "RB":
        tab1, tab2 = st.tabs(["👟 Rushing", "🤲 Receiving"])
        with tab1:
            st.markdown("##### Configuration")
            c1, c2, c3, c4 = st.columns(4)
            render_prop_row(
                df_sims, "rush_yards", "Rushing Yards",
                c1.number_input("Rushing Yds Line", value=st.session_state['rush_yds_input'], step=0.5, key="ryr"),
                c2.number_input("Rushing Yds Odds", value=st.session_state['rush_odds_input'], step=5, key="ryor"),
                "rush_tds", "Rushing TDs",
                c3.number_input("Rushing TDs Line", value=st.session_state['rush_tds_input'], step=0.5, key="rtr"),
                c4.number_input("Rushing TD Odds", value=st.session_state['rush_td_odds_input'], step=5, key="rtor"),
                context_metrics={"Starting QB": matchup["projected_qb"], "Team Rush Att": df_sims["team_rush"].mean(), "Player Carries": df_sims["carries"].mean(), "Player EPA/Rush": matchup["player_epa"], "Opp Scheme": coverage_scheme, "Vacated Rush Share": f"{matchup['vacated_rush_share']:.1%}"}
            )
        with tab2:
            st.markdown("##### Configuration")
            c1, c2, c3, c4 = st.columns(4)
            render_prop_row(
                df_sims, "rec_yards", "Receiving Yards",
                c1.number_input("Receiving Yds Line", value=st.session_state['rec_yds_input'], step=0.5, key="recyr"),
                c2.number_input("Receiving Yds Odds", value=st.session_state['rec_odds_input'], step=5, key="recyor"),
                "rec_tds", "Receiving TDs",
                c3.number_input("Receiving TDs Line", value=st.session_state['rec_tds_input'], step=0.5, key="rectr"),
                c4.number_input("Receiving TD Odds", value=st.session_state['rec_td_odds_input'], step=5, key="rector"),
                context_metrics={"Starting QB": matchup["projected_qb"], "Team Pass Att": df_sims["team_pass"].mean(), "Player Targets": df_sims["targets"].mean(), "Avg Target Depth (aDOT)": matchup["player_adot"], "Player EPA/Target": matchup["player_epa"], "Opp Scheme": coverage_scheme, "Vacated Target Share": f"{matchup['vacated_target_share']:.1%}"}
            )
    else:
        tab1, = st.tabs(["🤲 Receiving"])
        with tab1:
            st.markdown("##### Configuration")
            c1, c2, c3, c4 = st.columns(4)
            render_prop_row(
                df_sims, "rec_yards", "Receiving Yards",
                c1.number_input("Receiving Yds Line", value=st.session_state['rec_yds_input'], step=0.5, key="recyw"),
                c2.number_input("Receiving Yds Odds", value=st.session_state['rec_odds_input'], step=5, key="recyow"),
                "rec_tds", "Receiving TDs",
                c3.number_input("Receiving TDs Line", value=st.session_state['rec_tds_input'], step=0.5, key="rectw"),
                c4.number_input("Receiving TD Odds", value=st.session_state['rec_td_odds_input'], step=5, key="rectow"),
                context_metrics={"Starting QB": matchup["projected_qb"], "Team Pass Att": df_sims["team_pass"].mean(), "Player Targets": df_sims["targets"].mean(), "Avg Target Depth (aDOT)": matchup["player_adot"], "Player EPA/Target": matchup["player_epa"], "Opp Scheme": coverage_scheme, "Vacated Target Share": f"{matchup['vacated_target_share']:.1%}"}
            )

    st.divider()
    st.subheader(f"📊 {selected_player} - Recent Performance")
    render_last_10_games(selected_player, weekly_df, schedules_df)

def render_nfl():
    weekly_df = load_nfl_data()
    schedules_df = load_schedule_data()
    teams_metadata = load_teams_data()
    injuries_df = load_injury_data()
    rosters_df = load_roster_data()

    if weekly_df.empty:
        st.warning("No NFL data available. Please verify nflreadpy is installed and configured.")
        return

    st.sidebar.title("🏈 NFL AI Engine")
    app_mode = st.sidebar.radio("Engine Mode", ["🔮 Matchup Simulator", "📈 Historical Backtesting"])

    if app_mode == "🔮 Matchup Simulator":
        render_matchup_simulator(weekly_df, schedules_df, teams_metadata, injuries_df, rosters_df)
    else:
        render_backtester(weekly_df, schedules_df)