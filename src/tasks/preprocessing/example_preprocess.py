"""
This file serves as an example for how to read / write data in python and the general structure to follow in a given
task
"""
# Reading in anything needed from this module
from rankings_model.src.utils.read_write import read_data, read_all_data_in_dir, write_data
from rankings_model.src.configs.constants import (USAR_YOUTH_MEMBERSHIP_FILE,
                                                  NAME_CORRECTIONS,
                                                  )
# Reading in libraries
import os
import pandas as pd


# Defining the task ID
TASK_ID = "example_preprocess"


# Defining the helper functions
def example_helper(all_dfs: list) -> pd.DataFrame:
    return pd.concat(all_dfs)


# Defining the main run function
def run(dag_id: str, run_id: str) -> None:
    print(f"Starting {TASK_ID} task")

    # Reading in any data needed
    name_corrections = read_data([os.environ['input_dir'],
                                  "Players",
                                  ],
                                 NAME_CORRECTIONS
                                 )
    usar_members = read_data([os.environ['input_dir'],
                              "Players",
                              ],
                             USAR_YOUTH_MEMBERSHIP_FILE
                             )
    tourney_data_one = read_all_data_in_dir([os.environ['tourney_data_dir'],
                                             "Manual Downloads",
                                             ],
                                            )
    tourney_data_two = read_all_data_in_dir([os.environ['tourney_data_dir'],
                                             ],
                                            )

    # Performing the preprocessing
    all_tourney_data = example_helper([tourney_data_one, tourney_data_two])

    # Writing out finalized data
    write_data([os.environ["output_dir"],
                f"{dag_id}_{run_id}",
                f"{TASK_ID}",
                ],
               "preprocessed_tourney_data.csv",
               all_tourney_data
               )

    print(f"{TASK_ID} task completed")
    return None
