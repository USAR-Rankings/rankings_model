"""
Python utils file to hold the main read / write helper functions. These will be called in any task
which reads / writes data so that the data is written directly to the USAR file storage locations
"""
# Importing packages
import pandas as pd
import glob
import os


# Main function to read data into the pipeline
def read_all_data_in_dir(file_path_list: list) -> list:
    # Creating the full file path from the list provided
    full_path = "/".join(file_path_list)
    csv_files = glob.glob(os.path.join(full_path, "*.csv"))
    # loop over the list of csv files
    all_dfs = []
    for f in csv_files:
        # read the csv file and append to list
        all_dfs.append(pd.read_csv(f))
    return pd.concat(all_dfs)


def read_data(file_path_list: list, file_name: str) -> pd.DataFrame:
    # Creating the full file path from the list provided
    full_path = "/".join(file_path_list)
    return pd.read_csv(f"{full_path}/{file_name}")


def write_data(file_path_list: list, file_name: str, df: pd.DataFrame) -> None:
    # Creating the full file path from the list provided
    full_path = "/".join(file_path_list)
    # Checking if path exists, and if not creating it
    if not os.path.exists(full_path):
        os.makedirs(full_path)
    # Writing the file out
    df.to_csv(f"{full_path}/{file_name}")
    return None
