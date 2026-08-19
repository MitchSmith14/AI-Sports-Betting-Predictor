# shared/ui_components.py
import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

def render_team_card(title: str, name: str, team_abbr: str, primary_color: str, secondary_color: str, logo_url: str, headshot_url: str = None, subtitle: str = ""):
    """Universal card for any sport."""
    headshot_html = f'<img src="{headshot_url}" style="width:65px; height:65px; border-radius:50%; object-fit:cover; margin-right:14px; border: 2px solid {primary_color}; flex-shrink: 0;">' if headshot_url else ""
    html_code = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: linear-gradient(135deg, rgba(255,255,255,0.04) 0%, rgba(18,18,20,0.85) 100%); border: 1px solid rgba(255, 255, 255, 0.1); border-top: 5px solid {primary_color}; border-left: 3px solid {secondary_color}; border-radius: 10px; padding: 16px; margin-bottom: 8px; box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.35);">
        <div style="display: flex; align-items: center; justify-content: space-between;">
            <div style="display: flex; align-items: center;">
                {headshot_html}
                <div>
                    <span style="font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #94A3B8; font-weight: 600;">{title}</span>
                    <h3 style="margin: 2px 0 4px 0; color: #F8FAFC; font-size: 19px; font-weight: 700;">{name}</h3>
                    <p style="margin: 0; font-size: 13px; color: #CBD5E1;">
                        <span style="background-color: {primary_color}; color: #FFFFFF; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 11px;">{team_abbr}</span>
                        {f' &nbsp;•&nbsp; {subtitle}' if subtitle else ''}
                    </p>
                </div>
            </div>
            <div>
                <img src="{logo_url}" style="width: 50px; height: 50px; filter: drop-shadow(0px 2px 4px rgba(0,0,0,0.5));">
            </div>
        </div>
    </div>
    """
    components.html(html_code, height=115, scrolling=False)


def render_prop_row(df_sims: pd.DataFrame, stat1_col: str, stat1_name: str, stat1_line: float, stat1_odds: int, stat2_col: str, stat2_name: str, stat2_line: float, stat2_odds: int, context_metrics: dict = None):
    """
    Renders the side-by-side EV calculations, passing generic context metrics.
    context_metrics = {"Team Shots/G": 32.1, "Player Ice Time": 19.5}
    """
    mean1, median1 = df_sims[stat1_col].mean(), df_sims[stat1_col].median()
    win_prob1 = (df_sims[stat1_col] > stat1_line).mean()
    decimal_odds1 = ((100 / abs(stat1_odds)) + 1 if stat1_odds < 0 else (stat1_odds / 100) + 1)
    ev1 = (win_prob1 * (decimal_odds1 - 1)) - (1 - win_prob1)

    mean2 = df_sims[stat2_col].mean()
    win_prob2 = (df_sims[stat2_col] > stat2_line).mean()
    decimal_odds2 = ((100 / abs(stat2_odds)) + 1 if stat2_odds < 0 else (stat2_odds / 100) + 1)
    ev2 = (win_prob2 * (decimal_odds2 - 1)) - (1 - win_prob2)

    st.markdown("---")
    st.markdown(f"#### 📐 {stat1_name} vs. {stat2_name} Results")
    
    r1c1, r1c2, r1c3, r1c4 = st.columns(4)
    r1c1.metric(f"{stat1_name} Mean", f"{mean1:.1f}")
    r1c2.metric(f"OVER {stat1_line} Win Prob", f"{win_prob1:.1%}")
    r1c3.metric(f"{stat2_name} Mean", f"{mean2:.2f}")
    r1c4.metric(f"OVER {stat2_line} Win Prob", f"{win_prob2:.1%}")

    cl, c_yard, c_td = st.columns([1.2, 1.4, 1.4])
    with cl:
        st.write("**Context Averages**")
        if context_metrics:
            metrics_df = pd.DataFrame({
                "Metric": list(context_metrics.keys()) + [f"Sim {stat1_name}", f"Sim {stat2_name}"],
                "Average": list(context_metrics.values()) + [mean1, mean2]
            })
        else:
            metrics_df = pd.DataFrame({"Metric": [f"Sim {stat1_name}", f"Sim {stat2_name}"], "Average": [mean1, mean2]})
        st.dataframe(metrics_df.style.format({"Average": "{:.2f}"}), use_container_width=True)

    with c_yard:
        st.write(f"**{stat1_name} Distribution**")
        hist_values, bin_edges = np.histogram(df_sims[stat1_col], bins=25)
        st.bar_chart(pd.DataFrame({stat1_name: np.round(bin_edges[:-1], 1), "Frequency": hist_values}), x=stat1_name, y="Frequency")

    with c_td:
        st.write(f"**{stat2_name} Distribution**")
        td_counts = df_sims[stat2_col].value_counts().sort_index()
        st.bar_chart(pd.DataFrame({stat2_name: td_counts.index.astype(str), "Frequency": td_counts.values}), x=stat2_name, y="Frequency")