"""
Python utils file to hold the main read / write helper functions. These will be called in any task
which reads / writes data so that the data is written directly to the USAR file storage locations
"""
# Importing packages
import pandas as pd
from google.colab import drive
drive.mount("/Rankings Data/")


# Main function to read data into the pipeline
def read_data(file_path: str, file_name: str) -> pd.DataFrame:
    return pd.read_csv(f"{file_path}/{file_name}")


read_data("Predictions/2021/Open", "pred_1v2_df.csv")
