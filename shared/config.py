# shared/config.py

# Maps the Streamlit sport dropdown to The Odds API sport keys
ODDS_API_SPORT_KEYS = {
    "NFL": "americanfootball_nfl",
    "NHL": "icehockey_nhl",
    "NBA": "basketball_nba",
    "MLB": "baseball_mlb"
}

# Define which betting markets to pull for each sport
ODDS_API_MARKETS = {
    "NFL": "player_rush_yds,player_reception_yds,player_anytime_td,player_pass_yds,player_pass_tds,player_pass_completions,player_pass_interceptions",
    "NHL": "player_points,player_assists,player_shots_on_goal,player_goals,player_total_saves",
    "NBA": "player_points,player_rebounds,player_assists,player_threes",
    "MLB": "player_strikeouts,player_hits,player_home_runs,player_total_bases"
}