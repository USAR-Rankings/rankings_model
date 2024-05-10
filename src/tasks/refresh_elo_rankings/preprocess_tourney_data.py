# importing necessary modules
import pandas as pd
import os
from datetime import timedelta
from src.configs.refresh_elo_rankings import CFGS

TASK_ID = "preprocess_tourney_data"


def read_csv_if_exists(directory, filename):
    """
    Read a CSV file into a pandas DataFrame from a specific directory and file name if it exists.

    Parameters:
        directory (str): The name of the directory in which the CSV file is.
        filename (str): The name of the CSV file.

    Returns:
        pandas DataFrame or None: The DataFrame containing the data from the CSV file if the file exists,
                                  otherwise None.
    """
    # Check if the file exists in the specified directory
    filepath = os.path.join(directory, filename)
    if os.path.exists(filepath):
        # Read the CSV file into a DataFrame
        df = pd.read_csv(filepath)
        return df
    else:
        # If the file does not exist, return None
        return None


# creating a function to do some initial data preprocessing
def run():
    print(f"Starting Task: {TASK_ID}")

    """
    Step 1: Reading in the data
    """
    print("Reading in data")
    # Reading in the tourney list
    name_corrections = read_csv_if_exists(CFGS['spelling_corrections_path'], "all_name_corrections.csv")

    # Reading in the spelling corrections (in the top directory)
    tourney_list = read_csv_if_exists(CFGS['top_level'], "Tourney List.csv")

    """
    Step 2: Preprocessing
    """
    # Reading manual downloads
    manual_downloads_files = [f.replace(".csv", "") for f in os.listdir(CFGS['manual_downloads_dir']) if
                              f.endswith('.csv')]
    manual_downloads = pd.DataFrame({'Fwango File Title': manual_downloads_files, 'downloaded': True})

    # Loading the tourney list and updating it
    tourney_list['Date'] = pd.to_datetime(tourney_list['Date'], format='%m/%d/%Y')
    max_date = tourney_list['Date'].max()
    new_row = pd.DataFrame({'tourney': ['END OF SEASON'], 'Date': [max_date + timedelta(days=7)]})
    tourney_list = pd.concat([tourney_list, new_row], ignore_index=True)

    # Determine the tournament status
    tourney_files = [f.replace(".csv", "") for f in os.listdir(CFGS['tourney_results_dir']) if
                     f.endswith('.csv') and f != 'Manual Downloads']
    tourney_files_df = pd.DataFrame({'URL.identifier': map(str.upper, tourney_files), 'complete': True})

    tourney_status = pd.merge(tourney_list, tourney_files_df, how='left', left_on='tourney', right_on='URL.identifier')
    tourney_status = pd.merge(tourney_status, manual_downloads, on='Fwango File Title')

    # Filter to-do list
    to_do_list = tourney_status[(tourney_status['downloaded'] == True) &
                                ~(tourney_status['complete'].isna())]

    # Process each tournament file
    for index, row in to_do_list.iterrows():
        file_name = os.path.join(CFGS['manual_downloads_dir'], f"{row['Fwango File Title']}.csv")
        print('\n', file_name)
        downloaded_data = pd.read_csv(file_name)
        downloaded_data['og_order'] = range(1, len(downloaded_data) + 1)
        downloaded_data['tourney'] = row['tourney'].lower()

        # Denoting pool play in round col
        downloaded_data.loc[downloaded_data["Round"].isin([str(x) for x in range(1, 51)]), "Round"] = "Pool"

        # Renaming some columns
        downloaded_data = downloaded_data.rename(columns={"Team A": "Team1",
                                                          "Team B": "Team2",
                                                          "Team A - Player 1": "T1P1",
                                                          "Team A - Player 2": "T1P2",
                                                          "Team B - Player 1": "T2P1",
                                                          "Team B - Player 2": "T2P2",
                                                          })

        # Pivoting the score of each of the three games into rows instead of columns and retain which game it was
        keep_cols = ["og_order", "tourney", "Division", "Round", "Team1", "Team2", "T1P1", "T1P2", "T2P1", "T2P2"]
        renamed_cols = ["t1score", "t2score"]
        all_dfs = []
        for i in range(1, 4):
            # Keeping only the desired columns and renaming the score cols
            game_cols = [f"Game {i} - Score team A", f"Game {i} - Score team B"]
            rename_dict = {}
            for orig_col, new_col_name in zip(game_cols, renamed_cols):
                rename_dict[orig_col] = new_col_name
            cur_games = downloaded_data[keep_cols + game_cols].rename(columns=rename_dict)
            all_dfs.append(cur_games)
        # Appending together
        full_df = pd.concat(all_dfs)
        # Dropping matches with NA scores
        full_df = full_df.dropna(subset=['t1score', 't2score'])
        # Ordering by the game number
        full_df = full_df.sort_values('og_order')
        # Dropping the game number
        full_df = full_df.drop(columns=['og_order'])

        # Fixing spelling mistakes for names
        player_name_map = name_corrections[name_corrections["Column"] == "player_names"][
            ["OldName", "NewName"]].set_index("OldName").to_dict()
        name_cols = ["T1P1", "T1P2", "T2P1", "T2P2"]
        full_name_replace_dict = {}
        for col in name_cols:
            full_name_replace_dict[col] = player_name_map
        full_df = full_df.replace(full_name_replace_dict)

        # Now fixing for division
        division_map = name_corrections[name_corrections["Column"] == "division"][["OldName", "NewName"]].set_index(
            "OldName").to_dict()
        full_df = full_df.replace({"Division": division_map})

        """
        Step 4: Saving the output
        """
        output_file_path = os.path.join(CFGS['tourney_results_dir'], row['tourney'].lower() + ".csv")
        print(f"Saving preprocessed: {output_file_path}")
        full_df.to_csv(output_file_path, index=False)

    print(f"Completed Task: {TASK_ID}")
    return
