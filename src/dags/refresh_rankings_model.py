"""
Main python runner function to refresh the rankings model on the USAR website
"""
# Importing modules from the directory as needed
from src.utils.dag_runner_helpers import generate_run_id
from src.tasks.preprocessing import example_preprocess
# Importing packages needed
import subprocess
# Importing env variables
from dotenv import load_dotenv

load_dotenv()
import os

# Defining main DAG id (should match the filename)
DAG_ID = "refresh_rankings_model"


# Main runner function for the DAG
def run(dag_id: str, run_id: str):
    print(f"{dag_id} DAG started")

    # Scraping any new data from online

    # Preprocessing tournament results
    example_preprocess.run(dag_id, run_id)

    # Fitting the rankings model and producing the new predictions
    r_output = subprocess.run(["Rscript",
                               f"{os.environ['project_directory']}/src/tasks/modelling/fit_models_1v2.R"],
                              )

    # Post-processing the predictions to get any stats needed

    # Publishing the predictions online

    print(f"{dag_id} DAG finished")
    return


# Run this DAG if this is the main file
if __name__ == "__main__":
    cur_run_id = generate_run_id()
    run(DAG_ID, cur_run_id)
