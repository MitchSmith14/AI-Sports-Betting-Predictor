# shared/api_services.py
import requests
import pandas as pd
import streamlit as st
from shared.config import ODDS_API_SPORT_KEYS, ODDS_API_MARKETS

@st.cache_data(ttl=1800)
def fetch_weather(lat: float, lon: float, gameday_str: str, roof_type: str):
    """Universal weather fetcher using raw coordinates."""
    if roof_type.lower() == "dome":
        return {"temp": 72.0, "wind_mph": 0.0, "precip_mm": 0.0, "condition": "Dome"}
        
    try:
        game_dt = pd.to_datetime(gameday_str)
        now = pd.Timestamp.now()
        days_ahead = (game_dt - now).days
        
        if 0 <= days_ahead <= 15:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,precipitation_sum,windspeed_10m_max&timezone=auto&forecast_days=16"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                daily = data.get('daily', {})
                dates = daily.get('time', [])
                if gameday_str in dates:
                    idx = dates.index(gameday_str)
                    temp_c = daily['temperature_2m_max'][idx]
                    wind_kmh = daily['windspeed_10m_max'][idx]
                    precip_mm = daily['precipitation_sum'][idx]
                    
                    temp_f = (temp_c * 9/5) + 32 if temp_c is not None else 65.0
                    wind_mph = wind_kmh * 0.621371 if wind_kmh is not None else 5.0
                    
                    cond = "Clear"
                    if precip_mm and precip_mm > 5.0: cond = "Heavy Rain/Snow"
                    elif precip_mm and precip_mm > 1.0: cond = "Light Rain/Snow"
                    elif wind_mph > 15: cond = "High Wind"
                    
                    return {"temp": round(temp_f, 1), "wind_mph": round(wind_mph, 1), "precip_mm": precip_mm, "condition": cond}
                    
        return {"temp": 65.0, "wind_mph": 5.0, "precip_mm": 0.0, "condition": "Neutral (No Forecast Yet)"}
    except Exception:
        return {"temp": 65.0, "wind_mph": 5.0, "precip_mm": 0.0, "condition": "API Error"}

def fetch_live_game_odds(api_key: str, sport: str, team_name: str):
    """Fetches spread and totals dynamically based on the selected sport."""
    sport_key = ODDS_API_SPORT_KEYS.get(sport, "americanfootball_nfl")
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds?apiKey={api_key}&regions=us&markets=spreads,totals&oddsFormat=american"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            for game in resp.json():
                if game['home_team'] == team_name or game['away_team'] == team_name:
                    best_spread, best_total = None, None
                    for book in game.get('bookmakers', []):
                        for market in book.get('markets', []):
                            if market['key'] == 'spreads' and best_spread is None:
                                for outcome in market['outcomes']:
                                    if outcome['name'] == team_name:
                                        best_spread = outcome.get('point')
                            if market['key'] == 'totals' and best_total is None:
                                best_total = market['outcomes'][0].get('point')
                    return {"event_id": game["id"], "spread": best_spread, "total": best_total}
    except Exception as e:
        st.sidebar.error(f"Odds API Error: {e}")
    return None

def fetch_player_props(api_key: str, sport: str, event_id: str, player_name: str):
    """Fetches specific prop markets depending on the sport."""
    sport_key = ODDS_API_SPORT_KEYS.get(sport, "americanfootball_nfl")
    markets = ODDS_API_MARKETS.get(sport, "")
    
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/events/{event_id}/odds?apiKey={api_key}&regions=us&markets={markets}&oddsFormat=american"
    props = {}
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            for book in resp.json().get('bookmakers', []):
                for market in book.get('markets', []):
                    m_key = market['key']
                    for outcome in market['outcomes']:
                        desc = outcome.get('description', '').lower()
                        if player_name.lower() in desc or desc in player_name.lower():
                            if m_key not in props:
                                props[m_key] = {"point": outcome.get('point'), "price": outcome.get('price')}
    except Exception:
        pass
    return props