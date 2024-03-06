import pandas as pd
import streamlit as st
st.set_page_config(layout="wide")


# Creating the last updated date
st.write("Last Updated: March 6 2024")

# Creating the rankings versus player profile tabs
ranks, profiles = st.tabs(["Rankings", "Player Profiles"])

# Adding the ranks
with ranks:
    # Creating two columns for open and women
    open_col, womens_col = st.columns(2)

    # Adding the open data
    col_rename_dict = {"wins_365": "Wins",
                       "losses_365": "Losses",
                       "n_tourneys_365": "Tournaments",
                       "Avg_Partner_Score": "Avg Partner Rating",
                       "Avg_Opponent_Score": "Avg Opponent Rating",
                       "player_rank": "Rank",
                       }
    with open_col:
        open_ranks = pd.read_csv("./Predictions/2023/Open/player_ratings_1v2_df.csv").rename(columns=col_rename_dict)
        st.markdown("# Open Rankings")
        st.dataframe(open_ranks, hide_index=True)

    # Adding the women data
    with womens_col:
        women_ranks = pd.read_csv("./Predictions/2023/Women/player_ratings_1v2_df.csv").rename(columns=col_rename_dict)
        st.markdown("# Women Rankings")
        st.dataframe(women_ranks, hide_index=True)
