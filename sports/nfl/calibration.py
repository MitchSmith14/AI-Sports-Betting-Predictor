# sports/nfl/calibration.py

import numpy as np
import pandas as pd

def calculate_brier_score(df_results, prob_col, actual_col):
    """
    Calculates the Brier Score: Mean Squared Error of probabilities.
    Perfect score is 0.0, a random 50/50 guess is 0.25.
    """
    valid_data = df_results[[prob_col, actual_col]].dropna()
    if valid_data.empty:
        return np.nan
        
    probabilities = valid_data[prob_col].to_numpy()
    outcomes = valid_data[actual_col].to_numpy()
    
    return float(np.mean((probabilities - outcomes) ** 2))

def calculate_log_loss(df_results, prob_col, actual_col):
    """
    Calculates Logarithmic Loss to heavily penalize overconfident incorrect guesses.
    """
    valid_data = df_results[[prob_col, actual_col]].dropna()
    if valid_data.empty:
        return np.nan
        
    # Clip probabilities to avoid log(0) or log(1) errors
    probabilities = np.clip(valid_data[prob_col].to_numpy(), 1e-15, 1 - 1e-15)
    outcomes = valid_data[actual_col].to_numpy()
    
    loss = -np.mean(outcomes * np.log(probabilities) + (1 - outcomes) * np.log(1 - probabilities))
    return float(loss)

def compute_reliability_curve(df_results, prob_col, actual_col, n_bins=5):
    """
    Groups predictions into probability bins to calculate empirical calibration.
    e.g., Bin 1: 0-20%, Bin 2: 20-40%, etc.
    """
    valid_data = df_results[[prob_col, actual_col]].dropna().copy()
    if valid_data.empty:
        return pd.DataFrame()
        
    # Segment data into uniform probability ranges
    bins = np.linspace(0, 1, n_bins + 1)
    valid_data["bin"] = pd.cut(valid_data[prob_col], bins=bins, labels=False, include_lowest=True)
    
    bin_summaries = []
    for i in range(n_bins):
        bin_subset = valid_data[valid_data["bin"] == i]
        if bin_subset.empty:
            continue
            
        mean_predicted = bin_subset[prob_col].mean()
        actual_win_rate = bin_subset[actual_col].mean()
        sample_size = len(bin_subset)
        
        bin_summaries.append({
            "bin_index": i,
            "bin_range": f"{int(bins[i]*100)}-{int(bins[i+1]*100)}%",
            "mean_predicted": mean_predicted,
            "actual_win_rate": actual_win_rate,
            "sample_size": sample_size,
            "calibration_delta": actual_win_rate - mean_predicted
        })
        
    return pd.DataFrame(bin_summaries)

def simulate_flat_betting_roi(df_results, prob_col, actual_col, min_edge=0.05, bookie_vig=-110):
    """
    Simulates placing a flat $100 bet on any prop where the model's implied probability
    creates a value edge greater than min_edge against standard Vegas vig lines.
    """
    valid_data = df_results[[prob_col, actual_col]].dropna().copy()
    if valid_data.empty:
        return {"roi": 0.0, "total_bets": 0, "net_units": 0.0}
        
    # Convert standard American odds to decimal payout factors
    if bookie_vig < 0:
        payout_factor = 100 / abs(bookie_vig) # e.g., 0.9091 for -110
        implied_market_prob = abs(bookie_vig) / (abs(bookie_vig) + 100) # e.g., 52.38%
    else:
        payout_factor = bookie_vig / 100
        implied_market_prob = 100 / (bookie_vig + 100)

    net_pnl = 0.0
    total_bets = 0
    
    for row in valid_data.itertuples():
        pred_prob = getattr(row, prob_col)
        actual_hit = getattr(row, actual_col)
        
        # Check for OVER value edge
        if pred_prob - implied_market_prob >= min_edge:
            total_bets += 1
            if actual_hit == 1:
                net_pnl += payout_factor  # Won the bet
            else:
                net_pnl -= 1.00          # Lost the bet
                
        # Check for UNDER value edge
        elif (1 - pred_prob) - (1 - implied_market_prob) >= min_edge:
            total_bets += 1
            if actual_hit == 0:
                net_pnl += payout_factor  # Won the UNDER
            else:
                net_pnl -= 1.00          # Lost the UNDER

    roi = (net_pnl / total_bets) if total_bets > 0 else 0.0
    return {
        "roi_pct": round(roi * 100, 2),
        "total_bets": total_bets,
        "net_units": round(net_pnl, 2)
    }