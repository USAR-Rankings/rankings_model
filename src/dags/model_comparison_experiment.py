"""
Main python runner function to refresh the rankings model on the USAR website
"""
# Importing modules from the directory as needed
from rankings_model.src.utils.dag_runner_helpers import generate_run_id
from rankings_model.src.tasks.preprocessing import example_preprocess
# Importing packages needed
import subprocess
# Importing env variables
from dotenv import load_dotenv
load_dotenv()


# Defining main DAG id (should match the filename)
DAG_ID = "model_comparison_experiment"


# Main runner function for the DAG
def run(dag_id: str, run_id: str):
    print(f"{dag_id} DAG started")

    # Scraping any new data from online

    # Preprocessing tournament results
    example_preprocess.run(dag_id, run_id)

    # Fitting all individual models onto the preprocessed data. Each will output its predictions for
    # the desired test as defined in the config / params folder
    # PLACEHOLDER FOR ELO

    # PLACEHOLDER FOR MIXED MODEL
    subprocess.call("Rscript ../tasks/modelling/fit_models_1v2.R", shell=True)

    # Post-processing the predictions to get aggregated error metrics to compare all models

    # Creating any final visualizations

    print(f"{dag_id} DAG finished")
    return


# Run this DAG if this is the main file
if __name__ == "__main__":
    cur_run_id = generate_run_id()
    run(DAG_ID, cur_run_id)