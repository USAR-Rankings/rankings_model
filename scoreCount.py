import pandas as pd
import numpy as np
from pathlib import Path

# Functions to collect game data from a particular year and store in a dataframe
def read_game_data(year):
  tournaments = pd.read_csv("Tourney List.csv")
  tournaments = tournaments[["Year", "Date", "Scraped?", "Fwango File Title"]]
  tournaments = tournaments.loc[tournaments["Year"] == 2026]
  print(tournaments)

  game_dfs = []
  base_game_path = Path(".") / "Tourney Results"

  for _, tournament in tournaments.iterrows():

    # Handle normal case of manually downloaded game data
    if tournament["Scraped?"] == "Manual Download":

      # Get full path filename for tournament game data
      game_file = base_game_path / "Manual Downloads" / (tournament["Fwango File Title"] + ".csv")

      # Read the games
      games = pd.read_csv(game_file)

      # Add tournament metadata to each game
      games["Year"] = tournament["Year"]
      games["Date"] = tournament["Date"]
      games["Game num"] = 1

      game_dfs.append(games)

    # Handle differently formatted data
    # elif tournament["Scraped?"] == "X":

      # # Get full path filename for tournament game data
      # game_file = base_game_path / (tournament["URL identifier"] + ".csv")

      # # Read the games
      # games = pd.read_csv(game_file)

      # # Add tournament metadata to each game
      # games["Year"] = tournament["Year"]
      # games["Date"] = tournament["Date"]
      # games["Game num"] = 1

      # game_dfs.append(games)


    # else:
      # game_file = base_game_path + tournament["Fwango File Title"] + ".csv"

    
    # Combine all games into single df and clean-up unnecessary columns
    all_games = pd.concat(game_dfs, ignore_index=True)
    all_games = all_games[["Year", "Date", "Stage", "Division", "Round", "Match format", "Game num",
                           "Game 1 - Score team A", "Game 1 - Score team B",
                           "Game 2 - Score team A", "Game 2 - Score team B",
                           "Game 3 - Score team A", "Game 3 - Score team B"]]

  
  # print(all_games)
  # all_games.to_csv("./data/game_data_" + str(year) + ".csv")


  # Break out Best of 3 series into individual games list
  all_games_list = []
  for _, match in all_games.iterrows():

    all_games_list.append(match.to_dict())

    if match["Match format"] == "Best of 3":
      g2_A = match["Game 2 - Score team A"]
      g2_B = match["Game 2 - Score team B"]
      g3_A = match["Game 3 - Score team A"]
      g3_B = match["Game 3 - Score team B"]

      if pd.notna(g2_A) and pd.notna(g2_B):
        g2 = match.copy()
        g2["Game num"] = 2
        g2["Game 1 - Score team A"] = g2_A
        g2["Game 1 - Score team B"] = g2_B
        all_games_list.append(g2.to_dict())

      if pd.notna(g3_A) and pd.notna(g3_B):
        g3 = match.copy()
        g3["Game num"] = 3
        g3["Game 1 - Score team A"] = g3_A
        g3["Game 1 - Score team B"] = g3_B
        all_games_list.append(g3.to_dict())

  all_games_list_df = pd.DataFrame(all_games_list)

  all_games_list_df = all_games_list_df.drop(
                      columns=["Game 2 - Score team A", "Game 2 - Score team B",
                               "Game 3 - Score team A", "Game 3 - Score team B"])
  
  all_games_list_df = all_games_list_df.rename(
                      columns={"Game 1 - Score team A": "Score A",
                               "Game 1 - Score team B": "Score B"})

  print(all_games_list_df)
  all_games_list_df.to_csv("./game_data_" + str(year) + ".csv")

  count_scores(all_games_list_df)

# Function to categorize and count scores
def count_scores(df):

  # Regulation games (winner scored exactly 21)
  regulation_21 = df[
      ((df["Score A"] == 21) & (df["Score B"].between(0, 19))) |
      ((df["Score B"] == 21) & (df["Score A"].between(0, 19)))
  ]

  # Regulation games played to a score >10 and <21 (this will include overtime games that do not reach 21)
  regulation_other = df[
      (((df["Score A"].between(11, 20)) & (df["Score B"].between(0, df["Score A"] - 1))) |
       ((df["Score B"].between(11, 20)) & (df["Score A"].between(0, df["Score B"] - 1)))) &
      (df["Score A"] != df["Score B"])
  ]

  # Overtime games (Win-by-2 or hard cap >= 21)
  overtime = df[
      ((df["Score A"] > 21) & ((df["Score B"] == df["Score A"] - 2) | (df["Score B"] == df["Score A"] - 1))) |
      ((df["Score B"] > 21) & ((df["Score A"] == df["Score B"] - 2) | (df["Score A"] == df["Score B"] - 1))) |
      ((df["Score A"] == 21) & (df["Score B"] == 20)) |
      ((df["Score B"] == 21) & (df["Score A"] == 20))
  ]

  # Forfeit (-2 - 0)
  forfeit = df[
      ((df["Score A"] == -2) & (df["Score B"] == 0)) |
      ((df["Score B"] == -2) & (df["Score A"] == 0))
  ]

  # "Injury Forfeit" (-1 - 0)
  injury_forfeit = df[
      ((df["Score A"] == -1) & (df["Score B"] == 0)) |
      ((df["Score B"] == -1) & (df["Score A"] == 0))
  ]

  # Not enough info (1-0 or 1-1 or 2-0 or 2-1)
  not_enough_info = df[
      ((df["Score A"].isin([0, 1, 2])) & (df["Score B"].isin([0, 1, 2])))
  ]

  nan_score = df[df["Score A"].isna() | df["Score B"].isna()]

  # Compile all other scores into a df for analysis
  all_others = df.copy()
  all_others = all_others.drop(regulation_21.index)
  all_others = all_others.drop(regulation_other.index)
  all_others = all_others.drop(overtime.index)
  all_others = all_others.drop(forfeit.index)
  all_others = all_others.drop(injury_forfeit.index)
  all_others = all_others.drop(not_enough_info.index)
  all_others = all_others.drop(nan_score.index)

  # Add score counts to a separate df/csv for export
  score_counts = [{"type": "regulation_21",    "count": len(regulation_21)},
                  {"type": "regulation_other", "count": len(regulation_other)},
                  {"type": "overtime",         "count": len(overtime)},
                  {"type": "forfeit",          "count": len(forfeit)},
                  {"type": "injury_forfeit",   "count": len(injury_forfeit)},
                  {"type": "not_enough_info",  "count": len(not_enough_info)},
                  {"type": "all_others",       "count": len(all_others)}]

  score_counts_df = pd.DataFrame(score_counts)
  print(score_counts_df)
  print(all_others)
  score_counts_df.to_csv("./game_score_data_2026.csv")

read_game_data(2026)