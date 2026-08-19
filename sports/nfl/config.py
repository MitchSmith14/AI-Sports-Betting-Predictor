# sports/nfl/config.py

NFL_TEAM_COLORS = {
    "ARI": {"primary": "#97233F", "secondary": "#000000"}, "ATL": {"primary": "#A71930", "secondary": "#000000"},
    "BAL": {"primary": "#241773", "secondary": "#000000"}, "BUF": {"primary": "#00338D", "secondary": "#C60C30"},
    "CAR": {"primary": "#0085CA", "secondary": "#101820"}, "CHI": {"primary": "#0B162A", "secondary": "#C83803"},
    "CIN": {"primary": "#FB4F14", "secondary": "#000000"}, "CLE": {"primary": "#311D00", "secondary": "#FF3C00"},
    "DAL": {"primary": "#003594", "secondary": "#869397"}, "DEN": {"primary": "#FB4F14", "secondary": "#002244"},
    "DET": {"primary": "#0076B6", "secondary": "#B0B7BC"}, "GB": {"primary": "#203731", "secondary": "#FFB81C"},
    "HOU": {"primary": "#03202F", "secondary": "#A71930"}, "IND": {"primary": "#002C5F", "secondary": "#A2AAAD"},
    "JAX": {"primary": "#006778", "secondary": "#D7A22A"}, "KC": {"primary": "#E31837", "secondary": "#FFB81C"},
    "LV": {"primary": "#000000", "secondary": "#A5ACAF"},  "LAC": {"primary": "#0080C6", "secondary": "#FFC20E"},
    "LAR": {"primary": "#003594", "secondary": "#FFA300"}, "MIA": {"primary": "#008E97", "secondary": "#FC4C02"},
    "MIN": {"primary": "#4F2683", "secondary": "#FFC62F"}, "NE": {"primary": "#002244", "secondary": "#C60C30"},
    "NO": {"primary": "#D3BC8D", "secondary": "#101820"},  "NYG": {"primary": "#0B2265", "secondary": "#A71930"},
    "NYJ": {"primary": "#125740", "secondary": "#000000"}, "PHI": {"primary": "#004C54", "secondary": "#A5ACAF"},
    "PIT": {"primary": "#FFB81C", "secondary": "#101820"}, "SF": {"primary": "#AA0000", "secondary": "#B3995D"},
    "SEA": {"primary": "#002244", "secondary": "#69BE28"}, "TB": {"primary": "#D50A0A", "secondary": "#0A0A08"},
    "TEN": {"primary": "#0C2340", "secondary": "#4B92DB"}, "WAS": {"primary": "#5A1414", "secondary": "#FFB612"},
}

TEAM_ABBR_TO_NAME = {
    "ARI": "Arizona Cardinals", "ATL": "Atlanta Falcons", "BAL": "Baltimore Ravens",
    "BUF": "Buffalo Bills", "CAR": "Carolina Panthers", "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals", "CLE": "Cleveland Browns", "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos", "DET": "Detroit Lions", "GB": "Green Bay Packers",
    "HOU": "Houston Texans", "IND": "Indianapolis Colts", "JAX": "Jacksonville Jaguars",
    "KC": "Kansas City Chiefs", "LV": "Las Vegas Raiders", "LAC": "Los Angeles Chargers",
    "LAR": "Los Angeles Rams", "MIA": "Miami Dolphins", "MIN": "Minnesota Vikings",
    "NE": "New England Patriots", "NO": "New Orleans Saints", "NYG": "New York Giants",
    "NYJ": "New York Jets", "PHI": "Philadelphia Eagles", "PIT": "Pittsburgh Steelers",
    "SF": "San Francisco 49ers", "SEA": "Seattle Seahawks", "TB": "Tampa Bay Buccaneers",
    "TEN": "Tennessee Titans", "WAS": "Washington Commanders"
}

NFL_STADIUM_COORDS = {
    "ARI": {"lat": 33.5277, "lon": -112.2626}, "ATL": {"lat": 33.7554, "lon": -84.4006},
    "BAL": {"lat": 39.2780, "lon": -76.6227},  "BUF": {"lat": 42.7738, "lon": -78.7870},
    "CAR": {"lat": 35.2258, "lon": -80.8528},  "CHI": {"lat": 41.8623, "lon": -87.6167},
    "CIN": {"lat": 39.0954, "lon": -84.5160},  "CLE": {"lat": 41.5061, "lon": -81.6995},
    "DAL": {"lat": 32.7473, "lon": -97.0945},  "DEN": {"lat": 39.7439, "lon": -105.0201},
    "DET": {"lat": 42.3400, "lon": -83.0456},  "GB":  {"lat": 44.5013, "lon": -88.0622},
    "HOU": {"lat": 29.6847, "lon": -95.4107},  "IND": {"lat": 39.7601, "lon": -86.1639},
    "JAX": {"lat": 30.3239, "lon": -81.6373},  "KC":  {"lat": 39.0489, "lon": -94.4839},
    "LV":  {"lat": 36.0909, "lon": -115.1833}, "LAC": {"lat": 33.9534, "lon": -118.3387},
    "LAR": {"lat": 33.9534, "lon": -118.3387}, "MIA": {"lat": 25.9580, "lon": -80.2389},
    "MIN": {"lat": 44.9735, "lon": -93.2575},  "NE":  {"lat": 42.0909, "lon": -71.2643},
    "NO":  {"lat": 29.9511, "lon": -90.0812},  "NYG": {"lat": 40.8128, "lon": -74.0745},
    "NYJ": {"lat": 40.8128, "lon": -74.0745},  "PHI": {"lat": 39.9008, "lon": -75.1675},
    "PIT": {"lat": 40.4468, "lon": -80.0158},  "SF":  {"lat": 37.4032, "lon": -121.9698},
    "SEA": {"lat": 47.5952, "lon": -122.3316}, "TB":  {"lat": 27.9759, "lon": -82.5033},
    "TEN": {"lat": 36.1665, "lon": -86.7713},  "WAS": {"lat": 38.9076, "lon": -76.8645}
}