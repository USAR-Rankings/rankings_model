"""
Main utils file to define helper functions for running DAG's
"""
# Importing packages as needed
import datetime


# Defining helper functions
# Function to generate the run_id when running a DAG
def generate_run_id() -> str:
    # Generating the string of current date and time
    return datetime.date.today().strftime("%B_%d_%Y_%I_%M%p")