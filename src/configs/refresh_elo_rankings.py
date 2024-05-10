import os
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(script_dir, '..', '..'))

# Setting up a dictionary with all the configs for the find_name_corrections DAG
CFGS = {
    "top_level": parent_dir,
    "tourney_results_dir": os.path.join(parent_dir, "Tourney Results/"),
    "manual_downloads_dir": os.path.join(parent_dir, "Tourney Results/Manual Downloads/"),
    "data_output_path": os.path.join(parent_dir, "Tourney Results/Preprocessed/"),
    "spelling_corrections_path": os.path.join(parent_dir, "Players/"),
}
