"""
Main python runner function to refresh the rankings model on the USAR website
"""
# Importing modules from the directory as needed
from rankings_model.src.utils. dag_runner_helpers import generate_run_id
# Importing packages needed
# Importing env variables
from dotenv import load_dotenv
load_dotenv()


# Defining main DAG id (should match the filename)
DAG_ID = "refresh_rankings_model"


# Main runner function for the DAG
def run(dag_id: str, run_id: str):
    print(f"{dag_id} DAG started")

    # Scraping any new data from online

    # Preprocessing tournament results

    # Fitting the rankings model and producing the new predictions

    # Post-processing the predictions to get any stats needed

    # Publishing the predictions online

    # Uploading any generated files back to the cloud space

    print(f"{dag_id} DAG finished")
    return


# Run this DAG if this is the main file
if __name__ == "__main__":
    run_id = generate_run_id()
    run(DAG_ID, run_id)