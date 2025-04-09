import pandas as pd
import random as random
from itertools import chain
import warnings
warnings.filterwarnings(action='once')
from datetime import date,datetime
import sys
import os
import plotly.express as px

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
print(os.getcwd())  # Check the current working directory
from src.tasks.run_elo.core import *
from src.tasks.run_elo.helpers import test_elo_reaction
#from ..tasks.run_elo.core import *
#from ..tasks.run_elo.helpers import *
from src.configs.run_elo_open import (OPEN_P,WOMENS_P)

def main():
    params =[OPEN_P,WOMENS_P]  
    for param in params:  
        # Read in game data
        west_r=pd.read_csv(param["BASE_PATH"] + param["DATA_PATH"],encoding= 'unicode_escape').dropna(subset = ['mT1P1', 'mT1P2', 'mT2P1',"mT2P2"]).reset_index(drop=True)
        
        
        # Create tournemtnand dvisions combinations to play and teh order they occur in
        west_r_c=west_r[['tourney','Division',"Date"]].drop_duplicates().reset_index(drop=True)
        west_r_c["order"]=[list(dict.fromkeys(west_r_c["tourney"])).index(x)for x in west_r_c["tourney"]]
        
        

        # Add date data
        date_format = '%y-%m-%d'
        west_r_c["Date"]=[datetime.strptime(x, date_format)for x in west_r_c["Date"]]
    
        # Touranments to avereg elo for starting elo
        west_r_c["AVG_ELO"]=[True if x >param["NUMB_INITAL"]  else False for x in west_r_c["order"]]
        
        # Run elo model for whole timeframe
        test=ELO_Model(k_array= param["K_ARRAY"],dc=param["DC"],de=param["DE"],decay=param["DECAY"], decay_array=param["DECAY_ARRAY"],remove=param["REMOVE"],start_per=param["START_PER"])
        test.record_season(west_r,west_r_c)
        print("Brier Score: ", test.brier_score(mg=9))

        out_df = test.give_players_all()
        ranks = out_df[out_df["Date"] == out_df["Date"].max()].sort_values("elo", ascending=False)
        ranks["rank"] = np.arange(len(ranks))
        ranks.to_csv(param["BASE_PATH"] + "data/ranks_"+param["EXPORT_FILENAME"]+"_"+datetime.today().strftime('%Y-%m-%d')+".csv")

        # Export player results at all stages
        out_df.to_csv(param["BASE_PATH"] + "data/test_final_players_"+param["EXPORT_FILENAME"]+"_"+datetime.today().strftime('%Y-%m-%d')+".csv")
        # kieran_games = all_games[(all_games["tourney"] == "USAR25SOUTHEAST") & (
        #             (all_games["mT1P1"].str.contains("KIERAN ROSE")) | all_games["mT1P2"].str.contains("KIERAN ROSE") |
        #             all_games["mT2P1"].str.contains("KIERAN ROSE") | all_games["mT2P2"].str.contains("KIERAN ROSE"))]
        # Export games
        all_games = test.played_games
        all_games.to_csv(param["BASE_PATH"] + "data/test_all_games_"+param["EXPORT_FILENAME"]+"_"+ datetime.today().strftime('%Y-%m-%d')+".csv")

        track_players = ["COLEMAN EPPERSON", "RYDER RIVADENEYRA"]
        track_df = out_df[out_df["name"].isin(track_players)]
        fig = px.line(track_df, x="Date", y="elo", color="name")
        fig.write_image(param["BASE_PATH"] + "data/t