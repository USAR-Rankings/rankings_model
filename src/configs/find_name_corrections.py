# Setting up a dictionary with all the configs for the find_name_corrections DAG
#input column names
CONSTANTS = {
    "division": "Division",
    "play_round": "Round",
    "first_team": "Team A",
    "second_team": "Team B",
    "first_team_first_player": "Team A - Player 1",
    "first_team_second_player":  "Team A - Player 2",
    "second_team_first_player":  "Team B - Player 1",
    "second_team_second_player": "Team B - Player 2",
}
CFGS = {
    "data_input_path": "Tourney Results/Manual Downloads/",
    "data_output_path": "Tourney Results/Preprocessed/",
    "spelling_output_path": "Players/",
    "minimum_misspelling_confidence": 80,
    "interactive_spelling_correction": True,
    "str_cols_to_check": [
        'division',  # This means division names
        # 'team_names',  # This means team names
        'player_names',  # This means player names
    ],
}
